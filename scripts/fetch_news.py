import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

import argostranslate.package
import argostranslate.translate


TRANSLATION_VERSION = "football-ja-v3"

DATA_PATH = Path("data/news.json")


FEEDS = [
    ("BBC Sport", "https://feeds.bbci.co.uk/sport/football/rss.xml"),
    ("The Guardian Football", "https://www.theguardian.com/football/rss"),
    ("Sky Sports Football", "https://www.skysports.com/rss/12040"),
    ("ESPN FC", "https://www.espn.com/espn/rss/soccer/news"),
]


# =========================================================
# 第1段階
# 大会・クラブ・監督など、頻出する名称を固定
# =========================================================

FOOTBALL_ENTITY_OVERRIDES = {
    # 大会
    "UEFA Champions League": "UEFAチャンピオンズリーグ",
    "Champions League": "チャンピオンズリーグ",
    "Europa League": "ヨーロッパリーグ",
    "Conference League": "カンファレンスリーグ",
    "Premier League": "プレミアリーグ",
    "La Liga": "ラ・リーガ",
    "Serie A": "セリエA",
    "Bundesliga": "ブンデスリーガ",
    "Ligue 1": "リーグ・アン",
    "Eredivisie": "エールディヴィジ",

    # イングランド
    "Manchester City": "マンチェスター・シティ",
    "Man City": "マンチェスター・シティ",
    "Manchester United": "マンチェスター・ユナイテッド",
    "Man United": "マンチェスター・ユナイテッド",
    "Man Utd": "マンチェスター・ユナイテッド",
    "Liverpool": "リヴァプール",
    "Arsenal": "アーセナル",
    "Chelsea": "チェルシー",
    "Tottenham Hotspur": "トッテナム",
    "Tottenham": "トッテナム",
    "Spurs": "トッテナム",
    "Newcastle United": "ニューカッスル",
    "Newcastle": "ニューカッスル",
    "Aston Villa": "アストン・ヴィラ",
    "Crystal Palace": "クリスタル・パレス",
    "West Ham United": "ウェストハム",
    "West Ham": "ウェストハム",
    "Everton": "エヴァートン",
    "Brighton": "ブライトン",

    # スペイン
    "Real Madrid": "レアル・マドリード",
    "FC Barcelona": "バルセロナ",
    "Barcelona": "バルセロナ",
    "Atletico Madrid": "アトレティコ・マドリード",
    "Atlético Madrid": "アトレティコ・マドリード",
    "Real Sociedad": "レアル・ソシエダ",
    "Athletic Club": "アスレティック・クラブ",
    "Villarreal": "ビジャレアル",
    "Sevilla": "セビージャ",

    # イタリア
    "Inter Milan": "インテル",
    "Internazionale": "インテル",
    "Inter": "インテル",
    "AC Milan": "ACミラン",
    "Juventus": "ユヴェントス",
    "AS Roma": "ローマ",
    "Roma": "ローマ",
    "Atalanta": "アタランタ",
    "Napoli": "ナポリ",
    "Lazio": "ラツィオ",
    "Fiorentina": "フィオレンティーナ",

    # ドイツ
    "Bayern Munich": "バイエルン・ミュンヘン",
    "Bayern": "バイエルン",
    "Borussia Dortmund": "ボルシア・ドルトムント",
    "Dortmund": "ドルトムント",
    "Bayer Leverkusen": "レヴァークーゼン",
    "RB Leipzig": "RBライプツィヒ",

    # フランス・オランダ・ポルトガル・トルコ
    "Paris Saint-Germain": "パリ・サンジェルマン",
    "Paris St-Germain": "パリ・サンジェルマン",
    "PSG": "パリ・サンジェルマン",
    "Marseille": "マルセイユ",
    "Monaco": "モナコ",
    "Ajax": "アヤックス",
    "PSV": "PSV",
    "Feyenoord": "フェイエノールト",
    "Benfica": "ベンフィカ",
    "FC Porto": "ポルト",
    "Porto": "ポルト",
    "Sporting CP": "スポルティングCP",
    "Galatasaray": "ガラタサライ",
    "Fenerbahce": "フェネルバフチェ",
    "Fenerbahçe": "フェネルバフチェ",

    # 監督・著名人
    "José Mourinho": "ジョゼ・モウリーニョ",
    "Jose Mourinho": "ジョゼ・モウリーニョ",
    "Mourinho": "モウリーニョ",
    "Carlo Ancelotti": "カルロ・アンチェロッティ",
    "Ancelotti": "アンチェロッティ",
    "Pep Guardiola": "ペップ・グアルディオラ",
    "Guardiola": "グアルディオラ",
    "Mikel Arteta": "ミケル・アルテタ",
    "Arteta": "アルテタ",
    "Arne Slot": "アルネ・スロット",
    "Hansi Flick": "ハンジ・フリック",
    "Thomas Tuchel": "トーマス・トゥヘル",
    "Diego Simeone": "ディエゴ・シメオネ",
    "Antonio Conte": "アントニオ・コンテ",
    "Frank Lampard": "フランク・ランパード",
    "Lampard": "ランパード",
}


# =========================================================
# 第3段階
# 成長辞書
#
# 変な訳が出た選手だけ後から追加する。
# 全選手を登録する必要はありません。
# =========================================================

PLAYER_NAME_OVERRIDES = {
    # レアル・マドリード
    "Kylian Mbappé": "キリアン・エムバペ",
    "Kylian Mbappe": "キリアン・エムバペ",
    "Mbappé": "エムバペ",
    "Mbappe": "エムバペ",
    "Vinícius Júnior": "ヴィニシウス・ジュニオール",
    "Vinicius Junior": "ヴィニシウス・ジュニオール",
    "Vinicius Jr": "ヴィニシウス・ジュニオール",
    "Jude Bellingham": "ジュード・ベリンガム",
    "Bellingham": "ベリンガム",
    "Federico Valverde": "フェデリコ・バルベルデ",
    "Valverde": "バルベルデ",
    "Thibaut Courtois": "ティボー・クルトワ",
    "Courtois": "クルトワ",

    # バルセロナ
    "Lamine Yamal": "ラミン・ヤマル",
    "Yamal": "ヤマル",
    "Pedri": "ペドリ",
    "Gavi": "ガビ",
    "Raphinha": "ラフィーニャ",
    "Robert Lewandowski": "ロベルト・レヴァンドフスキ",
    "Lewandowski": "レヴァンドフスキ",

    # プレミア
    "Erling Haaland": "アーリング・ハーランド",
    "Haaland": "ハーランド",

    "Rayan Cherki": "ラヤン・シェルキ",
    "Cherki": "シェルキ",

    "Phil Foden": "フィル・フォーデン",
    "Foden": "フォーデン",

    "Mohamed Salah": "モハメド・サラー",
    "Salah": "サラー",

    "Virgil van Dijk": "フィルジル・ファン・ダイク",
    "Van Dijk": "ファン・ダイク",

    "Bukayo Saka": "ブカヨ・サカ",
    "Saka": "サカ",

    "Martin Ødegaard": "マルティン・ウーデゴール",
    "Martin Odegaard": "マルティン・ウーデゴール",
    "Odegaard": "ウーデゴール",

    "Cole Palmer": "コール・パーマー",
    "Palmer": "パーマー",

    "Bruno Fernandes": "ブルーノ・フェルナンデス",
    "Son Heung-min": "ソン・フンミン",

    # イタリア
    "Lautaro Martínez": "ラウタロ・マルティネス",
    "Lautaro Martinez": "ラウタロ・マルティネス",
    "Lautaro": "ラウタロ",

    "Nicolò Barella": "ニコロ・バレッラ",
    "Nicolo Barella": "ニコロ・バレッラ",
    "Barella": "バレッラ",

    "Alessandro Bastoni": "アレッサンドロ・バストーニ",
    "Bastoni": "バストーニ",

    # ブンデス
    "Harry Kane": "ハリー・ケイン",
    "Kane": "ケイン",
    "Jamal Musiala": "ジャマル・ムシアラ",
    "Musiala": "ムシアラ",

    # メディア関係者
    "Phil McNulty": "フィル・マクナルティ",
    "McNulty": "マクナルティ",
}


# =========================================================
# サッカー用語
# =========================================================

FOOTBALL_TERM_OVERRIDES = {
    "clean sheet": "クリーンシート",
    "hat-trick": "ハットトリック",
    "hat trick": "ハットトリック",
    "transfer fee": "移籍金",
    "transfer window": "移籍市場",
    "free transfer": "フリー移籍",
    "loan move": "レンタル移籍",
    "on loan": "レンタル移籍で",
    "release clause": "契約解除金",
    "buyout clause": "契約解除金",
    "personal terms": "個人条件",
    "medical": "メディカルチェック",
    "contract extension": "契約延長",
    "new deal": "新契約",
    "sacked": "解任された",
    "sack": "解任",
    "starting XI": "先発メンバー",
    "starting eleven": "先発メンバー",
    "injury time": "アディショナルタイム",
    "stoppage time": "アディショナルタイム",
    "own goal": "オウンゴール",
    "penalty shootout": "PK戦",
    "red card": "レッドカード",
    "yellow card": "イエローカード",
    "title race": "優勝争い",
    "relegation battle": "残留争い",
    "top four": "トップ4",
}


PRIORITY = [
    "champions league",
    "real madrid",
    "mourinho",
    "barcelona",
    "manchester city",
    "man city",
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
    "transfer",
]


# =========================================================
# 第2段階
# 辞書にない人名らしい英字を翻訳前に保護
# =========================================================

PROPER_NAME_STOPWORDS = {
    "A", "An", "The", "This", "That",
    "After", "Before", "From", "For", "With",
    "Without", "Against", "During", "Into",
    "And", "But", "Or", "If", "As",
    "At", "By", "On", "In", "Of", "To",
    "Is", "Are", "Was", "Were", "Be",
    "Could", "Would", "Should", "Will", "Can",
    "May", "New", "Latest", "Live",
    "Why", "How", "What", "When",
    "Premier", "League", "Champions",
    "Europa", "Conference", "Football",
    "Club", "City", "United",
}


def fetch(url):
    request = Request(
        url,
        headers={"User-Agent": "EURO-Football-Portal/3.0"},
    )

    with urlopen(request, timeout=30) as response:
        return response.read()


def clean(text):
    text = text or ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = (
        text.replace("&nbsp;", " ")
        .replace("&amp;", "&")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
    )
    return re.sub(r"\s+", " ", text).strip()


def classify(title, summary):
    text = f"{title} {summary}".lower()

    if "champions league" in text:
        return "ucl", "CL", "ucl"

    if any(x in text for x in [
        "premier league",
        "manchester city",
        "man city",
        "manchester united",
        "man utd",
        "liverpool",
        "arsenal",
        "chelsea",
        "tottenham",
        "newcastle",
        "aston villa",
        "crystal palace",
    ]):
        return "epl", "プレミア", "epl"

    if any(x in text for x in [
        "la liga",
        "real madrid",
        "barcelona",
        "atletico madrid",
        "atlético madrid",
        "real sociedad",
        "villarreal",
    ]):
        return "laliga", "ラ・リーガ", "laliga"

    if any(x in text for x in [
        "serie a",
        "inter",
        "ac milan",
        "juventus",
        "roma",
        "atalanta",
        "napoli",
        "lazio",
    ]):
        return "seriea", "セリエA", "seriea"

    if any(x in text for x in [
        "bundesliga",
        "bayern",
        "borussia dortmund",
        "leverkusen",
        "rb leipzig",
    ]):
        return "bundesliga", "ブンデス", "bundesliga"

    if any(x in text for x in [
        "transfer",
        "signing",
        "signed",
        "signs",
        "loan",
        "deal",
        "move",
        "fee",
        "medical",
        "personal terms",
        "contract",
    ]):
        return "transfer", "移籍", "transfer"

    return "other", "その他", "other"


def prepare_translator():
    try:
        installed = argostranslate.translate.get_installed_languages()

        english = next(
            (lang for lang in installed if lang.code == "en"),
            None,
        )

        japanese = next(
            (lang for lang in installed if lang.code == "ja"),
            None,
        )

        if english and japanese:
            return english.get_translation(japanese)

        print("Installing English -> Japanese translation model")

        argostranslate.package.update_package_index()

        packages = argostranslate.package.get_available_packages()

        package = next(
            p for p in packages
            if p.from_code == "en" and p.to_code == "ja"
        )

        downloaded = package.download()
        argostranslate.package.install_from_path(downloaded)

        installed = argostranslate.translate.get_installed_languages()

        english = next(lang for lang in installed if lang.code == "en")
        japanese = next(lang for lang in installed if lang.code == "ja")

        return english.get_translation(japanese)

    except Exception as error:
        print("Translator setup failed:", error)
        return None


def all_overrides():
    result = {}
    result.update(FOOTBALL_ENTITY_OVERRIDES)
    result.update(PLAYER_NAME_OVERRIDES)
    result.update(FOOTBALL_TERM_OVERRIDES)
    return result


def protect_known_entities(text):
    replacements = {}
    counter = 0

    entries = sorted(
        all_overrides().items(),
        key=lambda x: len(x[0]),
        reverse=True,
    )

    for english, japanese in entries:
        pattern = re.compile(
            re.escape(english),
            flags=re.IGNORECASE,
        )

        while True:
            match = pattern.search(text)

            if not match:
                break

            token = f"ZXQFB{counter:04d}ZXQ"
            counter += 1

            replacements[token] = japanese

            text = (
                text[:match.start()]
                + token
                + text[match.end():]
            )

    return text, replacements, counter


def protect_unknown_names(text, replacements, counter):
    # まず2〜3語の人名らしい表記を保護
    pattern = re.compile(
        r"\b("
        r"[A-ZÀ-ÖØ-Ý][A-Za-zÀ-ÖØ-öø-ÿ'’-]+"
        r"(?:\s+[A-ZÀ-ÖØ-Ý][A-Za-zÀ-ÖØ-öø-ÿ'’-]+){1,2}"
        r")\b"
    )

    matches = list(pattern.finditer(text))

    for match in reversed(matches):
        phrase = match.group(1)

        if "ZXQFB" in phrase:
            continue

        words = phrase.split()

        if all(word in PROPER_NAME_STOPWORDS for word in words):
            continue

        token = f"ZXQFB{counter:04d}ZXQ"
        counter += 1

        replacements[token] = phrase

        text = (
            text[:match.start()]
            + token
            + text[match.end():]
        )

    return text, replacements


def restore_tokens(text, replacements):
    for token, replacement in replacements.items():
        text = text.replace(token, replacement)

        # 翻訳エンジンが空白を挟んだ場合への保険
        spaced = " ".join(token)
        text = text.replace(spaced, replacement)

    return text


def postprocess(text):
    fixes = {
        "マンシティ": "マンチェスター・シティ",
        "マンチェスターシティ": "マンチェスター・シティ",
        "マンU": "マンチェスター・ユナイテッド",
        "レアルマドリード": "レアル・マドリード",
        "クリスタルパレス": "クリスタル・パレス",
        "アトレティコマドリード": "アトレティコ・マドリード",
        "ラリーガ": "ラ・リーガ",
        "セリエ A": "セリエA",
        "ブンデス・リーガ": "ブンデスリーガ",

        # 今回確認できた誤訳への保険
        "レイアン・チェレキ": "ラヤン・シェルキ",
        "レイアン・チェルキ": "ラヤン・シェルキ",
        "チェレキ": "シェルキ",
        "チェルキ": "シェルキ",
        "フィル・マッナルティ": "フィル・マクナルティ",
    }

    for old, new in fixes.items():
        text = text.replace(old, new)

    text = re.sub(r"\s+([。、！？])", r"\1", text)
    text = re.sub(r"\s{2,}", " ", text)

    return text.strip()


def translate_football_text(translator, text):
    if not text:
        return ""

    if translator is None:
        return text

    try:
        protected, replacements, counter = protect_known_entities(text)

        protected, replacements = protect_unknown_names(
            protected,
            replacements,
            counter,
        )

        translated = translator.translate(protected)

        translated = restore_tokens(
            translated,
            replacements,
        )

        return postprocess(translated)

    except Exception as error:
        print("Translation failed:", error)
        return text


# =========================================================
# 前回データを読み込み
# 同じ記事なら毎回翻訳し直さない
# =========================================================

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
        print("Could not read previous data:", error)


translator = prepare_translator()

items = []


for source, feed_url in FEEDS:
    try:
        root = ET.fromstring(fetch(feed_url))

        for feed_item in root.findall(".//item")[:30]:
            original_title = clean(
                feed_item.findtext("title")
            )

            original_summary = clean(
                feed_item.findtext("description")
            )

            link = clean(
                feed_item.findtext("link")
            )

            published = clean(
                feed_item.findtext("pubDate")
            )

            if not original_title or not link:
                continue

            category, label, item_type = classify(
                original_title,
                original_summary,
            )

            combined = (
                f"{original_title} {original_summary}"
            ).lower()

            featured = any(
                priority in combined
                for priority in PRIORITY
            )

            old = previous.get(link, {})

            reuse_translation = (
                old.get("translation_version")
                == TRANSLATION_VERSION
                and old.get("title_original")
                == original_title
                and old.get("summary_original")
                == original_summary[:500]
                and old.get("title")
            )

            if reuse_translation:
                title_ja = old.get(
                    "title",
                    original_title,
                )

                summary_ja = old.get(
                    "summary",
                    original_summary,
                )

            else:
                title_ja = translate_football_text(
                    translator,
                    original_title,
                )

                summary_ja = translate_football_text(
                    translator,
                    original_summary[:500],
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

                "translation_version": TRANSLATION_VERSION,
            })

    except Exception as error:
        print("Feed failed:", source, error)


# =========================================================
# 重複除去
# =========================================================

unique_items = []
seen = set()

for item in items:
    key = item["url"]

    if key in seen:
        continue

    seen.add(key)
    unique_items.append(item)


output = {
    "updated_at": datetime.now(
        timezone.utc
    ).isoformat(),

    "items": unique_items[:80],
}


DATA_PATH.parent.mkdir(
    parents=True,
    exist_ok=True,
)

DATA_PATH.write_text(
    json.dumps(
        output,
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)

print(
    f"Saved {len(output['items'])} football articles"
)
