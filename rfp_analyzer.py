import streamlit as st
import rfp_analyzer
import os
import json
from datetime import datetime

# Page Config
st.set_page_config(page_title="SSTECH RFP Platform", layout="wide")

# Standardize filename to match your screenshot
HISTORY_FILE = "rfp_history.json"

# ---------- CUSTOM CSS ----------
st.markdown("""
<style>
    body {background-color: #f6f8fb;}
    [data-testid="stSidebar"] {background-color: #0f172a; color: white;}
    .card {background: white; padding: 20px; border-radius: 12px; box-shadow: 0px 2px 10px rgba(0,0,0,0.05); margin-bottom: 15px;}
    .metric {font-size: 28px; font-weight: 700; color: #1e3a8a;}
    .label {font-size: 14px; color: #64748b; margin-bottom: 5px;}
    .badge {padding: 6px 14px; border-radius: 20px; font-weight: 600; font-size: 12px; display: inline-block;}
    .green { background:#dcfce7; color:#166534; }
    .orange { background:#fef3c7; color:#92400e; }
</style>
""", unsafe_allow_html=True)

# ---------- SIDEBAR ----------
st.sidebar.title("🏢 SSTECH")
menu = st.sidebar.radio("Navigation", ["Overview", "Analysis", "History"])

# ---------- HEADER ----------
col1, col2 = st.columns([1,6])
with col1:
    # Robust pathing for Azure
    logo_path = os.path.join(os.path.dirname(__file__), "logo.png")
    if os.path.exists(logo_path):
        st.image(logo_path, width=80)

with col2:
    st.markdown("<h1 style='margin-bottom:0;'>RFP Intelligence Platform</h1>", unsafe_allow_html=True)
    st.caption("Strategic AI-powered Opportunity Analysis")

st.divider()

# ---------- UTILITIES ----------
def save_to_history(data):
    history = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                history = json.load(f)
        except: history = []
    history.append(data)
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)

# ---------- OVERVIEW ----------
if menu == "Overview":
    st.subheader("📊 Portfolio Summary")
    files = st.file_uploader("Upload RFP Files", accept_multiple_files=True)
    
    if st.button("🚀 Run Portfolio Analysis") and files:
        scores, wins, count = 0, 0, 0
        for file in files:
            content = file.read().decode("utf-8")
            res = rfp_analyzer.process_rfp(content)
            
            s = res["scores"]["total"]
            w = int(res["win_probability"].replace("%",""))
            scores += s
            wins += w
            count += 1
            
            save_to_history({
                "name": file.name, "score": s, "win": f"{w}%",
                "time": datetime.now().strftime("%Y-%m-%d %H:%M")
            })

        c1, c2, c3 = st.columns(3)
        c1.markdown(f"<div class='card'><div class='label'>Avg Propensity</div><div class='metric'>{int(scores/count)}/25</div></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='card'><div class='label'>Avg Win Prob.</div><div class='metric'>{int(wins/count)}%</div></div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='card'><div class='label'>Total Documents</div><div class='metric'>{count}</div></div>", unsafe_allow_html=True)

# ---------- ANALYSIS ----------
elif menu == "Analysis":
    st.subheader("📄 Deep-Dive Analysis")
    files = st.file_uploader("Select RFP for Detail", accept_multiple_files=True)
    if files:
        for file in files:
            content = file.read().decode("utf-8")
            res = rfp_analyzer.process_rfp(content)
            
            with st.expander(f"Analysis: {file.name}", expanded=True):
                mc1, mc2, mc3, mc4 = st.columns(4)
                mc1.metric("Score", res["scores"]["total"])
                mc2.metric("Win %", res["win_probability"])
                mc3.metric("Action", res["recommendation"])
                mc4.metric("Partnering", res["partner_required"])
                
                win_val = int(res["win_probability"].replace("%",""))
                status = ("green", "Strong Opportunity") if win_val > 70 else ("orange", "Review Required")
                st.markdown(f"<div class='badge {status[0]}'>{status[1]}</div>", unsafe_allow_html=True)
                
                st.write("### AI Strategic Summary")
                st.info(res.get("explanation", "AI Engine offline."))

# ---------- HISTORY ----------
elif menu == "History":
    st.subheader("🕘 Recent Reports")
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            data = json.load(f)
        for item in reversed(data):
            st.markdown(f"<div class='card'><b>{item['name']}</b><br>Score: {item['score']} | Win: {item['win']}<br><small>{item['time']}</small></div>", unsafe_allow_html=True)
    else:
        st.warning("No local history found.")