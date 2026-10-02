# AP Claim Jacket QC - Streamlit

A local Streamlit quality-control assistant for AP claim-jacket review.

## What it does
- Upload a daily PDF binder or individual claim-jacket PDFs.
- Extract text from text-based PDFs.
- Detect likely voucher boundaries using voucher-number occurrences.
- Extract voucher number, vendor, vendor ID, invoice number/date/amount, PO number.
- Cross-check voucher numbers across pages.
- Check document sequence and missing/duplicate page-level voucher references.
- Perform deterministic arithmetic checks when line-item quantity/unit-price data can be identified.
- Classify each voucher:
  - READY TO SIGN
  - MINOR CORRECTION REQUIRED
  - HOLD – STAFF VERIFICATION REQUIRED
  - NOT READY FOR PAYMENT
- Review each voucher in the browser.
- Export Excel results and a text audit report.

## Important
This is a QC assistant, not an accounting approval engine. It does not post, match, unmatch, pay, approve, or alter PeopleSoft transactions.

Electronic approvals are intentionally NOT scored as an exception, consistent with the AP Manager workflow.

The application reports "Unable to verify from the provided documentation" when information cannot be established from the uploaded documents.

## Recommended workflow
1. Start the app.
2. Upload the complete daily binder PDF.
3. Review the detected voucher groups.
4. Review all exceptions first.
5. Open each voucher and inspect the page evidence.
6. Correct/verify items with AP staff.
7. Use the Excel report as the QC workpaper.
8. Perform your normal final AP Manager signature review.

## Run
Windows:
    start_app.bat

Or:
    python -m venv venv
    venv\Scripts\activate
    pip install -r requirements.txt
    streamlit run app.py

The app runs locally at http://localhost:8501
