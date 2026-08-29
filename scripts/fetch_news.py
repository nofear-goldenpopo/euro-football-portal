import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

FEEDS = [
    ("BBC Sport", "https://feeds.bbci.co.uk/sport/football/rss.xml"),
    ("The Guardian Football", "https://www.theguardian.com/football/rss"),
    ("Sky Sports Football", "https://www.skysports.com/rss/12040"),
    ("ESPN FC", "https://www.espn.com/espn/rss/soccer/news"),
]

SAFE_DOMAINS = {
    "bbc.co.uk",
    "theguardian.com",
    "skysports.com",
    "espn.com",
}

PRIORITY = [
    "real madrid",
    "mourinho",
    "barcelona",
    "manchester city",
    "manchester united",
    "liverpool",
    "arsenal",
    "chelsea",
    "tottenham",
    "inter",
    "milan",
    "juventus",
    "roma",
    "atalanta",
    "bayern",
]

def fetch(url):
    req = Request(url, headers={"User-Agent": "EURO-Football-Portal/1.0"})
    with urlopen(req, timeout=20) as response:
        return response.read()

def clean(text):
    text = text or ""
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def classify(title, summary):
    text = f"{title} {summary}".lower()

    if "champions league" in text:
        return "ucl", "CL", "ucl"

    if any(x in text for x in [
        "premier league", "manchester united", "manchester city",
        "liverpool", "arsenal", "chelsea", "tottenham"
    ]):
        return "epl", "プレミア", "epl"

    if any(x in text for x in [
        "la liga", "real madrid", "barcelona", "atletico madrid"
    ]):
        return "laliga", "ラ・リーガ", "laliga"

    if any(x in text for x in [
        "serie a", "inter", "milan", "juventus", "roma", "atalanta"
    ]):
        return "seriea", "セリエA", "seriea"

    if any(x in text for x in [
        "bundesliga", "bayern", "borussia dortmund"
    ]):
        return "bundesliga", "ブンデス", "bundesliga"

    if any(x in text for x in [
        "transfer", "signed", "signs", "loan", "deal", "move", "fee"
    ]):
        return "transfer", "移籍", "transfer"

    return "other", "その他", "other"

items = []

for source, feed_url in FEEDS:
    try:
        root = ET.fromstring(fetch(feed_url))

        for item in root.findall(".//item")[:30]:
            title = clean(item.findtext("title"))
            link = clean(item.findtext("link"))
            summary = clean(item.findtext("description"))
            published = clean(item.findtext("pubDate"))

            if not title or not link:
                continue

            category, label, item_type = classify(title, summary)
            combined = f"{title} {summary}".lower()
            featured = any(word in combined for word in PRIORITY)

            items.append({
                "title": title,
                "summary": summary[:360],
                "source": source,
                "url": link,
                "published": published,
                "category": category,
                "type": item_type,
                "label": label,
                "featured": featured,
            })

    except Exception as error:
        print("Feed failed:", source, error)

output = {
    "updated_at": datetime.now(timezone.utc).isoformat(),
    "items": items[:200],
}

Path("data/news.json").write_text(
    json.dumps(output, ensure_ascii=False, indent=2),
    encoding="utf-8"
)
