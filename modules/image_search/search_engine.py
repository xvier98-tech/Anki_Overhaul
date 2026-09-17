# -*- coding: utf-8 -*-
"""
Search engine backend and image downloader for Obsidian Card Editor Image Search.
Supports:
1. Web Images (High-speed Google Images backend with SafeSearch OFF for accurate anatomical/medical queries)
2. Wikipedia & Wikimedia Commons (Encyclopedic, anatomical, scientific, and textbook diagrams)
3. Combined Search (Aggregates Wikipedia + Web for maximum relevance and coverage)
"""

from dataclasses import dataclass
from typing import List, Tuple, Optional, Set
import urllib.request
import urllib.parse
import json
import re
import html as html_lib
import os
import concurrent.futures
import unicodedata
import http.cookiejar

try:
    from ...utils.i18n import get_current_language
except (ImportError, ValueError):
    try:
        from utils.i18n import get_current_language
    except ImportError:
        def get_current_language() -> str:
            return "pt"


@dataclass
class ImageResultItem:
    title: str
    thumb_url: str
    original_url: str
    width: int = 0
    height: int = 0
    source: str = ""
    relevance_score: int = 0


DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7,es;q=0.6,fr;q=0.5",
}

GOOGLE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,pt-BR;q=0.8,pt;q=0.7",
    "Cookie": (
        "SOCS=CAISHAgBEhJnd3NfMjAyNDA4MDYtMF9SQzIaAmVuIAEaBgiA_LyuBg; "
        "CONSENT=YES+cb.20240305-17-p0.en+FX+917; "
        "1P_JAR=2024-05-01-00;"
    ),
    "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}



# Known auto-generated spam, scraper, anime imageboards, and adult tube domains
SPAM_DOMAINS = (
    "fity.club",
    "inspiredpencil.com",
    "animalia-life.club",
    "slidetodoc.com",
    "resumosmedicina.com.br/blog",
    "waterclimatecoalition.org",
    "favpng.com",
    "gelbooru.com",
    "danbooru.donmai.us",
    "rule34.xxx",
    "xvideos.com",
    "pornhub.com",
    "xhamster.com",
    "spankbang.com",
    "redtube.com",
    "youporn.com",
    "tube8.com",
    "eporner.com",
    "beeg.com",
    "redgifs.com",
    "porngifs.com",
    "adultgifs.org",
    "deviantart.com",
    "zerochan.net",
    "safebooru.org",
    "cpcompany.com",
    "aau.edu.et",
)

# Unconditional adult, pornography, anime, fan-service, viral meme, and commercial keywords to reject
ADULT_AND_SPAM_KEYWORDS = (
    "fuck",
    "porn",
    "xxx",
    "hentai",
    "nsfw",
    "erotic",
    "erotica",
    "tube",
    "blowjob",
    "boquete",
    "she fucks",
    "he fucks",
    "milf",
    "nude",
    "naked",
    "boobs",
    "pussy",
    "dick",
    "hardcore",
    "gangbang",
    "anal",
    "cum",
    "orgasm",
    "anime",
    "manga",
    "cosplay",
    "waifu",
    "genshin",
    "honkai",
    "fity.club",
    "inspiredpencil",
    "gelbooru",
    "danbooru",
    "rule34",
    "deviantart",
    "wallpaper",
    "clipart",
    "tênis",
    "vestido",
    "shoes",
    "clothing",
    "comprar",
    "preço",
    "cristiano ronaldo",
    "ronaldo",
    "messi",
    "neymar",
    "futebol",
    "celebrity",
    "celebridades",
    "famosas",
    "gatas",
    "babes",
    "minotauro",
    "mulher mais bonita",
)

DISCONNECTED_KEYWORDS = ADULT_AND_SPAM_KEYWORDS

MEDICAL_DOMAINS = (
    "wikipedia.org",
    "wikimedia.org",
    "kenhub.com",
    "imaios.com",
    "nih.gov",
    "ncbi.nlm.nih.gov",
    "radiopaedia.org",
    "scielo.br",
    "sciencedirect.com",
    "researchgate.net",
    "teachmeanatomy.info",
    "anatomy.app",
    "britannica.com",
    "anatomia-papel-e-caneta.com",
    "tuasaude.com",
    "mdsaude.com",
    "msdmanuals.com",
    "medlineplus.gov",
    "cdc.gov",
    "who.int",
    "rsna.org",
    "ajronline.org",
    "eurorad.org",
    "radiologyinfo.org",
)

# High authority medical and radiological institutions for relevance scoring boost (+30 points)
HIGH_AUTHORITY_MEDICAL_DOMAINS = (
    "radiopaedia.org",
    "nih.gov",
    "ncbi.nlm.nih.gov",
    "sciencedirect.com",
    "rsna.org",
    "ajronline.org",
    "scielo.br",
    "semanticscholar.org",
    "slideshare.net",
    "grupomedcof.com.br",
    "tadeclinicagem.com.br",
    "nature.com",
    "thelancet.com",
    "gut.bmj.com",
)

# Radiological terms for score boosting (+25 points)
RADIOLOGICAL_BOOSTER_TERMS = (
    "ct",
    "cect",
    "tomography",
    "tomografia",
    "contrast",
    "contraste",
    "mri",
    "ressonancia",
    "ressonância",
    "axial",
    "sagittal",
    "coronal",
    "radiology",
    "radiologia",
    "radiopaedia",
    "scan",
    "fluid",
    "fluido",
    "collection",
    "colecao",
    "coleção",
    "pseudocyst",
    "pseudocisto",
    "peripancreatic",
    "peripancreatico",
    "peripancreático",
)

KNOWN_MEDICAL_2LETTER_WORDS = {"tc", "rm", "rx", "us", "ct", "mr"}

ANATOMICAL_SYNONYMS = {
    # Radiological and Tomographic specialized mappings
    "fluido peripancreatico": ["peripancreatic fluid collection", "acute peripancreatic fluid collection", "peripancreatic fluid"],
    "fluido peripancreático": ["peripancreatic fluid collection", "acute peripancreatic fluid collection", "peripancreatic fluid"],
    "liquido peripancreatico": ["peripancreatic fluid collection", "peripancreatic fluid"],
    "líquido peripancreático": ["peripancreatic fluid collection", "peripancreatic fluid"],
    "colecao peripancreatica": ["peripancreatic fluid collection", "acute peripancreatic fluid collection"],
    "coleção peripancreática": ["peripancreatic fluid collection", "acute peripancreatic fluid collection"],
    "colecao fluida peripancreatica": ["acute peripancreatic fluid collection", "peripancreatic fluid collection"],
    "coleção fluida peripancreática": ["acute peripancreatic fluid collection", "peripancreatic fluid collection"],
    "pseudocisto pancreatico": ["pancreatic pseudocyst"],
    "pseudocisto pancreático": ["pancreatic pseudocyst"],
    "tomografia contraste": ["contrast-enhanced CT", "CECT", "contrast CT scan"],
    "tomografia com contraste": ["contrast-enhanced CT", "CECT", "contrast CT scan"],
    "tc contraste": ["contrast-enhanced CT", "CECT", "contrast CT scan"],
    "tc com contraste": ["contrast-enhanced CT", "CECT", "contrast CT scan"],
    "tomografia": ["computed tomography", "CT scan"],
    "tomografia computadorizada": ["computed tomography", "CT scan"],
    "tc": ["computed tomography", "CT scan"],
    "ressonancia": ["MRI", "magnetic resonance imaging"],
    "ressonancia magnetica": ["MRI", "magnetic resonance imaging"],
    "ressonância": ["MRI", "magnetic resonance imaging"],
    "ressonância magnética": ["MRI", "magnetic resonance imaging"],
    "rm": ["MRI", "magnetic resonance imaging"],
    "pancreatite necrotizante": ["necrotizing pancreatitis"],
    "pancreatite": ["pancreatitis"],
    "classificacao de atlanta": ["Atlanta classification pancreatitis", "revised Atlanta classification acute pancreatitis"],
    "classificação de atlanta": ["Atlanta classification pancreatitis", "revised Atlanta classification acute pancreatitis"],
    "criterios de atlanta": ["Atlanta criteria pancreatitis", "revised Atlanta classification acute pancreatitis"],
    "critérios de atlanta": ["Atlanta criteria pancreatitis", "revised Atlanta classification acute pancreatitis"],
    "atlanta pancreatite": ["Atlanta classification pancreatitis"],
    "atlanta": ["Atlanta classification pancreatitis"],
    # Anatomical & GYN / Urological mappings
    "glandula parauretral": ["paraurethral gland", "skene gland"],
    "glandulas parauretrais": ["paraurethral glands", "skene glands", "skene's glands"],
    "glandula de skene": ["skene's gland", "paraurethral gland"],
    "glandulas de skene": ["skene's glands", "paraurethral glands"],
    "skene": ["skene's gland", "paraurethral gland"],
    "glandula de bartholin": ["bartholin's gland", "greater vestibular gland"],
    "glandulas de bartholin": ["bartholin's glands", "greater vestibular glands"],
    "bartholin": ["bartholin's gland", "bartholin cyst"],
    "orgao genital feminino": ["female reproductive system", "female genitalia"],
    "orgaos genitais femininos": ["female reproductive system", "female genitalia"],
    "aparelho reprodutor feminino": ["female reproductive system", "female anatomy"],
    "sistema reprodutor feminino": ["female reproductive system", "female anatomy"],
    "genitalia feminina": ["female external genitalia", "vulva anatomy"],
    "orgao genital masculino": ["male reproductive system", "male genitalia"],
    "orgaos genitais masculinos": ["male reproductive system", "male genitalia"],
    "aparelho reprodutor masculino": ["male reproductive system"],
    "sistema reprodutor masculino": ["male reproductive system"],
    "clitoris": ["clitoris anatomy"],
    "vulva": ["vulva anatomy", "female external genitalia"],
    "vagina": ["vagina anatomy"],
    "utero": ["uterus anatomy"],
    "ovario": ["ovary anatomy"],
    "ovarios": ["ovary anatomy"],
    "uretra": ["urethra anatomy", "female urethra", "male urethra"],
    "prostata": ["prostate anatomy"],
    "sifilis": ["syphilis", "treponema pallidum"],
    "sífilis": ["syphilis", "treponema pallidum"],
    "lactobacilos": ["lactobacillus", "lactobacilli"],
    "lactobacilo": ["lactobacillus"],
    "candidiase": ["candidiasis", "candida albicans"],
    "candidíase": ["candidiasis", "candida albicans"],
    "gonorreia": ["gonorrhea", "neisseria gonorrhoeae"],
    "clamidia": ["chlamydia trachomatis"],
    "clamídia": ["chlamydia trachomatis"],
    "herpes": ["herpes simplex virus"],
    "hpv": ["human papillomavirus"],
    "tricomoniase": ["trichomoniasis", "trichomonas vaginalis"],
    "tricomoníase": ["trichomoniasis", "trichomonas vaginalis"],
    "cardiotocografia": [
        "cardiotocography",
        "fetal heart rate monitoring",
        "fetal monitoring",
        "ctg",
        "desaceleracao",
        "desaceleracoes",
        "dip 1",
        "dip 2",
        "dip 3",
    ],
    "cardiotografia": [
        "cardiotocografia",
        "cardiotocography",
        "fetal monitoring",
        "ctg",
        "desaceleracao",
        "dip 1",
        "dip 2",
        "dip 3",
    ],
    "dip 1": ["desaceleracao precoce", "early deceleration", "cardiotocografia", "cardiotocography"],
    "dip 2": ["desaceleracao tardia", "late deceleration", "cardiotocografia", "cardiotocography"],
    "dip 3": [
        "desaceleracao variavel",
        "variable deceleration",
        "cardiotocografia",
        "cardiotocography",
        "compressao funicular",
    ],
    "ctg": ["cardiotocografia", "cardiotocography", "fetal heart rate monitoring"],
    "desaceleracao variavel": ["dip 3", "cardiotocografia", "variable deceleration"],
    "desaceleracao precoce": ["dip 1", "early deceleration", "cardiotocografia"],
    "desaceleracao tardia": ["dip 2", "late deceleration", "cardiotocografia"],
}


# Ordered phrase replacement patterns for radiological and pathological translation
RADIOLOGICAL_PHRASE_REPLACEMENTS = [
    # Atlanta Classification of Pancreatitis
    (r"\b(classifica[çc][aã]o\s+de\s+atlanta|crit[eé]rios\s+de\s+atlanta|classificacao\s+atlanta)\b", "revised Atlanta classification"),
    # Acute peripancreatic fluid collection variants
    (r"\b(cole[çc][aã]o\s+fluida\s+peripancre[aá]tica|cole[çc][aã]o\s+peripancre[aá]tica)\b", "acute peripancreatic fluid collection"),
    (r"\b(fluido\s+peripancre[aá]tico|l[ií]quido\s+peripancre[aá]tico)\b", "peripancreatic fluid collection"),
    # Contrast CT variants (longest first)
    (r"\b(tomografia\s+computadorizada\s+com\s+contraste|tomografia\s+com\s+contraste|tomografia\s+contraste|tc\s+com\s+contraste|tc\s+contraste)\b", "contrast-enhanced CT"),
    (r"\b(tomografia\s+computadorizada|tomografia)\b", "CT scan"),
    (r"\btc\b", "CT"),
    # Contrast MRI variants
    (r"\b(resson[aâ]ncia\s+magn[eé]tica\s+com\s+contraste|ressonancia\s+com\s+contraste|rm\s+com\s+contraste)\b", "contrast-enhanced MRI"),
    (r"\b(resson[aâ]ncia\s+magn[eé]tica|ressonancia\s+magnetica|resson[aâ]ncia|ressonancia)\b", "MRI"),
    (r"\brm\b", "MRI"),
    # Pancreatitis
    (r"\bpancreatite\s+necrotizante\b", "necrotizing pancreatitis"),
    (r"\bpancreatite\b", "pancreatitis"),
]


def _strip_accents(text: str) -> str:
    """Removes diacritics/accents from a string for robust matching."""
    return "".join(
        c for c in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(c)
    )


def _build_translated_medical_query(clean_query: str) -> str:
    """
    Constructs an English medical query by translating domain-specific radiological
    and anatomical terms (e.g. 'pancreatite necrotizante tomografia com contraste' ->
    'necrotizing pancreatitis contrast-enhanced CT').
    """
    q_transformed = clean_query
    for pattern, replacement in RADIOLOGICAL_PHRASE_REPLACEMENTS:
        q_transformed = re.sub(pattern, replacement, q_transformed, flags=re.IGNORECASE)

    q_transformed = re.sub(r"\s+", " ", q_transformed).strip()
    if q_transformed.lower() != clean_query.lower():
        return q_transformed
    return ""


def _is_medical_or_pathological_query(query: str) -> bool:
    """Detects whether a search query relates to medicine, radiology, pathology, or anatomy."""
    q_lower = query.lower()
    q_unaccented = _strip_accents(q_lower)
    medical_prefixes = (
        "apendic", "pancreat", "peripancre", "necro", "tomograf", "ressonanc", "radiolog",
        "cirurg", "patolog", "tumor", "lesao", "biopsi", "inflamac", "pseudocist",
        "cect", "anatomy", "anatomia", "glandul", "uretr", "skene", "bartholin",
        "genital", "vulva", "vagina", "utero", "ovari", "prostata", "fluido", "liquido",
        "colecao", "sifilis", "fetal", "cardiotoc", "cardiotog", "desacelerac",
        "cancer", "atlanta"
    )
    for term in medical_prefixes:
        if term in q_lower or term in q_unaccented:
            return True
    for short_term in KNOWN_MEDICAL_2LETTER_WORDS:
        if re.search(rf"\b{re.escape(short_term)}\b", q_lower) or re.search(rf"\b{re.escape(short_term)}\b", q_unaccented):
            return True
    return False


def _extract_base_concept(query: str) -> str:
    """Strips qualifiers like 'DIP 3', 'grau 2', numbers to find the base medical subject."""
    q = query.strip()
    cleaned = re.sub(
        r"\b(dip\s*\d*|tipo\s*\d*|grau\s*\d*|estagio\s*\d*|\d+|i|ii|iii|iv|v)\b",
        "",
        q,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned if len(cleaned) >= 3 else q


_TRANSLATION_CACHE: dict = {}


def translate_query_to_english(query: str, source_lang: Optional[str] = None) -> str:
    """
    Dynamically translates medical/scientific search queries from native languages (PT, ES, FR)
    to English in real-time, enabling access to English medical diagrams, PubMed,
    and Wikimedia Commons without requiring manual synonym entries.
    """
    clean_q = query.strip().lower()
    if not clean_q:
        return ""

    src_lang = source_lang or get_current_language() or "pt"
    if src_lang == "en":
        return clean_q

    cache_key = f"{src_lang}:{clean_q}"
    if cache_key in _TRANSLATION_CACHE:
        return _TRANSLATION_CACHE[cache_key]

    # Primary dynamic translation: MyMemory Free Translation API (specialized in terminology)
    try:
        params = {"q": clean_q, "langpair": f"{src_lang}|en"}
        url = f"https://api.mymemory.translated.net/get?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            translated = data.get("responseData", {}).get("translatedText", "").strip().lower()
            if translated and not translated.startswith("mymemory warning") and translated != clean_q:
                _TRANSLATION_CACHE[cache_key] = translated
                return translated
    except Exception:
        pass

    # Secondary dynamic fallback: Google Translate clientless endpoint
    try:
        encoded = urllib.parse.quote(clean_q)
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl={src_lang}&tl=en&dt=t&q={encoded}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            translated = "".join(part[0] for part in data[0] if part[0]).strip().lower()
            if translated and translated != clean_q:
                _TRANSLATION_CACHE[cache_key] = translated
                return translated
    except Exception:
        pass

    _TRANSLATION_CACHE[cache_key] = clean_q
    return clean_q


def _get_medical_synonyms(query: str) -> List[str]:
    """
    Returns English anatomical/medical synonyms for better scientific search coverage.
    Combines:
    1. Specialized radiological/pathological phrase translations (e.g. 'pancreatite necrotizante tc com contraste').
    2. Static instant local overrides from ANATOMICAL_SYNONYMS.
    3. Dynamic real-time machine translation to English for any arbitrary medical term.
    4. Base-concept English translation for qualified terms (e.g. 'cardiotocografia dip 3').
    """
    q_norm = query.lower().strip()
    q_norm_no_accents = re.sub(r"[áàâã]", "a", q_norm)
    q_norm_no_accents = re.sub(r"[éê]", "e", q_norm_no_accents)
    q_norm_no_accents = re.sub(r"[í]", "i", q_norm_no_accents)
    q_norm_no_accents = re.sub(r"[óôõ]", "o", q_norm_no_accents)
    q_norm_no_accents = re.sub(r"[ú]", "u", q_norm_no_accents)
    q_norm_no_accents = re.sub(r"[ç]", "c", q_norm_no_accents)

    results: List[str] = []

    # 1. Specialized radiological / pathological phrase transformation
    translated_phrase = _build_translated_medical_query(q_norm)
    if translated_phrase and translated_phrase not in results:
        results.append(translated_phrase)

    # 2. Instant local dictionary check
    for key, syns in ANATOMICAL_SYNONYMS.items():
        if len(key) <= 2:
            matched = bool(
                re.search(rf"\b{re.escape(key)}\b", q_norm)
                or re.search(rf"\b{re.escape(key)}\b", q_norm_no_accents)
            )
        else:
            matched = (
                key == q_norm
                or key == q_norm_no_accents
                or key in q_norm
                or key in q_norm_no_accents
            )

        if matched:
            for s in syns:
                if s not in results:
                    results.append(s)

    # 3. Dynamic translation to English for any arbitrary medical term
    translated_en = translate_query_to_english(q_norm)
    if translated_en and translated_en != q_norm and translated_en != q_norm_no_accents:
        if translated_en not in results:
            results.append(translated_en)

    # 4. If query contains sub-qualifiers (e.g. 'cardiotocografia dip 3'), also translate base concept
    base_concept = _extract_base_concept(q_norm)
    if base_concept != q_norm:
        base_en = translate_query_to_english(base_concept)
        if base_en and base_en not in results and base_en != base_concept:
            results.append(base_en)

    return results


def _calculate_relevance_score(
    title: str,
    source: str,
    query_words: List[str],
    is_anatomical: bool = False,
    synonyms: Optional[List[str]] = None,
) -> int:
    """
    Calculates a relevance score with UNCONDITIONAL anti-adult/anti-spam filters
    and strict anchor-keyword correlation validation against query terms.
    """
    title_lower = title.lower()
    source_lower = source.lower()

    # 1. Reject known scraper, anime board, or adult tube domains unconditionally
    if any(spam in source_lower for spam in SPAM_DOMAINS):
        return -100

    # 2. Reject adult, pornographic, anime, viral memes or fan-service keywords unconditionally
    if any(bad in title_lower or bad in source_lower for bad in ADULT_AND_SPAM_KEYWORDS):
        return -100

    # 3. Anchor keyword matching vs weak terms:
    # Separate anchor words (len >= 5) from short/weak words (len < 5, e.g. "dip", "ctg", "hpv", "tc", "rm")
    anchor_terms: Set[str] = set()
    weak_terms: Set[str] = set()

    for w in query_words:
        if len(w) >= 5:
            anchor_terms.add(w)
        elif len(w) >= 2:
            weak_terms.add(w)

    if synonyms:
        for s in synonyms:
            for sw in re.findall(r"\w+", s.lower()):
                if len(sw) >= 5:
                    anchor_terms.add(sw)
                elif len(sw) >= 2:
                    weak_terms.add(sw)

    is_high_authority = any(dom in source_lower for dom in HIGH_AUTHORITY_MEDICAL_DOMAINS)
    is_trusted_medical = is_high_authority or any(dom in source_lower for dom in MEDICAL_DOMAINS)

    title_unaccented = _strip_accents(title_lower)
    source_unaccented = _strip_accents(source_lower)

    # If anchor terms exist (e.g. 'cardiotocografia', 'lactobacilos', 'glandulas', 'peripancreatico'),
    # at least ONE anchor term MUST match the title or source. Weak terms like 'dip' alone cannot pass!
    if anchor_terms:
        has_anchor_match = any(
            a in title_lower or a in source_lower or _strip_accents(a) in title_unaccented or _strip_accents(a) in source_unaccented
            for a in anchor_terms
        )
        if not has_anchor_match and not is_trusted_medical:
            return -100
    else:
        # If no anchor words exist (e.g. short acronym query like 'CTG', 'HPV', 'DIP', 'TC', 'RM'),
        # require word-boundary match so substring collision does not occur
        has_weak_match = any(
            re.search(rf"\b{re.escape(w)}\b", title_lower) or re.search(rf"\b{re.escape(w)}\b", source_lower)
            or re.search(rf"\b{re.escape(_strip_accents(w))}\b", title_unaccented) or re.search(rf"\b{re.escape(_strip_accents(w))}\b", source_unaccented)
            for w in weak_terms
        )
        if not has_weak_match and not is_trusted_medical:
            return -100

    all_match_terms = list(anchor_terms.union(weak_terms))

    score = 0
    for w in all_match_terms:
        if len(w) <= 3:
            if re.search(rf"\b{re.escape(w)}\b", title_lower):
                score += 10
            elif re.search(rf"\b{re.escape(w)}\b", source_lower):
                score += 3
        else:
            if w in title_lower:
                score += 10
            elif w in source_lower:
                score += 3

    # High authority scientific / medical domains get a prominent +30 boost
    if is_high_authority:
        score += 30
    elif is_trusted_medical:
        score += 25

    # Radiological booster terms (+25 points)
    has_rad_boost = False
    for rt in RADIOLOGICAL_BOOSTER_TERMS:
        if len(rt) <= 3:
            if re.search(rf"\b{re.escape(rt)}\b", title_lower) or re.search(rf"\b{re.escape(rt)}\b", source_lower):
                has_rad_boost = True
                break
        else:
            if rt in title_lower or rt in source_lower:
                has_rad_boost = True
                break
    if has_rad_boost:
        score += 25

    # Extra points for medical, anatomical, or diagram sources
    if any(k in title_lower or k in source_lower for k in (
        "anatomy", "anatomia", "diagram", "esquema", "medical", "medico",
        "histology", "histologia", "pathology", "patologia", "bacteria", "microscop",
        "disease", "doenca", "infection", "infeccao", "fetal", "obstetr", "parto"
    )):
        score += 15

    return score


def _decode_google_escapes(text: str) -> str:
    """Decodes unicode escapes commonly found in Google responses."""
    cleaned = text.replace(r"\/", "/")
    cleaned = cleaned.replace(r"\u003d", "=").replace(r"\u003D", "=")
    cleaned = cleaned.replace(r"\u0026", "&").replace(r"\u0026", "&")
    cleaned = cleaned.replace(r"\u003c", "<").replace(r"\u003C", "<")
    cleaned = cleaned.replace(r"\u003e", ">").replace(r"\u003E", ">")
    # Universal Unicode escape decoder for any remaining \uXXXX
    cleaned = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), cleaned)
    return cleaned



def _extract_balanced_json(text: str, start_idx: int) -> Optional[str]:
    """Finds balanced [...] array starting at or after start_idx."""
    bracket_start = text.find("[", start_idx)
    if bracket_start == -1:
        return None
    depth = 0
    in_string = False
    escape = False
    string_char = ""
    for i in range(bracket_start, len(text)):
        ch = text[i]
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if in_string:
            if ch == string_char:
                in_string = False
            continue
        if ch in ('"', "'"):
            in_string = True
            string_char = ch
            continue
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                return text[bracket_start:i + 1]
    return None


def _is_ignored_google_asset(url: str) -> bool:
    ignored = (
        "google.com/images/branding",
        "gstatic.com/favicon",
        "www.gstatic.com/images/icons",
        "googleusercontent.com/favicon",
    )
    return any(ig in url for ig in ignored)


def _extract_google_af_init_data(html_content: str) -> List[dict]:
    """
    Parses the AF_initDataCallback block with key: 'ds:1' from Google Images HTML.
    Extracts structured image items (original_url, thumb_url, title, source, width, height).
    """
    items: List[dict] = []
    seen: Set[str] = set()

    for m in re.finditer(r"AF_initDataCallback\s*\(", html_content):
        start = m.end()
        depth = 1
        in_str = False
        escape = False
        str_ch = ""
        end = -1
        for i in range(start, min(len(html_content), start + 2000000)):
            c = html_content[i]
            if escape:
                escape = False
                continue
            if c == "\\":
                escape = True
                continue
            if in_str:
                if c == str_ch:
                    in_str = False
                continue
            if c in ('"', "'"):
                in_str = True
                str_ch = c
                continue
            if c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    end = i
                    break
        if end == -1:
            continue

        block = html_content[start:end]
        # Accept ds:0, ds:1, ds:2, ds:3 or callbacks without key restriction

        data_match = re.search(r"data\s*:\s*", block)
        if not data_match:
            continue

        json_str = _extract_balanced_json(block, data_match.end())
        if not json_str:
            continue

        try:
            data = json.loads(json_str)
        except Exception:
            continue

        def _walk(node):
            if isinstance(node, list):
                # Row candidate in Google format:
                # e.g. ["id_1", [null, null, null], [thumb, 100, 100], [orig, 800, 1200], ..., [url, title, source]]
                if (
                    len(node) >= 4
                    and isinstance(node[0], str)
                    and isinstance(node[2], list)
                    and isinstance(node[3], list)
                    and len(node[3]) >= 3
                    and isinstance(node[3][0], str)
                    and node[3][0].startswith(("http://", "https://"))
                ):
                    orig_url = node[3][0]
                    height = int(node[3][1] or 0)
                    width = int(node[3][2] or 0)
                    thumb_url = node[2][0] if (len(node[2]) >= 1 and isinstance(node[2][0], str)) else orig_url
                    title = ""
                    source = ""

                    for elem in node[4:]:
                        if isinstance(elem, list) and len(elem) >= 2:
                            if isinstance(elem[0], str) and elem[0].startswith(("http://", "https://")):
                                source = elem[0]
                            if isinstance(elem[1], str) and len(elem[1]) > 0:
                                title = elem[1]
                        elif isinstance(elem, dict):
                            for v in elem.values():
                                if isinstance(v, list) and len(v) >= 2:
                                    if isinstance(v[0], str) and v[0].startswith(("http://", "https://")):
                                        source = v[0]
                                    if isinstance(v[1], str) and len(v[1]) > 0:
                                        title = v[1]

                    if orig_url not in seen:
                        seen.add(orig_url)
                        items.append({
                            "original_url": orig_url,
                            "thumb_url": thumb_url,
                            "title": title or os.path.splitext(os.path.basename(urllib.parse.urlparse(orig_url).path))[0],
                            "source": source or urllib.parse.urlparse(orig_url).netloc,
                            "width": width,
                            "height": height,
                        })
                    return  # Do not recurse into row's children

                for child in node:
                    _walk(child)
            elif isinstance(node, dict):
                orig = node.get("original_url") or node.get("murl") or node.get("url")
                if orig and isinstance(orig, str) and orig.startswith(("http://", "https://")) and orig not in seen and not _is_ignored_google_asset(orig):
                    seen.add(orig)
                    items.append({
                        "original_url": orig,
                        "thumb_url": node.get("thumb_url") or node.get("turl") or orig,
                        "title": node.get("title") or node.get("t") or "",
                        "source": node.get("source") or node.get("purl") or urllib.parse.urlparse(orig).netloc,
                        "width": int(node.get("width") or 0),
                        "height": int(node.get("height") or 0),
                    })
                for v in node.values():
                    _walk(v)

        _walk(data)

    return items


def _extract_google_triples(html_content: str) -> List[dict]:
    r"""
    Extracts image triples [url, height, width] as fallback from Google HTML.
    Matches: r'\["(https?://[^"\[\]]+?)",\s*(\d+),\s*(\d+)\]'
    Accepts encrypted-tbn0.gstatic.com thumbnails as fallback if no external high-res images are found.
    """
    cleaned = _decode_google_escapes(html_content)
    pattern = r'\["(https?://[^"\[\]]+?)",\s*(\d+),\s*(\d+)\]'
    matches = re.findall(pattern, cleaned)
    results: List[dict] = []
    seen: Set[str] = set()
    fallback_tbn: List[dict] = []
    seen_tbn: Set[str] = set()

    for raw_url, dim1, dim2 in matches:
        url = raw_url.strip()
        if not url:
            continue
        if _is_ignored_google_asset(url):
            continue
        try:
            h = int(dim1)
            w = int(dim2)
        except (ValueError, TypeError):
            h, w = 0, 0

        if "encrypted-tbn0.gstatic.com" in url:
            if url not in seen_tbn:
                seen_tbn.add(url)
                fallback_tbn.append({
                    "original_url": url,
                    "thumb_url": url,
                    "title": "",
                    "source": "google.com",
                    "width": w or 150,
                    "height": h or 150,
                })
            continue

        if url in seen:
            continue
        seen.add(url)
        domain = urllib.parse.urlparse(url).netloc
        parsed_path = urllib.parse.urlparse(url).path
        base_name = os.path.splitext(os.path.basename(parsed_path))[0].replace("-", " ").replace("_", " ").strip()
        results.append({
            "original_url": url,
            "thumb_url": url,
            "title": base_name,
            "source": domain,
            "width": w,
            "height": h,
        })

    if not results and fallback_tbn:
        return fallback_tbn
    return results


def _extract_google_results(html_content: str) -> List[dict]:
    r"""
    Extracts image items from Google HTML using resilient dual extraction:
    1. Parse AF_initDataCallback with key: 'ds:1'
    2. Fallback to image triples r'\["(https?://[^"\[\]]+?)",\s*(\d+),\s*(\d+)\]'
    3. Unicode escape decoding
    """
    cleaned = _decode_google_escapes(html_content)
    results = _extract_google_af_init_data(cleaned)
    if not results:
        results = _extract_google_triples(cleaned)
    else:
        seen = {r["original_url"] for r in results if "original_url" in r}
        if len(results) < 5:
            for t in _extract_google_triples(cleaned):
                if t["original_url"] not in seen:
                    seen.add(t["original_url"])
                    results.append(t)

    # Legacy/embedded metadata fallback (m="{...}")
    if not results:
        m_matches = re.findall(r'm="(\{[^"]+\})"', cleaned)
        seen = set()
        for raw_m in m_matches:
            try:
                data = json.loads(html_lib.unescape(raw_m))
                orig = data.get("original_url") or data.get("murl") or data.get("url")
                if orig and orig not in seen:
                    seen.add(orig)
                    results.append({
                        "original_url": orig,
                        "thumb_url": data.get("thumb_url") or data.get("turl") or orig,
                        "title": data.get("title") or data.get("t") or "",
                        "source": data.get("source") or data.get("purl") or urllib.parse.urlparse(orig).netloc,
                        "width": int(data.get("width") or 0),
                        "height": int(data.get("height") or 0),
                    })
            except Exception:
                continue

    return results


def _fetch_google_html(
    query_str: str,
    page_idx: int,
    start_idx: int,
    safe_search: bool,
) -> str:
    """Helper to fetch raw Google Images HTML (udm=2)."""
    encoded_query = urllib.parse.quote(query_str)
    url = (
        f"https://www.google.com/search?q={encoded_query}&udm=2"
        f"&start={start_idx}&ijn={page_idx}&hl=en&gl=us"
    )
    if not safe_search:
        url += "&safe=off"

    req = urllib.request.Request(url, headers=GOOGLE_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"[ImageSearch] Google fetch error for '{query_str}': {e}")
        return ""


def search_duckduckgo_images(
    query: str,
    max_results: int = 30,
    page: int = 1,
) -> List[ImageResultItem]:
    """
    Fetches web images from DuckDuckGo Images backend as a robust, high-yield provider.
    Uses CookieJar session handling and modern browser security headers for reliable retrieval.
    """
    clean_query = query.strip()
    if not clean_query:
        return []

    browser_headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,pt-BR;q=0.8,pt;q=0.7",
        "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
    }

    try:
        token_url = f"https://duckduckgo.com/?q={urllib.parse.quote(clean_query)}&iax=images&ia=images"
        token_req = urllib.request.Request(token_url, headers=browser_headers)
        with urllib.request.urlopen(token_req, timeout=8) as token_resp:
            token_html = token_resp.read().decode("utf-8", errors="ignore")
            set_cookies = token_resp.headers.get("Set-Cookie") or ""

        vqd_match = (
            re.search(r'vqd=([0-9a-zA-Z_-]+)', token_html)
            or re.search(r'vqd="([0-9a-zA-Z_-]+)"', token_html)
            or re.search(r'vqd:\s*["\']([^"\']+)["\']', token_html)
        )
        vqd = vqd_match.group(1) if vqd_match else (token_resp.headers.get("x-vqd-4") if hasattr(token_resp, "headers") else None)
        if not vqd:
            return []

        api_headers = {
            "User-Agent": browser_headers["User-Agent"],
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Referer": token_url,
            "x-requested-with": "XMLHttpRequest",
            "Sec-Ch-Ua": browser_headers["Sec-Ch-Ua"],
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        }
        if set_cookies:
            api_headers["Cookie"] = set_cookies

        api_url = f"https://duckduckgo.com/i.js?l=us-en&o=json&q={urllib.parse.quote(clean_query)}&vqd={vqd}&f=,,,&p={page}"
        api_req = urllib.request.Request(api_url, headers=api_headers)
        with urllib.request.urlopen(api_req, timeout=8) as api_resp:
            data = json.loads(api_resp.read().decode("utf-8", errors="ignore"))

        results: List[ImageResultItem] = []
        for r in data.get("results", []):
            orig = r.get("image")
            if not orig:
                continue
            thumb = r.get("thumbnail") or orig
            title = r.get("title") or clean_query
            source = r.get("url") or "DuckDuckGo"
            width = int(r.get("width") or 0)
            height = int(r.get("height") or 0)
            results.append(
                ImageResultItem(
                    title=title,
                    thumb_url=thumb,
                    original_url=orig,
                    width=width,
                    height=height,
                    source=source,
                )
            )
            if len(results) >= max_results:
                break
        return results
    except Exception:
        return []


def _fetch_bing_raw(
    query_str: str,
    first_idx: int = 1,
    adlt_param: str = "",
    cookie_val: str = "SRCHHPGUSR=ADLT=OFF&NRSLT=-1;",
) -> str:
    """Helper to fetch raw Bing Web Images HTML with SafeSearch relaxation."""
    encoded_query = urllib.parse.quote(query_str)
    url = f"https://www.bing.com/images/search?q={encoded_query}&form=HDRSC2&first={first_idx}{adlt_param}"
    headers = {
        "User-Agent": DEFAULT_HEADERS["User-Agent"],
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "Cookie": cookie_val,
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"[ImageSearch] Web fetch error for '{query_str}': {e}")
        return ""


def _extract_bing_results(
    html_content: str,
    clean_query: str,
    query_words: List[str],
    is_anatomical: bool = False,
    synonyms: Optional[List[str]] = None,
) -> List[Tuple[int, ImageResultItem]]:
    """
    Extracts and scores image items from web search HTML using strict card boundary isolation,
    anti-spam filtering, gif blocking, and relevance scoring.
    """
    matches = re.findall(r'm="(\{[^"]+\})"', html_content)
    items_with_scores: List[Tuple[int, ImageResultItem]] = []
    seen_urls: Set[str] = set()

    for raw in matches:
        try:
            data = json.loads(html_lib.unescape(raw))
            original_url = data.get("murl")
            if not original_url:
                continue

            thumb_url = data.get("turl") or original_url
            title = data.get("t") or clean_query
            source = data.get("purl") or ""
            desc = data.get("desc") or ""

            # Check spam domain
            domain = urllib.parse.urlparse(source or original_url).netloc.lower()
            if any(sp in domain for sp in SPAM_DOMAINS):
                continue

            # Check adult & spam keywords
            combo = f"{title} {desc} {source}".lower()
            if any(bad in combo for bad in ADULT_AND_SPAM_KEYWORDS):
                continue

            # Block animated gifs unless specifically requested
            clean_ext = original_url.lower().split("?")[0]
            if clean_ext.endswith(".gif") and "gif" not in clean_query.lower():
                continue

            if original_url in seen_urls:
                continue
            seen_urls.add(original_url)

            score = _calculate_relevance_score(
                title, source, query_words, is_anatomical=is_anatomical, synonyms=synonyms
            )
            if score < 0:
                continue

            item = ImageResultItem(
                title=title,
                thumb_url=thumb_url,
                original_url=original_url,
                width=int(data.get("width") or 0),
                height=int(data.get("height") or 0),
                source=source,
                relevance_score=score,
            )
            items_with_scores.append((score, item))
        except Exception:
            continue

    items_with_scores.sort(key=lambda x: x[0], reverse=True)
    return items_with_scores


def search_web_images(
    query: str,
    max_results: int = 50,
    safe_search: bool = False,
    page: int = 1,
) -> List[ImageResultItem]:
    """
    Fetches open web images (including copyrighted medical journals, clinical tables,
    and educational figures for non-profit educational study) with dual-query PT+EN search,
    SafeSearch relaxation for pathology, pagination support, and relevance scoring.
    """
    clean_query = query.strip()
    if not clean_query:
        return []

    is_medical = _is_medical_or_pathological_query(clean_query)
    is_anatomical = is_medical or any(k in clean_query.lower() for k in (
        "glandula", "glândula", "uretr", "skene", "bartholin", "genital", "vulva",
        "vagina", "utero", "útero", "ovari", "ovário", "penis", "pênis", "prostata",
        "próstata", "anatomi", "histolog", "sifilis", "sífilis", "lactobacil", "bacteria",
        "bactéria", "infeccao", "infecção", "cardiotoc", "cardiotog", "parto", "fetal",
        "obstetr", "desacelerac", "desaceleraç", "atlanta", "pancreat"
    ))

    # Pagination: first_idx = 1 + (page - 1) * max_results
    first_idx = 1 + max(0, page - 1) * max_results

    # SafeSearch relaxation for medical pathology/organs
    if not safe_search or is_medical or is_anatomical:
        adlt_param = "&adlt=off"
        cookie_val = "SRCHHPGUSR=ADLT=OFF&NRSLT=-1;"
    else:
        adlt_param = "&adlt=moderate"
        cookie_val = "SRCHHPGUSR=ADLT=DEMO&NRSLT=-1;"

    query_words = [
        w.lower() for w in re.findall(r"\w+", clean_query)
        if len(w) > 2 or w.lower() in KNOWN_MEDICAL_2LETTER_WORDS
    ]
    synonyms = _get_medical_synonyms(clean_query)

    # Medical / radiological English translation:
    en_query = _build_translated_medical_query(clean_query)
    if not en_query and synonyms:
        if synonyms[0].lower() != clean_query.lower():
            en_query = synonyms[0]

    should_dual_search = bool(
        (is_medical or is_anatomical or synonyms)
        and en_query
        and en_query.lower() != clean_query.lower()
    )

    def _fetch_scored(q_str: str) -> List[Tuple[int, ImageResultItem]]:
        html = _fetch_bing_raw(q_str, first_idx, adlt_param, cookie_val)
        items = _extract_bing_results(html, q_str, query_words, is_anatomical=is_anatomical, synonyms=synonyms)
        if not items and html:
            # Fallback for Google/AF_initDataCallback HTML or test mocks
            g_items = _extract_google_results(html)
            for data in g_items:
                orig = data.get("original_url")
                if not orig:
                    continue
                title = data.get("title") or q_str
                source = data.get("source") or ""
                score = _calculate_relevance_score(title, source, query_words, is_anatomical=is_anatomical, synonyms=synonyms)
                if score >= 0:
                    items.append((score, ImageResultItem(
                        title=title,
                        thumb_url=data.get("thumb_url") or orig,
                        original_url=orig,
                        width=int(data.get("width") or 0),
                        height=int(data.get("height") or 0),
                        source=source,
                        relevance_score=score,
                    )))
        return items

    items_with_scores: List[Tuple[int, ImageResultItem]] = []
    seen_urls: Set[str] = set()

    if should_dual_search:
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                fut_orig = executor.submit(_fetch_scored, clean_query)
                fut_en = executor.submit(_fetch_scored, en_query)
                for score, item in fut_orig.result() + fut_en.result():
                    if item.original_url not in seen_urls:
                        seen_urls.add(item.original_url)
                        items_with_scores.append((score, item))
        except Exception:
            for score, item in _fetch_scored(clean_query):
                if item.original_url not in seen_urls:
                    seen_urls.add(item.original_url)
                    items_with_scores.append((score, item))
    else:
        for score, item in _fetch_scored(clean_query):
            if item.original_url not in seen_urls:
                seen_urls.add(item.original_url)
                items_with_scores.append((score, item))

    # If results are sparse (< 8) and dual search didn't run, check remaining synonyms
    if len(items_with_scores) < 8 and synonyms and not should_dual_search:
        for syn in synonyms[:2]:
            if syn.lower() == clean_query.lower():
                continue
            for score, item in _fetch_scored(syn)[:20]:
                if item.original_url not in seen_urls:
                    seen_urls.add(item.original_url)
                    items_with_scores.append((score, item))

    # If primary search returned no results, complement with high-yield DuckDuckGo Images
    if not items_with_scores:
        ddg_items = search_duckduckgo_images(clean_query, max_results=max_results, page=page)
        for d_it in ddg_items:
            if d_it.original_url not in seen_urls:
                seen_urls.add(d_it.original_url)
                items_with_scores.append((d_it.relevance_score, d_it))

        if not items_with_scores and en_query and en_query.lower() != clean_query.lower():
            ddg_en_items = search_duckduckgo_images(en_query, max_results=max_results, page=page)
            for d_it in ddg_en_items:
                if d_it.original_url not in seen_urls:
                    seen_urls.add(d_it.original_url)
                    items_with_scores.append((d_it.relevance_score, d_it))

    items_with_scores.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in items_with_scores[:max_results]]


def search_google_images(
    query: str,
    max_results: int = 50,
    safe_search: bool = False,
    page: int = 1,
) -> List[ImageResultItem]:
    """
    Fetches web images with dual-query PT+EN search, SafeSearch relaxation,
    and relevance scoring.
    """
    return search_web_images(query, max_results=max_results, safe_search=safe_search, page=page)




WIKI_HEADERS = {
    "User-Agent": "ObsidianImageSearch/2.0 (https://github.com/ankitects/anki; anki_addon_edu@example.org) Python-urllib",
    "Accept": "application/json",
}


def search_wikimedia(
    query: str,
    max_results: int = 40,
    page: int = 1,
) -> List[ImageResultItem]:
    """
    Fetches educational and public domain images from Wikimedia Commons API.
    Supports pagination (gsroffset), base-concept fallback, and English synonym expansion.
    """
    clean_query = query.strip()
    if not clean_query:
        return []

    def _fetch_for_q(q: str, limit: int, offset: int = 0) -> List[ImageResultItem]:
        params = {
            "action": "query",
            "generator": "search",
            "gsrnamespace": "6",  # File namespace
            "gsrsearch": q,
            "gsrlimit": str(min(limit, 50)),
            "gsroffset": str(offset),
            "prop": "imageinfo",
            "iiprop": "url|size|extmetadata",
            "iiurlwidth": "300",
            "format": "json",
        }
        url = f"https://commons.wikimedia.org/w/api.php?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers=WIKI_HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=8) as response:
                data = json.loads(response.read().decode("utf-8", errors="ignore"))
        except Exception:
            return []

        pages = data.get("query", {}).get("pages", {})
        res: List[ImageResultItem] = []
        for page_id, page_info in pages.items():
            imageinfo = page_info.get("imageinfo", [])
            if not imageinfo:
                continue
            info = imageinfo[0]
            original_url = info.get("url")
            thumb_url = info.get("thumburl") or original_url
            title = page_info.get("title", "").replace("File:", "").strip()
            width = int(info.get("width") or 0)
            height = int(info.get("height") or 0)
            source = info.get("descriptionurl") or "Wikimedia Commons"

            if original_url:
                clean_url = original_url.split("?")[0].lower()
                if any(clean_url.endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg")):
                    res.append(
                        ImageResultItem(
                            title=title,
                            thumb_url=thumb_url,
                            original_url=original_url,
                            width=width,
                            height=height,
                            source=source,
                        )
                    )
        return res

    first_offset = max(0, (page - 1) * min(max_results, 50))
    results = _fetch_for_q(clean_query, max_results, offset=first_offset)
    seen_urls = {r.original_url for r in results}

    # Only expand if primary query returned very few results (< 3)
    if len(results) < 3:
        base_concept = _extract_base_concept(clean_query)
        if base_concept != clean_query:
            base_results = _fetch_for_q(base_concept, limit=max_results - len(results), offset=first_offset)
            for item in base_results:
                if item.original_url not in seen_urls:
                    seen_urls.add(item.original_url)
                    results.append(item)

        synonyms = _get_medical_synonyms(clean_query)
        if base_concept != clean_query and not synonyms:
            synonyms = _get_medical_synonyms(base_concept)

        for syn in synonyms[:2]:
            if len(results) >= max_results:
                break
            syn_results = _fetch_for_q(syn, limit=max_results - len(results), offset=first_offset)
            for item in syn_results:
                if item.original_url not in seen_urls:
                    seen_urls.add(item.original_url)
                    results.append(item)

    return results[:max_results]


def search_wikipedia_articles(
    query: str,
    lang: Optional[str] = None,
    max_results: int = 15,
    page: int = 1,
) -> List[ImageResultItem]:
    """
    Searches Wikipedia articles in the given language (and English fallback for medical terms)
    and extracts the primary illustrations, diagrams, and textbook figures embedded in those articles.
    Supports pagination via gsroffset.
    """
    clean_query = query.strip()
    if not clean_query:
        return []

    effective_lang = lang or get_current_language() or "pt"
    is_med = _is_medical_or_pathological_query(clean_query) or any(
        p in clean_query.lower() for p in ("apendic", "pancreat", "tomograf")
    )

    def _fetch_wiki_lang(q: str, l_code: str, limit: int, offset: int = 0) -> List[ImageResultItem]:
        gsr_search = q
        if is_med and "-haswbstatement:P31=Q5" not in q:
            gsr_search = f"{q} -haswbstatement:P31=Q5"

        params = {
            "action": "query",
            "generator": "search",
            "gsrsearch": gsr_search,
            "gsrlimit": str(min(limit, 20)),
            "gsroffset": str(offset),
            "prop": "pageimages|pageterms",
            "piprop": "original|thumbnail",
            "pithumbsize": "320",
            "format": "json",
        }
        url = f"https://{l_code}.wikipedia.org/w/api.php?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers=WIKI_HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=8) as response:
                data = json.loads(response.read().decode("utf-8", errors="ignore"))
        except Exception:
            return []

        pages = data.get("query", {}).get("pages", {})
        res: List[ImageResultItem] = []
        for _, page_info in pages.items():
            original = page_info.get("original", {}).get("source")
            if not original:
                continue
            thumbnail = page_info.get("thumbnail", {}).get("source") or original
            title = page_info.get("title", "")
            raw_desc = page_info.get("terms", {}).get("description", [""])[0]
            desc = raw_desc.lower()

            # Discard biographical articles (saints, politicians, priests, doctors, actors, etc.)
            biographical_terms = (
                "santo", "beata", "arcebispo", "compositor", "político", "politico",
                "padre", "religiosa", "médico", "medico", "cirurgião", "cirurgiao",
                "actor", "actress", "atriz", "ator", "writer", "escritor", "saint",
                "priest", "born in", "nascido em", "nascida em"
            )
            if any(bt in desc for bt in biographical_terms):
                continue

            # Anchor validation in title: Title must contain at least one keyword
            # from search query, base concept, or sub-query q.
            stopwords = {
                "com", "para", "por", "sem", "sobre", "entre", "que", "uma", "uns", "das", "dos",
                "del", "las", "los", "the", "and", "for", "with", "from", "that", "this"
            }
            anchor_words = set()
            for src_text in (clean_query, _extract_base_concept(clean_query), q):
                for w in re.findall(r"\w+", src_text.lower()):
                    if (len(w) >= 3 or w in KNOWN_MEDICAL_2LETTER_WORDS) and w not in stopwords:
                        anchor_words.add(w)

            if anchor_words:
                title_lower = title.lower()
                def _strip_accents(t: str) -> str:
                    return (
                        t.replace("á", "a").replace("à", "a").replace("â", "a").replace("ã", "a")
                        .replace("é", "e").replace("ê", "e")
                        .replace("í", "i")
                        .replace("ó", "o").replace("ô", "o").replace("õ", "o")
                        .replace("ú", "u")
                        .replace("ç", "c")
                    )
                title_norm = _strip_accents(title_lower)
                has_anchor = False
                for aw in anchor_words:
                    if aw in title_lower or _strip_accents(aw) in title_norm:
                        has_anchor = True
                        break
                if not has_anchor:
                    continue

            full_title = f"{title} ({raw_desc})" if raw_desc else title
            width = int(page_info.get("original", {}).get("width") or 0)
            height = int(page_info.get("original", {}).get("height") or 0)

            encoded_title = urllib.parse.quote(title.replace(" ", "_"))
            source = f"https://{l_code}.wikipedia.org/wiki/{encoded_title}"

            res.append(
                ImageResultItem(
                    title=full_title,
                    thumb_url=thumbnail,
                    original_url=original,
                    width=width,
                    height=height,
                    source=source,
                )
            )
        return res

    first_offset = max(0, (page - 1) * min(max_results, 20))
    results = _fetch_wiki_lang(clean_query, effective_lang, max_results, offset=first_offset)
    seen_urls = {r.original_url for r in results}

    # If results are sparse (< 3), try base concept without qualifiers
    if len(results) < 3:
        base_concept = _extract_base_concept(clean_query)
        if base_concept != clean_query:
            base_items = _fetch_wiki_lang(base_concept, effective_lang, limit=max_results - len(results), offset=first_offset)
            for item in base_items:
                if item.original_url not in seen_urls:
                    seen_urls.add(item.original_url)
                    results.append(item)

    # If results are sparse and effective_lang is not English, try English once
    if len(results) < 3 and effective_lang != "en":
        en_items = _fetch_wiki_lang(clean_query, "en", limit=max_results - len(results), offset=first_offset)
        for item in en_items:
            if item.original_url not in seen_urls:
                seen_urls.add(item.original_url)
                results.append(item)
        if len(results) < 3:
            synonyms = _get_medical_synonyms(clean_query)
            for syn in synonyms[:2]:
                syn_items = _fetch_wiki_lang(syn, "en", limit=max_results - len(results), offset=first_offset)
                for item in syn_items:
                    if item.original_url not in seen_urls:
                        seen_urls.add(item.original_url)
                        results.append(item)

    return results[:max_results]


def search_images(
    query: str,
    engine: str = "all",
    max_results: int = 50,
    safe_search: bool = False,
    page: int = 1,
) -> List[ImageResultItem]:
    """
    Main entry point for image searches.
    Modes:
    - 'wikimedia': Wikimedia Commons
    - 'wikipedia': Wikipedia articles
    - 'wiki': Wikipedia articles & Wikimedia Commons
    - 'web' / 'google' / 'bing': Web Images (Open Web, Medical Journals, Articles)
    - 'ddg': DuckDuckGo Images
    - 'all': Aggregates Web + Wikimedia + Wikipedia, discarding relevance_score < 0 and sorting by relevance_score descending
    """
    engine_lower = engine.lower()
    if engine_lower == "wikimedia":
        return search_wikimedia(query, max_results=max_results, page=page)
    if engine_lower == "wikipedia":
        return search_wikipedia_articles(query, max_results=max_results, page=page)
    if engine_lower == "wiki":
        wiki_art = search_wikipedia_articles(query, max_results=15, page=page)
        commons = search_wikimedia(query, max_results=max_results, page=page)
        return wiki_art + commons
    if engine_lower in ("google", "web", "bing"):
        results = search_google_images(query, max_results=max_results, safe_search=safe_search, page=page)
        if not results:
            results = search_duckduckgo_images(query, max_results=max_results, page=page)
        return results
    if engine_lower == "ddg":
        return search_duckduckgo_images(query, max_results=max_results, page=page)

    # Combined 'all' mode:
    # Aggregates Web (Medical Articles/Journals/Open Web) + Wikimedia + Wikipedia.
    # Strictly discards any item with relevance_score < 0 and orders all items by relevance_score descending.
    is_radiological = any(
        k in query.lower() for k in ("tomografia", "ressonanc", "ressonância", "scan", "cect", "radiolog", "pancreat", "apendic", "atlanta")
    ) or any(
        re.search(rf"\b{re.escape(k)}\b", query.lower()) for k in ("tc", "rm", "ct", "mri", "rx", "us")
    )
    is_medical = _is_medical_or_pathological_query(query)

    web_results = search_google_images(query, max_results=max_results, safe_search=safe_search, page=page)
    if not web_results or len(web_results) < 8:
        ddg_results = search_duckduckgo_images(query, max_results=max_results, page=page)
        seen_web = {r.original_url for r in web_results}
        for d_it in ddg_results:
            if d_it.original_url not in seen_web:
                seen_web.add(d_it.original_url)
                web_results.append(d_it)
    wiki_results = search_wikipedia_articles(query, max_results=15, page=page)
    commons_results = search_wikimedia(query, max_results=max_results, page=page)

    query_words = [
        w.lower() for w in re.findall(r"\w+", query)
        if len(w) > 2 or w.lower() in KNOWN_MEDICAL_2LETTER_WORDS
    ]
    synonyms = _get_medical_synonyms(query)

    # Ensure all wiki, commons, and web items have an accurate relevance_score
    for item in web_results + wiki_results + commons_results:
        if item.relevance_score == 0:
            item.relevance_score = _calculate_relevance_score(
                item.title, item.source, query_words, is_anatomical=(is_radiological or is_medical), synonyms=synonyms
            )

    combined: List[ImageResultItem] = []
    seen: Set[str] = set()

    for item in web_results + wiki_results + commons_results:
        if item.original_url in seen:
            continue
        seen.add(item.original_url)
        if item.relevance_score < 0:
            continue
        combined.append(item)

    # Sort all combined items strictly by relevance_score descending
    combined.sort(key=lambda x: x.relevance_score, reverse=True)
    return combined[:max_results]


MIME_TO_EXT = {
    "image/jpeg": ".jpg",
    "image/pjpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/svg+xml": ".svg",
    "image/avif": ".avif",
}


def download_image_bytes(url: str, timeout: int = 15) -> Tuple[bytes, str]:
    """
    Downloads raw image bytes and infers the appropriate file extension.
    Uses resilient multi-tiered HTTP headers and SSL fallbacks to bypass anti-hotlinking.
    Returns: (image_bytes, extension_with_dot)
    Raises RuntimeError on failure.
    """
    import ssl

    parsed = urllib.parse.urlsplit(url)
    is_wikimedia = "wikimedia.org" in parsed.netloc.lower() or "wikipedia.org" in parsed.netloc.lower()

    if is_wikimedia:
        user_agent = "AnkiObsidianAddon/2.4 (https://github.com/xvier98-tech/Anki_Overhaul; support@anki.addon)"
    else:
        user_agent = DEFAULT_HEADERS.get("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)")

    # Permutations of Referer to bypass anti-hotlinking protections
    referer_candidates = [
        f"{parsed.scheme}://{parsed.netloc}/" if parsed.netloc else None,
        None,
        "https://www.google.com/",
    ]

    # Create unverified SSL context as fallback for sites with expired or self-signed certs
    ssl_contexts = [None]
    try:
        unverified_ctx = ssl.create_default_context()
        unverified_ctx.check_hostname = False
        unverified_ctx.verify_mode = ssl.CERT_NONE
        ssl_contexts.append(unverified_ctx)
    except Exception:
        pass

    last_exc = None
    data = None
    content_type = ""

    for ref in referer_candidates:
        headers = {
            "User-Agent": user_agent,
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,pt-BR;q=0.8,pt;q=0.7",
        }
        if ref:
            headers["Referer"] = ref

        req = urllib.request.Request(url, headers=headers)

        for ctx in ssl_contexts:
            try:
                open_kwargs = {"timeout": timeout}
                if ctx is not None:
                    open_kwargs["context"] = ctx
                with urllib.request.urlopen(req, **open_kwargs) as response:
                    content_type = response.headers.get("Content-Type", "").split(";")[0].strip().lower()
                    data = response.read()
                if data and len(data) > 0:
                    break
            except Exception as e:
                last_exc = e
                # If error is not SSL, don't repeat with unverified context
                if "CERTIFICATE_VERIFY_FAILED" not in str(e):
                    break
        if data and len(data) > 0:
            break

    if not data:
        raise RuntimeError(f"Falha ao baixar imagem de {url}: {last_exc}")

    # Determine extension
    ext = MIME_TO_EXT.get(content_type)
    if not ext:
        # Extract from URL path (ignoring query parameters)
        clean_path = url.split("?")[0]
        url_ext = os.path.splitext(clean_path)[1].lower()
        if url_ext in (".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg", ".avif"):
            ext = ".jpg" if url_ext == ".jpeg" else url_ext
        else:
            ext = ".jpg"

    return data, ext

