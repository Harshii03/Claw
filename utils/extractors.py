# (c) Mr. Avishkar

import re

def extract_links(text):
    url_pattern = r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
    matches = re.findall(url_pattern, text)

    return matches
