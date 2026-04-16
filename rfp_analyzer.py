import random
import os
import google.generativeai as genai

def process_rfp(content):
    # ---------- SCORING ----------
    score = random.randint(15, 25)
    win_probability = f"{random.randint(55, 85)}%"
    recommendation = "BID" if score > 18 else "NO BID"
    partner_required = "YES" if "partner" in content.lower() else "NO"

    # ---------- NAICS ----------
    naics = [
        {"code": "541511", "title": "Custom Software Development"},
        {"code": "541512", "title": "Systems Design"},
        {"code": "541513", "title": "IT Support"},
        {"code": "541519", "title": "Cybersecurity"},
        {"code": "541715", "title": "AI / ML Research"}
    ]

    # ---------- MATCHED PROJECTS ----------
    matched_projects = []
    if "cloud" in content.lower():
        matched_projects.append({
            "project": "Cloud Migration Program",
            "reason": "Matches cloud + architecture requirements"
        })

    if "security" in content.lower():
        matched_projects.append({
            "project": "Cybersecurity Upgrade",
            "reason": "Matches security requirements"
        })

    # ---------- AI EXPLANATION ----------
    explanation = generate_explanation(content, score, win_probability)

    return {
        "scores": {"total": score},
        "win_probability": win_probability,
        "recommendation": recommendation,
        "partner_required": partner_required,
        "naics": naics,
        "matched_projects": matched_projects,
        "explanation": explanation
    }

def generate_explanation(content, score, win_probability):
    try:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            return "AI explanation not available (API Key missing)"

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")

        prompt = f"""
        Analyze this RFP and explain why the score is {score} and win probability is {win_probability}.
        Focus on strengths and risks.
        
        RFP Content:
        {content[:2000]} 
        """
        response = model.generate_content(prompt)
        return response.text

    except Exception as e:
        return f"AI explanation unavailable: {str(e)}"