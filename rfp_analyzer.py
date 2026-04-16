import os
import re
import google.generativeai as genai

# Configure Gemini
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# =========================
# KEYWORD SCORING ENGINE
# =========================
def calculate_score(content):
    keywords = {
        "cloud": 5,
        "azure": 5,
        "aws": 5,
        "ai": 5,
        "machine learning": 5,
        "cybersecurity": 4,
        "data": 3,
        "analytics": 3,
        "support": 2
    }

    score = 0
    content_lower = content.lower()

    for key, value in keywords.items():
        if key in content_lower:
            score += value

    return min(score, 25)


# =========================
# AI EXPLANATION
# =========================
def generate_ai_summary(content, score, win_probability):
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")

        prompt = f"""
        Analyze this RFP and provide:
        - Strategic Summary
        - Recommendation (BID/NO BID)
        - Risks

        RFP:
        {content[:2000]}

        Score: {score}
        Win Probability: {win_probability}%
        """

        response = model.generate_content(prompt)
        return response.text

    except Exception as e:
        return f"AI Error: {str(e)}"


# =========================
# MAIN FUNCTION
# =========================
def analyze_rfp(content):

    score = calculate_score(content)

    # Convert score → probability
    win_probability = int((score / 25) * 100)

    recommendation = "BID" if win_probability >= 65 else "NO BID"
    partner_required = "NO" if win_probability >= 70 else "YES"

    explanation = generate_ai_summary(content, score, win_probability)

    return {
        "scores": {"total": score},
        "win_probability": f"{win_probability}%",
        "recommendation": recommendation,
        "partner_required": partner_required,
        "explanation": explanation
    }


# backward compatibility
def process_rfp(content):
    return analyze_rfp(content)