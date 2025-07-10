from atlassian import Confluence

import re
import json
import html

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

def get_content_property(page_id, prop_key):
    return confluence.get(f"/rest/api/content/{page_id}/property/{prop_key}")

def get_page_version(page_id):
    page = confluence.get(f"/rest/api/content/{page_id}?expand=version")
    return page['version']['number']

def set_full_width_property(page_id):
    prop_key = "content-appearance-published"
    value = "full-width"

    try:
        # Hole die Property (wenn vorhanden)
        prop = get_content_property(page_id, prop_key)

        # Wenn vorhanden: Property-Version hochzählen
        prop_version = prop['version']['number'] + 1
        print(f"Updating property for page {page_id}, prop version {prop_version}")

        data = {
            "key": prop_key,
            "value": value,
            "version": {"number": prop_version}
        }

        # PUT für Update
        endpoint = f"/rest/api/content/{page_id}/property/{prop_key}"
        response = confluence.put(endpoint, data=data)

    except Exception as e:
        # Property existiert vermutlich nicht → POST als Fallback
        print(f"Creating new property for page {page_id}")
        version = get_page_version(page_id)

        data = {
            "key": prop_key,
            "value": value,
            "version": {"number": version}
        }

        response = confluence.post(f"/rest/api/content/{page_id}/property", data=data)

    print(f"✔️ Done for page {page_id}: {response}")

    

# pattern generators
def insert_space_key_into_smart_link(space_key, title):
    return     {
        'old_pattern': f'<ri:page ri:content-title="{escape_umlauts(html.escape(title))}"',
        'new_pattern': f'<ri:page ri:space-key="{space_key}" ri:content-title="{escape_umlauts(html.escape(title))}"'
    }

# Parameter
target_space = 'isms2025'
old_space = 'isms2025'
new_space = 'ISMSpublic'
patterns = []

dry_run = False
update_limit = 0
limit = 50
set_full_width = True

### testing ...
# page_id = 1087151283
# content = confluence.get_page_by_id(page_id, expand='body.storage,version')
# body = content['body']['storage']['value']
# print(body)

# exit(0)
# ###

# generate patterns to make all smart links to pages in isms-public explicit:
pages = []
titles = []
count = 0
while True:
    print(f"Getting all pages from space ({count}-{count+limit}) ...")
    results = confluence.get_all_pages_from_space(new_space, start=count, limit=limit)
    if not results:
        break
    pages.extend(results)
    count += limit
    for page in pages:
        title = page['title']
        if title not in titles:
            titles.append(title)

for title in titles:
    pattern = insert_space_key_into_smart_link(new_space, title)
    patterns.append(pattern)

# try macro id for full width:
# patterns.append({"old_pattern": "79f97513-7ff5-467e-bbf8-5d243c319e65",
#                  "new_pattern": "42f29773-a991-468e-a643-a482faf2bdfa"})


# try layout overwrite:
patterns.append({"old_pattern": '<ac:layout-section ac:type="fixed-width"',
                  "new_pattern": '<ac:layout-section ac:type="single"'})



# Hole alle Seiten aus dem Target-Space
pages = []
count = 0
while True:
    print(f"Getting all pages from space ({count}-{count+limit}) ...")
    results = confluence.get_all_pages_from_space(target_space, start=count, limit=limit)
    if not results:
        break
    pages.extend(results)
    count += limit

# use this to specify explicitly which page to update (for testing)
pages = [ {'id': 1087144269, 'title': 'A.6.02 Beschäftigungs- und Vertragsbedingungen'} ]
#

# update pages in target space
count = 0
updated_pages = []
ids_used = []
updated_count = 0
for page in pages:
    if count % limit == 0:
        print(f"Checking pages ({count}-{count+limit}) / ({len(pages)}) ...")
       
    page_id = page['id']
    if page_id in ids_used:
        continue
    ids_used.append(page_id)
    title = page['title']

    if set_full_width:
        set_full_width_property(page_id)

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
        should_update = not dry_run and (update_limit == 0) or (updated_count < update_limit)
        if should_update:
            updated_count += 1
            #Seite aktualisieren
            confluence.update_page(
                page_id=page_id,
                title=title,
                body=body,
                type='page',
                representation='storage'
            )
        page_url = f"{confluence_base_url}/spaces/{target_space}/pages/{page_id}"
        updated_pages.append({
            "title": title,
            "url": page_url
        })
        print(f"{'Did not update' if not should_update else 'Updated'} page: {title}")

    count += 1

print("\n=== Summary of updated pages ===\n")
for page in updated_pages:
    print(f"- {page['url']}: {page['title']}")

print(f"\nTotal pages affected: {len(updated_pages)}")

print("Done.")