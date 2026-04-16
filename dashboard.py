import streamlit as st
import requests
import msal
import pdfplumber
from docx import Document
import io
import re
import os
import json
from openai import OpenAI

# ================= CONFIG =================
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
TENANT_ID = os.getenv("TENANT_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

DRIVE_ID = "b!ORTaGLwN-02_GrAVrK79m9MsvOiftmRArp9gOMPHOxcdYXfXWEvoTrGLSi4bzM20"

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPE = ["https://graph.microsoft.com/.default"]

client = OpenAI(api_key=OPENAI_API_KEY)

# ================= VALIDATION =================
if not CLIENT_ID or not CLIENT_SECRET or not TENANT_ID:
    st.error("❌ Missing Azure credentials")
    st.stop()

if not OPENAI_API_KEY:
    st.warning("⚠ OPENAI_API_KEY not set — AI extraction disabled")

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
                pages = pdf.pages[:5]  # 🔥 only first 5 pages
                return "\n".join([p.extract_text() or "" for p in pages])

        elif file_name.lower().endswith(".docx"):
            doc = Document(io.BytesIO(file_bytes))
            return "\n".join([p.text for p in doc.paragraphs[:50]])

        else:
            return file_bytes.decode("utf-8", errors="ignore")

    except Exception as e:
        return f"Error reading file: {str(e)}"

# ================= AI EXTRACTION =================
def extract_contract_info_ai(text):
    if not OPENAI_API_KEY:
        return {
            "Contract Date": "AI Disabled",
            "Contract Officer": "AI Disabled",
            "Contract Value": "AI Disabled"
        }

    prompt = f"""
Extract the following from the contract:

- Contract Date
- Contract Officer
- Contract Value

Return ONLY JSON:
{{
  "Contract Date": "",
  "Contract Officer": "",
  "Contract Value": ""
}}

Document:
{text[:6000]}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You extract structured data from contracts."},
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )

        return json.loads(response.choices[0].message.content)

    except Exception as e:
        return {
            "Contract Date": "Error",
            "Contract Officer": "Error",
            "Contract Value": str(e)
        }

# ================= UI =================
st.set_page_config(page_title="RFP Intelligence Platform", layout="wide")

st.title("📊 RFP Intelligence Platform")
st.caption("SharePoint Integrated AI Document Intelligence")

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

with st.spinner("🤖 AI analyzing contract..."):
    data = extract_contract_info_ai(text)

# ================= DISPLAY =================
st.subheader("📄 Extracted Contract Details")

col1, col2, col3 = st.columns(3)

col1.metric("Contract Date", data.get("Contract Date", "N/A"))
col2.metric("Contract Officer", data.get("Contract Officer", "N/A"))
col3.metric("Contract Value", data.get("Contract Value", "N/A"))

st.divider()

with st.expander("📜 Full Extracted Text"):
    st.text(text[:5000])