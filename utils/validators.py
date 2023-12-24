# (c) Mr. Avishkar

import re
import validators
from urllib.parse import urlparse
from validators.utils import ValidationError


def is_url(url: str) -> bool:
    result = validators.url(url)

    if isinstance(result, ValidationError):
        return False

    return result


def is_valid_url(url):
    try:
        parsed_url = urlparse(url)
        if parsed_url.scheme not in ("http", "https", "ftp"):
            return False
        if not parsed_url.netloc:
            return False
        return True
    except ValueError:
        return False


def is_clawbox_url(url):
    patterns = [
        r"clawbox\.in",
        r"www\.clawbox\.in",
        r"clawbox\.org",
        r"www\.clawbox\.org",
        r"clawbox\.xyz",
        r"www\.clawbox\.xyz",
    ]

    if not is_valid_url(url):
        return False

    for pattern in patterns:
        if re.search(pattern, url):
            return True

    return False
