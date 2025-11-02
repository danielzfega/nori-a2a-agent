import re
from typing import Tuple, Optional

KNOWN_TOPICS = ["technology", "tech", "business", "sports", "health", "science", "politics", "entertainment"]

def parse_user_query(text: str) -> Tuple[Optional[str], Optional[str], Optional[int]]:
    """
    Returns (topic, country_code, days)
    Simple heuristics: find topic keyword, country name/code, and range like '2 days'
    """
    s = text.lower()
    topic = None
    for t in KNOWN_TOPICS:
        if t in s:
            topic = "technology" if t == "tech" else t
            break

    # country detection (very simple). Expand mapping as needed
    country = None
    if re.search(r"\bnigeria\b|\bng\b", s): country = "ng"
    elif re.search(r"\bus\b|\bamerica\b|\bunited states\b", s): country = "us"
    elif re.search(r"\buk\b|\bengland\b|\bbritain\b", s): country = "gb"

    days = None
    m = re.search(r"past\s+(\d+)\s+days", s)
    if m:
        days = int(m.group(1))
    elif "today" in s:
        days = 1
    return topic, country, days
