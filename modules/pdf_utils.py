import re
from io import BytesIO
import fitz

VOUCHER_PATTERNS = [
    r"(?:voucher\s*(?:id|number|no\.?|#)?|voucher)\s*[:#\-]?\s*(\d{5,12})",
    r"\b(\d{7,9})\b"
]

def open_pdf(file_bytes):
    return fitz.open(stream=file_bytes, filetype="pdf")

def extract_pages(file_bytes):
    doc = open_pdf(file_bytes)
    pages = []
    for i, page in enumerate(doc):
        text = page.get_text("text") or ""
        pages.append({"page": i + 1, "text": text})
    return pages

def normalize_voucher(value):
    if value is None:
        return ""
    digits = re.sub(r"\D", "", str(value))
    if not digits:
        return ""
    return digits.lstrip("0") or "0"

def voucher_candidates(text):
    candidates = []
    for pat in VOUCHER_PATTERNS:
        for m in re.finditer(pat, text, flags=re.I):
            value = m.group(1)
            n = normalize_voucher(value)
            if 5 <= len(n) <= 10:
                candidates.append(value)
    # preserve order, remove duplicates
    seen = set()
    out = []
    for x in candidates:
        n = normalize_voucher(x)
        if n not in seen:
            seen.add(n)
            out.append(x)
    return out

def detect_voucher_for_page(text):
    vals = voucher_candidates(text)
    if not vals:
        return ""
    # Prefer the first explicit voucher-labelled value.
    m = re.search(r"(?:voucher\s*(?:id|number|no\.?|#)?|voucher)\s*[:#\-]?\s*(\d{5,12})", text, flags=re.I)
    return m.group(1) if m else vals[0]

def split_into_voucher_groups(pages):
    """
    Heuristic grouping:
    - A page with a clearly detected voucher starts a group if it differs
      from the active voucher.
    - Pages without a voucher inherit the active group.
    - Pages before the first detected voucher are placed in 'UNIDENTIFIED'.
    """
    groups = []
    current = None
    for p in pages:
        detected = detect_voucher_for_page(p["text"])
        nd = normalize_voucher(detected)
        if nd and (current is None or normalize_voucher(current["voucher"]) != nd):
            current = {"voucher": detected, "pages": []}
            groups.append(current)
        if current is None:
            current = {"voucher": "UNIDENTIFIED", "pages": []}
            groups.append(current)
        current["pages"].append(p)
    return groups
