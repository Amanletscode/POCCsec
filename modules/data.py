from __future__ import annotations

from pathlib import Path
import pandas as pd

from .validation import validate_capacity, validate_evidence, validate_resources


def read_table(file_or_path, **kwargs) -> pd.DataFrame:
    if file_or_path is None:
        raise FileNotFoundError("No file supplied")
    name = str(getattr(file_or_path, "name", file_or_path)).lower()
    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(file_or_path, **kwargs)
    return pd.read_csv(file_or_path, **kwargs)


def _sheet(book: dict, *names):
    lowered = {str(k).lower().strip(): v for k, v in book.items()}
    for name in names:
        if name.lower() in lowered:
            return lowered[name.lower()]
    return None


def load_workbook(file_obj):
    book = pd.read_excel(file_obj, sheet_name=None)
    resources = _sheet(book, "Resources", "Resource", "Employees", "Employee")
    capacity = _sheet(book, "Capacity", "Weekly Capacity", "WeeklyCapacity")
    evidence = _sheet(book, "DeliveryEvidence", "Evidence", "Project History", "ProjectHistory")
    return resources, capacity, evidence


def canonicalize_resources(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    aliases = {
        "employee_id": "resource_id", "emp_id": "resource_id", "name": "resource_name",
        "employee_name": "resource_name", "timezone": "time_zone", "time zone": "time_zone",
        "skills_proficiency": "skills", "skill_proficiency": "skills",
        "therapeutic_areas": "domains", "therapeutic_area": "domains",
        "development_interest": "development_interests", "manager": "manager_name",
        "email": "contact_email", "work_email": "contact_email",
    }
    for old, new in aliases.items():
        if old in out.columns and new not in out.columns:
            out[new] = out[old]
    defaults = {
        "resource_id": "", "resource_name": "", "team": "Unassigned", "grade": "Analyst",
        "location": "Unknown", "time_zone": "Unknown", "languages": "English",
        "skills": "", "domains": "", "development_interests": "", "years_experience": 0,
        "delivery_rating": 0, "profile_confidence": 0.5, "profile_updated": pd.Timestamp.today().date(),
        "manager_name": "Not provided", "manager_email": "", "contact_email": "",
        "geography_expertise": "", "country_expertise": "", "project_expertise": "",
        "capability_tags": "", "expertise_summary": "",
    }
    for col, default in defaults.items():
        if col not in out.columns:
            out[col] = default
    out["resource_id"] = out["resource_id"].astype(str).str.strip()
    out["resource_name"] = out["resource_name"].fillna("").astype(str).str.strip()
    out["profile_updated"] = pd.to_datetime(out["profile_updated"], errors="coerce")
    out["time_zone"] = out["time_zone"].fillna("").astype(str).str.strip()
    return out


def canonicalize_capacity(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is None:
        return pd.DataFrame(columns=["resource_id", "week_start", "working_capacity_pct", "confirmed_allocation_pct", "tentative_allocation_pct", "leave_pct"])
    out = df.copy()
    if "resource_id" not in out.columns:
        out["resource_id"] = ""
    if "week_start" not in out.columns:
        out["week_start"] = pd.NaT
    for col in ["working_capacity_pct", "confirmed_allocation_pct", "tentative_allocation_pct", "leave_pct"]:
        if col not in out.columns:
            out[col] = 0.0
        out[col] = pd.to_numeric(out[col], errors="coerce")
    out["resource_id"] = out["resource_id"].fillna("").astype(str).str.strip()
    out["week_start"] = pd.to_datetime(out["week_start"], errors="coerce").dt.normalize()
    return out


def canonicalize_evidence(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is None:
        return pd.DataFrame(columns=["resource_id", "project_name", "project_type", "domain", "role", "skills_used", "duration_months", "project_end", "outcome_score"])
    out = df.copy()
    defaults = {
        "resource_id": "", "project_name": "", "project_type": "", "domain": "", "role": "",
        "skills_used": "", "duration_months": 0, "project_end": pd.NaT, "outcome_score": 0,
    }
    for col, default in defaults.items():
        if col not in out.columns:
            out[col] = default
    out["resource_id"] = out["resource_id"].fillna("").astype(str).str.strip()
    out["project_end"] = pd.to_datetime(out["project_end"], errors="coerce")
    out["duration_months"] = pd.to_numeric(out["duration_months"], errors="coerce").fillna(0)
    out["outcome_score"] = pd.to_numeric(out["outcome_score"], errors="coerce").fillna(0)
    return out


def load_demo_data(data_dir: Path):
    resources = canonicalize_resources(pd.read_csv(data_dir / "resources.csv"))
    capacity = canonicalize_capacity(pd.read_csv(data_dir / "capacity.csv"))
    evidence = canonicalize_evidence(pd.read_csv(data_dir / "delivery_evidence.csv"))
    return resources, capacity, evidence


def dataset_health(resources, capacity, evidence) -> dict:
    rr = validate_resources(resources)
    cr = validate_capacity(capacity, resources)
    er = validate_evidence(evidence, resources)
    return {
        "resources_ok": rr.ok, "resources_errors": rr.errors, "resources_warnings": rr.warnings,
        "capacity_ok": cr.ok, "capacity_errors": cr.errors, "capacity_warnings": cr.warnings,
        "evidence_ok": er.ok, "evidence_errors": er.errors, "evidence_warnings": er.warnings,
        "resource_count": len(resources), "capacity_rows": len(capacity), "evidence_rows": len(evidence),
    }
