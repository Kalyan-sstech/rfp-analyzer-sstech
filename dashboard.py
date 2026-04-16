import streamlit as st
import requests
import msal
import pdfplumber
from docx import Document
import io
import re

# ================= CONFIG =================
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
TENANT_ID = os.getenv("TENANT_ID")

DRIVE_ID = "b!ORTaGLwN-02_GrAVrK79m9MsvOiftmRArp9gOMPHOxcdYXfXWEvoTrGLSi4bzM20"

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPE = ["https://graph.microsoft.com/.default"]

# ================= AUTH =================
def get_token():
    app = msal.ConfidentialClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        client_credential=CLIENT_SECRET
    )
    result = app.acquire_token_for_client(scopes=SCOPE)
    return result.get("access_token")

# ================= SHAREPOINT =================
def get_all_files_recursive(token):
    headers = {"Authorization": f"Bearer {token}"}
    all_files = []

    def traverse(path):
        url = f"https://graph.microsoft.com/v1.0/drives/{DRIVE_ID}/root:/{path}:/children"
        res = requests.get(url, headers=headers)

        if res.status_code != 200:
            return

        items = res.json().get("value", [])

        for item in items:
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


def download_file(token, file_id):
    url = f"https://graph.microsoft.com/v1.0/drives/{DRIVE_ID}/items/{file_id}/content"
    headers = {"Authorization": f"Bearer {token}"}
    return requests.get(url, headers=headers).content

# ================= DOCUMENT PARSER =================
def extract_text(file_bytes, file_name):
    try:
        if file_name.lower().endswith(".pdf"):
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                return "\n".join([p.extract_text() or "" for p in pdf.pages])

        elif file_name.lower().endswith(".docx"):
            doc = Document(io.BytesIO(file_bytes))
            return "\n".join([p.text for p in doc.paragraphs])

        else:
            return file_bytes.decode("utf-8", errors="ignore")

    except Exception as e:
        return f"Error reading file: {str(e)}"

# ================= EXTRACTION =================
def extract_contract_info(text):
    data = {
        "Contract Date": "Not Found",
        "Contract Officer": "Not Found",
        "Contract Value": "Not Found"
    }

    # Date
    date = re.search(r"\b(\d{1,2}[-/ ]\d{1,2}[-/ ]\d{2,4})\b", text)
    if date:
        data["Contract Date"] = date.group()

    # Value
    value = re.search(r"(\$|₹)\s?[\d,]+", text)
    if value:
        data["Contract Value"] = value.group()

    # Officer
    officer = re.search(r"(Contract Officer|Officer)[:\- ]+(.*)", text, re.IGNORECASE)
    if officer:
        data["Contract Officer"] = officer.group(2)

    return data

# ================= UI =================
st.set_page_config(page_title="RFP Intelligence Platform", layout="wide")

st.title("📊 RFP Intelligence Platform")
st.caption("SharePoint Integrated Document Intelligence")

# ================= MAIN =================
token = get_token()

if not token:
    st.error("❌ Authentication failed")
    st.stop()

with st.spinner("Fetching SharePoint files..."):
    files = get_all_files_recursive(token)

if not files:
    st.warning("⚠ No files found in SharePoint")
    st.stop()

# Select file
options = [f["path"] for f in files]
selected = st.selectbox("📂 Select Document", options)

selected_file = next(f for f in files if f["path"] == selected)

# Download file
file_bytes = download_file(token, selected_file["id"])

# Extract text
text = extract_text(file_bytes, selected_file["name"])

# Extract contract data
data = extract_contract_info(text)

# ================= DISPLAY =================
st.subheader("📄 Extracted Contract Details")

col1, col2, col3 = st.columns(3)

col1.metric("Contract Date", data["Contract Date"])
col2.metric("Contract Officer", data["Contract Officer"])
col3.metric("Contract Value", data["Contract Value"])

st.divider()

with st.expander("📜 Full Extracted Text"):
    st.text(text[:5000])