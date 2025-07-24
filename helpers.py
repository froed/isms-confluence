import requests
from requests.auth import HTTPBasicAuth
import json
import os
import re
from datetime import datetime

HTML_ESCAPE_MAP = {
    'ä': '&auml;',
    'ö': '&ouml;',
    'ü': '&uuml;',
    'Ä': '&Auml;',
    'Ö': '&Ouml;',
    'Ü': '&Uuml;',
    'ß': '&szlig;',
}

def escape_umlauts(text):
    """Wandelt deutsche Umlaute in HTML-Entities um."""
    for char, entity in HTML_ESCAPE_MAP.items():
        text = text.replace(char, entity)
    return text

def get_content_property(confluence, page_id, prop_key):
    return confluence.get(f"/rest/api/content/{page_id}/property/{prop_key}")

def get_page_version(confluence, page_id):
    page = confluence.get(f"/rest/api/content/{page_id}?expand=version")
    return page['version']['number']

def get_all_pages_from_space(confluence, target_space, pagination=100):
    pages = []
    count = 0
    while True:
        print(f"Getting all pages from space: {target_space} ({len(pages)}) ...")
        results = confluence.get_all_pages_from_space(target_space, start=count, limit=pagination)
        if not results:
            break
        pages.extend(results)
        count += pagination
    return pages

def get_unique_pages_from_space(confluence, target_space, pagination=100):
    pages = []
    seen_ids = set()
    count = 0

    while True:
        print(f"Getting all pages from space ({len(pages)}) ...")
        results = confluence.get_all_pages_from_space(target_space, start=count, limit=pagination)
        if not results:
            break

        for page in results:
            page_id = page.get('id')
            if page_id and page_id not in seen_ids:
                pages.append(page)
                seen_ids.add(page_id)

        count += pagination

    return pages

def download_page_body(confluence, page_id):
    content = confluence.get_page_by_id(page_id, expand='body.storage,version')
    body = content['body']['storage']['value']
    return body

def update_confluence_page_v2(base_url, email, api_token, page_id, title, body):
    auth = HTTPBasicAuth(email, api_token)

    # 1. Get current version
    version_resp = requests.get(
        f'{base_url}/api/v2/pages/{page_id}',
        auth=auth,
        headers={'Accept': 'application/json'}
    )
    version_resp.raise_for_status()
    current_version = version_resp.json()['version']['number']

    # 2. Update the page
    payload = {
        "id": page_id,
        "status": "current",
        "title": title,
        "body": {
            "representation": "storage",
            "value": body
        },
        "version": {
            "number": current_version + 1
        }
    }

    update_resp = requests.put(
        f'{base_url}/api/v2/pages/{page_id}',
        auth=auth,
        headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        },
        json=payload
    )
    update_resp.raise_for_status()

    return update_resp.json()

def emit_page_body(confluence, page_id):
        content = confluence.get_page_by_id(page_id, expand='body.storage')
        body = content['body']['storage']['value']
        return body

def find_pages_with_pattern(confluence, base_url, target_space, pages, patterns, negate=False):
    """
    Search for patterns in a list of Confluence pages and return matching page URLs.

    :param confluence: Confluence API client
    :param base_url: Your Confluence base URL (e.g., https://your-domain.atlassian.net/wiki)
    :param target_space: The space key (used to build the URL)
    :param pages: List of page dicts with 'id' and 'title'
    :param patterns: List of dicts with 'old_pattern' strings to search for
    :param patterns: Emits pages that do NOT match the pattern instead
    :return: List of dicts with 'title' and 'url' for pages that contain any pattern
    """
    matched_pages = []
    check_count = 0
    divider = 100

    for page in pages:

        if check_count % divider == 0:
            print(f"Checking pages ({check_count}/{len(pages)}) ...")

        page_id = page['id']
        title = page['title']

        # Get current page content
        content = confluence.get_page_by_id(page_id, expand='body.storage')
        body = content['body']['storage']['value']
        has_match = False

        for pattern in patterns:
            old_pattern = pattern['old_pattern']
            if old_pattern in body:
                page_url = f"{base_url}/spaces/{target_space}/pages/{page_id}"
                if not negate:
                    matched_pages.append({
                        "title": title,
                        "url": page_url
                    })
                has_match = True
                break  # Stop after first match

        if not has_match and negate:
            matched_pages.append({
                "title": title,
                "url": page_url
            })            

        check_count += 1

    return matched_pages

def update_pages(confluence, email, api_token, base_url, target_space, pages, patterns, limit=0, dry_run=True):
    check_count = 0
    updated_pages = []
    ids_used = []
    divider = 100
    for page in pages:
        if check_count % divider == 0:
            print(f"Checking pages ({check_count}/{len(pages)}) ...")
        
        page_id = page['id']
        if page_id in ids_used:
            continue
        ids_used.append(page_id)
        title = page['title']

        content = confluence.get_page_by_id(page_id, expand='body.storage,version')
        body = content['body']['storage']['value']
        action = False
        
        for pattern in patterns:
            old_pattern = pattern['old_pattern']
            new_pattern = pattern['new_pattern']
            if old_pattern in body:
                action = True
                body = body.replace(old_pattern, new_pattern)
            
        if action:
            should_update = not dry_run and ( (limit == 0) or (len(updated_pages) < limit) )
            if should_update:
                update_confluence_page_v2(base_url, email, api_token, page_id, title, body)
                page_url = f"{base_url}/spaces/{target_space}/pages/{page_id}"
                updated_pages.append({
                    "title": title,
                    "url": page_url
                })

            print(f"{'Did not update' if not should_update else 'Updated'} page: {title}")

        check_count += 1
    return {"checked_count":check_count, "updated pages": updated_pages}

def widen_thin_pages(base_url, email, api_token, pages, target_space, dry_run=True):
    """
    Directly uses REST API to find and widen pages with fixed-width layout.

    :param base_url: Base Confluence URL (e.g., https://your-domain.atlassian.net/wiki)
    :param email: Email for HTTP basic auth
    :param api_token: API token for authentication
    :param pages: List of page dicts with at least 'id' and 'title'
    :param target_space: Space key, used to construct page URLs
    :param dry_run: If True, no changes will be made
    :return: Summary dict with checked and widened pages
    """
    auth = HTTPBasicAuth(email, api_token)
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }

    updated_pages = []
    total = len(pages)

    for i, page in enumerate(pages):
        if i % 100 == 0:
            print(f"Progress: Checked {i} of {total} pages...")

        page_id = page.get("id")
        title = page.get("title", "(Untitled)")
        page_url = f"{base_url}/spaces/{target_space}/pages/{page_id}"

        # Step 1: Get current layout property
        prop_url = f"{base_url}/api/v2/pages/{page_id}/properties"

        needs_full_width = []

        try:
            
            response = requests.get(prop_url, auth=auth, headers=headers)
            if response.status_code == 404:
                print(f"404 in url: {prop_url}")
                continue
            response.raise_for_status()
            data = response.json()
            for result in data["results"]:
                version = result["version"]
                if result["key"] == "content-appearance-published" or result["key"] == "content-appearance-draft":
                    if result["value"] != "full-width":
                        needs_full_width.append({
                            "key": result["key"],
                            "number": version["number"],
                            "id": result["id"]
                        })
        except Exception as e:
            print(f"Error fetching layout for page {title} ({page_id}): {e}")
            continue


        once = True
        # Step 2: If it's fixed-width, update it to full-width
        for item in needs_full_width:
            print(f"Found fixed-width layout: {title} — {page_url} | {item["key"]}")
            if not dry_run:
                payload = {
                    "key": item["key"],
                    "value": "full-width",
                    "version": {
                        "number": item["number"]+1,
                        "message": "Making it full-width again."
                    }
                }

                try:
                    put_resp = requests.put(f"{prop_url}/{item['id']}", auth=auth, headers=headers, json=payload)
                    put_resp.raise_for_status()
                    if once:
                        updated_pages.append({
                            "title": title,
                            "url": page_url
                        })
                    once = False
                except Exception as e:
                    print(f"❌ Failed to update page {title} | {item["key"]}: {e}")
            else:
                    if once:
                        updated_pages.append({
                            "title": title,
                            "url": page_url,
                            "note": "Dry run – not updated"
                        })
                    once = False

    print(f"\n✅ Completed: {len(updated_pages)} pages set to full-width.")
    return {
        "checked": total,
        "widened": updated_pages
    }

def cache(key: str, miss_fn, use=True, cache_dir='cache'):
    """
    Cache function to store/retrieve JSON-serializable objects.

    Args:
        key (str): Identifier for the cache.
        miss_fn (callable): Function (usually a lambda) to call if cache is missing or use=False.
        use (bool): Whether to use the cache or not. If False, always refresh using miss_fn.
        cache_dir (str): Directory to store cache files.

    Returns:
        Cached data (loaded from cache or result of miss_fn).
    """
    os.makedirs(cache_dir, exist_ok=True)
    filename = os.path.join(cache_dir, f'{key}.json')

    if use and os.path.exists(filename):
        with open(filename, 'r') as f:
            return json.load(f)
    else:
        result = miss_fn()
        with open(filename, 'w') as f:
            json.dump(result, f, indent=2)
        return result
    
def get_last_modified(confluence, page_id):
    """
    Returns the last modified timestamp of a Confluence page.

    Args:
        confluence: Confluence API client object.
        page_id (str or int): The ID of the Confluence page.

    Returns:
        str: ISO 8601 formatted timestamp of last modification.
    """
    page = confluence.get_page_by_id(page_id, expand='version')
    if not page or 'version' not in page:
        raise ValueError(f"Could not retrieve page or version info for page_id={page_id}")
    
    return page['version']['when']

import re
from datetime import datetime

def update_freigabe_date_if_needed(confluence, page_id, dry_run=False):
    """
    Updates the 'Freigabe am' date in the page body if the page was modified after that date.

    Args:
        confluence: Confluence API client.
        page_id (str or int): ID of the page to check and possibly update.
        dry_run (bool): If True, show what would be updated without actually modifying the page.

    Returns:
        bool: True if update is (or would be) needed.
        dict: Info with old date, modified date, and new date (if applicable).
    """
    page = confluence.get_page_by_id(page_id, expand='body.storage,version')
    if not page:
        raise ValueError(f"Page not found: {page_id}")

    html = page['body']['storage']['value']
    modified_str = page['version']['when']
    modified_dt = datetime.fromisoformat(modified_str.rstrip('Z'))

    # Look for Freigabe am datetime
    match = re.search(r'(<strong>Freigabe am</strong>.*?<time datetime=")(\d{4}-\d{2}-\d{2})(")', html, re.DOTALL)
    if not match:
        return False, {
            "updated": False,
            "reason": "not found",
        }

    freigabe_str = match.group(2)
    freigabe_dt = datetime.strptime(freigabe_str, "%Y-%m-%d")

    if modified_dt.date() <= freigabe_dt.date():
        return False, {
            "updated": False,
            "reason": "Last modified is not newer than 'Freigabe am'",
            "freigabe_am": freigabe_dt.isoformat(),
            "last_modified": modified_dt.isoformat()
        }

    today_str = datetime.today().strftime("%Y-%m-%d")
    updated_html = html[:match.start(2)] + today_str + html[match.end(2):]

    if dry_run:
        return True, {
            "updated": False,
            "dry_run": True,
            "would_update": True,
            "old_date": freigabe_str,
            "new_date": today_str,
            "last_modified": modified_dt.isoformat()
        }

    # Perform the update
    confluence.update_page(
        page_id=page_id,
        title=page['title'],
        body=updated_html,
        minor_edit=True
    )

    return True, {
        "updated": True,
        "dry_run": False,
        "old_date": freigabe_str,
        "new_date": today_str,
        "last_modified": modified_dt.isoformat()
    }

def make_page_url(space, id):
    return f"https://quantrefy.atlassian.net/wiki/spaces/{space}/pages/{id}"

def update_freigabe_am(confluence, base_url, email, api_token, target_space, pages, dry_run):
    for page in pages:
        updated, info = update_freigabe_date_if_needed(confluence, page["id"], dry_run)
        if updated:
            print(f"Updated page: {make_page_url(target_space, page["id"])}, info: {info}")
            widen_thin_pages(base_url, email, api_token, [{"id": page["id"]}], target_space, dry_run)
            