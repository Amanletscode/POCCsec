# Project guide

## Architecture

- `app.py`: accessible guided Streamlit experience and session state.
- `modules/data.py`: two-dataset loading, canonicalization, and health checks.
- `modules/validation.py`: governed schema, request, skill, and capacity validation.
- `modules/engine.py`: fixed hard gates, explainable scoring, role-mix matching, and team creation.
- `modules/discovery.py`: deterministic search plus the validated runtime LLM boundary.
- `modules/sample_data.py`: deterministic synthetic resources and weekly availability.
- `modules/config.py`: governed grades, skills, locations, time zones, and policy versions.
- `modules/records.py`: seeded Excel register and idempotent opportunity/allocation appends.

## Request flow

1. Capture project constraints.
2. Add exact designation/headcount rows.
3. Add mandatory and nice-to-have skill/proficiency rows.
4. Validate the request and active datasets.
5. Assess each person for each requested role.
6. Apply hard gates before scoring.
7. Rank eligible people inside each role.
8. Let the manager select approved people.
9. Append confirmed rows to the Opportunities and Allocations workbook sheets.

## Hard gates

Country, optional specific team, time zone, language, designation/grade, mandatory skill presence, mandatory proficiency, complete weekly capacity, and requested weekly hours are strict. A PSA week is 42.5 hours. Confirmed register allocations reduce free hours in every overlapping week before matching; no tolerance is applied. Team is a gate only and never contributes ranking points.

## Ranking

Eligible people are compared using:

- mandatory skill coverage;
- nice-to-have skill coverage;
- proficiency depth;
- direct available-capacity fit.

Governed defaults are used unless the manager enables manual scoring and supplies weights totalling 100%. A total above or below 100% blocks matching and reports the exact adjustment needed.

## Capacity & risk

This page is deliberately not a person search. It reports on the supply side across a horizon of
four to twelve weeks:

- bench and redeployment: sustained free weekly hours, plus people who free up in later weeks;
- capability coverage risk: proficient headcount, how many of those are actually free, team
  concentration, and single points of failure;
- capacity trend: total free hours per week across the horizon.

A week missing from the capacity sheet counts as unavailable, matching the hard gate.

An excluded person cannot rank above an eligible person. Near matches remain explicitly labelled as excluded.

## Copilot contract

Natural-language interpretation is replaceable; policy is not. `interpret_with_runtime` can call an approved adapter at runtime, validates the result against governed catalogues, and falls back to deterministic parsing. Employee profile data does not need to be sent to the model because matching and search execute locally after interpretation.

## UX principles

- one primary task per page;
- progressive disclosure instead of a dense sidebar;
- labels, placeholders, and help text for project managers;
- explicit empty and no-match states;
- compact policy notes near decisions;
- keyboard-compatible native Streamlit controls;
- no hidden relaxation of business rules.
