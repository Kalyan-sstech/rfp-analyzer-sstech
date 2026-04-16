import os
import google.generativeai as genai

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

def process_rfp(text):

    score = 0
    keywords = ["cloud","ai","data","security","migration","azure"]

    for k in keywords:
        if k in text.lower():
            score += 4

    score = min(score, 25)

    if score >= 20:
        win = "80%"
        rec = "BID"
    elif score >= 15:
        win = "60%"
        rec = "REVIEW"
    else:
        win = "40%"
        rec = "NO BID"

    partner = "YES" if "partner" in text.lower() else "NO"

    prompt = f"Give a short enterprise recommendation for this RFP:\n{text[:2000]}"

    try:
        model = genai.GenerativeModel("gemini-1.0-pro")
        response = model.generate_content(prompt)
        explanation = response.text
    except:
        explanation = "AI engine unavailable. Showing rule-based recommendation."

    return {
        "scores": {"total": score},
        "win_probability": win,
        "recommendation": rec,
        "partner_required": partner,
        "explanation": explanation
    }