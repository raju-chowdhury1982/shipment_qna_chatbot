from datetime import datetime
from typing import Any, Dict


def get_today_date() -> str:
    """
    Returns the current date in YYYY-MM-DD format.
    """
    return datetime.now().strftime("%Y-%m-%d")


GET_TODAY_DATE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_today_date",
        "description": "Get the current date. Useful for resolving relative date queries like 'shipped today', 'arriving tomorrow', 'next Friday', etc.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
}
