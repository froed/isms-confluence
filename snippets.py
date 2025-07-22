

# pattern generators
def insert_space_key_into_smart_link(space_key, title):
    return     {
        'old_pattern': f'<ri:page ri:content-title="{escape_umlauts(html.escape(title))}"',
        'new_pattern': f'<ri:page ri:space-key="{space_key}" ri:content-title="{escape_umlauts(html.escape(title))}"'
    }

# usage example