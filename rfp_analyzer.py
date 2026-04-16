def process_rfp(text):

    text = text.lower()

    # -------------------------------
    # 1. SCORING ENGINE (Weighted)
    # -------------------------------
    score = 0

    # Strength areas
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

    # Risk deductions
    if "clearance" in text:
        score -= 6

    if "onsite" in text:
        score -= 4

    if "short timeline" in text or "urgent" in text:
        score -= 3

    score = max(0, min(score, 30))

    # -------------------------------
    # 2. DECISION ENGINE
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
    # 3. CAPABILITY MATCHING
    # -------------------------------
    capabilities_match = []

    if "cybersecurity" in text:
        capabilities_match.append(
            "Strong cybersecurity capability aligned with NIST, FedRAMP compliance"
        )

    if "cloud" in text or "azure" in text:
        capabilities_match.append(
            "Cloud & Azure expertise including migration and operations"
        )

    if "ai" in text or "automation" in text:
        capabilities_match.append(
            "AI/ML and RPA automation capabilities available"
        )

    if "data" in text:
        capabilities_match.append(
            "Data engineering, BI, and analytics experience"
        )

    if "erp" in text or "crm" in text:
        capabilities_match.append(
            "ERP/CRM integration (SAP, Salesforce, Dynamics)"
        )

    # -------------------------------
    # 4. PAST PERFORMANCE MAPPING
    # -------------------------------
    past_performance = []

    if "data" in text:
        past_performance.append(
            "Azure data warehouse project for banking client"
        )

    if "automation" in text or "rpa" in text:
        past_performance.append(
            "RPA automation delivering 50% efficiency improvement"
        )

    if "cybersecurity" in text:
        past_performance.append(
            "Security operations for government and compliance projects"
        )

    # -------------------------------
    # 5. RISK ENGINE
    # -------------------------------
    risks = []

    if "clearance" in text:
        risks.append("Security clearance requirement")

    if "onsite" in text:
        risks.append("Onsite delivery dependency")

    if "experience of 10 years" in text:
        risks.append("High experience requirement")

    if not capabilities_match:
        risks.append("Low capability alignment")

    # -------------------------------
    # 6. EXECUTIVE SUMMARY (Manual)
    # -------------------------------
    summary = f"""
This opportunity has a score of {score}/30 indicating a {decision} decision.

Strength Areas:
- {'; '.join(capabilities_match) if capabilities_match else 'Limited alignment'}

Relevant Past Performance:
- {'; '.join(past_performance) if past_performance else 'No strong references'}

Key Risks:
- {'; '.join(risks) if risks else 'No major risks identified'}

Recommendation:
Proceed with {decision} strategy with focus on highlighted strengths.
"""

    # -------------------------------
    # FINAL OUTPUT
    # -------------------------------
    return {
        "scores": {"total": score},
        "win_probability": win_probability,
        "recommendation": decision,
        "capability_match": capabilities_match,
        "past_performance": past_performance,
        "risks": risks,
        "explanation": summary
    }