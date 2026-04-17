import streamlit as st
import requests
import msal
import pdfplumber
from docx import Document
import io
import re
import os
import pandas as pd

# ================= CONFIG =================
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
TENANT_ID = os.getenv("TENANT_ID")

DRIVE_ID = "b!ORTaGLwN-02_GrAVrK79m9MsvOiftmRArp9gOMPHOxcdYXfXWEvoTrGLSi4bzM20"

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPE = ["https://graph.microsoft.com/.default"]

# ================= VALIDATION =================
if not CLIENT_ID or not CLIENT_SECRET or not TENANT_ID:
    st.error("❌ Missing Azure credentials")
    st.stop()

# ================= AUTH =================
def get_token():
    app = msal.ConfidentialClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        client_credential=CLIENT_SECRET
    )

    result = app.acquire_token_for_client(scopes=SCOPE)

    if "access_token" in result:
        return result["access_token"]
    else:
        st.error("❌ Authentication failed")
        st.json(result)
        return None

# ================= CLEAN TEXT =================
def clean_text(text):
    return re.sub(r"\s+", " ", text).strip()

# ================= CLIENT NAME (FIXED) =================
def extract_client_name(path):
    parts = path.split("/")

    if "Client" in parts:
        idx = parts.index("Client")

        if idx + 1 < len(parts):
            return clean_text(parts[idx + 1])

    return "Unknown"

# ================= SHAREPOINT =================
def get_all_files_recursive(token):
    headers = {"Authorization": f"Bearer {token}"}
    all_files = []

    def traverse(path):
        url = f"https://graph.microsoft.com/v1.0/drives/{DRIVE_ID}/root:/{path}:/children"
        res = requests.get(url, headers=headers)

        if res.status_code != 200:
            return

        for item in res.json().get("value", []):
            name = item["name"]

            if "folder" in item:
                traverse(f"{path}/{name}")
            else:
                all_files.append({
                    "name": name,
                    "id": item["id"],
                    "path": f"{path}/{name}"
                })

    traverse("SST Inc/Client")
    return all_files

# ================= DOWNLOAD =================
@st.cache_data(show_spinner=False)
def download_file(token, file_id):
    url = f"https://graph.microsoft.com/v1.0/drives/{DRIVE_ID}/items/{file_id}/content"
    headers = {"Authorization": f"Bearer {token}"}
    return requests.get(url, headers=headers).content

# ================= TEXT EXTRACTION =================
def extract_text(file_bytes, file_name):
    try:
        if file_name.lower().endswith(".pdf"):
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                pages = pdf.pages[:5]  # speed optimization
                return "\n".join([p.extract_text() or "" for p in pages])

        elif file_name.lower().endswith(".docx"):
            doc = Document(io.BytesIO(file_bytes))
            return "\n".join([p.text for p in doc.paragraphs[:50]])

        else:
            return file_bytes.decode("utf-8", errors="ignore")

    except:
        return ""

# ================= CONTRACT EXTRACTION =================
def extract_contract_info(text):
    data = {
        "Contract Date": "Not Found",
        "Contract Officer": "Not Found",
        "Contract Value": "Not Found"
    }

    # Date patterns
    date_patterns = [
        r"\b\d{1,2}/\d{1,2}/\d{4}\b",
        r"\b\d{1,2}-\d{1,2}-\d{4}\b"
    ]
    for pattern in date_patterns:
        match = re.search(pattern, text)
        if match:
            data["Contract Date"] = match.group()
            break

    # Value
    value = re.search(r"(\$|₹)\s?[\d,]+", text)
    if value:
        data["Contract Value"] = value.group()

    # Officer
    officer_patterns = [
        r"Authorized by[:\- ]+(.*)",
        r"Authored by[:\- ]+(.*)",
        r"Prepared by[:\- ]+(.*)",
        r"Contract Officer[:\- ]+(.*)"
    ]

    for pattern in officer_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            data["Contract Officer"] = clean_text(match.group(1))
            break

    return data

# ================= UI =================
st.set_page_config(page_title="RFP Intelligence Platform", layout="wide")

st.title("📊 RFP Intelligence Platform")
st.caption("SharePoint Integrated Document Intelligence")

# ================= MAIN =================
token = get_token()

if not token:
    st.stop()

with st.spinner("📂 Fetching SharePoint files..."):
    files = get_all_files_recursive(token)

if not files:
    st.warning("No files found")
    st.stop()

st.info(f"Total Files Found: {len(files)}")

# ================= PROCESS BUTTON =================
if st.button("🚀 Process All Documents"):

    results = []
    progress = st.progress(0)

    for i, file in enumerate(files):
        file_bytes = download_file(token, file["id"])
        text = extract_text(file_bytes, file["name"])
        extracted = extract_contract_info(text)

        results.append({
            "Client Name": extract_client_name(file["path"]),
            "File Name": file["name"],
            "Contract Date": extracted["Contract Date"],
            "Contract Officer": extracted["Contract Officer"],
            "Contract Value": extracted["Contract Value"]
        })

        progress.progress((i + 1) / len(files))

    df = pd.DataFrame(results)

    st.success("✅ Processing Completed")

    # ================= DISPLAY =================
    st.dataframe(df)

    # ================= CSV =================
    csv = df.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="📥 Download CSV",
        data=csv,
        file_name="contract_extraction.csv",
        mime="text/csv"
    )