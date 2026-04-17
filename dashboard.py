import streamlit as st
import requests
import msal
import pdfplumber
from docx import Document
import io
import re
import os
import pandas as pd
from urllib.parse import urlparse, parse_qs, unquote

# ================= CONFIG =================
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
TENANT_ID = os.getenv("TENANT_ID")

DRIVE_ID = "b!ORTaGLwN-02_GrAVrK79m9MsvOiftmRArp9gOMPHOxcdYXfXWEvoTrGLSi4bzM20"

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPE = ["https://graph.microsoft.com/.default"]

MAX_FILES = 200
TIMEOUT = 15

# ================= AUTH =================
def get_token():
    try:
        app = msal.ConfidentialClientApplication(
            CLIENT_ID,
            authority=AUTHORITY,
            client_credential=CLIENT_SECRET
        )
        result = app.acquire_token_for_client(scopes=SCOPE)
        return result.get("access_token")
    except:
        return None

# ================= URL PARSER =================
def extract_path_from_url(url):
    try:
        parsed = urlparse(url)
        query = parse_qs(parsed.query)

        if "id" in query:
            decoded = unquote(query["id"][0]).lstrip("/")
            if "Shared Documents/" in decoded:
                return decoded.split("Shared Documents/")[1]

        if "Shared Documents/" in url:
            decoded = unquote(url)
            return decoded.split("Shared Documents/")[1]

        return None
    except:
        return None

# ================= UTIL =================
def clean_text(text):
    return re.sub(r"\s+", " ", text).strip()

def extract_client_name(path):
    parts = path.split("/")
    if "Client" in parts:
        idx = parts.index("Client")
        if idx + 1 < len(parts):
            return clean_text(parts[idx + 1])
    return "Unknown"

# ================= SHAREPOINT =================
def get_files(token, base_path):
    headers = {"Authorization": f"Bearer {token}"}
    files = []

    def traverse(path):
        if len(files) >= MAX_FILES:
            return

        url = f"https://graph.microsoft.com/v1.0/drives/{DRIVE_ID}/root:/{path}:/children"

        try:
            res = requests.get(url, headers=headers, timeout=TIMEOUT)
            if res.status_code != 200:
                return

            for item in res.json().get("value", []):
                name = item["name"]

                if "folder" in item:
                    traverse(f"{path}/{name}")
                else:
                    if name.lower().endswith((".pdf", ".docx", ".txt")):
                        files.append({
                            "name": name,
                            "id": item["id"],
                            "path": f"{path}/{name}"
                        })
        except:
            pass

    traverse(base_path)
    return files

# ================= DOWNLOAD =================
@st.cache_data(show_spinner=False)
def download_file(token, file_id):
    try:
        url = f"https://graph.microsoft.com/v1.0/drives/{DRIVE_ID}/items/{file_id}/content"
        headers = {"Authorization": f"Bearer {token}"}
        res = requests.get(url, headers=headers, timeout=TIMEOUT)
        return res.content if res.status_code == 200 else None
    except:
        return None

# ================= TEXT =================
def extract_text(file_bytes, file_name):
    try:
        if not file_bytes:
            return ""

        if file_name.lower().endswith(".pdf"):
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                return "\n".join([p.extract_text() or "" for p in pdf.pages[:5]])

        elif file_name.lower().endswith(".docx"):
            doc = Document(io.BytesIO(file_bytes))
            return "\n".join([p.text for p in doc.paragraphs[:50]])

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

    try:
        date = re.search(r"\b\d{1,2}/\d{1,2}/\d{4}\b", text)
        if date:
            data["Contract Date"] = date.group()

        value = re.search(r"(\$|₹)\s?[\d,]+", text)
        if value:
            data["Contract Value"] = value.group()

        officer = re.search(
            r"(Authorized by|Authored by|Prepared by|Contract Officer)[:\- ]+(.*)",
            text,
            re.IGNORECASE
        )
        if officer:
            data["Contract Officer"] = clean_text(officer.group(2))

    except:
        pass

    return data

# ================= UI =================
st.set_page_config(page_title="RFP Intelligence Platform", layout="wide")

# ===== HEADER WITH LOGO =====
col1, col2 = st.columns([1, 6])

with col1:
    st.image("logo.png", width=80)

with col2:
    st.markdown("## RFP Intelligence Platform")
    st.caption("Enterprise Contract Intelligence Dashboard")

st.divider()

# ================= INPUT =================
input_urls = st.text_area("🔗 Paste SharePoint URLs (one per line)", height=150)

token = get_token()

# ================= PROCESS =================
if st.button("🚀 Process Documents"):

    if not token:
        st.error("Authentication failed")
        st.stop()

    urls = [u.strip() for u in input_urls.split("\n") if u.strip()]

    results = []
    errors = 0

    progress = st.progress(0)

    for i, url in enumerate(urls):
        base_path = extract_path_from_url(url)

        if not base_path:
            errors += 1
            continue

        files = get_files(token, base_path)

        for file in files:
            try:
                file_bytes = download_file(token, file["id"])
                text = extract_text(file_bytes, file["name"])
                extracted = extract_contract_info(text)

                results.append({
                    "Source Path": base_path,
                    "Client Name": extract_client_name(file["path"]),
                    "File Name": file["name"],
                    **extracted
                })
            except:
                errors += 1

        progress.progress((i + 1) / len(urls))

    df = pd.DataFrame(results)

    # ================= KPI =================
    col1, col2, col3 = st.columns(3)

    col1.metric("📄 Total Files", len(df))
    col2.metric("⚠ Errors", errors)
    col3.metric("✅ Success Rate", f"{round((len(df)/(len(df)+errors+1))*100,2)}%")

    st.divider()

    st.dataframe(df, use_container_width=True)

    csv = df.to_csv(index=False).encode("utf-8")

    st.download_button(
        "📥 Download CSV",
        csv,
        "rfp_output.csv",
        "text/csv"
    )