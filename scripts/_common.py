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
