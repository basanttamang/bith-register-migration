"""
Cleaning and validation rules, shared by the profiling, migration and
reconciliation scripts so all three apply exactly the same logic.
Each rule is listed in docs/03-mapping-specification.md.
"""
import re
from datetime import date
import nepali_datetime as nd

WARD_MIN, WARD_MAX = 1, 32          # Kathmandu Metropolitan City has 32 wards
MOBILE_RE = re.compile(r"^9[678]\d{8}$")
BS_YEAR_MIN = 2050                   # years 2050+ are Bikram Sambat (2050 BS = 1993 AD); AD years in this register are 2019–2027

# ---------- Names (R1) ----------
ABBREVIATIONS = {"bdr": "bahadur", "pd": "prasad"}

def clean_name(text):
    """Tidy a name for storage: trim, single spaces, Title Case, expand known abbreviations."""
    words = re.sub(r"\s+", " ", (text or "").strip()).split(" ")
    out = []
    for w in words:
        key = w.lower().rstrip(".")
        if w.isupper() and len(w) <= 2:          # keep short capitalised surnames such as KC
            out.append(w); continue
        out.append(ABBREVIATIONS.get(key, key).title() if key else "")
    return " ".join(w for w in out if w)

def match_key(text):
    """Looser version of a name used only to find likely duplicates."""
    return clean_name(text).lower()

# ---------- Dates (R2) ----------
DATE_PATTERNS = [
    ("YYYY/MM/DD", re.compile(r"^(\d{4})/(\d{1,2})/(\d{1,2})$"), ("y", "m", "d")),
    ("YYYY-MM-DD", re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})$"), ("y", "m", "d")),
    ("DD-MM-YYYY", re.compile(r"^(\d{1,2})-(\d{1,2})-(\d{4})$"), ("d", "m", "y")),
    ("DD/MM/YYYY", re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$"), ("d", "m", "y")),
]

def classify_date(text):
    """Return (pattern_name, calendar) without converting. calendar is 'BS', 'AD' or None."""
    t = (text or "").strip()
    for name, rx, order in DATE_PATTERNS:
        m = rx.match(t)
        if m:
            parts = dict(zip(order, map(int, m.groups())))
            return name, ("BS" if parts["y"] >= BS_YEAR_MIN else "AD")
    return ("blank" if not t else "unrecognised"), None

def parse_date(text, today=None):
    """Convert any accepted format to an AD date.
    Returns (ad_date, calendar, error). error is None when the date is usable."""
    today = today or date.today()
    t = (text or "").strip()
    if not t:
        return None, None, "Date of birth is blank"
    for name, rx, order in DATE_PATTERNS:
        m = rx.match(t)
        if not m:
            continue
        p = dict(zip(order, map(int, m.groups())))
        cal = "BS" if p["y"] >= BS_YEAR_MIN else "AD"
        try:
            ad = nd.date(p["y"], p["m"], p["d"]).to_datetime_date() if cal == "BS" else date(p["y"], p["m"], p["d"])
        except (ValueError, OverflowError, KeyError, IndexError):
            return None, cal, f"Date of birth '{t}' is not a real {cal} date"
        if ad > today:
            return None, cal, f"Date of birth '{t}' is in the future"
        return ad, cal, None
    return None, None, f"Date of birth '{t}' is not in a recognised format"

# ---------- Ward (R3) ----------
def parse_ward(text):
    t = (text or "").strip()
    if not t:
        return None, "Ward number is missing"
    if not t.isdigit() or not (WARD_MIN <= int(t) <= WARD_MAX):
        return None, f"Ward number '{t}' is outside 1–32"
    return int(t), None

# ---------- Phone (R4) ----------
def parse_phone(text):
    """Returns (phone_or_None, status) where status is ok / reformatted / missing / invalid."""
    raw = (text or "").strip()
    if not raw:
        return None, "missing"
    digits = re.sub(r"\D", "", raw)
    if digits.startswith("977") and len(digits) == 13:
        digits = digits[3:]
    if MOBILE_RE.match(digits):
        return "+977" + digits, ("ok" if raw == digits else "reformatted")
    return None, "invalid"

# ---------- Sex (R5) ----------
SEX_MAP = {"m": "M", "male": "M", "f": "F", "female": "F"}

def parse_sex(text):
    t = (text or "").strip().lower()
    if not t:
        return "U", "missing"
    if t in SEX_MAP:
        return SEX_MAP[t], ("ok" if text.strip() in ("M", "F") else "standardised")
    return "U", "unrecognised"
