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

def update_pages(confluence, email, api_token, base_url, target_space, pages, patterns, limit=0, dry_run=True):
    count = 0
    updated_pages = []
    ids_used = []
    divider = 50
    for page in pages:
        if count % divider == 0:
            print(f"Checking pages ({count}-{count+divider}) / ({len(pages)}) ...")
        
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
            should_update = not dry_run and (limit == 0) or (len(updated_pages) < limit)
            if should_update:
                update_confluence_page_v2(base_url, email, api_token, page_id, title, body)
                # confluence.update_page(
                #     page_id=page_id,
                #     title=title,
                #     body=body,
                #     type='page',
                #     representation='storage'
                # )
                page_url = f"{base_url}/spaces/{target_space}/pages/{page_id}"
                updated_pages.append({
                    "title": title,
                    "url": page_url
                })

            print(f"{'Did not update' if not should_update else 'Updated'} page: {title}")

        count += 1
    return count, updated_pages