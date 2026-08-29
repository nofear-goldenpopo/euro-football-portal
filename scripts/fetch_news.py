import json
import re
import html
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

import argostranslate.package
import argostranslate.translate


TRANSLATION_VERSION = "football-ja-v7"
DATA_PATH = Path("data/news.json")

FEEDS = [
    ("BBC Sport", "https://feeds.bbci.co.uk/sport/football/rss.xml"),
    ("The Guardian Football", "https://www.theguardian.com/football/rss"),
    ("Sky Sports Football", "https://www.skysports.com/rss/12040"),
    ("ESPN FC", "https://www.espn.com/espn/rss/soccer/news"),
]


# =========================================================
# 固定辞書
# ここにある名前はWikipedia照合より優先します
# =========================================================

FOOTBALL_ENTITY_OVERRIDES = {
    # UEFA大会
    "UEFA Champions League": "UEFAチャンピオンズリーグ",
    "Champions League": "チャンピオンズリーグ",
    "UEFA Europa League": "UEFAヨーロッパリーグ",
    "Europa League": "ヨーロッパリーグ",
    "UEFA Conference League": "UEFAカンファレンスリーグ",
    "Conference League": "カンファレンスリーグ",

    # 主要リーグ
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
    "Nottingham Forest": "ノッティンガム・フォレスト",

    # スペイン
    "Real Madrid": "レアル・マドリード",
    "FC Barcelona": "バルセロナ",
    "Barcelona": "バルセロナ",
    "Barca": "バルセロナ",
    "Barça": "バルセロナ",
    "Atletico Madrid": "アトレティコ・マドリード",
    "Atlético Madrid": "アトレティコ・マドリード",
    "Athletic Club": "アスレティック・ビルバオ",
    "Real Sociedad": "レアル・ソシエダ",
    "Villarreal": "ビジャレアル",
    "Sevilla": "セビージャ",
    "Real Betis": "レアル・ベティス",

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
    "Bologna": "ボローニャ",

    # ドイツ
    "Bayern Munich": "バイエルン・ミュンヘン",
    "Bayern": "バイエルン",
    "Borussia Dortmund": "ボルシア・ドルトムント",
    "Dortmund": "ドルトムント",
    "Bayer Leverkusen": "レヴァークーゼン",
    "RB Leipzig": "RBライプツィヒ",
    "Eintracht Frankfurt": "アイントラハト・フランクフルト",
    "Stuttgart": "シュトゥットガルト",

    # フランス
    "Paris Saint-Germain": "パリ・サンジェルマン",
    "Paris St-Germain": "パリ・サンジェルマン",
    "PSG": "パリ・サンジェルマン",
    "Marseille": "マルセイユ",
    "Monaco": "モナコ",
    "Lille": "リール",
    "Lyon": "リヨン",

    # オランダ
    "Ajax": "アヤックス",
    "PSV Eindhoven": "PSVアイントホーフェン",
    "PSV": "PSV",
    "Feyenoord": "フェイエノールト",
    "AZ Alkmaar": "AZアルクマール",

    # ポルトガル
    "Benfica": "ベンフィカ",
    "FC Porto": "ポルト",
    "Porto": "ポルト",
    "Sporting CP": "スポルティングCP",
    "Braga": "ブラガ",

    # トルコ
    "Galatasaray": "ガラタサライ",
    "Fenerbahce": "フェネルバフチェ",
    "Fenerbahçe": "フェネルバフチェ",
    "Besiktas": "ベシクタシュ",
    "Beşiktaş": "ベシクタシュ",

    # スコットランド
    "Celtic": "セルティック",
    "Rangers": "レンジャーズ",

    # その他欧州で頻出
    "Club Brugge": "クラブ・ブルッヘ",
    "Anderlecht": "アンデルレヒト",
    "Union Saint-Gilloise": "ユニオン・サン＝ジロワーズ",
    "RB Salzburg": "RBザルツブルク",
    "Red Bull Salzburg": "RBザルツブルク",
    "Sturm Graz": "シュトゥルム・グラーツ",
    "Slavia Prague": "スラヴィア・プラハ",
    "Sparta Prague": "スパルタ・プラハ",
    "Dinamo Zagreb": "ディナモ・ザグレブ",
    "Red Star Belgrade": "レッドスター・ベオグラード",
    "Olympiacos": "オリンピアコス",
    "Panathinaikos": "パナシナイコス",
    "PAOK": "PAOK",
    "Shakhtar Donetsk": "シャフタール・ドネツク",
    "Dynamo Kyiv": "ディナモ・キーウ",
    "Young Boys": "ヤングボーイズ",
    "Basel": "バーゼル",
    "Copenhagen": "コペンハーゲン",
    "Midtjylland": "ミッティラン",
    "Bodo/Glimt": "ボデ/グリムト",
    "Bodø/Glimt": "ボデ/グリムト",
    "Malmo": "マルメ",
    "Malmö": "マルメ",
    "Ferencvaros": "フェレンツヴァーロシュ",
    "Ferencváros": "フェレンツヴァーロシュ",

    # 監督・著名人
    "José Mourinho": "ジョゼ・モウリーニョ",
    "Jose Mourinho": "ジョゼ・モウリーニョ",
    "Mourinho": "モウリーニョ",
    "Pep Guardiola": "ペップ・グアルディオラ",
    "Guardiola": "グアルディオラ",
    "Mikel Arteta": "ミケル・アルテタ",
    "Arteta": "アルテタ",
    "Arne Slot": "アルネ・スロット",
    "Hansi Flick": "ハンジ・フリック",
    "Diego Simeone": "ディエゴ・シメオネ",
    "Antonio Conte": "アントニオ・コンテ",
    "Luis Enrique": "ルイス・エンリケ",
    "Vincent Kompany": "ヴァンサン・コンパニ",
    "Xabi Alonso": "シャビ・アロンソ",
    "Simone Inzaghi": "シモーネ・インザーギ",
}


PLAYER_NAME_OVERRIDES = {
    # レアル・マドリード
    "Kylian Mbappé": "キリアン・エムバペ",
    "Kylian Mbappe": "キリアン・エムバペ",
    "Mbappé": "エムバペ",
    "Mbappe": "エムバペ",
    "Vinícius Júnior": "ヴィニシウス・ジュニオール",
    "Vinicius Junior": "ヴィニシウス・ジュニオール",
    "Jude Bellingham": "ジュード・ベリンガム",
    "Bellingham": "ベリンガム",
    "Federico Valverde": "フェデリコ・バルベルデ",
    "Thibaut Courtois": "ティボー・クルトワ",

    # バルセロナ
    "Lamine Yamal": "ラミン・ヤマル",
    "Yamal": "ヤマル",
    "Pedri": "ペドリ",
    "Gavi": "ガビ",
    "Raphinha": "ラフィーニャ",
    "Robert Lewandowski": "ロベルト・レヴァンドフスキ",

    # PSG
    "Bradley Barcola": "ブラッドリー・バルコラ",
    "Barcola": "バルコラ",
    "Ousmane Dembélé": "ウスマン・デンベレ",
    "Ousmane Dembele": "ウスマン・デンベレ",
    "Khvicha Kvaratskhelia": "フヴィチャ・クヴァラツヘリア",
    "Vitinha": "ヴィティーニャ",
    "Achraf Hakimi": "アクラフ・ハキミ",

    # プレミア
    "Erling Haaland": "アーリング・ハーランド",
    "Haaland": "ハーランド",
    "Rayan Cherki": "ラヤン・シェルキ",
    "Cherki": "シェルキ",
    "Phil Foden": "フィル・フォーデン",
    "Mohamed Salah": "モハメド・サラー",
    "Virgil van Dijk": "フィルジル・ファン・ダイク",
    "Bukayo Saka": "ブカヨ・サカ",
    "Martin Ødegaard": "マルティン・ウーデゴール",
    "Martin Odegaard": "マルティン・ウーデゴール",
    "Cole Palmer": "コール・パーマー",
    "Bruno Fernandes": "ブルーノ・フェルナンデス",
    "Marcus Rashford": "マーカス・ラッシュフォード",
    "Adam Wharton": "アダム・ウォートン",
    "Florian Wirtz": "フロリアン・ヴィルツ",
    "Alexander Isak": "アレクサンデル・イサク",

    # セリエA
    "Lautaro Martínez": "ラウタロ・マルティネス",
    "Lautaro Martinez": "ラウタロ・マルティネス",
    "Nicolò Barella": "ニコロ・バレッラ",
    "Nicolo Barella": "ニコロ・バレッラ",
    "Alessandro Bastoni": "アレッサンドロ・バストーニ",

    # ブンデス
    "Harry Kane": "ハリー・ケイン",
    "Jamal Musiala": "ジャマル・ムシアラ",

    # 記者
    "Phil McNulty": "フィル・マクナルティ",
}


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
    "Saturday's gossip": "土曜日の移籍ゴシップ",
    "Sunday's gossip": "日曜日の移籍ゴシップ",
}


PRIORITY = [
    "champions league",
    "europa league",
    "conference league",
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
    "transfer",
]


def fetch(url):
    request = Request(
        url,
        headers={"User-Agent": "EURO-Football-Portal/7.0"},
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

    if "europa league" in text:
        return "uel", "EL", "uel"

    if "conference league" in text:
        return "uecl", "ECL", "uecl"

    if any(x in text for x in [
        "premier league", "manchester city", "man city",
        "manchester united", "man utd", "liverpool", "arsenal",
        "chelsea", "tottenham", "newcastle", "aston villa",
        "crystal palace",
    ]):
        return "epl", "プレミア", "epl"

    if any(x in text for x in [
        "la liga", "real madrid", "barcelona", "barca",
        "atletico madrid", "atlético madrid", "real sociedad",
        "villarreal",
    ]):
        return "laliga", "ラ・リーガ", "laliga"

    if any(x in text for x in [
        "serie a", "inter", "ac milan", "juventus", "roma",
        "atalanta", "napoli", "lazio",
    ]):
        return "seriea", "セリエA", "seriea"

    if any(x in text for x in [
        "bundesliga", "bayern", "borussia dortmund",
        "leverkusen", "rb leipzig",
    ]):
        return "bundesliga", "ブンデス", "bundesliga"

    if any(x in text for x in [
        "transfer", "signing", "signed", "signs", "loan",
        "deal", "move", "fee", "medical", "personal terms",
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
        english = next((x for x in installed if x.code == "en"), None)
        japanese = next((x for x in installed if x.code == "ja"), None)

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
        english = next(x for x in installed if x.code == "en")
        japanese = next(x for x in installed if x.code == "ja")
        return english.get_translation(japanese)

    except Exception as error:
        print("Translator setup failed:", error)
        return None


def combined_entities(dynamic_entities=None):
    result = {}
    result.update(FOOTBALL_ENTITY_OVERRIDES)
    result.update(PLAYER_NAME_OVERRIDES)
    result.update(FOOTBALL_PHRASE_OVERRIDES)
    if dynamic_entities:
        result.update(dynamic_entities)
    return result


# =========================================================
# Wikipedia日本語名の自動補完
# 英語Wikipediaの同名ページに日本語版がある場合、
# 日本語ページ名を固有名詞表記として利用します。
# =========================================================

UNKNOWN_NAME_PATTERN = re.compile(
    r"\b("
    r"[A-ZÀ-ÖØ-Ý][A-Za-zÀ-ÖØ-öø-ÿ'’.-]+"
    r"(?:\s+[A-ZÀ-ÖØ-Ý][A-Za-zÀ-ÖØ-öø-ÿ'’.-]+){1,3}"
    r")\b"
)

UNKNOWN_NAME_STOPWORDS = {
    "Premier League",
    "Champions League",
    "UEFA Champions League",
    "Europa League",
    "UEFA Europa League",
    "Conference League",
    "UEFA Conference League",
    "Saturday Gossip",
    "Sunday Gossip",
    "BBC Sport",
    "Sky Sports",
    "The Guardian",
}


def extract_unknown_candidates(text, known_entities):
    results = []
    known_lower = {key.lower() for key in known_entities}

    for match in UNKNOWN_NAME_PATTERN.finditer(text or ""):
        phrase = match.group(1).strip()
        if phrase in UNKNOWN_NAME_STOPWORDS:
            continue
        if phrase.lower() in known_lower:
            continue

        words = phrase.split()
        # 見出しの一般語を人名と誤認しにくくする
        generic = {
            "After", "Before", "Why", "How", "What", "When", "Where",
            "Could", "Would", "Should", "Premier", "Champions", "Europa",
            "Conference", "League", "Transfer", "Football", "Saturday",
            "Sunday",
        }
        if any(word in generic for word in words):
            continue

        results.append(phrase)

    return results


def wikipedia_ja_batch(names, cache):
    names = [n for n in dict.fromkeys(names) if n and n not in cache]
    if not names:
        return

    # 1回20件にしてWikipedia APIへの負荷を抑える
    for start in range(0, len(names), 20):
        batch = names[start:start + 20]

        try:
            params = urlencode({
                "action": "query",
                "format": "json",
                "formatversion": "2",
                "redirects": "1",
                "prop": "langlinks",
                "lllang": "ja",
                "lllimit": "1",
                "titles": "|".join(batch),
            })

            request = Request(
                "https://en.wikipedia.org/w/api.php?" + params,
                headers={
                    "User-Agent":
                        "EURO-Football-Portal/7.0 "
                        "(GitHub Pages football news translator)"
                },
            )

            with urlopen(request, timeout=15) as response:
                data = json.loads(response.read().decode("utf-8"))

            query = data.get("query", {})
            normalized = {
                x.get("from"): x.get("to")
                for x in query.get("normalized", [])
            }
            redirects = {
                x.get("from"): x.get("to")
                for x in query.get("redirects", [])
            }

            page_by_title = {
                p.get("title"): p
                for p in query.get("pages", [])
                if not p.get("missing")
            }

            for original in batch:
                title = normalized.get(original, original)
                title = redirects.get(title, title)
                page = page_by_title.get(title, {})
                links = page.get("langlinks", [])

                if links:
                    ja_title = links[0].get("title", "").strip()
                    cache[original] = ja_title
                else:
                    # 空文字もキャッシュし、次回以降の再照会を防ぐ
                    cache[original] = ""

        except Exception as error:
            print("Wikipedia lookup failed:", error)
            # 通信失敗時は空文字を保存しない。
            # 次回の更新時に再試行できるようにする。


def entity_to_ja(name, dynamic_entities):
    name = name.strip()
    for english, japanese in combined_entities(dynamic_entities).items():
        if english.lower() == name.lower():
            return japanese
    return name


def find_protected_spans(text, dynamic_entities):
    candidates = []

    entries = sorted(
        combined_entities(dynamic_entities).items(),
        key=lambda item: len(item[0]),
        reverse=True,
    )

    for english, japanese in entries:
        pattern = re.compile(re.escape(english), re.IGNORECASE)
        for match in pattern.finditer(text):
            candidates.append(
                (match.start(), match.end(), japanese, len(match.group(0)))
            )

    candidates.sort(key=lambda x: (x[0], -x[3]))
    selected = []

    for start, end, replacement, _ in candidates:
        overlap = any(
            start < old_end and end > old_start
            for old_start, old_end, _ in selected
        )
        if not overlap:
            selected.append((start, end, replacement))

    selected.sort(key=lambda x: x[0])
    return selected


def add_unknown_name_spans(text, spans):
    occupied = [(start, end) for start, end, _ in spans]

    for match in UNKNOWN_NAME_PATTERN.finditer(text):
        phrase = match.group(1)
        if phrase in UNKNOWN_NAME_STOPWORDS:
            continue

        start, end = match.start(), match.end()
        overlap = any(
            start < old_end and end > old_start
            for old_start, old_end in occupied
        )
        if overlap:
            continue

        # Wikipediaで日本語名が見つからなかった名前は
        # Argosに壊されないよう英語表記のまま保護する
        spans.append((start, end, phrase))
        occupied.append((start, end))

    spans.sort(key=lambda x: x[0])
    return spans


def translate_piece(translator, text):
    if not text:
        return ""
    if not re.search(r"[A-Za-z]", text):
        return text
    if translator is None:
        return text

    try:
        return translator.translate(text)
    except Exception as error:
        print("Piece translation failed:", error)
        return text


def translate_preserving_entities(translator, text, dynamic_entities):
    spans = find_protected_spans(text, dynamic_entities)
    spans = add_unknown_name_spans(text, spans)

    if not spans:
        return translate_piece(translator, text)

    result = []
    position = 0

    for start, end, replacement in spans:
        if start > position:
            result.append(
                translate_piece(translator, text[position:start])
            )
        result.append(replacement)
        position = end

    if position < len(text):
        result.append(translate_piece(translator, text[position:]))

    return "".join(result)


# =========================================================
# 見出し・要約の自然化
# =========================================================

def format_millions(amount, currency="£"):
    amount = int(amount)

    if currency == "€":
        unit = "ユーロ"
    else:
        unit = "ポンド"

    if amount >= 100:
        oku = amount // 100
        man = (amount % 100) * 100
        if man:
            return f"{oku}億{man}万{unit}"
        return f"{oku}億{unit}"

    return f"{amount * 100}万{unit}"


def rewrite_headline(title, dynamic_entities):
    raw = title.strip()
    lower = raw.lower()

    # =====================================================
    # v7: 移籍ニュース見出しの自然化
    # =====================================================

    # Liverpool agree £123m deal for Paris St-Germain's Barcola
    match = re.fullmatch(
        r"(.+?) agree(?:s)?\s+(?:a\s+)?([£€])([0-9]+(?:\.[0-9]+)?)m\s+"
        r"(?:deal|fee)\s+for\s+(.+?)['’]s\s+(.+)",
        raw,
        flags=re.IGNORECASE,
    )
    if match:
        buyer = entity_to_ja(match.group(1), dynamic_entities)
        currency = match.group(2)
        amount_raw = float(match.group(3))
        seller = entity_to_ja(match.group(4), dynamic_entities)
        player = entity_to_ja(match.group(5), dynamic_entities)

        if amount_raw.is_integer():
            amount_ja = format_millions(int(amount_raw), currency)
        else:
            unit = "ユーロ" if currency == "€" else "ポンド"
            amount_ja = f"{amount_raw:g}百万{unit}"

        return (
            f"{buyer}、{seller}の{player}獲得で"
            f"{amount_ja}合意"
        )

    # Liverpool agree deal for PSG's Barcola
    match = re.fullmatch(
        r"(.+?) agree(?:s)?\s+(?:a\s+)?deal\s+for\s+(.+?)['’]s\s+(.+)",
        raw,
        flags=re.IGNORECASE,
    )
    if match:
        buyer = entity_to_ja(match.group(1), dynamic_entities)
        seller = entity_to_ja(match.group(2), dynamic_entities)
        player = entity_to_ja(match.group(3), dynamic_entities)
        return f"{buyer}、{seller}の{player}獲得で合意"

    # Liverpool make enquiry for PSG's Barcola
    match = re.fullmatch(
        r"(.+?) (?:make|makes|made) (?:an\s+)?enquir(?:y|ies)\s+"
        r"(?:for|about)\s+(.+?)['’]s\s+(.+)",
        raw,
        flags=re.IGNORECASE,
    )
    if match:
        club = entity_to_ja(match.group(1), dynamic_entities)
        seller = entity_to_ja(match.group(2), dynamic_entities)
        player = entity_to_ja(match.group(3), dynamic_entities)
        return f"{club}、{seller}の{player}獲得を問い合わせ"

    # Liverpool bid £80m for Barcola
    match = re.fullmatch(
        r"(.+?) (?:bid|bids|offer|offers)\s+([£€])([0-9]+(?:\.[0-9]+)?)m\s+"
        r"for\s+(.+)",
        raw,
        flags=re.IGNORECASE,
    )
    if match:
        club = entity_to_ja(match.group(1), dynamic_entities)
        currency = match.group(2)
        amount_raw = float(match.group(3))
        player = entity_to_ja(match.group(4), dynamic_entities)

        if amount_raw.is_integer():
            amount_ja = format_millions(int(amount_raw), currency)
        else:
            unit = "ユーロ" if currency == "€" else "ポンド"
            amount_ja = f"{amount_raw:g}百万{unit}"

        return f"{club}、{player}獲得へ{amount_ja}を提示"

    # Liverpool close to signing Barcola
    match = re.fullmatch(
        r"(.+?) (?:are|is)?\s*(?:close to|set to|poised to)\s+"
        r"(?:sign|signing)\s+(.+)",
        raw,
        flags=re.IGNORECASE,
    )
    if match:
        club = entity_to_ja(match.group(1), dynamic_entities)
        player = entity_to_ja(match.group(2), dynamic_entities)
        return f"{club}、{player}獲得に迫る"

    # Barcola set to join Liverpool
    match = re.fullmatch(
        r"(.+?) (?:is\s+)?(?:set to|poised to|close to)\s+join\s+(.+)",
        raw,
        flags=re.IGNORECASE,
    )
    if match:
        player = entity_to_ja(match.group(1), dynamic_entities)
        club = entity_to_ja(match.group(2), dynamic_entities)
        return f"{player}、{club}加入へ"

    # Liverpool sign Barcola from PSG
    match = re.fullmatch(
        r"(.+?) (?:sign|signs|signed)\s+(.+?)\s+from\s+(.+)",
        raw,
        flags=re.IGNORECASE,
    )
    if match:
        club = entity_to_ja(match.group(1), dynamic_entities)
        player = entity_to_ja(match.group(2), dynamic_entities)
        old_club = entity_to_ja(match.group(3), dynamic_entities)
        return f"{club}、{old_club}から{player}を獲得"

    # Liverpool in talks to sign Barcola
    match = re.fullmatch(
        r"(.+?) (?:in talks|hold talks|holding talks)\s+"
        r"(?:to sign|over)\s+(.+)",
        raw,
        flags=re.IGNORECASE,
    )
    if match:
        club = entity_to_ja(match.group(1), dynamic_entities)
        player = entity_to_ja(match.group(2), dynamic_entities)
        return f"{club}、{player}獲得へ交渉"

    # Liverpool target Barcola / Liverpool eye Barcola
    match = re.fullmatch(
        r"(.+?) (?:target|targets|eye|eyes|monitor|monitors)\s+(.+)",
        raw,
        flags=re.IGNORECASE,
    )
    if match:
        club = entity_to_ja(match.group(1), dynamic_entities)
        player = entity_to_ja(match.group(2), dynamic_entities)
        return f"{club}、{player}を獲得候補に"

    # Barcola wants Liverpool move
    match = re.fullmatch(
        r"(.+?) (?:want|wants|seeks|keen on)\s+(.+?)\s+move",
        raw,
        flags=re.IGNORECASE,
    )
    if match:
        player = entity_to_ja(match.group(1), dynamic_entities)
        club = entity_to_ja(match.group(2), dynamic_entities)
        return f"{player}、{club}移籍を希望"


    match = re.fullmatch(
        r"Do (.+?) have defensive problems\?",
        raw,
        flags=re.IGNORECASE,
    )
    if match:
        club = entity_to_ja(match.group(1), dynamic_entities)
        return f"{club}に守備面の問題はあるのか？"

    match = re.fullmatch(
        r"(.+?) backs himself to bring (.+?) success",
        raw,
        flags=re.IGNORECASE,
    )
    if match:
        person = entity_to_ja(match.group(1), dynamic_entities)
        club = entity_to_ja(match.group(2), dynamic_entities)
        return f"{person}、自らの手腕に自信　{club}を成功へ導けるか"

    match = re.fullmatch(
        r"(.+?) genius and (.+?) excels\s*-\s*(.+?) v (.+?) player ratings",
        raw,
        flags=re.IGNORECASE,
    )
    if match:
        p1 = entity_to_ja(match.group(1), dynamic_entities)
        p2 = entity_to_ja(match.group(2), dynamic_entities)
        t1 = entity_to_ja(match.group(3), dynamic_entities)
        t2 = entity_to_ja(match.group(4), dynamic_entities)
        return f"{p1}が圧巻、{p2}も高評価　{t1}対{t2}の選手採点"

    match = re.fullmatch(
        r"(.+?)\s*&\s*(.+?) monitor (.+?)\s*-\s*(Saturday|Sunday)'s gossip",
        raw,
        flags=re.IGNORECASE,
    )
    if match:
        c1 = entity_to_ja(match.group(1), dynamic_entities)
        c2 = entity_to_ja(match.group(2), dynamic_entities)
        player = entity_to_ja(match.group(3), dynamic_entities)
        day = "土曜日" if match.group(4).lower() == "saturday" else "日曜日"
        return f"{c1}と{c2}が{player}を注視　{day}の移籍ゴシップ"

    match = re.fullmatch(
        r"A magician and a maverick\s*-\s*this could be (.+?)['’]s moment for (.+)",
        raw,
        flags=re.IGNORECASE,
    )
    if match:
        player = entity_to_ja(match.group(1), dynamic_entities)
        club = entity_to_ja(match.group(2), dynamic_entities)
        return f"技巧と型破りな才能――{player}が{club}で輝く時が来たか"

    if "bundesliga debut" in lower and "small town" in lower:
        return "小さな町からブンデスリーガへ――番狂わせを狙う挑戦"

    return None


def rewrite_summary(summary, dynamic_entities):
    raw = summary.strip()

    match = re.fullmatch(
        r"After two goals and a swaggering display against (.+?), "
        r"(.+?) asks if this is (.+?)['’]s time to shine for (.+?)[.]?",
        raw,
        flags=re.IGNORECASE,
    )
    if match:
        opponent = entity_to_ja(match.group(1), dynamic_entities)
        journalist = entity_to_ja(match.group(2), dynamic_entities)
        player = entity_to_ja(match.group(3), dynamic_entities)
        club = entity_to_ja(match.group(4), dynamic_entities)
        return (
            f"{opponent}戦で2ゴールを挙げ、圧巻のパフォーマンスを見せた"
            f"{player}。{journalist}は、{club}で{player}が輝く時が"
            f"来たのかを問う。"
        )

    return None


def football_postprocess(text):
    fixes = {
        "マンシティ": "マンチェスター・シティ",
        "マンチェスターシティ": "マンチェスター・シティ",
        "マンU": "マンチェスター・ユナイテッド",
        "レアルマドリード": "レアル・マドリード",
        "クリスタルパレス": "クリスタル・パレス",
        "アトレティコマドリード": "アトレティコ・マドリード",
        "レイアン・チェレキ": "ラヤン・シェルキ",
        "レイアン・チェルキ": "ラヤン・シェルキ",
        "チェレキ": "シェルキ",
        "フィル・マッナルティ": "フィル・マクナルティ",
        "ラリーガ": "ラ・リーガ",
        "セリエ A": "セリエA",
        "ブンデス・リーガ": "ブンデスリーガ",
        "2つの目標": "2ゴール",
        "二つの目標": "2ゴール",
        "3つの目標": "3ゴール",
        "目標を決め": "ゴールを決め",
        "目標を挙げ": "ゴールを挙げ",
        "分散表示": "パフォーマンス",
        "華やかなディスプレイ": "圧巻のパフォーマンス",
        "印象的なディスプレイ": "印象的なパフォーマンス",
        "輝く時間": "輝く時",
        "ペナルティシュートアウト": "PK戦",
        "防御的な問題": "守備面の問題",
        "防御問題": "守備面の問題",
        "プレイヤーの評価": "選手採点",
        "プレイヤー評価": "選手採点",
        "契約に同意する": "獲得で合意",
        "契約に同意": "獲得で合意",
        "お問い合わせ": "獲得を問い合わせ",
        "問い合わせ": "獲得を問い合わせ",
        "新着情報": "獲得",
        "取引": "移籍",
    }

    for old, new in fixes.items():
        text = text.replace(old, new)

    text = re.sub(r"([ァ-ヶー一-龠々]+)'s", r"\1の", text)
    text = re.sub(
        r"([A-Za-z0-9])([ぁ-んァ-ヶ一-龠])",
        r"\1 \2",
        text,
    )
    text = re.sub(
        r"([ぁ-んァ-ヶ一-龠])([A-Za-z])",
        r"\1 \2",
        text,
    )
    text = re.sub(r"\s+([。、！？])", r"\1", text)
    text = re.sub(r"([。、！？])\s+", r"\1", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


def translate_title(translator, title, dynamic_entities):
    rewritten = rewrite_headline(title, dynamic_entities)
    if rewritten:
        return football_postprocess(rewritten)

    translated = translate_preserving_entities(
        translator, title, dynamic_entities
    )
    return football_postprocess(translated)


def translate_summary(translator, summary, dynamic_entities):
    rewritten = rewrite_summary(summary, dynamic_entities)
    if rewritten:
        return football_postprocess(rewritten)

    translated = translate_preserving_entities(
        translator, summary, dynamic_entities
    )
    return football_postprocess(translated)


# =========================================================
# 前回データとWikipediaキャッシュ
# =========================================================

previous = {}
wiki_cache = {}

if DATA_PATH.exists():
    try:
        old_data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
        wiki_cache = old_data.get("entity_cache", {}) or {}

        for item in old_data.get("items", []):
            url = item.get("url")
            if url:
                previous[url] = item

    except Exception as error:
        print("Could not read previous data:", error)


# =========================================================
# まずRSSを全部取得
# =========================================================

raw_items = []

for source, feed_url in FEEDS:
    try:
        root = ET.fromstring(fetch(feed_url))

        for feed_item in root.findall(".//item")[:30]:
            original_title = clean(feed_item.findtext("title"))
            original_summary = clean(feed_item.findtext("description"))
            link = clean(feed_item.findtext("link"))
            published = clean(feed_item.findtext("pubDate"))

            if not original_title or not link:
                continue

            raw_items.append({
                "source": source,
                "title_original": original_title,
                "summary_original": original_summary[:500],
                "url": link,
                "published": published,
            })

    except Exception as error:
        print("Feed failed:", source, error)


# =========================================================
# 未知の人名・クラブ名候補をWikipediaで一括照合
# =========================================================

fixed = combined_entities()
unknown_candidates = []

for item in raw_items:
    unknown_candidates.extend(
        extract_unknown_candidates(item["title_original"], fixed)
    )
    unknown_candidates.extend(
        extract_unknown_candidates(item["summary_original"], fixed)
    )

# 1回の更新で新規照会は最大100候補。
# キャッシュ済みの候補はこの制限には含まれません。
new_candidates = [
    name for name in dict.fromkeys(unknown_candidates)
    if name not in wiki_cache
][:100]

wikipedia_ja_batch(new_candidates, wiki_cache)

dynamic_entities = {
    english: japanese
    for english, japanese in wiki_cache.items()
    if japanese
}


# =========================================================
# 翻訳
# =========================================================

translator = prepare_translator()
items = []

for raw in raw_items:
    original_title = raw["title_original"]
    original_summary = raw["summary_original"]
    link = raw["url"]

    category, label, item_type = classify(
        original_title, original_summary
    )

    combined = f"{original_title} {original_summary}".lower()
    featured = any(priority in combined for priority in PRIORITY)

    old = previous.get(link, {})

    reuse_translation = (
        old.get("translation_version") == TRANSLATION_VERSION
        and old.get("title_original") == original_title
        and old.get("summary_original") == original_summary
        and old.get("title")
    )

    if reuse_translation:
        title_ja = old.get("title", original_title)
        summary_ja = old.get("summary", original_summary)
    else:
        title_ja = translate_title(
            translator, original_title, dynamic_entities
        )
        summary_ja = translate_summary(
            translator, original_summary, dynamic_entities
        )

    items.append({
        "title": title_ja,
        "summary": summary_ja,
        "title_original": original_title,
        "summary_original": original_summary,
        "source": raw["source"],
        "url": link,
        "published": raw["published"],
        "category": category,
        "type": item_type,
        "label": label,
        "featured": featured,
        "translation_version": TRANSLATION_VERSION,
    })


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


# =========================================================
# JSON保存
# =========================================================

# キャッシュが無制限に大きくならないよう上限を設定
if len(wiki_cache) > 3000:
    wiki_cache = dict(list(wiki_cache.items())[-3000:])

output = {
    "updated_at": datetime.now(timezone.utc).isoformat(),
    "translation_version": TRANSLATION_VERSION,
    "entity_cache": wiki_cache,
    "items": unique_items[:80],
}

DATA_PATH.parent.mkdir(parents=True, exist_ok=True)

DATA_PATH.write_text(
    json.dumps(output, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

print(f"Saved {len(output['items'])} football articles")
print(f"Entity cache: {len(wiki_cache)} entries")
