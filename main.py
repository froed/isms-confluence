from atlassian import Confluence

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

