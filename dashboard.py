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

# ================= PAGE =================
st.set_page_config(page_title="RFP Intelligence", layout="wide")

# ================= POWER BI UI =================
st.markdown("""
<style>
.stApp {background-color: #f5f7fb;}
.block-container {padding: 2rem;}

.kpi-card {
    background: white;
    padding: 20px;
    border-radius: 12px;
    text-align: center;
    box-shadow: 0px 2px 10px rgba(0,0,0,0.05);
}

.sidebar .sidebar-content {
    background-color: #1f4e79;
    color: white;
}
</style>
""", unsafe_allow_html=True)

# ================= HEADER =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
logo_path = os.path.join(BASE_DIR, "logo.svg")

col1, col2 = st.columns([1,6])
with col1:
    if os.path.exists(logo_path):
        st.image(logo_path, width=120)

with col2:
    st.markdown("## RFP Intelligence Dashboard")
    st.caption("Enterprise SharePoint Contract Intelligence")

st.markdown("---")

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

# ================= CLEAN =================
def clean_text(text):
    return re.sub(r"\s+", " ", text).strip()

# ================= CLIENT EXTRACTION =================
def extract_client_name(text):
    header = text[:1500]

    patterns = [
        (r"([A-Z][A-Za-z&,\.\s]{3,} (Inc|LLC|Ltd|Corporation|Corp|Technologies|Services|Solutions))", 90),
        (r"Client[:\- ]+(.*)", 80),
        (r"Customer[:\- ]+(.*)", 80),
        (r"Agreement between (.*) and", 85),
    ]

    for pattern, score in patterns:
        match = re.search(pattern, header, re.IGNORECASE)
        if match:
            val = match.group(1) if isinstance(match.group(), tuple) else match.group()
            return clean_text(val), score

    return "Unknown", 0

# ================= CONTRACT EXTRACTION =================
def extract_contract_info(text):
    data = {
        "Contract Date": "Not Found",
        "Contract Officer": "Not Found",
        "Contract Value": "Not Found"
    }

    d = re.search(r"\d{1,2}/\d{1,2}/\d{4}", text)
    if d:
        data["Contract Date"] = d.group()

    v = re.search(r"(\$|₹)\s?[\d,]+", text)
    if v:
        data["Contract Value"] = v.group()

    o = re.search(r"(Authorized by|Prepared by|Contract Officer)[:\- ]+(.*)", text, re.IGNORECASE)
    if o:
        data["Contract Officer"] = clean_text(o.group(2))

    return data

# ================= SHAREPOINT DEEP SCAN =================
def get_files(token, base_path):
    headers = {"Authorization": f"Bearer {token}"}
    files = []

    def traverse(path):
        url = f"https://graph.microsoft.com/v1.0/drives/{DRIVE_ID}/root:/{path}:/children"

        while url:
            res = requests.get(url, headers=headers, timeout=TIMEOUT)
            if res.status_code != 200:
                break

            data = res.json()

            for item in data.get("value", []):
                if "folder" in item:
                    traverse(f"{path}/{item['name']}")
                else:
                    files.append({
                        "name": item["name"],
                        "id": item["id"],
                        "path": f"{path}/{item['name']}"
                    })

            url = data.get("@odata.nextLink")

    traverse(base_path)
    return files

# ================= DOWNLOAD =================
@st.cache_data(show_spinner=False)
def download_file(token, file_id):
    url = f"https://graph.microsoft.com/v1.0/drives/{DRIVE_ID}/items/{file_id}/content"
    res = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=TIMEOUT)
    return res.content if res.status_code == 200 else None

# ================= TEXT =================
def extract_text(file_bytes, name):
    try:
        if not file_bytes:
            return ""

        if name.lower().endswith(".pdf"):
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                return "\n".join([p.extract_text() or "" for p in pdf.pages[:5]])

        if name.lower().endswith(".docx"):
            doc = Document(io.BytesIO(file_bytes))
            return "\n".join([p.text for p in doc.paragraphs[:50]])

        return file_bytes.decode("utf-8", errors="ignore")
    except:
        return ""

# ================= SIDEBAR =================
st.sidebar.title("🔗 SharePoint Input")
urls = st.sidebar.text_area("Paste URLs (one per line)", height=150)

process = st.sidebar.button("🚀 Process Documents")

# ================= PROCESS =================
if process:
    token = get_token()

    if not token:
        st.error("Authentication failed")
        st.stop()

    results = []
    errors = 0

    for url in urls.split("\n"):
        if not url.strip():
            continue

        base_path = extract_path_from_url(url.strip())
        if not base_path:
            errors += 1
            continue

        files = get_files(token, base_path)

        for f in files:
            try:
                file_bytes = download_file(token, f["id"])
                text = extract_text(file_bytes, f["name"])

                if len(text) < 50:
                    continue

                if not any(k in text.lower() for k in ["contract", "agreement", "license"]):
                    continue

                client, confidence = extract_client_name(text)
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
    st.session_state["df"] = df

# ================= DISPLAY =================
if "df" in st.session_state:
    df = st.session_state["df"]

    # ===== KPI =====
    col1, col2, col3 = st.columns(3)

    col1.markdown(f"<div class='kpi-card'><h3>{len(df)}</h3>Total Files</div>", unsafe_allow_html=True)
    col2.markdown(f"<div class='kpi-card'><h3>{df['Client Name'].nunique()}</h3>Clients</div>", unsafe_allow_html=True)
    col3.markdown(f"<div class='kpi-card'><h3>{df['Contract Value'].count()}</h3>Contracts</div>", unsafe_allow_html=True)

    st.markdown("---")

    # ===== FILTER =====
    selected = st.selectbox("Filter by Client", ["All"] + list(df["Client Name"].unique()))
    if selected != "All":
        df = df[df["Client Name"] == selected]

    # ===== CHARTS =====
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Contracts by Client")
        st.bar_chart(df["Client Name"].value_counts())

    with col2:
        st.subheader("Contract Value")
        val = df["Contract Value"].str.replace("$","").str.replace(",","")
        val = pd.to_numeric(val, errors="coerce")
        st.bar_chart(val.fillna(0))

    st.markdown("---")

    # ===== TABLE =====
    st.dataframe(df, use_container_width=True)

    # ===== DOWNLOAD =====
    st.download_button("📥 Download CSV", df.to_csv(index=False), "contracts.csv")