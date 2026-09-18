# CSEC Resource Manager

A Streamlit decision-support application for project staffing, capability discovery, and portfolio supply intelligence.

## Core workflows

1. **Project brief** captures dates, allocation, country, optional specific team, time zone, language, and the opportunity record.
2. **Team & skills** captures headcount, role-specific skill/proficiency requirements, and optional manual ranking weights.
3. **Recommendations** applies fixed eligibility rules, supports deliberate manager selection, and appends confirmed rows to the allocation register.
4. **Capacity & risk** answers portfolio questions a person search cannot: where unused capacity sits, who frees up later, which capabilities have thin or single-person coverage, and how free capacity moves week by week.
5. **Ask Copilot** interprets governed natural-language filters without requiring an API key.

Ranking weights default to governed values. A manager may override them for a run; the four
weights must total exactly 100% and the app states the exact amount to add or remove.

## Matching policy

The following are hard gates when requested:

- exact work country;
- exact specific team, when selected;
- exact time zone;
- all required languages;
- exact designation and numeric grade;
- every mandatory skill and minimum proficiency;
- complete weekly capacity data;
- available hours greater than or equal to the requested weekly hours in every week.

There is no capacity tolerance. A PSA week is 42.5 hours (8.5 hours × 5 days); percentages remain an internal/source representation. Team is never scored. Eligible people use governed default weights for mandatory skills, nice-to-have skills, proficiency depth, and capacity fit; managers may replace these weights for a run as long as they total 100%.

## Numeric grades

| Grade | Designation |
|---|---|
| 130 | Analyst / Associate Consultant |
| 140 | Consultant |
| 150 | Senior Consultant |
| 160 | Engagement Manager |
| 170 | Principal |
| 180 | Senior Principal |

Designation distinguishes Analyst from Associate Consultant at grade 130.

## Data

Only two input datasets are used:

- `data/resources.csv`: one row per person;
- `data/capacity.csv`: one row per person per week with direct `available_capacity_pct`.

The committed synthetic data contains 320 people and 9,600 weekly capacity rows. Weekly availability stays between 30% and 70%. Skills and project breadth grow with seniority while retaining hands-on foundations: junior profiles commonly include SQL, Python, Tableau and GenAI, while consultant and senior profiles add Power BI, cloud, data platforms, governance and leadership capability.

Confirmed results are persisted to `data/staffing_register.xlsx`. It contains separate `Opportunities` and `Allocations` sheets, is seeded with randomized demonstration history, and is updated idempotently from Recommendations. Confirmed hours are deducted from overlapping employee-weeks before the next match, so a person can join another project only when sufficient hours remain.

## Future LLM integration

`modules.discovery.interpret_with_runtime()` accepts an optional runtime adapter with:

```python
adapter.interpret(text, schema) -> dict
```

The model may translate language into governed fields only. Returned skills, countries, domains, time zones, languages, and designations are validated against application catalogues. Invalid output, timeouts, or provider failures fall back to deterministic parsing. Model output cannot change hard gates or scoring.

## Run

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\run_app.bat
```

## Test

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```
