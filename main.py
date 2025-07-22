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

dry_run = True
update_limit = 0
limit = 50

AT_FREDERIK_SCHAAF = '<ri:user ri:account-id="712020:3722c289-95b2-4ac0-aa48-d43e373b9d7a"'
VERANTWORTLICH = 'Verantwortlich'
VERANTWORTLICH_FREDERIK = 'Verantwortlich</strong></p></th><td colspan="2"><p><ac:link><ri:user ri:account-id="712020:3722c289-95b2-4ac0-aa48-d43e373b9d7a"'
VERANTWORTLICH_ENRICO = 'Verantwortlich</strong></p></th><td colspan="2"><p><ac:link><ri:user ri:account-id="712020:3722c289-95b2-4ac0-aa48-d43e373b9d7a"'

patterns = [
    {
        'old_pattern': VERANTWORTLICH,
        'new_pattern': f'FOUNDYOU'
    }
]

# print(emit_page_body(confluence, "1132658690"))
# exit(0)

pages = get_unique_pages_from_space(confluence, ISMS_SPACE)
print(f"Found {len(pages)} pages.")

#result = update_pages(confluence=confluence, email=username, api_token=password, base_url=confluence_base_url, target_space=ISMS_SPACE, pages=pages, patterns=patterns, limit=1, dry_run=dry_run)
result = find_pages_with_pattern(confluence, confluence_base_url, ISMS_SPACE, pages, patterns)

for page in result:
    print(f"{page["title"]}: {page["url"]}")