from datetime import date
from pathlib import Path

import pandas as pd

from modules.config import DEFAULT_WEIGHTS, DESIGNATION_TO_GRADE, STANDARD_WEEK_HOURS
from modules.data import (
    canonicalize_capacity,
    canonicalize_resources,
    load_demo_data,
)
from modules.discovery import discovery_search, interpret_query, interpret_with_runtime
from modules.engine import build_near_matches, build_team, candidate_capacity, run_matching
from modules.records import (
    ALLOCATION_COLUMNS,
    OPPORTUNITY_COLUMNS,
    apply_confirmed_allocations,
    append_confirmed_allocations,
    load_register,
)
from modules.sample_data import generate_demo_data
from modules.validation import (
    parse_skill_string,
    validate_capacity,
    validate_request,
    validate_resources,
)


DEMO_RESOURCES, DEMO_CAPACITY = generate_demo_data()


def default_request():
    return {
        "request_id": "T1",
        "project_name": "Healthcare analytics",
        "start_date": date(2026, 9, 21),
        "end_date": date(2026, 10, 12),
        "allocation_pct": 50,
        "allowed_locations": ["India"],
        "time_zones": ["Asia/Kolkata"],
        "languages": ["English"],
        "domains": ["Healthcare"],
        "role_mix": [
            {"designation": "Consultant", "grade": 140, "headcount": 2},
        ],
        "mandatory_skills": {"SQL": 3, "Python": 2},
        "preferred_skills": {"Power BI": 2},
    }


def test_numeric_grade_mapping_follows_hr_codes():
    assert DESIGNATION_TO_GRADE == {
        "Analyst": 130,
        "Associate Consultant": 130,
        "Consultant": 140,
        "Senior Consultant": 150,
        "Engagement Manager": 160,
        "Principal": 170,
        "Senior Principal": 180,
    }


def test_demo_contract_is_simplified_and_valid():
    resources, capacity = DEMO_RESOURCES, DEMO_CAPACITY
    assert validate_resources(resources).ok
    assert validate_capacity(capacity, resources).ok
    assert list(capacity.columns) == [
        "resource_id",
        "week_start",
        "available_capacity_pct",
    ]
    assert not {
        "profile_confidence",
        "country_expertise",
        "capability_tags",
    }.intersection(resources.columns)
    assert capacity.available_capacity_pct.between(30, 70).all()


def test_senior_people_have_broader_profiles_than_junior_people():
    resources = DEMO_RESOURCES.assign(
        skill_count=DEMO_RESOURCES.skills.str.count(r"\|") + 1,
        project_count=DEMO_RESOURCES.project_expertise.str.count(r"\|") + 1,
    )
    junior = resources[resources.grade.eq(130)]
    senior = resources[resources.grade.ge(170)]
    assert senior.skill_count.median() > junior.skill_count.median()
    assert senior.project_count.median() > junior.project_count.median()
    analyst_skills = set().union(
        *(parse_skill_string(value) for value in junior.skills)
    )
    assert {"SQL", "Python", "Tableau", "GenAI"} <= analyst_skills
    consultant_skills = set().union(
        *(parse_skill_string(value) for value in resources[resources.grade.eq(140)].skills)
    )
    assert {"Power BI", "AWS"} <= consultant_skills


def test_default_request_returns_two_consultants_and_top_anchor():
    result = run_matching(DEMO_RESOURCES, DEMO_CAPACITY, default_request())
    eligible = result.table[result.table.status.eq("Eligible")]
    assert result.diagnostics["fillable_slots"] == 2
    assert set(eligible.role_title) == {"Consultant"}
    assert set(eligible.grade) == {140}
    assert eligible.sort_values("rank").iloc[0].resource_name == "Aarav Sharma"


def test_principal_request_never_returns_analyst():
    request = default_request()
    request["role_mix"] = [
        {"designation": "Principal", "grade": 170, "headcount": 1}
    ]
    result = run_matching(DEMO_RESOURCES, DEMO_CAPACITY, request)
    eligible = result.table[result.table.status.eq("Eligible")]
    assert set(eligible.grade) <= {170}
    assert set(eligible.role_title) <= {"Principal"}


def test_role_mix_builds_unique_team():
    request = default_request()
    request["role_mix"] = [
        {"designation": "Consultant", "grade": 140, "headcount": 2},
        {"designation": "Senior Consultant", "grade": 150, "headcount": 1},
    ]
    result = run_matching(DEMO_RESOURCES, DEMO_CAPACITY, request)
    team = [row for row in build_team(result.table) if row["status"] == "Filled"]
    resource_ids = [row["resource_id"] for row in team]
    assert len(resource_ids) == len(set(resource_ids))
    assert len(team) <= 3


def test_each_role_can_have_different_skill_requirements():
    request = default_request()
    request["mandatory_skills"] = {}
    request["preferred_skills"] = {}
    request["role_mix"] = [
        {
            "designation": "Associate Consultant",
            "grade": 130,
            "headcount": 1,
            "mandatory_skills": {"Tableau": 2},
            "preferred_skills": {"GenAI": 1},
        },
        {
            "designation": "Consultant",
            "grade": 140,
            "headcount": 1,
            "mandatory_skills": {"Power BI": 2, "AWS": 1},
            "preferred_skills": {"Databricks": 1},
        },
    ]
    result = run_matching(DEMO_RESOURCES, DEMO_CAPACITY, request)
    associate = result.table[
        result.table.requested_designation.eq("Associate Consultant")
    ].iloc[0]
    consultant = result.table[
        result.table.requested_designation.eq("Consultant")
    ].iloc[0]
    assert associate.requested_mandatory_skills == {"Tableau": 2}
    assert consultant.requested_mandatory_skills == {"Power BI": 2, "AWS": 1}


def test_specific_team_is_a_hard_gate_not_a_score_component():
    request = default_request()
    request["allowed_teams"] = ["CSEC Analytics India"]
    result = run_matching(DEMO_RESOURCES, DEMO_CAPACITY, request)
    eligible = result.table[result.table.status.eq("Eligible")]
    assert not eligible.empty
    assert set(eligible.team) == {"CSEC Analytics India"}
    assert all("team" not in component for component in eligible.score_components)


def test_manual_weights_change_ranking_components_without_changing_gates():
    request = default_request()
    custom = {
        "mandatory_skills": 0.10,
        "preferred_skills": 0.10,
        "proficiency": 0.10,
        "capacity": 0.70,
    }
    result = run_matching(DEMO_RESOURCES, DEMO_CAPACITY, request, custom)
    eligible = result.table[result.table.status.eq("Eligible")]
    assert not eligible.empty
    assert set(eligible.iloc[0].score_components) == set(DEFAULT_WEIGHTS)
    assert eligible.iloc[0].score_components["capacity"] > 50


def test_allocation_register_seeds_and_appends_idempotently(tmp_path):
    register = tmp_path / "staffing_register.xlsx"
    opportunities, allocations = load_register(register, DEMO_RESOURCES)
    assert list(opportunities.columns) == OPPORTUNITY_COLUMNS
    assert list(allocations.columns) == ALLOCATION_COLUMNS
    assert len(opportunities) == 10
    assert len(allocations) == 12
    assert allocations["Allocation Hours / Week"].notna().all()
    assert allocations["Employee ID"].nunique() < len(allocations)
    assert allocations["Employee ID"].tolist() != DEMO_RESOURCES.head(12).resource_id.tolist()

    request = default_request()
    request["request_id"] = "OPP-TEST-001"
    request["client"] = "Demo Client"
    request["allowed_teams"] = []
    result = run_matching(DEMO_RESOURCES, DEMO_CAPACITY, request)
    selected = result.table[result.table.status.eq("Eligible")].head(2)
    first = append_confirmed_allocations(
        register, DEMO_RESOURCES, request, selected
    )
    second = append_confirmed_allocations(
        register, DEMO_RESOURCES, request, selected
    )
    assert first["opportunity_added"] == 1
    assert first["allocations_added"] == 2
    assert second["opportunity_added"] == 0
    assert second["allocations_added"] == 0
    assert second["allocations_skipped"] == 2
    _, saved_allocations = load_register(register, DEMO_RESOURCES)
    saved = saved_allocations[
        saved_allocations["Opportunity Number"].eq("OPP-TEST-001")
    ]
    assert saved["Allocation Hours / Week"].eq(STANDARD_WEEK_HOURS / 2).all()


def test_confirmed_allocations_reduce_only_overlapping_weekly_capacity():
    capacity = pd.DataFrame(
        {
            "resource_id": ["X", "X", "X", "Y"],
            "week_start": pd.to_datetime(
                ["2026-09-14", "2026-09-21", "2026-09-28", "2026-09-21"]
            ),
            "available_capacity_pct": [60.0, 60.0, 60.0, 60.0],
        }
    )
    allocations = pd.DataFrame(
        [
            {
                "Employee ID": "X",
                "Employee Name": "Person X",
                "Opportunity Number": "OPP-1",
                "Project Name": "Project",
                "Allocation Hours / Week": 8.5,
                "Allocation %": 20.0,
                "Allocation Start Date": "2026-09-21",
                "Allocation End Date": "2026-09-27",
                "Status": "Confirmed",
            }
        ],
        columns=ALLOCATION_COLUMNS,
    )
    adjusted = apply_confirmed_allocations(capacity, allocations)
    x = adjusted[adjusted.resource_id.eq("X")].set_index("week_start")
    assert x.loc[pd.Timestamp("2026-09-14"), "available_capacity_pct"] == 60
    assert x.loc[pd.Timestamp("2026-09-21"), "available_capacity_pct"] == 40
    assert x.loc[pd.Timestamp("2026-09-28"), "available_capacity_pct"] == 60
    assert adjusted[adjusted.resource_id.eq("Y")].available_capacity_pct.iloc[0] == 60


def test_discovery_accepts_weekly_hours_and_converts_to_capacity_percentage():
    intent = interpret_query("Power BI people with 21.25-25.5 hours free")
    assert intent.availability_min == 50
    assert intent.availability_max == 60


def test_capacity_has_no_tolerance():
    resources = canonicalize_resources(
        pd.DataFrame(
            {
                "resource_id": ["X"],
                "resource_name": ["Person"],
                "team": ["Team"],
                "grade": [140],
                "role_title": ["Consultant"],
                "location": ["India"],
                "time_zone": ["Asia/Kolkata"],
                "languages": ["English"],
                "skills": ["SQL:4|Python:3"],
                "domains": ["Healthcare"],
                "development_interests": [""],
                "years_experience": [5],
                "delivery_rating": [4],
                "profile_updated": ["2026-09-01"],
            }
        )
    )
    capacity = canonicalize_capacity(
        pd.DataFrame(
            {
                "resource_id": ["X"],
                "week_start": ["2026-09-21"],
                "available_capacity_pct": [49],
            }
        )
    )
    request = default_request()
    request["start_date"] = request["end_date"] = date(2026, 9, 21)
    request["role_mix"][0]["headcount"] = 1
    result = run_matching(resources, capacity, request)
    person = result.table.iloc[0]
    assert person.status == "Excluded"
    assert "Available capacity is below" in " ".join(person.exclusion_reasons)


def test_missing_capacity_is_not_assumed_available():
    result = run_matching(
        DEMO_RESOURCES,
        DEMO_CAPACITY[DEMO_CAPACITY.resource_id.ne("EMP-1001")],
        default_request(),
    )
    anchor = result.table[result.table.resource_id.eq("EMP-1001")].iloc[0]
    assert anchor.status == "Excluded"
    assert "Weekly capacity data is incomplete" in anchor.exclusion_reasons


def test_candidate_capacity_reports_missing_week():
    window = candidate_capacity(
        DEMO_CAPACITY.iloc[0:0],
        "UNKNOWN",
        date(2026, 9, 21),
        date(2026, 10, 5),
        50,
    )
    assert len(window) == 3
    assert window.data_missing.all()


def test_germany_query_returns_only_germany_not_europe():
    intent, found = discovery_search(
        DEMO_RESOURCES,
        DEMO_CAPACITY,
        "Find Consultants with SQL and Python in Germany",
        20,
    )
    assert intent.locations == {"Germany"}
    assert not found.empty
    assert set(found.location) == {"Germany"}


def test_europe_query_uses_geography_expertise():
    intent = interpret_query("Who has price elasticity expertise in Europe?")
    assert intent.locations == set()
    assert intent.geographies == {"Europe"}
    _, found = discovery_search(
        DEMO_RESOURCES,
        DEMO_CAPACITY,
        "Who has price elasticity expertise in Europe?",
        10,
    )
    assert not found.empty
    assert found.geography_expertise.str.contains("Europe").all()


def test_keyword_search_parses_capacity_range_and_date():
    intent, found = discovery_search(
        DEMO_RESOURCES,
        DEMO_CAPACITY,
        "Find SQL Python Tableau Power BI GenAI people in India with 50-60% availability from 2026-09-21",
        20,
    )
    assert intent.availability_min == 50
    assert intent.availability_max == 60
    assert intent.start_date == date(2026, 9, 21)
    assert not found.empty
    assert set(found.location) == {"India"}
    assert found.minimum_available_pct.between(50, 60).all()
    assert "Aarav Sharma" in set(found.resource_name)


def test_llm_runtime_validates_payload_and_falls_back():
    class Adapter:
        def interpret(self, text, schema):
            assert schema["interface"]
            return {
                "intent": "resource_matching",
                "skills": ["SQL", "Invented Skill"],
                "locations": ["Germany", "Europe"],
            }

    intent = interpret_with_runtime("find someone", Adapter())
    assert intent.interpreted_by == "llm"
    assert intent.skills == {"SQL"}
    assert intent.locations == {"Germany"}

    class BrokenAdapter:
        def interpret(self, text, schema):
            raise TimeoutError

    fallback = interpret_with_runtime("Python in India", BrokenAdapter())
    assert fallback.interpreted_by == "deterministic"
    assert fallback.locations == {"India"}


def test_skill_parser_remains_tolerant():
    parsed = parse_skill_string("SQL:3|PowerBI:4|bad|Python:nope|Gen AI:2")
    assert parsed == {"SQL": 3, "Power BI": 4, "GenAI": 2}


def test_request_validation_rejects_duplicate_or_bad_roles():
    request = default_request()
    request["role_mix"].append(
        {"designation": "Consultant", "grade": 140, "headcount": 1}
    )
    report = validate_request(request)
    assert not report.ok
    assert any("Duplicate role row" in error for error in report.errors)


def test_near_matches_are_still_explicitly_excluded():
    request = default_request()
    request["languages"] = ["French"]
    result = run_matching(DEMO_RESOURCES, DEMO_CAPACITY, request)
    near = build_near_matches(result.table, limit=10)
    assert all(row["failed_gate_count"] >= 1 for row in near)
    assert all(row["exclusion_reasons"] for row in near)


def test_committed_data_roundtrip():
    resources, capacity = load_demo_data(Path("data"))
    assert len(resources) == 320
    assert len(capacity) == 9600
