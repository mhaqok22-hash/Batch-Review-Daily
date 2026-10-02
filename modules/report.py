from io import BytesIO
import pandas as pd

def make_excel(vouchers):
    rows = []
    checks = []
    for v in vouchers:
        rows.append({
            "Voucher": v["voucher"],
            "Vendor": v["vendor"],
            "Vendor ID": v["vendor_id"],
            "Invoice Number": v["invoice_number"],
            "Invoice Date": v["invoice_date"],
            "PO Number": v["po_number"],
            "Invoice Amount": v["invoice_amount"],
            "Pages": ", ".join(map(str,v["pages"])),
            "Recommendation": v["recommendation"],
            "Exception Count": sum(1 for c in v["checks"] if c["status"] in ("FAIL","UNVERIFIED"))
        })
        for c in v["checks"]:
            checks.append({
                "Voucher": v["voucher"],
                "Check": c["check"],
                "Status": c["status"],
                "Issue": c["issue"],
                "Detail": c["detail"]
            })
    df = pd.DataFrame(rows)
    cdf = pd.DataFrame(checks)
    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Voucher Review")
        cdf.to_excel(writer, index=False, sheet_name="Exceptions & Checks")
        if not df.empty:
            summary = df["Recommendation"].value_counts().rename_axis("Recommendation").reset_index(name="Count")
        else:
            summary = pd.DataFrame(columns=["Recommendation","Count"])
        summary.to_excel(writer, index=False, sheet_name="Summary")
        for ws in writer.book.worksheets:
            for col in ws.columns:
                maxlen = max(len(str(c.value or "")) for c in col)
                ws.column_dimensions[col[0].column_letter].width = min(max(maxlen + 2, 12), 45)
            ws.freeze_panes = "A2"
    return out.getvalue()

def make_text_report(vouchers):
    lines = ["AP CLAIM JACKET QC REPORT", "="*70, ""]
    for v in vouchers:
        lines += [
            f"Voucher: {v['voucher']}",
            f"Vendor: {v['vendor'] or 'Unable to verify'}",
            f"Invoice: {v['invoice_number'] or 'Unable to verify'}",
            f"Amount: {v['invoice_amount'] or 'Unable to verify'}",
            f"Recommendation: {v['recommendation']}",
            "Checks:"
        ]
        for c in v["checks"]:
            lines.append(f"  [{c['status']}] {c['check']}: {c['issue'] or c['detail']}")
        lines.append("")
    return "\n".join(lines)
