"""Shared helpers for the job-search scan scripts (hn_scan.py, oss_scan.py,
remotive_scan.py, jobicy_scan.py, ...). Keeping this in one place means a new
scan script gets dated-folder output, don't-touch-existing-files, tag
persistence, and blocklist/region handling for free, without re-copying (and
re-debugging) the same logic a fourth or fifth time.
"""
import glob
import os
import re
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCAN_DIR = os.path.join(ROOT, "scan-results")
BLOCKLIST_PATH = os.path.join(ROOT, "07-companies-to-avoid.md")

CHECKBOX_RE = re.compile(r"^-\s\[([ xX])\]\s(?:\[(?P<tag>[^\]]*)\]\s)?\*\*\[[^\]]+\]\((?P<url>[^)]+)\)")
SKIPPED_LINE_RE = re.compile(r"^-\s~~\[[^\]]+\]\((?P<url>[^)]+)\):.*~~\s\(skipped:\s*(?P<tag>[^)]+)\)")
TABLE_ROW_RE = re.compile(r"^\|\s*([^|]+?)\s*\|")
SKIPPED_PREFIX_RE = re.compile(r"^\s*skipped\s*:\s*", re.I)

# Region handling shared by any source with a location/geo field: US-only is a
# hard skip (residency fact, not negotiable), EMEA/APAC/Worldwide is preferred.
US_ONLY_LOCATION_RE = re.compile(r"\b(usa|u\.s\.a?\.?|united states)\b", re.I)
OTHER_REGION_RE = re.compile(
    r"\b(worldwide|anywhere|global|europe|emea|asia|africa|oceania|americas|apac|"
    r"asia.pacific|uk|canada|israel|international)\b", re.I
)
PREFERRED_REGION_RE = re.compile(
    r"\b(europe|emea|asia|africa|oceania|apac|asia.pacific|worldwide|anywhere|global)\b", re.I
)


def dated_out(source: str) -> str:
    """scan-results/<today>/<source>-scan.md, one folder per day so every
    source's report for a given day sits together, sorted naturally by
    folder name."""
    today = datetime.now().strftime("%Y-%m-%d")
    return os.path.join(SCAN_DIR, today, f"{source}-scan.md")


def find_prior_report(out_path: str, source: str) -> str | None:
    """Today's own file if a same-day rerun, else the most recent earlier
    day's report for this source, searched across all date folders."""
    if os.path.exists(out_path):
        return out_path
    others = sorted(glob.glob(os.path.join(SCAN_DIR, "*", f"{source}-scan.md")))
    return others[-1] if others else None


def read_prior_state(path: str) -> dict[str, dict]:
    """URL -> {checked, tag}, covers both a normal checkbox line (main list)
    and a struck-through line already moved to the Skipped section."""
    if not path or not os.path.exists(path):
        return {}
    state = {}
    with open(path) as f:
        for line in f:
            m = CHECKBOX_RE.match(line)
            if m:
                state[m.group("url")] = {"checked": m.group(1).lower() == "x", "tag": m.group("tag")}
                continue
            m = SKIPPED_LINE_RE.match(line)
            if m:
                state[m.group("url")] = {"checked": True, "tag": m.group("tag")}
    return state


def load_blocklist(path: str = BLOCKLIST_PATH) -> list[str]:
    """Reads company names out of the Blocked table in 07-companies-to-avoid.md."""
    if not os.path.exists(path):
        return []
    names = []
    with open(path) as f:
        for line in f:
            m = TABLE_ROW_RE.match(line)
            if not m:
                continue
            first = m.group(1).strip()
            if not first or first.lower() == "company" or set(first) <= {"-", " "}:
                continue
            names.append(first)
    return names


def resolve_reason(prior_tag: str | None, auto_reason: str | None) -> str | None:
    """Your own tag wins if one's on record, otherwise the auto-detected
    reason. Strips a leading "skipped:" since the section it lands in
    already says that."""
    reason = prior_tag if prior_tag else auto_reason
    if reason:
        reason = SKIPPED_PREFIX_RE.sub("", reason).strip()
    return reason


def is_us_only(location: str) -> bool:
    if not location:
        return False
    return bool(US_ONLY_LOCATION_RE.search(location)) and not OTHER_REGION_RE.search(location)


def is_preferred_region(location: str) -> bool:
    return bool(PREFERRED_REGION_RE.search(location or ""))


# English-language detection, no external library, two checks: script and
# common-word density. Script alone catches Cyrillic (Russian) and Armenian
# script outright, since those are entirely different Unicode blocks from
# Latin. Word density catches other Latin-script languages (Turkish, French,
# German, ...) that script-checking alone would let through.
_LATIN_LETTER_RE = re.compile(r"[A-Za-z]")
_ANY_LETTER_RE = re.compile(r"[^\W\d_]", re.UNICODE)
_ENGLISH_WORDS = frozenset(
    "the and you will with for is are this that our we experience team remote "
    "years work role skills strong looking join required must have has who "
    "about company product build development engineer engineering software".split()
)
_WORD_RE = re.compile(r"[a-zA-Z]+")


def is_english_text(text: str, min_letters: int = 30) -> bool:
    """True if text is confidently English. Short/empty text passes by
    default (not enough signal to say otherwise, better to under-filter than
    silently drop something that just had a short title)."""
    if not text:
        return True
    letters = _ANY_LETTER_RE.findall(text)
    if len(letters) < min_letters:
        return True
    latin = sum(1 for c in letters if _LATIN_LETTER_RE.match(c))
    if latin / len(letters) < 0.85:
        return False
    words = [w.lower() for w in _WORD_RE.findall(text)]
    if len(words) < 15:
        return True
    hits = sum(1 for w in words if w in _ENGLISH_WORDS)
    return (hits / len(words)) >= 0.03


# A job can be written in English but still require a language you don't
# speak ("Armenian native speaker", "fluent Russian required"), catch that
# as a separate check from is_english_text, which only judges the text
# itself.
_OTHER_LANGUAGES = (
    "armenian|russian|turkish|arabic|georgian|azerbaijani|persian|farsi|ukrainian|"
    "polish|german|french|spanish|italian|portuguese|dutch|chinese|mandarin|"
    "japanese|korean|hindi|hebrew|romanian|greek|bulgarian|serbian|croatian|"
    "czech|slovak|hungarian|vietnamese|thai|indonesian|swedish|norwegian|danish|finnish"
)
OTHER_LANGUAGE_REQUIREMENT_RE = re.compile(
    rf"\b(fluent|native|proficient|proficiency|speak|speaking|speaker|knowledge of|"
    rf"command of|required?)\b[^.\n]{{0,40}}\b({_OTHER_LANGUAGES})\b"
    rf"|\b({_OTHER_LANGUAGES})\b[^.\n]{{0,40}}\b(fluent|native|proficient|proficiency|"
    rf"required|speaking|speaker|language)\b",
    re.I,
)


def requires_other_language(text: str) -> str | None:
    """Returns the language name if the text seems to require one you don't
    speak, else None. English itself is never flagged (checking for "English
    required" would otherwise self-match the language name list's neighbors)."""
    m = OTHER_LANGUAGE_REQUIREMENT_RE.search(text or "")
    if not m:
        return None
    lang = (m.group(2) or m.group(3) or "").capitalize()
    return lang or None


def progress_bar(done: int, total: int, width: int = 24) -> str:
    """[###########-------------] 46%, plain text so it degrades fine when
    piped to a log file instead of a live terminal."""
    total = max(total, 1)
    frac = min(done / total, 1.0)
    filled = int(width * frac)
    bar = "#" * filled + "-" * (width - filled)
    return f"[{bar}] {frac * 100:5.1f}%"
