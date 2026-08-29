import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

import argostranslate.package
import argostranslate.translate


FEEDS = [
    ("BBC Sport", "https://feeds.bbci.co.uk/sport/football/rss.xml"),
    ("The Guardian Football", "https://www.theguardian.com/football/rss"),
    ("Sky Sports Football", "https://www.skysports.com/rss/12040"),
    ("ESPN FC", "https://www.espn.com/espn/rss/soccer/news"),
]

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
    req = Request(
        url,
        headers={"User-Agent": "EURO-Football-Portal/1.0"}
    )
    with urlopen(req, timeout=30) as response:
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
        "premier league",
        "manchester united",
        "manchester city",
        "liverpool",
        "arsenal",
        "chelsea",
        "tottenham"
    ]):
        return "epl", "プレミア", "epl"

    if any(x in text for x in [
        "la liga",
        "real madrid",
        "barcelona",
        "atletico madrid"
    ]):
        return "laliga", "ラ・リーガ", "laliga"

    if any(x in text for x in [
        "serie a",
        "inter",
        "milan",
        "juventus",
        "roma",
        "atalanta"
    ]):
        return "seriea", "セリエA", "seriea"

    if any(x in text for x in [
        "bundesliga",
        "bayern",
        "borussia dortmund"
    ]):
        return "bundesliga", "ブンデス", "bundesliga"

    if any(x in text for x in [
        "transfer",
        "signed",
        "signs",
        "loan",
        "deal",
        "move",
        "fee"
    ]):
        return "transfer", "移籍", "transfer"

    return "other", "その他", "other"


def prepare_translator():
    try:
        installed = argostranslate.translate.get_installed_languages()

        en = next(
            (lang for lang in installed if lang.code == "en"),
            None
        )
        ja = next(
            (lang for lang in installed if lang.code == "ja"),
            None
        )

        if en and ja:
            return en.get_translation(ja)

        print("Installing English -> Japanese translation model...")

        argostranslate.package.update_package_index()

        packages = argostranslate.package.get_available_packages()

        package = next(
            p for p in packages
            if p.from_code == "en" and p.to_code == "ja"
        )

        argostranslate.package.install_from_path(
            package.download()
        )

        installed = argostranslate.translate.get_installed_languages()

        en = next(lang for lang in installed if lang.code == "en")
        ja = next(lang for lang in installed if lang.code == "ja")

        return en.get_translation(ja)

    except Exception as error:
        print("Translator setup failed:", error)
        return None


def translate_text(translator, text):
    if not text:
        return ""

    if translator is None:
        return text

    try:
        return translator.translate(text)
    except Exception as error:
        print("Translation failed:", error)
        return text


DATA_PATH = Path("data/news.json")

previous = {}

if DATA_PATH.exists():
    try:
        old_data = json.loads(
            DATA_PATH.read_text(encoding="utf-8")
        )

        for item in old_data.get("items", []):
            url = item.get("url")

            if url:
                previous[url] = item

    except Exception as error:
        print("Could not load old translations:", error)


translator = prepare_translator()

items = []


for source, feed_url in FEEDS:
    try:
        root = ET.fromstring(fetch(feed_url))

        for feed_item in root.findall(".//item")[:30]:

            original_title = clean(
                feed_item.findtext("title")
            )

            link = clean(
                feed_item.findtext("link")
            )

            original_summary = clean(
                feed_item.findtext("description")
            )

            published = clean(
                feed_item.findtext("pubDate")
            )

            if not original_title or not link:
                continue

            category, label, item_type = classify(
                original_title,
                original_summary
            )

            combined = (
                f"{original_title} {original_summary}".lower()
            )

            featured = any(
                word in combined
                for word in PRIORITY
            )

            old = previous.get(link, {})

            same_article = (
                old.get("title_original") == original_title
            )

            if same_article and old.get("title"):
                title_ja = old["title"]
            else:
                title_ja = translate_text(
                    translator,
                    original_title
                )

            if same_article and old.get("summary"):
                summary_ja = old["summary"]
            else:
                summary_ja = translate_text(
                    translator,
                    original_summary[:500]
                )

            items.append({
                "title": title_ja,
                "summary": summary_ja,
                "title_original": original_title,
                "summary_original": original_summary[:500],
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


seen = set()
unique_items = []

for item in items:
    key = item["url"]

    if key in seen:
        continue

    seen.add(key)
    unique_items.append(item)


output = {
    "updated_at": datetime.now(timezone.utc).isoformat(),
    "items": unique_items[:100],
}


DATA_PATH.parent.mkdir(
    parents=True,
    exist_ok=True
)

DATA_PATH.write_text(
    json.dumps(
        output,
        ensure_ascii=False,
        indent=2
    ),
    encoding="utf-8"
)

print(
    f"Saved {len(output['items'])} articles."
)
