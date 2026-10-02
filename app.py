import streamlit as st
import pandas as pd
from modules.pdf_utils import extract_pages, split_into_voucher_groups
from modules.extractor import extract_fields
from modules.checks import run_all_checks, classify
from modules.report import make_excel, make_text_report

st.set_page_config(page_title="AP Claim Jacket QC", page_icon="📄", layout="wide")

st.title("📄 AP Claim Jacket QC")
st.caption("Accounts Payable Manager quality-control assistant • Local Streamlit application")

with st.sidebar:
    st.header("Review Settings")
    st.info(
        "Electronic invoice approvals are intentionally not scored. "
        "This app focuses on document, voucher, invoice, PO, arithmetic, and support checks."
    )
    st.markdown("### Review statuses")
    st.write("🟢 READY TO SIGN")
    st.write("🟡 MINOR CORRECTION REQUIRED")
    st.write("🟠 HOLD – STAFF VERIFICATION REQUIRED")
    st.write("🔴 NOT READY FOR PAYMENT")

uploaded = st.file_uploader(
    "Upload the daily claim-jacket binder PDF",
    type=["pdf"],
    accept_multiple_files=False
)

if not uploaded:
    st.markdown("""
### Daily workflow

1. Upload your complete daily PDF binder.
2. The app detects likely voucher groups.
3. Review the dashboard.
4. Open every exception.
5. Verify the flagged pages/documents with AP staff.
6. Download the Excel QC workpaper.
7. Complete your normal AP Manager signature process.

**Important:** The application is a QC assistant. It does not approve, post, match, unmatch, or pay vouchers.
""")
    st.stop()

if "results" not in st.session_state or st.session_state.get("file_name") != uploaded.name:
    with st.spinner("Reading PDF and running QC checks..."):
        file_bytes = uploaded.getvalue()
        pages = extract_pages(file_bytes)
        groups = split_into_voucher_groups(pages)
        results = []
        for g in groups:
            fields = extract_fields(g)
            checks = run_all_checks(fields, g["pages"])
            rec = classify(checks)
            # Minor correction is reserved for simple document presentation issues.
            fields["checks"] = checks
            fields["recommendation"] = rec
            results.append(fields)
        st.session_state["results"] = results
        st.session_state["file_name"] = uploaded.name

results = st.session_state["results"]

if not results:
    st.error("No claim-jacket groups could be detected.")
    st.stop()

df = pd.DataFrame([{
    "Voucher": r["voucher"],
    "Vendor": r["vendor"],
    "Invoice": r["invoice_number"],
    "Amount": r["invoice_amount"],
    "PO": r["po_number"],
    "Pages": ", ".join(map(str,r["pages"])),
    "Recommendation": r["recommendation"],
    "Exceptions": sum(1 for c in r["checks"] if c["status"] in ("FAIL","UNVERIFIED"))
} for r in results])

st.subheader("Daily Batch Dashboard")

c1,c2,c3,c4 = st.columns(4)
c1.metric("Claim Jackets", len(results))
c1.caption("Detected groups")
c2.metric("Ready to Sign", int((df["Recommendation"]=="READY TO SIGN").sum()))
c3.metric("Staff Verification", int((df["Recommendation"]=="HOLD – STAFF VERIFICATION REQUIRED").sum()))
c4.metric("Not Ready", int((df["Recommendation"]=="NOT READY FOR PAYMENT").sum()))

st.divider()

st.subheader("Voucher Review")
st.dataframe(df, use_container_width=True, hide_index=True)

st.subheader("Exception Review")
exceptions = []
for r in results:
    for c in r["checks"]:
        if c["status"] in ("FAIL","UNVERIFIED"):
            exceptions.append({
                "Voucher": r["voucher"],
                "Vendor": r["vendor"],
                "Check": c["check"],
                "Status": c["status"],
                "Issue": c["issue"],
                "Detail": c["detail"],
                "Pages": ", ".join(map(str,r["pages"]))
            })
if exceptions:
    st.dataframe(pd.DataFrame(exceptions), use_container_width=True, hide_index=True)
else:
    st.success("No exceptions were identified by the automated checks.")

st.divider()
st.subheader("Open Individual Claim Jacket")

labels = [
    f"{i+1}. {r['voucher']} | {r['vendor'] or 'Vendor not detected'} | {r['recommendation']}"
    for i,r in enumerate(results)
]
choice = st.selectbox("Select a voucher", labels)
idx = labels.index(choice)
r = results[idx]

st.markdown(f"### Voucher {r['voucher']}")
a,b,c,d = st.columns(4)
a.write("**Vendor**"); a.write(r["vendor"] or "Unable to verify")
b.write("**Vendor ID**"); b.write(r["vendor_id"] or "Unable to verify")
c.write("**Invoice**"); c.write(r["invoice_number"] or "Unable to verify")
d.write("**Amount**"); d.write(r["invoice_amount"] or "Unable to verify")

a,b = st.columns(2)
a.write("**Invoice Date:** " + (r["invoice_date"] or "Unable to verify"))
b.write("**PO:** " + (r["po_number"] or "Unable to verify"))

if r["recommendation"] == "READY TO SIGN":
    st.success("🟢 READY TO SIGN")
elif r["recommendation"] == "NOT READY FOR PAYMENT":
    st.error("🔴 NOT READY FOR PAYMENT")
else:
    st.warning("🟠 " + r["recommendation"])

st.markdown("#### QC Checks")
for c in r["checks"]:
    if c["status"] == "PASS":
        st.write(f"✅ **{c['check']}** — {c['detail']}")
    elif c["status"] == "FAIL":
        st.error(f"❌ **{c['check']}** — {c['issue']} {c['detail']}")
    else:
        st.warning(f"⚠️ **{c['check']}** — {c['issue']} {c['detail']}")

with st.expander("Show extracted document text"):
    st.text(r["raw_text"][:30000])

st.markdown("#### Page Evidence")
st.write("Pages in this detected claim-jacket group:", ", ".join(map(str,r["pages"])))
st.caption("This first release uses text extraction. Scanned/image-only pages may require OCR in the next enhancement.")

st.divider()
st.subheader("Download QC Workpapers")

excel = make_excel(results)
report = make_text_report(results)

st.download_button(
    "⬇️ Download Excel QC Report",
    data=excel,
    file_name="AP_Claim_Jacket_QC_Report.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

st.download_button(
    "⬇️ Download Text QC Report",
    data=report,
    file_name="AP_Claim_Jacket_QC_Report.txt",
    mime="text/plain"
)

st.caption(
    "QC note: A missing field is reported as 'Unable to verify from the provided documentation' "
    "rather than being assumed. Electronic approval status is not reviewed."
)
