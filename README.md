# CSEC RM Copilot POC

## Documentation

- [Complete project guide](docs/PROJECT_GUIDE.md) — architecture, end-to-end flow, every tab, scoring, guardrails, limitations and glossary.
- [Data dictionary](docs/DATA_DICTIONARY.md) — every source, request, derived, result and audit field with formats and validation.
- [Stakeholder walkthrough](docs/STAKEHOLDER_WALKTHROUGH.md) — presentation script, demo scenario, FAQs, honest limitations and roadmap.

## Purpose

A decision-support POC for CSEC capability discovery and resource matching.

The product has two user journeys over the same backend:

1. **Copilot / capability discovery**: a manager can ask lightweight natural-language questions such as `I have an MMX project, who should I contact?` or `Who has expertise in price elasticity for Europe?` The current POC uses deterministic vocabulary-aware search. An approved LLM can later replace only the interpretation layer.
2. **Structured resource matching**: when a manager has a fuller demand definition, the form captures role, dates, allocation, skills, proficiency, grade, location, time zone, language and domain. The deterministic engine validates the request, applies hard gates, ranks feasible candidates and explains the result.

## Important business rules

- Location is a **hard gate** whenever locations are selected.
- Time zone is a **hard gate** whenever time zones are selected.
- Every mandatory skill and proficiency requirement must be satisfied.
- Grade range follows: **Analyst → Associate Consultant → Consultant → Senior Consultant → Engagement Manager → Principal → Senior Principal**.
- The UI prevents a minimum grade above the selected maximum.
- A high fit score can never compensate for a failed hard gate.
- Weekly capacity is checked across the complete request horizon when the hard capacity gate is enabled.
- Missing capacity data is not silently interpreted as free capacity.
- Missing profile information is surfaced as uncertainty, not as an ability penalty.
- Alternatives explicitly exclude the selected person.
- Protected or sensitive attributes are not used in matching.
- The fit score is a comparison aid, not a prediction of performance or employee value.
- Excluded candidates retain a separate potential-fit score for audit/near-match review, but their recommendation score remains zero.
- Near matches are explicitly labelled as excluded and require a human to change a constraint; the engine never relaxes a gate silently.

## Recommended RM guardrails

Treat these as strict when the requester explicitly supplies them:

- request dates and weekly allocation;
- mandatory skill presence and minimum proficiency;
- minimum/maximum grade;
- required work location, time zone and client language;
- complete weekly capacity data and confirmed headroom when hard-capacity mode is enabled;
- domain only when regulation, client context or delivery policy genuinely requires prior domain experience.

Treat preferred skills, development interests, additional proficiency, prior delivery evidence and tentative capacity as ranking or risk signals rather than automatic exclusions. Before production, add governed fields for work authorization, contractual entity, security clearance and local labor restrictions; the POC does not infer these from location or nationality.

The system must never score protected characteristics, infer missing skills, hide missing capacity, autonomously allocate a person, or let a high weighted score override a failed strict constraint. Profiles below the confidence threshold and tentative conflicts require verification by RM.

## Score interpretation

The 0–100 fit score applies only to candidates who pass every hard gate. It combines mandatory coverage, preferred capabilities, proficiency depth, relevant and recent delivery evidence, capacity resilience, domain fit, development alignment and profile confidence. It is deterministic and versioned, and should be used to compare feasible candidates—not as a probability of project success.

## Dataset

The included synthetic POC data contains:

- 320 resource profiles
- 9,600 weekly capacity records across 30 weeks
- 1,200+ delivery-evidence records
- 50+ governed skills
- 7 CSEC grades
- 11 work locations including India and Philippines
- time zones, languages, therapeutic/domain expertise, development interests
- manager/contact information
- geography/country expertise
- project/capability expertise including MMX and price elasticity examples

The people and operational records are synthetic and are intended for demonstration only.

## Folder structure

```text
csec_rm_copilot/
├── app.py
├── requirements.txt
├── run_app.bat
├── README.md
├── data/
│   ├── resources.csv
│   ├── capacity.csv
│   └── delivery_evidence.csv
├── modules/
│   ├── config.py
│   ├── data.py
│   ├── discovery.py
│   ├── engine.py
│   ├── sample_data.py
│   └── validation.py
└── tests/
    ├── conftest.py
    └── test_engine.py
```

## Windows setup

From the project directory:

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
streamlit run app.py
```

Or use `run_app.bat` after dependencies are installed.

## Testing

```powershell
.venv\\Scripts\\activate
pytest -q
```

The current suite covers hard location/time-zone rules, grade-order validation, French/no-match handling, impossible capability combinations, missing capacity data, skill aliases, capability discovery, MMX discovery, price-elasticity discovery, canonicalization of sparse uploads and dataset round-tripping.

## Future LLM integration

The file `modules/discovery.py` exposes the intended interpretation contract through `mock_llm_adapter_spec()`.

The future architecture should be:

```text
Natural-language request
        ↓
LLM / NLP interpretation layer
        ↓
Structured intent contract
        ↓
Deterministic validation + hard eligibility gates
        ↓
Evidence-based scoring
        ↓
Capacity / alternatives / contact paths
        ↓
Human decision
```

The LLM should not become the system of record for eligibility or scoring. It should translate user language into the governed request/intent schema.

No API key is needed for the current application. When approved access arrives, the LLM adapter should read credentials from `st.secrets`, return schema-validated structured intent, preserve the original user text for audit, and reject unsupported taxonomy values. Prompt text must never be allowed to alter hard-gate policy or matching weights.

## External product-design benchmark

The design intentionally follows the modern resource-management pattern of combining demand, skills, availability, cross-team visibility, bottleneck detection and scenario-oriented decision support rather than treating resource matching as a simple name search. Examples include Planview, Kantata and Runn.

## Demo scenario

Use:

- Role: Healthcare Data Analyst
- Dates: 14 Sep 2026 to 30 Nov 2026
- Allocation: 50%
- Location: India
- Time zone: Asia/Kolkata
- Language: English
- Mandatory: SQL Proficient, Python Working, Healthcare Data Working
- Preferred: Power BI Working, Claims Data Working
- Grade: Analyst to Consultant

The deterministic demo is engineered so that **Aarav Sharma** is a strong top feasible candidate, while other resources provide genuine comparisons and cross-team context.
