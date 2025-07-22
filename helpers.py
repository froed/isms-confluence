import requests
from requests.auth import HTTPBasicAuth

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

def get_all_pages_from_space(confluence, target_space, pagination=50):
    pages = []
    count = 0
    while True:
        print(f"Getting all pages from space ({len(pages)}) ...")
        results = confluence.get_all_pages_from_space(target_space, start=count, limit=pagination)
        if not results:
            break
        pages.extend(results)
        count += pagination
    return pages

def get_unique_pages_from_space(confluence, target_space, pagination=50):
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

def find_pages_with_pattern(confluence, base_url, target_space, pages, patterns):
    """
    Search for patterns in a list of Confluence pages and return matching page URLs.

    :param confluence: Confluence API client
    :param base_url: Your Confluence base URL (e.g., https://your-domain.atlassian.net/wiki)
    :param target_space: The space key (used to build the URL)
    :param pages: List of page dicts with 'id' and 'title'
    :param patterns: List of dicts with 'old_pattern' strings to search for
    :return: List of dicts with 'title' and 'url' for pages that contain any pattern
    """
    matched_pages = []
    check_count = 0
    divider = 50

    for page in pages:

        if check_count % divider == 0:
            print(f"Checking pages ({check_count}/{len(pages)}) ...")

        page_id = page['id']
        title = page['title']

        # Get current page content
        content = confluence.get_page_by_id(page_id, expand='body.storage')
        body = content['body']['storage']['value']

        for pattern in patterns:
            old_pattern = pattern['old_pattern']
            if old_pattern in body:
                page_url = f"{base_url}/spaces/{target_space}/pages/{page_id}"
                matched_pages.append({
                    "title": title,
                    "url": page_url
                })
                break  # Stop after first match

        check_count += 1

    return matched_pages

def update_pages(confluence, email, api_token, base_url, target_space, pages, patterns, limit=0, dry_run=True):
    check_count = 0
    updated_pages = []
    ids_used = []
    divider = 50
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