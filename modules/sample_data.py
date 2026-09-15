from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import hashlib
import random
import pandas as pd

from .config import GRADE_LEVELS, LANGUAGES, LOCATIONS, LOCATION_TO_TIMEZONE, DOMAINS, SKILL_CATALOG

RNG = random.Random(20260915)

FIRST = ["Aarav", "Priya", "Rohan", "Ishita", "Kabir", "Ananya", "Arjun", "Neha", "Vikram", "Sana", "Aditya", "Meera", "Rahul", "Karan", "Tanya", "Dev", "Aisha", "Nikhil", "Sara", "Varun", "Camille", "Lena", "Sofia", "Noah", "Maya", "Ethan", "Olivia", "Haruto", "Daniel", "Claire"]
LAST = ["Sharma", "Nair", "Mehta", "Kapoor", "Singh", "Patel", "Verma", "Rao", "Iyer", "Bose", "Gupta", "Malhotra", "Dubois", "Fischer", "Martinez", "Wilson", "Thompson", "Sato", "Chen", "Brown", "Khan", "Das"]
TEAM_BY_LOC = {
    "India": ["CSEC Analytics India", "Patient Analytics India", "Data Engineering India", "AI Solutions India", "Commercial Analytics India", "RWE India"],
    "UK": ["CSEC Europe", "Commercial Analytics Europe", "RWE Europe"], "France": ["CSEC Europe", "Patient Analytics Europe", "Pricing Europe"],
    "Germany": ["CSEC Europe", "AI Solutions Europe", "RWE Europe"], "Spain": ["CSEC Europe", "Commercial Analytics Europe", "Pricing Europe"],
    "USA": ["CSEC Americas", "AI Solutions Americas", "Healthcare Analytics Americas", "Pricing Americas"], "Canada": ["CSEC Americas", "Data Science Americas"],
    "Singapore": ["CSEC APAC", "Data Engineering APAC"], "Japan": ["CSEC APAC", "AI Solutions APAC"],
    "Australia": ["CSEC APAC", "Healthcare Analytics APAC"], "Philippines": ["CSEC APAC", "Analytics Operations APAC"],
}
DOMAIN_SKILLS = {
    "Healthcare": ["SQL", "Python", "Healthcare Data", "EHR Data", "Claims Data", "Power BI", "R"],
    "Life Sciences": ["SAS", "SQL", "Python", "Clinical Trial Data", "Pharmacovigilance", "R", "Data Visualization"],
    "Commercial Analytics": ["SQL", "Python", "Commercial Analytics", "Power BI", "Tableau", "Forecasting", "Segmentation"],
    "Patient Services": ["SQL", "Python", "Patient Journey Analytics", "Power BI", "Data Visualization", "Customer Analytics"],
    "Market Analytics": ["SQL", "Python", "Commercial Analytics", "Tableau", "Power BI", "Clustering", "Segmentation"],
    "Real World Evidence": ["SQL", "Python", "Real World Evidence", "Claims Data", "EHR Data", "Statistical Modeling", "Causal Inference"],
    "Clinical Analytics": ["SQL", "Python", "Clinical Trial Data", "SAS", "R", "Statistical Modeling", "Data Visualization"],
    "Pharmacovigilance": ["SQL", "SAS", "Pharmacovigilance", "Python", "Statistical Modeling", "Clinical Trial Data"],
    "Manufacturing Analytics": ["SQL", "Python", "Forecasting", "Supply Chain Analytics", "Power BI", "Data Engineering"],
    "Insurance": ["SQL", "Python", "Claims Data", "Forecasting", "Excel", "Predictive Modeling"],
    "Technology": ["Python", "SQL", "GenAI", "Agentic AI", "Machine Learning", "Data Engineering", "AWS", "Azure", "GCP"],
    "Public Sector": ["SQL", "Python", "Power BI", "Data Visualization", "Excel"],
    "Financial Services": ["SQL", "Python", "Financial Analytics", "Forecasting", "Power BI", "Predictive Modeling"],
    "Pricing & Promotion": ["SQL", "Python", "Price Elasticity", "Market Mix Modeling", "Pricing Strategy", "Promo Optimization", "Segmentation"],
}
GEOGRAPHY_BY_LOC = {
    "India": ["India", "South Asia"], "UK": ["UK", "Europe", "Western Europe"], "France": ["France", "Europe", "Western Europe"],
    "Germany": ["Germany", "Europe", "DACH"], "Spain": ["Spain", "Europe", "Southern Europe"], "USA": ["USA", "North America", "United States"],
    "Canada": ["Canada", "North America"], "Singapore": ["Singapore", "Southeast Asia", "APAC"], "Japan": ["Japan", "East Asia", "APAC"],
    "Australia": ["Australia", "ANZ", "APAC"], "Philippines": ["Philippines", "Southeast Asia", "APAC"],
}

PROJECTS_BY_DOMAIN = {
    "Healthcare": ["Patient analytics modernization", "Claims reporting transformation", "EHR insight platform", "Healthcare dashboard rollout"],
    "Commercial Analytics": ["European commercial analytics", "Sales force effectiveness", "Commercial dashboard rollout", "Market opportunity sizing"],
    "Pricing & Promotion": ["MMX European pricing study", "Price elasticity assessment", "Promo optimization program", "Pricing strategy transformation"],
    "Technology": ["GenAI insight accelerator", "Agentic analytics pilot", "Data platform modernization", "LLM evaluation framework"],
    "Life Sciences": ["Clinical analytics platform", "Safety signal analytics", "Trial data modernization"],
    "Real World Evidence": ["RWE study enablement", "Claims evidence accelerator", "Observational research analytics"],
}
ROLE_BY_GRADE = {
    "Analyst": "Data Analyst", "Associate Consultant": "Analytics Consultant", "Consultant": "Consultant",
    "Senior Consultant": "Senior Consultant", "Engagement Manager": "Engagement Manager", "Principal": "Principal", "Senior Principal": "Senior Principal",
}

MANAGERS = [
    ("Anika Kapoor", "anika.kapoor@csec-demo.example"), ("Vivek Rao", "vivek.rao@csec-demo.example"),
    ("Elena Garcia", "elena.garcia@csec-demo.example"), ("James Wilson", "james.wilson@csec-demo.example"),
    ("Mei Tan", "mei.tan@csec-demo.example"), ("Daniel Brooks", "daniel.brooks@csec-demo.example"),
]


def _skill_string(skills: dict[str, int]) -> str:
    return "|".join(f"{k}:{v}" for k, v in sorted(skills.items()))


def _choose_skills(domain: str, level: int) -> dict[str, int]:
    core = DOMAIN_SKILLS.get(domain, ["SQL", "Python", "Data Visualization"])
    extras = [x for x in SKILL_CATALOG if x not in core]
    selected = list(dict.fromkeys(core))[:]
    if len(selected) < 6:
        selected += RNG.sample(extras, min(6 - len(selected), len(extras)))
    selected = RNG.sample(selected, min(len(selected), RNG.randint(7, 12)))
    return {skill: max(1, min(4, level + RNG.choice([-1, 0, 0, 1]))) for skill in selected}


def _email(name: str) -> str:
    slug = ".".join(name.lower().split())
    return f"{slug}@csec-demo.example"


def generate_demo_data(n_resources: int = 320, start: date = date(2026, 8, 31), weeks: int = 30):
    anchors = [
        {
            "resource_id": "EMP-1001", "resource_name": "Aarav Sharma", "location": "India", "grade": "Consultant", "team": "CSEC Analytics India",
            "skills": {"SQL": 4, "Python": 3, "Healthcare Data": 3, "Power BI": 4, "Claims Data": 3, "GenAI": 3, "RAG": 2},
            "languages": {"English", "Hindi"}, "domains": {"Healthcare", "Patient Services", "Real World Evidence"}, "dev": {"GenAI", "Agentic AI"},
            "years": 6.2, "rating": 4.7, "confidence": 0.97, "geo": {"India", "Europe"},
            "country": {"India", "UK", "Germany"}, "project": {"Healthcare Analytics", "RWE", "Claims Analytics"}, "tags": {"Healthcare SME", "Cross-team analytics"},
        },
        {
            "resource_id": "EMP-1002", "resource_name": "Priya Nair", "location": "India", "grade": "Consultant", "team": "Patient Analytics India",
            "skills": {"SQL": 4, "Python": 3, "Healthcare Data": 3, "Power BI": 4, "EHR Data": 3, "Data Visualization": 4},
            "languages": {"English", "Hindi"}, "domains": {"Healthcare", "Patient Services"}, "dev": {"GenAI"},
            "years": 5.5, "rating": 4.5, "confidence": 0.94, "geo": {"India"}, "country": {"India"}, "project": {"Patient Services"}, "tags": {"Patient analytics SME"},
        },
        {
            "resource_id": "EMP-1003", "resource_name": "Rohan Mehta", "location": "India", "grade": "Senior Consultant", "team": "AI Solutions India",
            "skills": {"SQL": 4, "Python": 4, "GenAI": 4, "Agentic AI": 4, "RAG": 4, "Machine Learning": 4, "Healthcare Data": 2},
            "languages": {"English", "Hindi"}, "domains": {"Technology", "Healthcare"}, "dev": {"Agentic AI", "LLM Evaluation"},
            "years": 8.0, "rating": 4.6, "confidence": 0.96, "geo": {"India", "APAC"}, "country": {"India", "Singapore"},
            "project": {"GenAI", "Agentic AI"}, "tags": {"AI SME", "GenAI capability lead"},
        },
        {
            "resource_id": "EMP-1004", "resource_name": "Camille Dubois", "location": "France", "grade": "Consultant", "team": "Pricing Europe",
            "skills": {"SQL": 4, "Python": 4, "Price Elasticity": 4, "Market Mix Modeling": 4, "Pricing Strategy": 4, "Promo Optimization": 3, "Segmentation": 3},
            "languages": {"English", "French"}, "domains": {"Commercial Analytics", "Pricing & Promotion", "Market Analytics"}, "dev": {"GenAI"},
            "years": 6.7, "rating": 4.8, "confidence": 0.98, "geo": {"France", "Germany", "Spain", "Italy", "Europe"},
            "country": {"France", "Germany", "Spain", "Italy", "UK"}, "project": {"MMX", "Price Elasticity", "European Pricing"}, "tags": {"Pricing SME", "MMX SME"},
        },
        {
            "resource_id": "EMP-1005", "resource_name": "Lena Fischer", "location": "Germany", "grade": "Principal", "team": "CSEC Europe",
            "skills": {"SQL": 4, "Python": 4, "Market Mix Modeling": 4, "Price Elasticity": 3, "Pricing Strategy": 4, "Commercial Analytics": 4, "Segmentation": 4},
            "languages": {"English", "German", "French"}, "domains": {"Commercial Analytics", "Pricing & Promotion", "Market Analytics"}, "dev": {"GenAI"},
            "years": 13.2, "rating": 4.9, "confidence": 0.99, "geo": {"Germany", "France", "Spain", "Europe", "DACH"},
            "country": {"Germany", "France", "Spain", "UK", "Italy"}, "project": {"MMX", "European Pricing", "Commercial Strategy"}, "tags": {"Commercial SME", "Pricing Practice Lead"},
        },
        {
            "resource_id": "EMP-1006", "resource_name": "Sofia Martinez", "location": "Spain", "grade": "Engagement Manager", "team": "Commercial Analytics Europe",
            "skills": {"SQL": 4, "Python": 3, "Market Mix Modeling": 4, "Price Elasticity": 4, "Pricing Strategy": 4, "Forecasting": 4, "Commercial Analytics": 4},
            "languages": {"English", "Spanish", "French"}, "domains": {"Commercial Analytics", "Pricing & Promotion"}, "dev": {"Agentic AI"},
            "years": 11.4, "rating": 4.8, "confidence": 0.97, "geo": {"Spain", "France", "UK", "Europe"},
            "country": {"Spain", "France", "UK", "Germany"}, "project": {"MMX", "Price Elasticity", "European Commercial Analytics"}, "tags": {"Commercial Lead", "Pricing SME"},
        },
    ]
    rows = list(anchors)
    idx = 1007
    grade_base = {"Analyst": 1, "Associate Consultant": 2, "Consultant": 2, "Senior Consultant": 3, "Engagement Manager": 3, "Principal": 4, "Senior Principal": 4}
    while len(rows) < n_resources:
        loc = RNG.choice(LOCATIONS)
        grade = RNG.choice(GRADE_LEVELS)
        domain = RNG.choice(DOMAINS)
        skills = _choose_skills(domain, grade_base[grade])
        base_lang = {"India": {"English", "Hindi"}, "France": {"French", "English"}, "Germany": {"German", "English"}, "Spain": {"Spanish", "English"},
                     "USA": {"English"}, "UK": {"English"}, "Canada": {"English", "French"}, "Singapore": {"English"}, "Japan": {"Japanese", "English"},
                     "Australia": {"English"}, "Philippines": {"English"}}[loc]
        languages = set(base_lang)
        if RNG.random() < 0.17:
            languages.add(RNG.choice([x for x in LANGUAGES if x not in languages]))
        domains = {domain}
        if RNG.random() < 0.35:
            domains.add(RNG.choice(DOMAINS))
        dev = set(RNG.sample(SKILL_CATALOG, RNG.randint(1, 3)))
        years = round(max(0.8, {"Analyst": 1.7, "Associate Consultant": 3.0, "Consultant": 5.2, "Senior Consultant": 7.2, "Engagement Manager": 10.0, "Principal": 13.0, "Senior Principal": 17.0}[grade] + RNG.uniform(-1.0, 1.8)), 1)
        geo = set(GEOGRAPHY_BY_LOC[loc])
        country = {loc}
        if loc in {"France", "Germany", "Spain", "UK"} and RNG.random() < 0.35:
            country.add(RNG.choice(["France", "Germany", "Spain", "UK", "Italy", "Netherlands"]))
            geo.add("Europe")
        project_pool = PROJECTS_BY_DOMAIN.get(domain, ["Analytics Project"]); project = set(RNG.sample(project_pool, RNG.randint(1, min(2, len(project_pool)))))
        tags = {domain + " SME"} if grade_base[grade] >= 3 else {"Emerging " + domain}
        rows.append({
            "resource_id": f"EMP-{idx}", "resource_name": f"{RNG.choice(FIRST)} {RNG.choice(LAST)}", "location": loc, "grade": grade,
            "team": RNG.choice(TEAM_BY_LOC[loc]), "skills": skills, "languages": languages, "domains": domains, "dev": dev,
            "years": years, "rating": round(RNG.uniform(3.4, 4.9), 1), "confidence": round(RNG.uniform(0.72, 0.99), 2),
            "geo": geo, "country": country, "project": project, "tags": tags,
        })
        idx += 1

    resources = []
    for i, r in enumerate(rows):
        manager_name, manager_email = MANAGERS[i % len(MANAGERS)]
        resources.append({
            "resource_id": r["resource_id"], "resource_name": r["resource_name"], "team": r["team"], "grade": r["grade"],
            "role_title": ROLE_BY_GRADE[r["grade"]], "location": r["location"], "time_zone": LOCATION_TO_TIMEZONE[r["location"]],
            "languages": "|".join(sorted(r["languages"])), "skills": _skill_string(r["skills"]), "domains": "|".join(sorted(r["domains"])),
            "development_interests": "|".join(sorted(r["dev"])), "years_experience": r["years"], "delivery_rating": r["rating"],
            "profile_confidence": r["confidence"], "profile_updated": date(2026, 8, 1) + timedelta(days=RNG.randint(0, 40)),
            "contact_email": _email(r["resource_name"]), "manager_name": manager_name, "manager_email": manager_email,
            "geography_expertise": "|".join(sorted(r["geo"])), "country_expertise": "|".join(sorted(r["country"])),
            "project_expertise": "|".join(sorted(r["project"])), "capability_tags": "|".join(sorted(r["tags"])),
            "expertise_summary": f"{r['grade']} in {r['team']} with {r['years']:.1f} years' experience across {', '.join(sorted(r['domains'])[:3])}.",
        })
    resources_df = pd.DataFrame(resources)

    capacity_rows = []
    evidence_rows = []
    projects = [
        "Patient analytics modernization", "Claims reporting transformation", "Commercial dashboard rollout", "RWE study enablement",
        "GenAI insight accelerator", "Clinical analytics platform", "Data quality remediation", "Forecast automation",
        "Omnichannel measurement", "Safety signal analytics", "MMX European pricing study", "Price elasticity assessment",
    ]
    for i, r in resources_df.iterrows():
        base = 58 if r.grade in ["Analyst", "Associate Consultant"] else 53 if r.grade in ["Consultant", "Senior Consultant"] else 46
        pressure = RNG.randint(-18, 24)
        for w in range(weeks):
            wk = start + timedelta(weeks=w)
            # Anchors are intentionally stable enough to demonstrate the full decision workflow.
            if r.resource_id in {"EMP-1001", "EMP-1002"}:
                confirmed = 27 + (w % 4) * 3
                tentative = 0 if w % 5 else 8
                leave = 0
                working = 100
            else:
                confirmed = max(0, min(100, base + pressure + RNG.randint(-10, 18)))
                tentative = max(0, min(30, RNG.randint(0, 25) if RNG.random() < 0.58 else 0))
                leave = RNG.choice([0, 0, 0, 0, 5, 10, 20])
                working = 80 if RNG.random() < 0.08 else 100
            capacity_rows.append({
                "resource_id": r.resource_id, "week_start": wk, "working_capacity_pct": working,
                "confirmed_allocation_pct": confirmed, "tentative_allocation_pct": tentative, "leave_pct": leave,
            })
        # Historical delivery evidence: 2 to 6 records per resource.
        domains = split = [x for x in str(r.domains).split("|") if x]
        skill_names = [x.rsplit(":", 1)[0] for x in str(r.skills).split("|") if x]
        for j in range(RNG.randint(2, 6)):
            domain = RNG.choice(domains) if domains else "Technology"
            project_name = RNG.choice(PROJECTS_BY_DOMAIN.get(domain, projects))
            if r.resource_id in {"EMP-1004", "EMP-1005", "EMP-1006"} and RNG.random() < 0.65:
                project_name = RNG.choice(["MMX European pricing study", "Price elasticity assessment", "European commercial analytics"])
                domain = "Pricing & Promotion"
            used = RNG.sample(skill_names, min(len(skill_names), RNG.randint(2, 5)))
            evidence_rows.append({
                "resource_id": r.resource_id, "project_name": project_name, "project_type": "Analytics / Consulting",
                "domain": domain, "role": r.role_title, "skills_used": "|".join(used), "duration_months": RNG.randint(2, 12),
                "project_end": date(2026, 9, 1) - timedelta(days=RNG.randint(40, 1500)), "outcome_score": round(RNG.uniform(3.6, 4.9), 1),
            })
    return resources_df, pd.DataFrame(capacity_rows), pd.DataFrame(evidence_rows)


def write_demo_data(data_dir: Path):
    data_dir.mkdir(parents=True, exist_ok=True)
    resources, capacity, evidence = generate_demo_data()
    resources.to_csv(data_dir / "resources.csv", index=False)
    capacity.to_csv(data_dir / "capacity.csv", index=False)
    evidence.to_csv(data_dir / "delivery_evidence.csv", index=False)
    return resources, capacity, evidence
