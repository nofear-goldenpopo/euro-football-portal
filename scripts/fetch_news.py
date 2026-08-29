import json
import re
import html
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

import argostranslate.package
import argostranslate.translate


TRANSLATION_VERSION = "football-ja-v4"
DATA_PATH = Path("data/news.json")


FEEDS = [
    ("BBC Sport", "https://feeds.bbci.co.uk/sport/football/rss.xml"),
    ("The Guardian Football", "https://www.theguardian.com/football/rss"),
    ("Sky Sports Football", "https://www.skysports.com/rss/12040"),
    ("ESPN FC", "https://www.espn.com/espn/rss/soccer/news"),
]


# =========================================================
# 第1段階：大会・クラブ・監督などの固定辞書
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
    "Everton": "エヴァートン",
    "West Ham United": "ウェストハム",
    "West Ham": "ウェストハム",
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

    # その他主要クラブ
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
# 第2段階：成長型の選手名辞書
# 変な表記が出た選手だけ、今後ここへ追加
# =========================================================

PLAYER_NAME_OVERRIDES = {
    # Real Madrid
    "Kylian Mbappé": "キリアン・エムバペ",
    "Kylian Mbappe": "キリアン・エムバペ",
    "Mbappé": "エムバペ",
    "Mbappe": "エムバペ",
    "Vinícius Júnior": "ヴィニシウス・ジュニオール",
    "Vinicius Junior": "ヴィニシウス・ジュニオール",
    "Jude Bellingham": "ジュード・ベリンガム",
    "Bellingham": "ベリンガム",
    "Federico Valverde": "フェデリコ・バルベルデ",
    "Valverde": "バルベルデ",
    "Thibaut Courtois": "ティボー・クルトワ",
    "Courtois": "クルトワ",

    # Barcelona
    "Lamine Yamal": "ラミン・ヤマル",
    "Yamal": "ヤマル",
    "Pedri": "ペドリ",
    "Gavi": "ガビ",
    "Raphinha": "ラフィーニャ",
    "Robert Lewandowski": "ロベルト・レヴァンドフスキ",
    "Lewandowski": "レヴァンドフスキ",

    # Premier League
    "Erling Haaland": "アーリング・ハーランド",
    "Haaland": "ハーランド",
    "Rayan Cherki": "ラヤン・シェルキ",
    "Cherki": "シェルキ",
    "Phil Foden": "フィル・フォーデン",
    "Foden": "フォーデン",
    "Mohamed Salah": "モハメド・サラー",
    "Salah": "サラー",
    "Virgil van Dijk": "フィルジル・ファン・ダイク",
    "Bukayo Saka": "ブカヨ・サカ",
    "Saka": "サカ",
    "Martin Ødegaard": "マルティン・ウーデゴール",
    "Martin Odegaard": "マルティン・ウーデゴール",
    "Cole Palmer": "コール・パーマー",
    "Palmer": "パーマー",
    "Bruno Fernandes": "ブルーノ・フェルナンデス",
    "Son Heung-min": "ソン・フンミン",

    # Serie A
    "Lautaro Martínez": "ラウタロ・マルティネス",
    "Lautaro Martinez": "ラウタロ・マルティネス",
    "Nicolò Barella": "ニコロ・バレッラ",
    "Nicolo Barella": "ニコロ・バレッラ",
    "Barella": "バレッラ",
    "Alessandro Bastoni": "アレッサンドロ・バストーニ",
    "Bastoni": "バストーニ",

    # Bundesliga
    "Harry Kane": "ハリー・ケイン",
    "Kane": "ケイン",
    "Jamal Musiala": "ジャマル・ムシアラ",
    "Musiala": "ムシアラ",

    # 記者など
    "Phil McNulty": "フィル・マクナルティ",
    "McNulty": "マクナルティ",
}


# =========================================================
# 第3段階：サッカー記事用の表現辞書
# 「辞書翻訳」ではなく文脈に合う日本語へ
# =========================================================

FOOTBALL_PHRASE_OVERRIDES = {
    "clean sheet": "クリーンシート",
    "hat-trick": "ハットトリック",
    "hat trick": "ハットトリック",

    "two goals": "2ゴール",
    "three goals": "3ゴール",
    "four goals": "4ゴール",
    "brace": "2ゴール",

    "swaggering display": "圧巻のパフォーマンス",
    "impressive display": "印象的なパフォーマンス",
    "superb display": "素晴らしいパフォーマンス",
    "fine display": "好パフォーマンス",

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

    "time to shine": "輝く時",
    "moment to shine": "輝く時",
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
# 基本処理
# =========================================================

def fetch(url):
    request = Request(
        url,
        headers={"User-Agent": "EURO-Football-Portal/4.0"},
    )

    with urlopen(request, timeout=30) as response:
        return response.read()


def clean(text):
    text = html.unescape(text or "")
    text = re.sub(r"<[^>]+>", " ", text)
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


# =========================================================
# Argos Translate
# =========================================================

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

        english = next(
            lang for lang in installed
            if lang.code == "en"
        )

        japanese = next(
            lang for lang in installed
            if lang.code == "ja"
        )

        return english.get_translation(japanese)

    except Exception as error:
        print("Translator setup failed:", error)
        return None


# =========================================================
# 固有名詞検索
#
# 前回のZXQトークン方式は廃止。
# 固有名詞部分を翻訳エンジンへ渡さず、
# 文章を分割して翻訳する。
# =========================================================

def combined_entities():
    result = {}

    result.update(FOOTBALL_ENTITY_OVERRIDES)
    result.update(PLAYER_NAME_OVERRIDES)
    result.update(FOOTBALL_PHRASE_OVERRIDES)

    return result


def find_protected_spans(text):
    candidates = []

    entries = sorted(
        combined_entities().items(),
        key=lambda item: len(item[0]),
        reverse=True,
    )

    for english, japanese in entries:
        pattern = re.compile(
            re.escape(english),
            re.IGNORECASE,
        )

        for match in pattern.finditer(text):
            candidates.append(
                (
                    match.start(),
                    match.end(),
                    japanese,
                )
            )

    # 長い一致を優先
    candidates.sort(
        key=lambda x: (
            x[0],
            -(x[1] - x[0]),
        )
    )

    selected = []
    last_end = -1

    for start, end, replacement in candidates:
        if start < last_end:
            continue

        selected.append(
            (start, end, replacement)
        )

        last_end = end

    return selected


# =========================================================
# 未登録の「複数語の人名」を英字で保護
#
# 例：
# Alejandro Garnacho
# Florian Wirtz
#
# 無理なカタカナ化より原語表記を優先
# =========================================================

NAME_STOPWORDS = {
    "The",
    "After",
    "Before",
    "Premier League",
    "Champions League",
    "Manchester City",
    "Manchester United",
    "Real Madrid",
    "Crystal Palace",
    "Aston Villa",
    "West Ham",
}


def add_unknown_name_spans(text, spans):
    occupied = []

    for start, end, replacement in spans:
        occupied.append((start, end))

    pattern = re.compile(
        r"\b("
        r"[A-ZÀ-ÖØ-Ý][A-Za-zÀ-ÖØ-öø-ÿ'’-]+"
        r"(?:\s+[A-ZÀ-ÖØ-Ý][A-Za-zÀ-ÖØ-öø-ÿ'’-]+){1,2}"
        r")\b"
    )

    for match in pattern.finditer(text):
        phrase = match.group(1)

        if phrase in NAME_STOPWORDS:
            continue

        start = match.start()
        end = match.end()

        overlap = any(
            start < other_end
            and end > other_start
            for other_start, other_end in occupied
        )

        if overlap:
            continue

        spans.append(
            (
                start,
                end,
                phrase,
            )
        )

        occupied.append((start, end))

    spans.sort(key=lambda x: x[0])

    return spans


# =========================================================
# 第3段階：英文そのものをサッカー文脈で先に解釈
#
# 一般機械翻訳で壊れやすい定型表現を
# 「意味単位」で日本語化する。
# =========================================================

def entity_to_ja(name):
    normalized = name.strip()

    all_names = {}
    all_names.update(FOOTBALL_ENTITY_OVERRIDES)
    all_names.update(PLAYER_NAME_OVERRIDES)

    for english, japanese in all_names.items():
        if english.lower() == normalized.lower():
            return japanese

    return normalized


def smart_source_rewrite(text):
    # -----------------------------------------------------
    # 例:
    # This could be Cherki's moment for Man City
    # -----------------------------------------------------
    pattern = re.compile(
        r"this could be "
        r"(.+?)['’]s moment for "
        r"(.+)$",
        re.IGNORECASE,
    )

    match = pattern.search(text)

    if match:
        person = entity_to_ja(
            match.group(1)
        )

        club = entity_to_ja(
            match.group(2)
        )

        prefix = text[:match.start()].strip()

        if prefix:
            prefix_ja = translate_simple_phrase(prefix)

            return (
                f"{prefix_ja}――"
                f"{person}が{club}で"
                f"輝く時が来たか"
            )

        return (
            f"{person}が{club}で"
            f"輝く時が来たか"
        )

    # -----------------------------------------------------
    # BBCで今回出た文章のような構造
    #
    # After two goals and a swaggering display against
    # Crystal Palace, Phil McNulty asks if this is
    # Rayan Cherki's time to shine for Manchester City.
    # -----------------------------------------------------
    pattern = re.compile(
        r"After two goals and a swaggering display against "
        r"(.+?), "
        r"(.+?) asks if this is "
        r"(.+?)['’]s time to shine for "
        r"(.+?)[.]?$",
        re.IGNORECASE,
    )

    match = pattern.match(text)

    if match:
        opponent = entity_to_ja(
            match.group(1)
        )

        journalist = entity_to_ja(
            match.group(2)
        )

        player = entity_to_ja(
            match.group(3)
        )

        club = entity_to_ja(
            match.group(4)
        )

        return (
            f"{opponent}戦で2ゴールを挙げ、"
            f"圧巻のパフォーマンスを見せた{player}。"
            f"{journalist}は、"
            f"{club}で{player}が"
            f"輝く時が来たのかを問う。"
        )

    return None


# smart_source_rewrite内から使う簡易表現補正
def translate_simple_phrase(text):
    lower = text.lower().strip(" -–—")

    known = {
        "a magician and a maverick":
            "魔術師のような技巧と型破りな才能",

        "a magician and a maverick -":
            "魔術師のような技巧と型破りな才能",

        "magician and a maverick":
            "魔術師のような技巧と型破りな才能",

        "a magician":
            "魔術師のような技巧",

        "a maverick":
            "型破りな才能",
    }

    if lower in known:
        return known[lower]

    return text.strip(" -–—")


# =========================================================
# 通常翻訳
# =========================================================

def translate_piece(translator, text):
    if not text:
        return ""

    if not re.search(r"[A-Za-z]", text):
        return text

    try:
        return translator.translate(text)

    except Exception as error:
        print(
            "Piece translation failed:",
            error,
        )
        return text


def translate_preserving_entities(
    translator,
    text,
):
    spans = find_protected_spans(text)
    spans = add_unknown_name_spans(
        text,
        spans,
    )

    if not spans:
        return translate_piece(
            translator,
            text,
        )

    result = []
    position = 0

    for start, end, replacement in spans:
        if start > position:
            normal_text = text[
                position:start
            ]

            result.append(
                translate_piece(
                    translator,
                    normal_text,
                )
            )

        result.append(replacement)
        position = end

    if position < len(text):
        result.append(
            translate_piece(
                translator,
                text[position:]
            )
        )

    return "".join(result)


# =========================================================
# 第3段階：翻訳後の日本語をサッカー記事向けに補正
# =========================================================

def football_postprocess(text):
    fixes = {
        # クラブ
        "マンシティ":
            "マンチェスター・シティ",

        "マンチェスターシティ":
            "マンチェスター・シティ",

        "マンU":
            "マンチェスター・ユナイテッド",

        "レアルマドリード":
            "レアル・マドリード",

        "クリスタルパレス":
            "クリスタル・パレス",

        "アトレティコマドリード":
            "アトレティコ・マドリード",

        # 選手・人物
        "レイアン・チェレキ":
            "ラヤン・シェルキ",

        "レイアン・チェルキ":
            "ラヤン・シェルキ",

        "チェレキ":
            "シェルキ",

        "チェルキ":
            "シェルキ",

        "フィル・マッナルティ":
            "フィル・マクナルティ",

        # 大会
        "ラリーガ":
            "ラ・リーガ",

        "セリエ A":
            "セリエA",

        "ブンデス・リーガ":
            "ブンデスリーガ",

        # サッカー文脈
        "2つの目標":
            "2ゴール",

        "二つの目標":
            "2ゴール",

        "3つの目標":
            "3ゴール",

        "目標を決め":
            "ゴールを決め",

        "目標を挙げ":
            "ゴールを挙げ",

        "分散表示":
            "パフォーマンス",

        "華やかなディスプレイ":
            "圧巻のパフォーマンス",

        "印象的なディスプレイ":
            "印象的なパフォーマンス",

        "優れたディスプレイ":
            "素晴らしいパフォーマンス",

        "シェルキの瞬間":
            "シェルキが輝く時",

        "輝く時間":
            "輝く時",

        "ペナルティシュートアウト":
            "PK戦",

        "ペナルティーシュートアウト":
            "PK戦",

        "解雇された":
            "解任された",
    }

    for old, new in fixes.items():
        text = text.replace(
            old,
            new,
        )

    # ZXQ等の旧方式の残骸が万一あっても表示しない
    text = re.sub(
        r"\bZXQ(?:FB)?\w*\b",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"\s+([。、！？])",
        r"\1",
        text,
    )

    text = re.sub(
        r"([。、！？])\s+",
        r"\1",
        text,
    )

    text = re.sub(
        r"\s{2,}",
        " ",
        text,
    )

    return text.strip()


def translate_football_text(
    translator,
    text,
):
    if not text:
        return ""

    if translator is None:
        return text

    # まず高度なサッカー定型文処理
    rewritten = smart_source_rewrite(text)

    if rewritten:
        return football_postprocess(
            rewritten
        )

    # それ以外は固有名詞保護＋通常翻訳
    translated = translate_preserving_entities(
        translator,
        text,
    )

    return football_postprocess(
        translated
    )


# =========================================================
# 前回データ
# =========================================================

previous = {}

if DATA_PATH.exists():
    try:
        old_data = json.loads(
            DATA_PATH.read_text(
                encoding="utf-8"
            )
        )

        for item in old_data.get(
            "items",
            [],
        ):
            url = item.get("url")

            if url:
                previous[url] = item

    except Exception as error:
        print(
            "Could not read previous data:",
            error,
        )


translator = prepare_translator()

items = []


# =========================================================
# RSS取得
# =========================================================

for source, feed_url in FEEDS:
    try:
        root = ET.fromstring(
            fetch(feed_url)
        )

        for feed_item in root.findall(
            ".//item"
        )[:30]:

            original_title = clean(
                feed_item.findtext(
                    "title"
                )
            )

            original_summary = clean(
                feed_item.findtext(
                    "description"
                )
            )

            link = clean(
                feed_item.findtext(
                    "link"
                )
            )

            published = clean(
                feed_item.findtext(
                    "pubDate"
                )
            )

            if not original_title or not link:
                continue

            category, label, item_type = classify(
                original_title,
                original_summary,
            )

            combined = (
                f"{original_title} "
                f"{original_summary}"
            ).lower()

            featured = any(
                priority in combined
                for priority in PRIORITY
            )

            old = previous.get(
                link,
                {},
            )

            reuse_translation = (
                old.get(
                    "translation_version"
                )
                == TRANSLATION_VERSION

                and old.get(
                    "title_original"
                )
                == original_title

                and old.get(
                    "summary_original"
                )
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

                "title_original":
                    original_title,

                "summary_original":
                    original_summary[:500],

                "source": source,
                "url": link,
                "published": published,

                "category": category,
                "type": item_type,
                "label": label,

                "featured": featured,

                "translation_version":
                    TRANSLATION_VERSION,
            })

    except Exception as error:
        print(
            "Feed failed:",
            source,
            error,
        )


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
    "updated_at":
        datetime.now(
            timezone.utc
        ).isoformat(),

    "items":
        unique_items[:80],
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
