# ============================================================
# GEM Protocol v2 — News Fetcher (Google News RSS)
# ============================================================
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote

import feedparser
import streamlit as st


@dataclass
class NewsItem:
    title: str
    link: str
    published: str
    source: str = ""


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_news(query: str, max_items: int = 8) -> list[NewsItem]:
    """Fetch latest news from Google News RSS for a given query.

    Returns up to *max_items* headlines.  Cached for 30 minutes.
    """
    encoded = quote(query)
    url = f"https://news.google.com/rss/search?q={encoded}&hl=en-US&gl=US&ceid=US:en"

    try:
        feed = feedparser.parse(url)
        items: list[NewsItem] = []
        for entry in feed.entries[:max_items]:
            source = ""
            if " - " in entry.get("title", ""):
                source = entry["title"].rsplit(" - ", 1)[-1]
            items.append(
                NewsItem(
                    title=entry.get("title", ""),
                    link=entry.get("link", ""),
                    published=entry.get("published", ""),
                    source=source,
                )
            )
        return items
    except Exception:
        return []
