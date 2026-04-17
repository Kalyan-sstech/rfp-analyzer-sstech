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

TIMEOUT = 20

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

# ================= URL PARSER (FORCE ROOT FOLDER) =================
def extract_path_from_url(url):
    try:
        parsed = urlparse(url)
        query = parse_qs(parsed.query)

        if "id" in query:
            decoded = unquote(query["id"][0]).lstrip("/")

            if "Shared Documents/" in decoded:
                path = decoded.split("Shared Documents/")[1]
                return path.split("/")[0]   # 🔥 ROOT ONLY

        if "Shared Documents/" in url:
            decoded = unquote(url)
            path = decoded.split("Shared Documents/")[1]
            return path.split("/")[0]

        return None
    except:
        return None

# ================= UTIL =================
def clean_text(text):
    return re.sub(r"\s+", " ", text).strip()

# ================= CLIENT EXTRACTION =================
def extract_client_name_advanced(text, path):
    candidates = []
    scores = []

    header = text[:1500]

    patterns = [
        (r"([A-Z][A-Za-z&,\.\s]{3,} (Inc|LLC|Ltd|Corporation|Corp|Technologies|Solutions|Services|Systems))", 0.9),
        (r"Client[:\- ]+(.*)", 0.8),
        (r"Customer[:\- ]+(.*)", 0.8),
        (r"Company[:\- ]+(.*)", 0.8),
        (r"Agreement between (.*) and", 0.85),
    ]

    for pattern, score in patterns:
        matches = re.findall(pattern, header, re.IGNORECASE)
        for m in matches:
            val = m[0] if isinstance(m, tuple) else m
            candidates.append(clean_text(val))
            scores.append(score)

    sig = text[-1000:]
    sig_match = re.search(r"(Authorized by|By)[:\- ]+(.*)", sig, re.IGNORECASE)
    if sig_match:
        candidates.append(clean_text(sig_match.group(2)))
        scores.append(0.6)

    filtered = [(c, s) for c, s in zip(candidates, scores)
                if 5 < len(c) < 80 and "agreement" not in c.lower()]

    if filtered:
        best = sorted(filtered, key=lambda x: x[1], reverse=True)[0]
        return best[0], round(best[1]*100, 2)

    parts = path.split("/")
    if "Client" in parts:
        idx = parts.index("Client")
        if idx+1 < len(parts):
            return parts[idx+1], 40.0

    return "Unknown", 0.0

# ================= CONTRACT EXTRACTION =================
def extract_contract_info(text):
    data = {
        "Contract Date": "Not Found",
        "Contract Officer": "Not Found",
        "Contract Value": "Not Found"
    }

    date = re.search(r"\b\d{1,2}/\d{1,2}/\d{4}\b", text)
    if date:
        data["Contract Date"] = date.group()

    value = re.search(r"(\$|₹)\s?[\d,]+", text)
    if value:
        data["Contract Value"] = value.group()

    officer = re.search(
        r"(Authorized by|Prepared by|Contract Officer)[:\- ]+(.*)",
        text,
        re.IGNORECASE
    )
    if officer:
        data["Contract Officer"] = clean_text(officer.group(2))

    return data

# ================= SHAREPOINT DEEP SCAN =================
def get_files(token, base_path):
    headers = {"Authorization": f"Bearer {token}"}
    files = []

    def traverse(path):
        url = f"https://graph.microsoft.com/v1.0/drives/{DRIVE_ID}/root:/{path}:/children"

        while url:
            try:
                res = requests.get(url, headers=headers, timeout=TIMEOUT)
                if res.status_code != 200:
                    break

                data = res.json()

                for item in data.get("value", []):
                    name = item["name"]

                    # Skip system folders
                    if any(x in name.lower() for x in ["forms", "style library"]):
                        continue

                    if "folder" in item:
                        traverse(f"{path}/{name}")
                    else:
                        files.append({
                            "name": name,
                            "id": item["id"],
                            "path": f"{path}/{name}"
                        })

                url = data.get("@odata.nextLink")

            except:
                break

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

# ================= TEXT EXTRACTION =================
def extract_text(file_bytes, name):
    try:
        if not file_bytes:
            return ""

        if name.lower().endswith(".pdf"):
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                return "\n".join([p.extract_text() or "" for p in pdf.pages[:5]])

        elif name.lower().endswith(".docx"):
            doc = Document(io.BytesIO(file_bytes))
            return "\n".join([p.text for p in doc.paragraphs[:50]])

        return file_bytes.decode("utf-8", errors="ignore")
    except:
        return ""

# ================= UI =================
st.set_page_config(layout="wide")
st.title("📊 RFP Intelligence Platform")

urls = st.text_area("🔗 Paste SharePoint URLs (one per line)")

token = get_token()

# ================= PROCESS =================
if st.button("🚀 Process Documents"):

    if not token:
        st.error("Authentication failed")
        st.stop()

    results = []
    errors = 0

    for url in urls.split("\n"):
        url = url.strip()
        if not url:
            continue

        base_path = extract_path_from_url(url)
        if not base_path:
            errors += 1
            continue

        files = get_files(token, base_path)

        for f in files:
            try:
                file_bytes = download_file(token, f["id"])
                text = extract_text(file_bytes, f["name"])

                # 🔥 CONTENT FILTER
                if len(text) < 50:
                    continue

                if not any(k in text.lower() for k in ["contract", "agreement", "invoice", "license"]):
                    continue

                client, confidence = extract_client_name_advanced(text, f["path"])
                info = extract_contract_info(text)

                results.append({
                    "Source Path": base_path,
                    "Client Name": client,
                    "Confidence (%)": confidence,
                    "File Name": f["name"],
                    **info
                })

            except:
                errors += 1

    df = pd.DataFrame(results)

    col1, col2, col3 = st.columns(3)
    col1.metric("📄 Total Files", len(df))
    col2.metric("⚠ Errors", errors)
    col3.metric("📊 Avg Confidence", f"{round(df['Confidence (%)'].mean(),2) if not df.empty else 0}%")

    st.divider()
    st.dataframe(df, use_container_width=True)

    st.download_button(
        "📥 Download CSV",
        df.to_csv(index=False),
        "rfp_output.csv"
    )