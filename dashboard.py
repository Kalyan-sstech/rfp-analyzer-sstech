import streamlit as st
import requests
import msal
import pdfplumber
from docx import Document
import io
import re
import os

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

# ================= SHAREPOINT =================
def get_all_files_recursive(token):
    headers = {"Authorization": f"Bearer {token}"}
    all_files = []

    def traverse(path):
        url = f"https://graph.microsoft.com/v1.0/drives/{DRIVE_ID}/root:/{path}:/children"
        res = requests.get(url, headers=headers)

        if res.status_code != 200:
            st.error(f"Error fetching: {path}")
            st.json(res.json())
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

# ================= CACHE DOWNLOAD =================
@st.cache_data(show_spinner=False)
def download_file(token, file_id):
    url = f"https://graph.microsoft.com/v1.0/drives/{DRIVE_ID}/items/{file_id}/content"
    headers = {"Authorization": f"Bearer {token}"}
    return requests.get(url, headers=headers).content

# ================= FAST TEXT EXTRACTION =================
def extract_text(file_bytes, file_name):
    try:
        if file_name.lower().endswith(".pdf"):
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                pages = pdf.pages[:5]  # 🔥 speed optimization
                return "\n".join([p.extract_text() or "" for p in pages])

        elif file_name.lower().endswith(".docx"):
            doc = Document(io.BytesIO(file_bytes))
            return "\n".join([p.text for p in doc.paragraphs[:50]])

        else:
            return file_bytes.decode("utf-8", errors="ignore")

    except Exception as e:
        return f"Error reading file: {str(e)}"

# ================= IMPROVED EXTRACTION =================
def extract_contract_info(text):
    data = {
        "Contract Date": "Not Found",
        "Contract Officer": "Not Found",
        "Contract Value": "Not Found"
    }

    # ===== DATE =====
    date_patterns = [
        r"\b(\d{1,2}[-/ ]\d{1,2}[-/ ]\d{2,4})\b",
        r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}"
    ]
    for pattern in date_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            data["Contract Date"] = match.group()
            break

    # ===== VALUE =====
    value = re.search(r"(\$|₹)\s?[\d,]+", text)
    if value:
        data["Contract Value"] = value.group()

    # ===== OFFICER =====
    officer_patterns = [
        r"Contract Officer[:\- ]+(.*)",
        r"Officer[:\- ]+(.*)",
        r"Authorized by[:\- ]+(.*)",
        r"Authored by[:\- ]+(.*)",
        r"Prepared by[:\- ]+(.*)"
    ]

    for pattern in officer_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            data["Contract Officer"] = match.group(1).strip()
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

options = [f["path"] for f in files]
selected = st.selectbox("Select Document", options)

selected_file = next(f for f in files if f["path"] == selected)

# ================= PROCESS =================
with st.spinner("📥 Downloading document..."):
    file_bytes = download_file(token, selected_file["id"])

with st.spinner("🧠 Extracting text..."):
    text = extract_text(file_bytes, selected_file["name"])

with st.spinner("📊 Analyzing document..."):
    data = extract_contract_info(text)

# ================= DISPLAY =================
st.subheader("📄 Extracted Contract Details")

col1, col2, col3 = st.columns(3)

col1.metric("Contract Date", data.get("Contract Date", "N/A"))
col2.metric("Contract Officer", data.get("Contract Officer", "N/A"))
col3.metric("Contract Value", data.get("Contract Value", "N/A"))

st.divider()

with st.expander("📜 Full Extracted Text"):
    st.text(text[:5000])