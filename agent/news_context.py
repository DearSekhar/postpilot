"""
Fetches a small set of recent, relevant headlines from public no-auth RSS
feeds to use as OPTIONAL supporting context for a post — never as the
topic itself. The model is instructed to weave it in only if it naturally
strengthens the business-problem narrative (e.g. citing a real recent
breach when writing about security posture), and to ignore it otherwise.

Deliberately dependency-free (stdlib only) and fully best-effort: any
failure here (network, parsing, timeout) should never break post
generation — it just means no news context gets attached this run.
"""
import re
import socket
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

FEEDS = {
    # Azure feature/service updates — official, no auth required.
    "Azure Updates": "https://www.microsoft.com/releasecommunications/api/v2/azure/rss",
    # Security/breach-relevant industry news — widely used, no auth required.
    "Security News": "https://feeds.feedburner.com/TheHackersNews",
}

FETCH_TIMEOUT_SECONDS = 6
MAX_ITEMS_PER_FEED = 20
MAX_ITEM_AGE_DAYS = 14
MAX_RESULTS = 3

_ATOM_NS = "{http://www.w3.org/2005/Atom}"


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text or "").strip()


def _fetch_feed(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "PostPilot/1.0"})
    with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT_SECONDS) as resp:
        return resp.read()


def _parse_items(xml_bytes: bytes) -> list[dict]:
    """Handles both RSS 2.0 (<item>) and Atom (<entry>) shapes."""
    items = []
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return items

    for item in root.iter("item"):  # RSS 2.0
        title = (item.findtext("title") or "").strip()
        summary = _strip_html(item.findtext("description") or "")
        link = (item.findtext("link") or "").strip()
        pub_date = item.findtext("pubDate")
        if title:
            items.append({"title": title, "summary": summary, "link": link, "pub_date": pub_date})

    for entry in root.iter(f"{_ATOM_NS}entry"):  # Atom fallback
        title = (entry.findtext(f"{_ATOM_NS}title") or "").strip()
        summary = _strip_html(entry.findtext(f"{_ATOM_NS}summary") or "")
        link_el = entry.find(f"{_ATOM_NS}link")
        link = link_el.get("href") if link_el is not None else ""
        pub_date = entry.findtext(f"{_ATOM_NS}updated") or entry.findtext(f"{_ATOM_NS}published")
        if title:
            items.append({"title": title, "summary": summary, "link": link, "pub_date": pub_date})

    return items[:MAX_ITEMS_PER_FEED]


def _keywords_for(industry: str | None, category: str | None, prefs: dict) -> list[str]:
    words = set()
    for source in [industry, category]:
        if source:
            words.update(w.lower() for w in re.split(r"[^a-zA-Z0-9]+", source) if len(w) > 3)
    for topic in prefs.get("preferred_ai_topics", []) + prefs.get("primary_domains", []):
        words.update(w.lower() for w in re.split(r"[^a-zA-Z0-9]+", topic) if len(w) > 3)
    return list(words)


def get_relevant_context(industry: str | None, category: str | None, prefs: dict) -> list[dict]:
    """Best-effort: returns up to MAX_RESULTS relevant, recent items across
    all feeds, or an empty list on any failure — never raises."""
    keywords = _keywords_for(industry, category, prefs)
    if not keywords:
        return []

    all_items = []
    for source_name, url in FEEDS.items():
        try:
            raw = _fetch_feed(url)
            for item in _parse_items(raw):
                item["source"] = source_name
                all_items.append(item)
        except (urllib.error.URLError, socket.timeout, TimeoutError, Exception) as e:
            print(f"Warning: news_context fetch failed for {source_name}, skipping. {e}")
            continue

    scored = []
    for item in all_items:
        text = f"{item['title']} {item['summary']}".lower()
        matches = sum(1 for kw in keywords if kw in text)
        if matches > 0:
            scored.append((matches, item))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in scored[:MAX_RESULTS]]


def format_context_block(items: list[dict]) -> str:
    if not items:
        return ""
    lines = [
        "\nOptional recent context (only mention if it naturally strengthens the post's "
        "point — paraphrase in your own words, don't quote directly, and don't just announce "
        "it as news. If none of these genuinely fit, ignore this section entirely):",
    ]
    for item in items:
        lines.append(f"- [{item['source']}] {item['title']}")
    return "\n".join(lines)
