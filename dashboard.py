import streamlit as st
import rfp_analyzer
import os
import glob
import requests
from msal import ConfidentialClientApplication
from streamlit_echarts import st_echarts

st.set_page_config(layout="wide")

# ---------------- SECURE CONFIG ----------------
TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

# ---------------- AUTH ----------------
def get_token():
    app = ConfidentialClientApplication(
        CLIENT_ID,
        authority=f"https://login.microsoftonline.com/{TENANT_ID}",
        client_credential=CLIENT_SECRET,
    )
    token = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    return token["access_token"]

# ---------------- ONEDRIVE ----------------
def get_rfp_files(token):
    url = "https://graph.microsoft.com/v1.0/me/drive/root:/RFP-AI/Active RFPs:/children"
    headers = {"Authorization": f"Bearer {token}"}
    return requests.get(url, headers=headers).json().get("value", [])

def download_file(token, file_id):
    url = f"https://graph.microsoft.com/v1.0/me/drive/items/{file_id}/content"
    headers = {"Authorization": f"Bearer {token}"}
    return requests.get(url, headers=headers).content

# ---------------- UI ----------------
st.sidebar.title("🚀 SYSTEMSOFT")
st.title("RFP Intelligence Platform")
st.write("Manual Intelligence Engine")

st.markdown("---")

mode = st.radio("Select Data Source", ["Local", "OneDrive"])

result = None

# ---------------- LOCAL MODE ----------------
if mode == "Local":
    files = glob.glob("data/rfp/*.txt")

    if not files:
        st.warning("No local RFP files found")
    else:
        names = sorted([os.path.basename(f) for f in files])
        selected = st.selectbox("Select Local RFP", names)

        if selected:
            with open(f"data/rfp/{selected}", "r", encoding="utf-8") as f:
                content = f.read()

            result = rfp_analyzer.process_rfp(content)

# ---------------- ONEDRIVE MODE ----------------
if mode == "OneDrive":
    if not CLIENT_ID or not CLIENT_SECRET or not TENANT_ID:
        st.error("Azure credentials not configured. Please set environment variables.")
    else:
        try:
            token = get_token()
            files = get_rfp_files(token)

            if not files:
                st.warning("No files found in OneDrive path")
            else:
                names = [f["name"] for f in files]
                selected = st.selectbox("Select RFP from OneDrive", names)

                if selected:
                    obj = next(f for f in files if f["name"] == selected)
                    content = download_file(token, obj["id"]).decode("utf-8", errors="ignore")

                    result = rfp_analyzer.process_rfp(content)

        except Exception as e:
            st.error(f"OneDrive error: {e}")

# ---------------- DISPLAY ----------------
if result:

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("Score")
        st.write(result["scores"]["total"])

    with col2:
        st.subheader("Win Probability")
        st.write(result["win_probability"])

    with col3:
        st.subheader("Decision")

        if result["recommendation"] == "BID":
            st.success("BID")
        elif result["recommendation"] == "REVIEW":
            st.warning("REVIEW")
        else:
            st.error("NO BID")

    st.markdown("---")

    st.subheader("Executive Summary")
    st.write(result["explanation"])

    st.subheader("Capability Match")
    for c in result["capability_match"]:
        st.write("✔️", c)

    st.subheader("Past Performance")
    for p in result["past_performance"]:
        st.write("🏆", p)

    st.subheader("Risks")
    for r in result["risks"]:
        st.write("⚠️", r)