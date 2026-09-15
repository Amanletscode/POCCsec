from __future__ import annotations

from dataclasses import dataclass

PROFICIENCY = {
    "Awareness": 1,
    "Working": 2,
    "Proficient": 3,
    "Expert": 4,
}
PROFICIENCY_LABELS = list(PROFICIENCY.keys())

# Governed CSEC hierarchy. Lower index = lower seniority.
GRADE_LEVELS = [
    "Analyst",
    "Associate Consultant",
    "Consultant",
    "Senior Consultant",
    "Engagement Manager",
    "Principal",
    "Senior Principal",
]

LANGUAGES = [
    "English", "Hindi", "French", "Spanish", "German", "Mandarin", "Japanese",
    "Portuguese", "Italian", "Arabic", "Korean", "Dutch", "Russian",
]

LOCATIONS = [
    "India", "UK", "France", "Germany", "Spain", "USA", "Canada",
    "Singapore", "Japan", "Australia", "Philippines",
]

TIME_ZONES = [
    "Asia/Kolkata", "Europe/London", "Europe/Paris", "Europe/Berlin",
    "America/New_York", "America/Chicago", "America/Los_Angeles",
    "America/Toronto", "Asia/Singapore", "Asia/Manila", "Asia/Tokyo", "Australia/Sydney",
]

LOCATION_TO_TIMEZONE = {
    "India": "Asia/Kolkata",
    "UK": "Europe/London",
    "France": "Europe/Paris",
    "Germany": "Europe/Berlin",
    "Spain": "Europe/Paris",
    "USA": "America/New_York",
    "Canada": "America/Toronto",
    "Singapore": "Asia/Singapore",
    "Japan": "Asia/Tokyo",
    "Australia": "Australia/Sydney",
    "Philippines": "Asia/Manila",
}

DOMAINS = [
    "Healthcare", "Life Sciences", "Commercial Analytics", "Patient Services",
    "Market Analytics", "Real World Evidence", "Clinical Analytics",
    "Pharmacovigilance", "Manufacturing Analytics", "Insurance", "Technology",
    "Public Sector", "Financial Services", "Pricing & Promotion",
]

SKILL_CATALOG = [
    "SQL", "Python", "R", "SAS", "Excel", "Power BI", "Tableau", "Alteryx",
    "Databricks", "Snowflake", "Azure", "AWS", "GCP", "Spark", "dbt",
    "Machine Learning", "Deep Learning", "NLP", "GenAI", "Agentic AI", "MLOps",
    "Prompt Engineering", "LLM Evaluation", "RAG", "AI Governance", "Forecasting",
    "Predictive Modeling", "Clustering", "Causal Inference", "A/B Testing",
    "Data Visualization", "Data Engineering", "ETL", "Statistical Modeling",
    "Healthcare Data", "Claims Data", "EHR Data", "Clinical Trial Data",
    "Real World Evidence", "Patient Journey Analytics", "Commercial Analytics",
    "Market Access", "HEOR", "Pharmacovigilance", "Omnichannel Analytics",
    "Customer Analytics", "Supply Chain Analytics", "Financial Analytics", "Project Management",
    "Price Elasticity", "Market Mix Modeling", "Pricing Strategy", "Segmentation", "Promo Optimization",
]

SKILL_ALIASES = {
    "structured query language": "SQL",
    "powerbi": "Power BI",
    "power bi": "Power BI",
    "gen ai": "GenAI",
    "generative ai": "GenAI",
    "generative artificial intelligence": "GenAI",
    "agentic artificial intelligence": "Agentic AI",
    "agent ai": "Agentic AI",
    "large language models": "GenAI",
    "llms": "GenAI",
    "real-world evidence": "Real World Evidence",
    "rwe": "Real World Evidence",
    "healthcare analytics": "Healthcare Data",
    "clinical data": "Clinical Trial Data",
    "market mix modelling": "Market Mix Modeling",
    "mme": "Market Mix Modeling",
    "price elasticity modelling": "Price Elasticity",
    "price elasticity modeling": "Price Elasticity",
}

SEARCH_ALIASES = {
    "mmx": {"tags": {"MMX", "Market Mix Modeling"}, "skills": {"Market Mix Modeling"}},
    "pricing": {"tags": {"Pricing", "Pricing Strategy", "Price Elasticity"}, "skills": {"Price Elasticity", "Pricing Strategy"}},
    "europe": {"locations": {"France", "Germany", "Spain", "UK"}},
    "india": {"locations": {"India"}},
    "asia": {"locations": {"India", "Singapore", "Japan", "Australia", "Philippines"}},
}

DEFAULT_WEIGHTS = {
    "mandatory_skills": 0.35,
    "preferred_skills": 0.10,
    "proficiency": 0.10,
    "relevant_evidence": 0.15,
    "capacity": 0.15,
    "delivery_fit": 0.08,
    "development_alignment": 0.04,
    "data_confidence": 0.03,
}

RULE_VERSION = "RM-RULES-3.0"
TAXONOMY_VERSION = "SKILL-CATALOG-2.0"
DATA_VERSION = "SYNTHETIC-2026-09"

@dataclass(frozen=True)
class CapacityPolicy:
    require_full_allocation: bool = True
    tentative_is_reserved: bool = False
    allow_small_capacity_shortfall_pct: float = 0.0

CAPACITY_POLICY = CapacityPolicy()
