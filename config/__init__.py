"""Модуль конфигурации pc-games."""
from config.subforums import (
    PARENT_FORUM_ID,
    PARENT_FORUM_NAME,
    EXCLUDED_SUBFORUM_IDS,
    SUBFORUMS,
    is_subforum_allowed,
    get_subforum_info,
    get_all_allowed_subforums,
)

__all__ = [
    "PARENT_FORUM_ID",
    "PARENT_FORUM_NAME",
    "EXCLUDED_SUBFORUM_IDS",
    "SUBFORUMS",
    "is_subforum_allowed",
    "get_subforum_info",
    "get_all_allowed_subforums",
]
