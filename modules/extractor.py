import re
from decimal import Decimal, InvalidOperation

def clean_text(text):
    return re.sub(r"[ \t]+", " ", text or "").strip()

def first_match(patterns, text, flags=re.I):
    for pat in patterns:
        m = re.search(pat, text or "", flags)
        if m:
            return m.group(1).strip()
    return ""

def money_to_decimal(value):
    if value is None:
        return None
    s = str(value).replace("$", "").replace(",", "").strip()
    s = re.sub(r"[^\d.\-()]", "", s)
    if not s:
        return None
    if s.startswith("(") and s.endswith(")"):
        s = "-" + s[1:-1]
    try:
        return Decimal(s)
    except InvalidOperation:
        return None

def extract_amounts(text):
    vals = []
    for m in re.finditer(r"\$?\(?\d{1,3}(?:,\d{3})*(?:\.\d{2})?\)?|\$?\d+(?:\.\d{2})", text or ""):
        d = money_to_decimal(m.group(0))
        if d is not None:
            vals.append(d)
    return vals

def extract_fields(group):
    text = "\n".join(p["text"] for p in group["pages"])
    compact = clean_text(text)

    voucher = group.get("voucher", "")
    vendor = first_match([
        r"(?:supplier|vendor)\s*(?:name)?\s*[:\-]\s*([^\n]+)",
        r"(?:payee)\s*[:\-]\s*([^\n]+)"
    ], text)

    vendor_id = first_match([
        r"(?:vendor|supplier)\s*(?:id|number|no\.?|#)\s*[:\-]?\s*([A-Z0-9\-]+)"
    ], text)

    invoice_no = first_match([
        r"(?:invoice)\s*(?:number|no\.?|#|id)?\s*[:\-]\s*([A-Z0-9][A-Z0-9\-\/\.]+)",
        r"\bINV(?:OICE)?\s*#?\s*([A-Z0-9\-\/\.]+)"
    ], text)

    invoice_date = first_match([
        r"(?:invoice\s*)?date\s*[:\-]\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",
        r"(?:invoice\s*)?date\s*[:\-]\s*(\d{4}[\/\-]\d{1,2}[\/\-]\d{1,2})"
    ], text)

    po = first_match([
        r"(?:purchase order|p\.?o\.?|po)\s*(?:number|no\.?|#|id)?\s*[:\-]\s*(\d{5,15})"
    ], text)

    total = first_match([
        r"(?:invoice\s*)?(?:total|amount due|amount payable|grand total)\s*[:\-]?\s*\$?\(?([\d,]+\.\d{2})\)?",
        r"(?:total due)\s*\$?\(?([\d,]+\.\d{2})\)?"
    ], text)

    if not total:
        amounts = extract_amounts(text)
        # Conservative fallback: do not call an arbitrary number the invoice total.
        total = str(amounts[-1]) if amounts else ""

    return {
        "voucher": voucher,
        "vendor": vendor,
        "vendor_id": vendor_id,
        "invoice_number": invoice_no,
        "invoice_date": invoice_date,
        "po_number": po,
        "invoice_amount": total,
        "page_count": len(group["pages"]),
        "pages": [p["page"] for p in group["pages"]],
        "raw_text": text
    }
