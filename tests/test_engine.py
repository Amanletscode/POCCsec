from datetime import date
import pandas as pd

from modules.config import DEFAULT_WEIGHTS, GRADE_LEVELS
from modules.data import load_demo_data, canonicalize_resources, canonicalize_capacity, canonicalize_evidence
from modules.discovery import discovery_search, interpret_query
from modules.engine import build_near_matches, run_matching, candidate_capacity
from modules.sample_data import generate_demo_data
from modules.validation import parse_skill_string, validate_request, validate_resources, validate_capacity
DEMO_DATA = generate_demo_data()


def default_request():
    return {
        "request_id": "T1", "role_title": "Healthcare Data Analyst", "start_date": date(2026, 9, 14), "end_date": date(2026, 11, 30),
        "allocation_pct": 50, "allowed_locations": ["India"], "time_zones": ["Asia/Kolkata"], "languages": ["English"],
        "domains": ["Healthcare"], "mandatory_skills": {"SQL": 3, "Python": 2, "Healthcare Data": 2},
        "preferred_skills": {"Power BI": 2, "Claims Data": 2}, "grade_min": "Analyst", "grade_max": "Consultant",
        "capacity_strict": True, "domain_strict": False,
    }


def test_default_has_aarav_and_is_top():
    r, c, e = DEMO_DATA
    mr = run_matching(r, c, e, default_request(), DEFAULT_WEIGHTS)
    elig = mr.table[mr.table.status.eq("Eligible")]
    assert not elig.empty
    aarav = elig[elig.resource_name.eq("Aarav Sharma")].iloc[0]
    assert int(aarav["rank"]) == 1
    assert aarav.total_score > 70
    assert 0 <= aarav.fit_percentile <= 100


def test_french_is_graceful_zero_match_or_valid_match():
    r, c, e = DEMO_DATA
    q = default_request(); q["languages"] = ["French"]; q["allowed_locations"] = ["India"]
    mr = run_matching(r, c, e, q, DEFAULT_WEIGHTS)
    assert isinstance(mr.table, pd.DataFrame)
    assert "status" in mr.table.columns
    if mr.diagnostics["eligible"] == 0:
        assert mr.diagnostics["zero_match"] is True


def test_location_is_hard_gate():
    r, c, e = DEMO_DATA
    q = default_request()
    mr = run_matching(r, c, e, q, DEFAULT_WEIGHTS)
    elig = mr.table[mr.table.status.eq("Eligible")]
    assert set(elig.location) == {"India"}


def test_timezone_is_hard_gate():
    r, c, e = DEMO_DATA
    q = default_request(); q["time_zones"] = ["Europe/Paris"]
    mr = run_matching(r, c, e, q, DEFAULT_WEIGHTS)
    elig = mr.table[mr.table.status.eq("Eligible")]
    assert set(elig.time_zone) <= {"Europe/Paris"}


def test_inverted_grade_range_is_rejected_and_catalog_is_correct():
    assert GRADE_LEVELS == ["Analyst", "Associate Consultant", "Consultant", "Senior Consultant", "Engagement Manager", "Principal", "Senior Principal"]
    q = default_request(); q["grade_min"] = "Principal"; q["grade_max"] = "Consultant"
    assert not validate_request(q).ok


def test_missing_skill_is_exclusion_not_error():
    r, c, e = DEMO_DATA
    q = default_request(); q["mandatory_skills"] = {"Agentic AI": 4}
    mr = run_matching(r, c, e, q, DEFAULT_WEIGHTS)
    assert len(mr.table) == len(r)
    assert "gates" in mr.table.columns
    row = mr.table.iloc[0]
    assert not (
        "Mandatory skill missing" in row.exclusion_reasons
        and "Mandatory proficiency below required level" in row.exclusion_reasons
    )


def test_impossible_combination_is_zero_match_without_fake_candidate():
    r, c, e = DEMO_DATA
    q = default_request(); q["mandatory_skills"] = {"SQL": 4, "Python": 4, "Agentic AI": 4}; q["languages"] = ["French"]
    mr = run_matching(r, c, e, q, DEFAULT_WEIGHTS)
    assert mr.diagnostics["eligible"] >= 0
    assert len(mr.table) == len(r)
    assert mr.diagnostics["zero_match"] is True


def test_strict_domain_gate():
    r, c, e = DEMO_DATA
    q = default_request(); q["domain_strict"] = True
    mr = run_matching(r, c, e, q, DEFAULT_WEIGHTS)
    elig = mr.table[mr.table.status.eq("Eligible")]
    resmap = r.set_index("resource_id")
    assert all("Healthcare" in str(resmap.loc[row.resource_id, "domains"]).split("|") for _, row in elig.iterrows())


def test_missing_capacity_data_fails_hard():
    r, c, e = DEMO_DATA
    c = c[c.resource_id.ne("EMP-1001")].copy()
    q = default_request()
    mr = run_matching(r, c, e, q, DEFAULT_WEIGHTS)
    aarav = mr.table[mr.table.resource_id.eq("EMP-1001")].iloc[0]
    assert aarav.status == "Excluded"
    assert "Missing weekly capacity data" in aarav.exclusion_reasons


def test_candidate_capacity_marks_missing_rows():
    r, c, e = DEMO_DATA
    c = c[c.resource_id.ne("EMP-1001")].copy()
    cap = candidate_capacity(c, "EMP-1001", date(2026, 9, 14), date(2026, 9, 30), 50)
    assert cap.data_missing.all()
    assert (cap.status == "Missing capacity data").all()


def test_skill_parser_is_tolerant_and_aliases():
    parsed = parse_skill_string(" SQL:3 | PowerBI:4 | bad | Python:nope | Gen AI:2 ")
    assert parsed["SQL"] == 3
    assert parsed["Power BI"] == 4
    assert parsed["GenAI"] == 2
    assert "Python" not in parsed


def test_discovery_mmx_europe_returns_people_and_contact():
    r, c, e = DEMO_DATA
    intent = interpret_query("I have an MMX project, who should I contact?")
    assert "Market Mix Modeling" in intent.skills
    assert "EUROPE" in {x.upper() for x in intent.terms} or "MMX" in {x.upper() for x in intent.terms}
    _, found = discovery_search(r, e, "I have an MMX project, who should I contact?", 5)
    assert not found.empty
    assert "contact_email" in found.columns
    assert "manager_email" in found.columns
    assert found.iloc[0].resource_name in {"Camille Dubois", "Lena Fischer", "Sofia Martinez"}


def test_discovery_price_elasticity_europe_prioritizes_european_experts():
    r, c, e = DEMO_DATA
    _, found = discovery_search(r, e, "Who has expertise in price elasticity for Europe?", 10)
    assert not found.empty
    assert found.iloc[0].resource_name in {"Camille Dubois", "Lena Fischer", "Sofia Martinez"}


def test_canonicalizers_accept_minimal_optional_data():
    raw = pd.DataFrame({"resource_id": ["X"], "resource_name": ["X Person"], "team": ["T"], "grade": ["Analyst"], "location": ["India"], "time_zone": ["Asia/Kolkata"], "languages": ["English"], "skills": ["SQL:3"], "domains": ["Healthcare"], "development_interests": [""] , "years_experience":[1], "delivery_rating":[4], "profile_confidence":[0.9], "profile_updated":["2026-09-01"]})
    res = canonicalize_resources(raw)
    cap = canonicalize_capacity(None)
    ev = canonicalize_evidence(None)
    assert "contact_email" in res.columns
    assert cap.empty and ev.empty
    assert validate_resources(res).ok
    assert validate_capacity(pd.DataFrame({"resource_id": ["X"], "week_start": ["2026-09-14"], "working_capacity_pct": [100], "confirmed_allocation_pct": [20], "tentative_allocation_pct": [0], "leave_pct": [0]}), res).ok


def test_dataset_roundtrip_loads():
    r, c, e = load_demo_data(__import__('pathlib').Path('data'))
    assert len(r) == 320
    assert len(c) == 9600
    assert len(e) >= 640


def test_scores_are_bounded_and_excluded_candidates_keep_audit_score():
    r, c, e = DEMO_DATA
    mr = run_matching(r, c, e, default_request(), DEFAULT_WEIGHTS)
    assert mr.table.total_score.between(0, 100).all()
    assert mr.table.potential_score.between(0, 100).all()
    excluded = mr.table[mr.table.status.eq("Excluded")]
    assert (excluded.total_score == 0).all()
    assert (excluded.potential_score > 0).any()


def test_near_matches_never_masquerade_as_eligible_recommendations():
    r, c, e = DEMO_DATA
    q = default_request()
    q["languages"] = ["French"]
    mr = run_matching(r, c, e, q, DEFAULT_WEIGHTS)
    near = build_near_matches(mr.table, limit=10)
    assert all(1 <= row["failed_gate_count"] <= 2 for row in near)
    assert all(row["exclusion_reasons"] for row in near)


def test_capacity_validation_rejects_confirmed_overbooking():
    r, _, _ = DEMO_DATA
    bad = pd.DataFrame({
        "resource_id": [r.iloc[0].resource_id], "week_start": ["2026-09-14"],
        "working_capacity_pct": [80], "confirmed_allocation_pct": [75],
        "tentative_allocation_pct": [0], "leave_pct": [10],
    })
    report = validate_capacity(bad, r)
    assert not report.ok
    assert any("cannot exceed working capacity" in error for error in report.errors)


def test_request_longer_than_two_years_is_rejected():
    q = default_request()
    q["end_date"] = date(2029, 1, 1)
    assert not validate_request(q).ok
