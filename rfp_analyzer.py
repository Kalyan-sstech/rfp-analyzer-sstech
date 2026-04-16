import os
import re

# ---------- SAFE IMPORTS ----------
try:
    import google.generativeai as genai
except:
    genai = None

try:
    import requests
except:
    requests = None


# ---------- CONFIG ----------
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")

# ---------- GEMINI SETUP ----------
def get_gemini_response(prompt):
    if not genai or not GEMINI_API_KEY:
        return None

    try:
        genai.configure(api_key=GEMINI_API_KEY)

        model = genai.GenerativeModel("gemini-1.0-pro")  # ✅ stable model

        response = model.generate_content(prompt)

        return response.text

    except Exception as e:
        return None


# ---------- CLAUDE FALLBACK ----------
def get_claude_response(prompt):
    if not requests or not CLAUDE_API_KEY:
        return None

    try:
        url = "https://api.anthropic.com/v1/messages"

        headers = {
            "x-api-key": CLAUDE_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

        data = {
            "model": "claude-3-haiku-20240307",
            "max_tokens": 500,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }

        response = requests.post(url, headers=headers, json=data)

        if response.status_code == 200:
            return response.json()["content"][0]["text"]

        return None

    except:
        return None


# ---------- RULE-BASED SCORING ----------
def calculate_score(text):
    score = 0

    keywords = {
        "cloud": 5,
        "aws": 3,
        "azure": 3,
        "migration": 4,
        "ai": 5,
        "ml": 5,
        "data": 3,
        "security": 4,
        "cyber": 4,
        "support": 2,
        "infra": 3
    }

    text_lower = text.lower()

    for key, val in keywords.items():
        if key in text_lower:
            score += val

    return min(score, 25)


# ---------- WIN PROBABILITY ----------
def calculate_win_probability(score):
    if score >= 20:
        return "80%"
    elif score >= 15:
        return "60%"
    elif score >= 10:
        return "40%"
    else:
        return "20%"


# ---------- RECOMMENDATION ----------
def get_recommendation(score):
    if score >= 18:
        return "BID"
    elif score >= 12:
        return "REVIEW"
    else:
        return "NO BID"


# ---------- MAIN FUNCTION ----------
def process_rfp(text):

    # ---------- SCORE ----------
    score = calculate_score(text)

    win_probability = calculate_win_probability(score)
    recommendation = get_recommendation(score)

    partner_required = "YES" if "partner" in text.lower() else "NO"

    # ---------- AI PROMPT ----------
    prompt = f"""
    Analyze the following RFP and give a short strategic recommendation:

    RFP:
    {text[:2000]}

    Provide:
    - Summary
    - Risks
    - Recommendation
    """

    # ---------- AI ENGINE ----------
    explanation = get_gemini_response(prompt)

    if not explanation:
        explanation = get_claude_response(prompt)

    if not explanation:
        explanation = "AI engine unavailable. Showing rule-based recommendation."

    # ---------- FINAL OUTPUT ----------
    return {
        "scores": {
            "total": score
        },
        "win_probability": win_probability,
        "recommendation": recommendation,
        "partner_required": partner_required,
        "explanation": explanation
    }