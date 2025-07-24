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
target_spaces = [ISMS_SPACE, ISMS_SPACE_PUBLIC]

dry_run = False

# define patterns
AT_FREDERIK_SCHAAF = '<ri:user ri:account-id="712020:3722c289-95b2-4ac0-aa48-d43e373b9d7a"'
VERANTWORTLICH = 'Verantwortlich'
VERANTWORTLICH_FREDERIK = 'Verantwortlich</strong></p></th><td colspan="2"><p><ac:link><ri:user ri:account-id="712020:3722c289-95b2-4ac0-aa48-d43e373b9d7a"'
VERANTWORTLICH_ENRICO = 'Verantwortlich</strong></p></th><td colspan="2"><p><ac:link><ri:user ri:account-id="712020:3722c289-95b2-4ac0-aa48-d43e373b9d7a"'
REVIEW_DURCHGEFÜHRT_AM = escape_umlauts('Review durchgeführt am')
FREIGABE_DURCH_FREDDY = 'Freigabe durch</strong></p></th><td colspan="2"><p><ac:link><ri:user ri:account-id="712020:3722c289-95b2-4ac0-aa48-d43e373b9d7a"'
FREIGABE_DURCH_ENRICO = 'Freigabe durch</strong></p></th><td colspan="2"><p><ac:link><ri:user ri:account-id="712020:0b17fa08-4976-44ad-9737-f08bb77db445"'

patterns = [
    {
        'old_pattern': FREIGABE_DURCH_FREDDY,
        'new_pattern': FREIGABE_DURCH_ENRICO
    }
]

for target_space in target_spaces:
    print(f"examining space: {target_space} ...")

    print("finding all pages ...")
    pages = get_unique_pages_from_space(confluence, target_space)
    print(f"Found {len(pages)} pages.")

    print("widen ...")
    result = widen_thin_pages(confluence_base_url, username, password, pages, target_space, dry_run=dry_run)

    print("finding bad patterns ...")
    result = find_pages_with_pattern(confluence, confluence_base_url, target_space, pages, patterns)

    print("updating ""Freigabe am"" ...")
    update_freigabe_am(confluence, confluence_base_url, username, password, target_space, pages, dry_run)
