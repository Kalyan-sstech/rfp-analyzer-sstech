import os
import json
import requests

# ==============================
# CONFIG
# ==============================
API_KEY = os.getenv("GOOGLE_API_KEY")

if not API_KEY:
    raise ValueError("❌ GOOGLE_API_KEY not set")

# Use WORKING Gemini model (important)
MODEL = "gemini-1.5-flash-latest"
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={API_KEY}"


# ==============================
# GEMINI CALL
# ==============================
def call_gemini(prompt):
    try:
        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ]
        }

        response = requests.post(URL, json=payload)
        data = response.json()

        if "candidates" in data:
            return data["candidates"][0]["content"]["parts"][0]["text"]

        return None

    except Exception as e:
        print("Gemini Error:", e)
        return None


# ==============================
# NAICS CLASSIFICATION
# ==============================
def classify_naics(text):
    text = text.lower()

    mapping = {
        "cloud": ("541512", "Systems Design"),
        "software": ("541511", "Custom Software Development"),
        "cybersecurity": ("541519", "Cybersecurity"),
        "support": ("541513", "IT Support"),
        "data": ("541511", "Data Engineering"),
        "ai": ("541715", "AI / ML Research")
    }

    result = []
    for key, val in mapping.items():
        if key in text:
            result.append({"code": val[0], "title": val[1]})

    if not result:
        result.append({"code": "000000", "title": "General IT"})

    return result


# ==============================
# MATCH PROJECTS
# ==============================
def match_projects(text):
    projects = []

    if "cloud" in text.lower():
        projects.append({
            "project": "Cloud Migration Program",
            "reason": "Matches cloud + architecture requirements"
        })

    if "cyber" in text.lower():
        projects.append({
            "project": "Cybersecurity Upgrade",
            "reason": "Matches security requirements"
        })

    return projects


# ==============================
# EXPLANATION (AI)
# ==============================
def generate_explanation(text):
    prompt = f"""
    Analyze this RFP and explain:
    - Why this score is given
    - Strengths
    - Risks
    - Recommendation

    RFP:
    {text}
    """

    result = call_gemini(prompt)

    if result:
        return result.strip()

    return "AI explanation not available"


# ==============================
# SCORING LOGIC
# ==============================
def calculate_score(text):
    score = 0

    if "cloud" in text.lower():
        score += 5
    if "ai" in text.lower():
        score += 5
    if "security" in text.lower():
        score += 5
    if "support" in text.lower():
        score += 3
    if "experience" in text.lower():
        score += 2

    return min(score, 25)


# ==============================
# MAIN ANALYZER
# ==============================
def analyze_rfp_text(text, filename="RFP"):
    score = calculate_score(text)
    win_probability = int((score / 25) * 100)

    recommendation = "BID" if score >= 15 else "NO BID"
    partner_required = "YES" if score < 12 else "NO"

    return {
        "file": filename,
        "score": score,
        "win_probability": f"{win_probability}%",
        "recommendation": recommendation,
        "partner": partner_required,
        "naics": classify_naics(text),
        "matched_projects": match_projects(text),
        "explanation": generate_explanation(text)
    }