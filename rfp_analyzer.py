import random

def analyze_rfp(content):
    """
    Main RFP analysis logic
    """

    # 🔹 Simulated scoring logic (replace with AI later)
    score = random.randint(15, 25)
    win_probability = random.randint(60, 85)

    recommendation = "BID" if win_probability > 65 else "NO BID"
    partner_required = "NO"

    explanation = generate_explanation(content, score, win_probability)

    return {
        "scores": {
            "total": score
        },
        "win_probability": f"{win_probability}%",
        "recommendation": recommendation,
        "partner_required": partner_required,
        "explanation": explanation
    }


def generate_explanation(content, score, win_probability):
    """
    AI explanation (can replace with Gemini later)
    """

    if win_probability > 75:
        return "Strong alignment with your organization's capabilities in cloud, AI, and cybersecurity."
    elif win_probability > 65:
        return "Moderate alignment. Some technical and delivery risks should be reviewed."
    else:
        return "Low alignment. Consider evaluating resource fit before bidding."


# ✅ CRITICAL (fixes your error)
def process_rfp(content):
    return analyze_rfp(content)