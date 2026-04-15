import os

# =========================
# GEMINI SETUP
# =========================
try:
    from google import genai
    GEMINI_AVAILABLE = True
except:
    GEMINI_AVAILABLE = False

API_KEY = os.getenv("GOOGLE_API_KEY")

if GEMINI_AVAILABLE and not API_KEY:
    raise ValueError("❌ GOOGLE_API_KEY not set")

if GEMINI_AVAILABLE:
    client = genai.Client(api_key=API_KEY)


# =========================
# GEMINI CALL
# =========================
def ask_gemini(prompt):
    if not GEMINI_AVAILABLE:
        return None

    try:
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt
        )

        if hasattr(response, "text") and response.text:
            return response.text

        if response.candidates:
            return response.candidates[0].content.parts[0].text

        return None

    except Exception:
        return None


# =========================
# NAICS DETECTION
# =========================
def detect_naics(text):
    text = text.lower()
    naics = []

    if any(k in text for k in ["ai", "machine learning", "automation", "application"]):
        naics.append({"code": "541511", "title": "Custom Software Development"})

    if any(k in text for k in ["architecture", "integration", "cloud"]):
        naics.append({"code": "541512", "title": "System Design"})

    if any(k in text for k in ["support", "helpdesk", "operations"]):
        naics.append({"code": "541513", "title": "IT Support"})

    if any(k in text for k in ["security", "nist", "fedramp"]):
        naics.append({"code": "541519", "title": "Cybersecurity"})

    if any(k in text for k in ["consulting", "pmo", "strategy"]):
        naics.append({"code": "541611", "title": "Consulting"})

    if any(k in text for k in ["staffing", "resources"]):
        naics.append({"code": "561320", "title": "Staffing"})

    return naics


# =========================
# AI / FALLBACK EXPLANATION
# =========================
def generate_explanation(text, decision):

    prompt = f"""
    Explain why this RFP received this evaluation:

    Score: {decision['scores']['total']}
    Recommendation: {decision['recommendation']}
    """

    result = ask_gemini(prompt)

    if result:
        return result

    # ✅ FALLBACK (IMPORTANT FOR DEMO)
    return f"""
    This opportunity was evaluated using rule-based scoring.

    • Identified NAICS categories: {len(decision.get('naics', []))}
    • Capability alignment with IT / Cloud / AI services
    • Final recommendation: {decision['recommendation']}

    This explanation is generated without AI due to API limitation.
    """


# =========================
# EVALUATION
# =========================
def evaluate_opportunity(text):

    naics = detect_naics(text)

    score = 15 + len(naics) * 2
    score = min(score, 25)

    win_probability = f"{score * 3}%"

    if score >= 20:
        rec = "BID"
    elif score >= 15:
        rec = "TEAM-AS-SUB"
    else:
        rec = "NO-BID"

    decision = {
        "scores": {"total": score},
        "win_probability": win_probability,
        "recommendation": rec,
        "confidence": "HIGH" if score >= 18 else "MEDIUM",
        "partner_required": "YES" if rec != "BID" else "NO",
        "partner_type": "8(a)" if rec != "BID" else None,
        "naics": naics,
        "matched_projects": [
            {
                "project": "Cloud Migration Program",
                "reason": "Matches cloud + architecture requirements"
            }
        ]
    }

    decision["explanation"] = generate_explanation(text, decision)

    return decision


# =========================
# MAIN
# =========================
def analyze_rfp_text(text, filename="RFP"):
    return {
        "file": filename,
        "decision": evaluate_opportunity(text)
    }