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
@st.cache_data
def download_file(token, file_id):
    url = f"https://graph.microsoft.com/v1.0/drives/{DRIVE_ID}/items/{file_id}/content"
    headers = {"Authorization": f"Bearer {token}"}
    return requests.get(url, headers=headers).content

# ================= TEXT =================
def extract_text(file_bytes, file_name):
    try:
        if file_name.lower().endswith(".pdf"):
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                return "\n".join([p.extract_text() or "" for p in pdf.pages[:5]])

        elif file_name.lower().endswith(".docx"):
            doc = Document(io.BytesIO(file_bytes))
            return "\n".join([p.text for p in doc.paragraphs[:50]])

        else:
            return file_bytes.decode("utf-8", errors="ignore")
    except:
        return ""

# ================= EXTRACTION =================
def extract_contract_info(text):
    data = {
        "Contract Date": "Not Found",
        "Contract Officer": "Not Found",
        "Contract Value": "Not Found"
    }

    # Date
    date = re.search(r"\b\d{1,2}/\d{1,2}/\d{4}\b", text)
    if date:
        data["Contract Date"] = date.group()

    # Value
    value = re.search(r"(\$|₹)\s?[\d,]+", text)
    if value:
        data["Contract Value"] = value.group()

    # Officer
    officer = re.search(r"(Authorized by|Authored by|Prepared by)[:\- ]+(.*)", text, re.IGNORECASE)
    if officer:
        data["Contract Officer"] = officer.group(2).strip()

    return data

# ================= CLIENT NAME =================
def extract_client_name(path):
    parts = path.split("/")
    try:
        return parts[2]  # SST Inc / Client / CLIENT NAME
    except:
        return "Unknown"

# ================= UI =================
st.title("📊 RFP Intelligence Platform")

token = get_token()

if not token:
    st.error("Authentication failed")
    st.stop()

files = get_all_files_recursive(token)

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
            **extracted
        })

        progress.progress((i + 1) / len(files))

    df = pd.DataFrame(results)

    st.success("✅ Processing Completed")

    st.dataframe(df)

    # CSV DOWNLOAD
    csv = df.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="📥 Download CSV",
        data=csv,
        file_name="contract_extraction.csv",
        mime="text/csv"
    )