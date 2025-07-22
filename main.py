from atlassian import Confluence
from helpers import *

import json

def read_json(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)  # parse JSON content
    return data

config=read_json("config.json")
username = config.get("username")
password = config.get("password")
confluence_base_url = config.get("confluence_base_url")

# Verbindung zu Confluence
confluence = Confluence(
    url=confluence_base_url,
    username=username,
    password=password
)

ISMS_SPACE = 'isms2025'
ISMS_SPACE_PUBLIC = 'ISMSpublic'

# config
target_space = ISMS_SPACE

dry_run = False
update_limit = 0
limit = 50

patterns = [
    {
        'old_pattern': f'UPDATEME',
        'new_pattern': f'FOUNDYOU'
    }
]

#pages = get_all_pages_from_space(confluence, ISMS_SPACE)
pages = [
    {
        "id":"1087149764",
        "title":"Aufgabenbericht"
    }
]

def update_pages(confluence, email, api_token, base_url, target_space, pages, patterns, limit=0, dry_run=True):
    check_count = 0
    updated_pages = []
    ids_used = []
    divider = 50
    for page in pages:
        if check_count % divider == 0:
            print(f"Checking pages ({check_count}-{check_count+divider}) / ({len(pages)}) ...")
        
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

        check_count += 1
    return {"checked_count":check_count, "updated pages": updated_pages}

result = update_pages(confluence=confluence, email=username, api_token=password, base_url=confluence_base_url, target_space=ISMS_SPACE, pages=pages, patterns=patterns, limit=1, dry_run=dry_run)

print(result)