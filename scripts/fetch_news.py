import json
import re
import html
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

import argostranslate.package
import argostranslate.translate


TRANSLATION_VERSION = "football-ja-v5"
DATA_PATH = Path("data/news.json")


FEEDS = [
    ("BBC Sport", "https://feeds.bbci.co.uk/sport/football/rss.xml"),
    ("The Guardian Football", "https://www.theguardian.com/football/rss"),
    ("Sky Sports Football", "https://www.skysports.com/rss/12040"),
    ("ESPN FC", "https://www.espn.com/espn/rss/soccer/news"),
]


# =========================================================
# 第1段階
# 大会・クラブ・監督などの固定辞書
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
    "Palace": "クリスタル・パレス",
    "Everton": "エヴァートン",
    "West Ham United": "ウェストハム",
    "West Ham": "ウェストハム",
    "Brighton": "ブライトン",
    "Wrexham": "レクサム",
    "Rangers": "レンジャーズ",

    # スペイン
    "Real Madrid": "レアル・マドリード",
    "FC Barcelona": "バルセロナ",
    "Barcelona": "バルセロナ",
    "Barca": "バルセロナ",
    "Barça": "バルセロナ",
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
    "Derek McInnes": "デレク・マッキネス",
    "McInnes": "マッキネス",
}


# =========================================================
# 第2段階
# 成長型の選手名辞書
# =========================================================

PLAYER_NAME_OVERRIDES = {
    # レアル
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
    "Bukayo Saka": "ブカヨ・サカ",
    "Saka": "サカ",
    "Martin Ødegaard": "マルティン・ウーデゴール",
    "Martin Odegaard": "マルティン・ウーデゴール",
    "Cole Palmer": "コール・パーマー",
    "Palmer": "パーマー",
    "Bruno Fernandes": "ブルーノ・フェルナンデス",
    "Son Heung-min": "ソン・フンミン",
    "Marcus Rashford": "マーカス・ラッシュフォード",
    "Rashford": "ラッシュフォード",
    "Adam Wharton": "アダム・ウォートン",
    "Wharton": "ウォートン",
    "Harvey Elliott": "ハーヴェイ・エリオット",
    "Elliott": "エリオット",
    "Dom Hyam": "ドム・ハイアム",
    "Lamine Camara": "ラミン・カマラ",

    # セリエA
    "Lautaro Martínez": "ラウタロ・マルティネス",
    "Lautaro Martinez": "ラウタロ・マルティネス",
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

    # 記者
    "Phil McNulty": "フィル・マクナルティ",
    "McNulty": "マクナルティ",
}


# =========================================================
# 第3段階
# サッカー用語
# =========================================================

FOOTBALL_PHRASE_OVERRIDES = {
    "clean sheet": "クリーンシート",
    "hat-trick": "ハットトリック",
    "hat trick": "ハットトリック",
    "two goals": "2ゴール",
    "three goals": "3ゴール",
    "brace": "2ゴール",
    "swaggering display": "圧巻のパフォーマンス",
    "impressive display": "印象的なパフォーマンス",
    "superb display": "素晴らしいパフォーマンス",
    "fine display": "好パフォーマンス",
    "player ratings": "選手採点",
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
    "Saturday's gossip": "土曜日の移籍ゴシップ",
    "Sunday's gossip": "日曜日の移籍ゴシップ",
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
        headers={"User-Agent": "EURO-Football-Portal/5.0"},
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
        "barca",
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
            if p.from_code == "en"
            and p.to_code == "ja"
        )

        downloaded = package.download()

        argostranslate.package.install_from_path(
            downloaded
        )

        installed = (
            argostranslate.translate
            .get_installed_languages()
        )

        english = next(
            lang for lang in installed
            if lang.code == "en"
        )

        japanese = next(
            lang for lang in installed
            if lang.code == "ja"
        )

        return english.get_translation(
            japanese
        )

    except Exception as error:
        print(
            "Translator setup failed:",
            error,
        )

        return None


# =========================================================
# 固有名詞処理
# =========================================================

def combined_entities():
    result = {}

    result.update(
        FOOTBALL_ENTITY_OVERRIDES
    )

    result.update(
        PLAYER_NAME_OVERRIDES
    )

    result.update(
        FOOTBALL_PHRASE_OVERRIDES
    )

    return result


def entity_to_ja(name):
    name = name.strip()

    for english, japanese in (
        combined_entities().items()
    ):
        if english.lower() == name.lower():
            return japanese

    return name


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
                    len(match.group(0)),
                )
            )

    candidates.sort(
        key=lambda x: (
            x[0],
            -x[3],
        )
    )

    selected = []

    for start, end, replacement, _ in candidates:
        overlap = any(
            start < old_end
            and end > old_start
            for old_start, old_end, _
            in selected
        )

        if not overlap:
            selected.append(
                (
                    start,
                    end,
                    replacement,
                )
            )

    selected.sort(
        key=lambda x: x[0]
    )

    return selected


UNKNOWN_NAME_PATTERN = re.compile(
    r"\b("
    r"[A-ZÀ-ÖØ-Ý]"
    r"[A-Za-zÀ-ÖØ-öø-ÿ'’-]+"
    r"(?:\s+"
    r"[A-ZÀ-ÖØ-Ý]"
    r"[A-Za-zÀ-ÖØ-öø-ÿ'’-]+"
    r"){1,2}"
    r")\b"
)


UNKNOWN_NAME_STOPWORDS = {
    "Premier League",
    "Champions League",
    "Europa League",
    "Conference League",
    "Saturday Gossip",
    "Sunday Gossip",
}


def add_unknown_name_spans(
    text,
    spans,
):
    occupied = [
        (start, end)
        for start, end, _
        in spans
    ]

    for match in (
        UNKNOWN_NAME_PATTERN
        .finditer(text)
    ):
        phrase = match.group(1)

        if phrase in UNKNOWN_NAME_STOPWORDS:
            continue

        start = match.start()
        end = match.end()

        overlap = any(
            start < old_end
            and end > old_start
            for old_start, old_end
            in occupied
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

        occupied.append(
            (start, end)
        )

    spans.sort(
        key=lambda x: x[0]
    )

    return spans


def translate_piece(
    translator,
    text,
):
    if not text:
        return ""

    if not re.search(
        r"[A-Za-z]",
        text,
    ):
        return text

    try:
        return translator.translate(
            text
        )

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
    spans = find_protected_spans(
        text
    )

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
            result.append(
                translate_piece(
                    translator,
                    text[position:start],
                )
            )

        result.append(
            replacement
        )

        position = end

    if position < len(text):
        result.append(
            translate_piece(
                translator,
                text[position:],
            )
        )

    return "".join(result)


# =========================================================
# 第4段階
# サッカーニュース見出し専用の自然化
# =========================================================

def rewrite_headline(title):
    raw = title.strip()
    lower = raw.lower()

    # Do Wrexham have defensive problems?
    match = re.fullmatch(
        r"Do (.+?) have defensive problems\?",
        raw,
        flags=re.IGNORECASE,
    )

    if match:
        club = entity_to_ja(
            match.group(1)
        )

        return (
            f"{club}に守備面の"
            f"問題はあるのか？"
        )


    # McInnes backs himself to bring Rangers success
    match = re.fullmatch(
        r"(.+?) backs himself to bring "
        r"(.+?) success",
        raw,
        flags=re.IGNORECASE,
    )

    if match:
        person = entity_to_ja(
            match.group(1)
        )

        club = entity_to_ja(
            match.group(2)
        )

        return (
            f"{person}、自らの手腕に自信　"
            f"{club}を成功へ導けるか"
        )


    # Cherki genius and Wharton excels -
    # Palace v Man City player ratings
    match = re.fullmatch(
        r"(.+?) genius and (.+?) excels"
        r"\s*-\s*"
        r"(.+?) v (.+?) player ratings",
        raw,
        flags=re.IGNORECASE,
    )

    if match:
        player1 = entity_to_ja(
            match.group(1)
        )

        player2 = entity_to_ja(
            match.group(2)
        )

        team1 = entity_to_ja(
            match.group(3)
        )

        team2 = entity_to_ja(
            match.group(4)
        )

        return (
            f"{player1}が圧巻、"
            f"{player2}も高評価　"
            f"{team1}対{team2}の選手採点"
        )


    # Arsenal & Barca monitor Rashford -
    # Saturday's gossip
    match = re.fullmatch(
        r"(.+?)\s*&\s*(.+?) "
        r"monitor (.+?)"
        r"\s*-\s*"
        r"(Saturday|Sunday)'s gossip",
        raw,
        flags=re.IGNORECASE,
    )

    if match:
        club1 = entity_to_ja(
            match.group(1)
        )

        club2 = entity_to_ja(
            match.group(2)
        )

        player = entity_to_ja(
            match.group(3)
        )

        day = (
            match.group(4)
            .lower()
        )

        if day == "saturday":
            day_ja = "土曜日"
        else:
            day_ja = "日曜日"

        return (
            f"{club1}と{club2}が"
            f"{player}を注視　"
            f"{day_ja}の移籍ゴシップ"
        )


    # A magician and a maverick -
    # this could be Cherki's moment for Man City
    match = re.fullmatch(
        r"A magician and a maverick"
        r"\s*-\s*"
        r"this could be "
        r"(.+?)['’]s moment for (.+)",
        raw,
        flags=re.IGNORECASE,
    )

    if match:
        player = entity_to_ja(
            match.group(1)
        )

        club = entity_to_ja(
            match.group(2)
        )

        return (
            f"技巧と型破りな才能――"
            f"{player}が{club}で"
            f"輝く時が来たか"
        )


    # Bundesligaの小都市記事
    if (
        "bundesliga debut" in lower
        and "small town" in lower
    ):
        return (
            "小さな町からブンデスリーガへ――"
            "番狂わせを狙う挑戦"
        )


    return None


# =========================================================
# 要約専用の自然化
# =========================================================

def rewrite_summary(summary):
    raw = summary.strip()

    # シェルキ記事
    match = re.fullmatch(
        r"After two goals and a swaggering "
        r"display against (.+?), "
        r"(.+?) asks if this is "
        r"(.+?)['’]s time to shine "
        r"for (.+?)[.]?",
        raw,
        flags=re.IGNORECASE,
    )

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
            f"圧巻のパフォーマンスを見せた"
            f"{player}。"
            f"{journalist}は、"
            f"{club}で{player}が"
            f"輝く時が来たのかを問う。"
        )


    # Wrexham守備記事
    match = re.fullmatch(
        r"Defender (.+?) suggests "
        r"(.+?) need to find a "
        r"['“\"]ruthless['”\"] streak "
        r"to address their defensive "
        r"problems[.]?",
        raw,
        flags=re.IGNORECASE,
    )

    if match:
        player = entity_to_ja(
            match.group(1)
        )

        club = entity_to_ja(
            match.group(2)
        )

        return (
            f"DF{player}は、"
            f"{club}が守備面の課題を"
            f"改善するには、"
            f"より勝負に徹する姿勢が"
            f"必要だと指摘した。"
        )


    return None


# =========================================================
# 翻訳後の日本語補正
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

        # 人名
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

        # サッカー表現
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

        "輝く時間":
            "輝く時",

        "ペナルティシュートアウト":
            "PK戦",

        "ペナルティーシュートアウト":
            "PK戦",

        "解雇された":
            "解任された",

        # 不自然な一般翻訳
        "自分自身をバックアップ":
            "自らの手腕に自信を見せ",

        "防御的な問題":
            "守備面の問題",

        "防御問題":
            "守備面の問題",

        "成功をもたらす":
            "成功へ導く",

        "プレイヤーの評価":
            "選手採点",

        "プレイヤー評価":
            "選手採点",
    }


    for old, new in fixes.items():
        text = text.replace(
            old,
            new,
        )


    # 英語の所有格が残った場合
    text = re.sub(
        r"([ァ-ヶー一-龠々]+)'s",
        r"\1の",
        text,
    )


    # 英字と日本語の密着を防止
    text = re.sub(
        r"([A-Za-z0-9])"
        r"([ぁ-んァ-ヶ一-龠])",
        r"\1 \2",
        text,
    )

    text = re.sub(
        r"([ぁ-んァ-ヶ一-龠])"
        r"([A-Za-z])",
        r"\1 \2",
        text,
    )


    # 句読点整理
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


# =========================================================
# 最終翻訳
# =========================================================

def translate_title(
    translator,
    title,
):
    rewritten = rewrite_headline(
        title
    )

    if rewritten:
        return football_postprocess(
            rewritten
        )

    translated = (
        translate_preserving_entities(
            translator,
            title,
        )
    )

    return football_postprocess(
        translated
    )


def translate_summary(
    translator,
    summary,
):
    rewritten = rewrite_summary(
        summary
    )

    if rewritten:
        return football_postprocess(
            rewritten
        )

    translated = (
        translate_preserving_entities(
            translator,
            summary,
        )
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

            if (
                not original_title
                or not link
            ):
                continue


            category, label, item_type = (
                classify(
                    original_title,
                    original_summary,
                )
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
                title_ja = translate_title(
                    translator,
                    original_title,
                )

                summary_ja = translate_summary(
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

    unique_items.append(
        item
    )


# =========================================================
# JSON保存
# =========================================================

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
    f"Saved "
    f"{len(output['items'])} "
    f"football articles"
)
