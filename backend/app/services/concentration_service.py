# @TASK HHI-T1 - Supply chain concentration index (HHI) calculation
# @SPEC docs/planning/02-trd.md#analytics-api

"""Supply chain concentration index calculation (HHI)."""

from sqlmodel import Session, select, func

from app.models.company import Company
from app.models.company_relation import CompanyRelation


def calculate_tier_hhi(session: Session) -> list[dict]:
    """Calculate HHI (Herfindahl-Hirschman Index) per tier.

    HHI = sum of squared market shares.
    - HHI < 1500: competitive
    - 1500 <= HHI < 2500: moderately concentrated
    - HHI >= 2500: highly concentrated

    We approximate "market share" by each company's share of total
    outgoing relations (supply connections) in their tier.
    """
    tiers = ["raw_material", "equipment", "fab", "packaging", "module"]
    tier_labels = {
        "raw_material": "원자재",
        "equipment": "장비사",
        "fab": "팹",
        "packaging": "패키징",
        "module": "모듈",
    }

    results = []
    for tier in tiers:
        # Get companies in this tier
        companies = session.exec(
            select(Company).where(Company.tier == tier)
        ).all()

        if not companies:
            results.append({
                "tier": tier,
                "tier_label": tier_labels.get(tier, tier),
                "hhi": 0,
                "level": "unknown",
                "company_count": 0,
                "shares": [],
            })
            continue

        # Count relations per company (both as source and target)
        total_relations = 0
        company_relations = {}

        for company in companies:
            rel_count = session.exec(
                select(func.count()).where(
                    (CompanyRelation.source_id == company.id)
                    | (CompanyRelation.target_id == company.id)
                )
            ).one()
            company_relations[company.id] = rel_count
            total_relations += rel_count

        # Calculate HHI
        shares = []
        hhi = 0.0
        for company in companies:
            if total_relations > 0:
                share = (company_relations[company.id] / total_relations) * 100
            else:
                share = 100 / len(companies)  # equal share if no relations

            shares.append({
                "company_id": company.id,
                "company_name": company.name,
                "share_pct": round(share, 1),
            })
            hhi += share ** 2

        hhi = round(hhi)

        if hhi >= 2500:
            level = "highly_concentrated"
        elif hhi >= 1500:
            level = "moderately_concentrated"
        else:
            level = "competitive"

        results.append({
            "tier": tier,
            "tier_label": tier_labels.get(tier, tier),
            "hhi": hhi,
            "level": level,
            "company_count": len(companies),
            "shares": sorted(shares, key=lambda x: x["share_pct"], reverse=True),
        })

    return results
