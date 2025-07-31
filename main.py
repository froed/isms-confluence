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
use_cache = True

AT_FREDERIK_SCHAAF = '<ri:user ri:account-id="712020:3722c289-95b2-4ac0-aa48-d43e373b9d7a"'
FREIGABE_DURCH_FREDDY = 'Freigabe durch</strong></p></th><td colspan="2"><p><ac:link><ri:user ri:account-id="712020:3722c289-95b2-4ac0-aa48-d43e373b9d7a"'
FREIGABE_DURCH_ENRICO = 'Freigabe durch</strong></p></th><td colspan="2"><p><ac:link><ri:user ri:account-id="712020:0b17fa08-4976-44ad-9737-f08bb77db445"'
FREIGABE_AM = 'Freigabe am'
REVIEW_DURCHGEFÜHRT_AM = escape_umlauts('Review durchgeführt am')
VERANTWORTLICH = 'Verantwortlich'
VERANTWORTLICH_FREDERIK = 'Verantwortlich</strong></p></th><td colspan="2"><p><ac:link><ri:user ri:account-id="712020:3722c289-95b2-4ac0-aa48-d43e373b9d7a"'
VERANTWORTLICH_ENRICO = 'Verantwortlich</strong></p></th><td colspan="2"><p><ac:link><ri:user ri:account-id="712020:3722c289-95b2-4ac0-aa48-d43e373b9d7a"'
INTERN_LABEL = '<ac:parameter ac:name="colour">Yellow</ac:parameter><ac:parameter ac:name="title">INTERN</ac:parameter>'

# print(emit_page_body(confluence, "285376513"))
# exit(0)

patterns = [
    {
        'old_pattern': INTERN_LABEL,
    }
]

pages = cache(f"PAGES_{target_space}", lambda: get_unique_pages_from_space(confluence, target_space), use=use_cache)
print(f"Found {len(pages)} pages.")

# for page in pages:
#     updated, info = update_freigabe_date_if_needed(confluence, page["id"], dry_run)
#     if updated:
#         print(f"Updated page: {make_page_url(target_space, page["id"])}")
#         break

result = find_pages_with_pattern(confluence, confluence_base_url, target_space, pages, patterns)
print(result)

# result = update_pages(confluence=confluence, email=username, api_token=password, base_url=confluence_base_url, target_space=target_space, pages=pages, patterns=patterns, limit=0, dry_run=dry_run)

#result = widen_thin_pages(confluence_base_url, username, password, pages, target_space, dry_run=dry_run)
# result = find_pages_with_pattern(confluence, confluence_base_url, target_space, pages, patterns)
# for item in result:
#     print(f"Title: {item['title']}: URL: {item['url']}")
    