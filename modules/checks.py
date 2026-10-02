import re
from decimal import Decimal
from .pdf_utils import normalize_voucher
from .extractor import money_to_decimal

def norm(s):
    return re.sub(r"\s+", " ", str(s or "").strip()).lower()

def check_voucher_cross_reference(voucher, pages):
    expected = normalize_voucher(voucher)
    if not expected or voucher == "UNIDENTIFIED":
        return {"status":"FAIL","issue":"Unable to verify voucher number from the provided documentation.","detail":"No reliable voucher number was detected."}
    mismatches = []
    missing = []
    for p in pages:
        text = p["text"]
        # Find explicit voucher references.
        found = []
        for m in re.finditer(r"(?:voucher\s*(?:id|number|no\.?|#)?|voucher)\s*[:#\-]?\s*(\d{5,12})", text, re.I):
            found.append(m.group(1))
        if found:
            if not any(normalize_voucher(x) == expected for x in found):
                mismatches.append((p["page"], found))
        else:
            # Supporting pages may legitimately not have a voucher number.
            missing.append(p["page"])
    if mismatches:
        return {"status":"FAIL","issue":"Voucher number mismatch on one or more pages.","detail":str(mismatches)}
    return {"status":"PASS","issue":"","detail":f"Detected voucher cross-reference on {len(pages)-len(missing)} page(s); pages without an explicit number were not treated as errors."}

def check_required_fields(fields):
    checks = {}
    for key, label in [
        ("voucher","Voucher Number"),
        ("vendor","Vendor"),
        ("invoice_number","Invoice Number"),
        ("invoice_date","Invoice Date"),
        ("invoice_amount","Invoice Amount"),
    ]:
        checks[key] = {
            "status": "PASS" if str(fields.get(key,"")).strip() else "UNVERIFIED",
            "issue": "" if str(fields.get(key,"")).strip() else f"{label} could not be verified from the provided documentation."
        }
    return checks

def find_line_items(text):
    """
    Conservative quantity x unit price detector.
    It looks for lines containing quantity and currency/decimal unit price.
    """
    items = []
    patterns = [
        r"(?m)^\s*(\d+(?:\.\d+)?)\s+(?:x\s+)?\$?([\d,]+\.\d{2})\s+\$?([\d,]+\.\d{2})\s*$",
        r"(?m)^\s*qty\.?\s*(\d+(?:\.\d+)?)\s+.*?\$?([\d,]+\.\d{2}).*?\$?([\d,]+\.\d{2})\s*$"
    ]
    for pat in patterns:
        for m in re.finditer(pat, text or "", re.I):
            try:
                qty = Decimal(m.group(1))
                unit = Decimal(m.group(2).replace(",",""))
                stated = Decimal(m.group(3).replace(",",""))
                items.append((qty, unit, stated))
            except Exception:
                pass
    return items

def check_arithmetic(fields):
    text = fields.get("raw_text","")
    items = find_line_items(text)
    if not items:
        return {"status":"UNVERIFIED","issue":"Arithmetic could not be independently verified from the extracted invoice table.","detail":"No reliable quantity × unit-price line items were detected."}
    differences = []
    calculated = Decimal("0")
    for qty, unit, stated in items:
        calc = qty * unit
        calculated += calc
        if abs(calc - stated) > Decimal("0.01"):
            differences.append({"qty":str(qty),"unit":str(unit),"stated":str(stated),"calculated":str(calc)})
    if differences:
        return {"status":"FAIL","issue":"One or more line-item calculations do not agree.","detail":str(differences)}
    return {"status":"PASS","issue":"","detail":f"{len(items)} line item(s) independently calculated successfully. Line total sum: ${calculated:,.2f}"}

def classify(all_checks):
    fails = [x for x in all_checks if x["status"] == "FAIL"]
    unver = [x for x in all_checks if x["status"] == "UNVERIFIED"]
    if any("amount" in x["issue"].lower() or "mismatch" in x["issue"].lower() for x in fails):
        return "NOT READY FOR PAYMENT"
    if fails:
        return "HOLD – STAFF VERIFICATION REQUIRED"
    if unver:
        return "HOLD – STAFF VERIFICATION REQUIRED"
    return "READY TO SIGN"

def run_all_checks(fields, pages):
    results = []
    v = check_voucher_cross_reference(fields["voucher"], pages)
    results.append({"check":"Voucher Cross-Reference", **v})
    required = check_required_fields(fields)
    for key, r in required.items():
        label = {"voucher":"Voucher Number","vendor":"Vendor","invoice_number":"Invoice Number","invoice_date":"Invoice Date","invoice_amount":"Invoice Amount"}[key]
        results.append({"check":label, "status":r["status"], "issue":r["issue"], "detail":""})
    ar = check_arithmetic(fields)
    results.append({"check":"Arithmetic", **ar})
    return results
