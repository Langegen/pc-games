"""Ядро парсера pc-games."""
from core.filter import is_portable, is_allowed_size, parse_size_to_bytes, clean_game_title
from core.atom import fetch_subforum_feed, fetch_all_subforums_feeds
from core.forum import scrape_forum_page
from core.topic_parser import get_topic_data, merge_topic_details
from core.storage import (
    load_json,
    save_json,
    update_subforums_catalog,
    enrich_incomplete,
    write_changes_log,
    GAMES_FILE,
    STATS_FILE,
    SUBFORUMS_FILE,
)
from core.stats import scrape_torrents_stats

__all__ = [
    "is_portable",
    "is_allowed_size",
    "parse_size_to_bytes",
    "clean_game_title",
    "fetch_subforum_feed",
    "fetch_all_subforums_feeds",
    "scrape_forum_page",
    "get_topic_data",
    "merge_topic_details",
    "load_json",
    "save_json",
    "update_subforums_catalog",
    "enrich_incomplete",
    "write_changes_log",
    "GAMES_FILE",
    "STATS_FILE",
    "SUBFORUMS_FILE",
    "scrape_torrents_stats",
]
