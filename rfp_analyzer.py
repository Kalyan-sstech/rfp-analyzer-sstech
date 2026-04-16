def process_rfp(text):

    text = text.lower()

    # -------------------------------
    # 1. SCORING ENGINE
    # -------------------------------
    score = 0

    if "cloud" in text or "azure" in text:
        score += 10

    if "cybersecurity" in text or "security" in text:
        score += 10

    if "ai" in text or "machine learning" in text:
        score += 8

    if "data" in text or "analytics" in text:
        score += 8

    if "federal" in text or "government" in text:
        score += 7

    # Risks
    if "clearance" in text:
        score -= 6

    if "onsite" in text:
        score -= 4

    if "urgent" in text or "short timeline" in text:
        score -= 3

    score = max(0, min(score, 30))

    # -------------------------------
    # 2. DECISION
    # -------------------------------
    if score >= 22:
        decision = "BID"
        win_probability = "80%"
    elif score >= 15:
        decision = "REVIEW"
        win_probability = "60%"
    else:
        decision = "NO BID"
        win_probability = "40%"

    # -------------------------------
    # 3. CAPABILITIES
    # -------------------------------
    capabilities = []

    if "cybersecurity" in text:
        capabilities.append("Cybersecurity (NIST, FedRAMP)")

    if "cloud" in text:
        capabilities.append("Cloud & Azure expertise")

    if "ai" in text:
        capabilities.append("AI/ML capability")

    if "data" in text:
        capabilities.append("Data engineering & analytics")

    # -------------------------------
    # 4. PAST PERFORMANCE
    # -------------------------------
    past = []

    if "data" in text:
        past.append("Azure Data Warehouse project (Banking)")

    if "automation" in text:
        past.append("RPA automation (50% efficiency gain)")

    if "cybersecurity" in text:
        past.append("Government security operations experience")

    # -------------------------------
    # 5. RISKS
    # -------------------------------
    risks = []

    if "clearance" in text:
        risks.append("Security clearance required")

    if "onsite" in text:
        risks.append("Onsite requirement")

    if not capabilities:
        risks.append("No strong capability match")

    # -------------------------------
    # 6. SUMMARY
    # -------------------------------
    summary = f"""
Score: {score}/30 → {decision}

Strengths:
- {', '.join(capabilities) if capabilities else 'Limited'}

Past Performance:
- {', '.join(past) if past else 'Not available'}

Risks:
- {', '.join(risks) if risks else 'Low'}

Recommendation:
Proceed with {decision}
"""

    return {
        "scores": {"total": score},
        "win_probability": win_probability,
        "recommendation": decision,
        "capability_match": capabilities,
        "past_performance": past,
        "risks": risks,
        "explanation": summary
    }