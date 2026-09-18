from pathlib import Path

from streamlit.testing.v1 import AppTest


APP = Path(__file__).resolve().parents[1] / "app.py"


def run_app():
    return AppTest.from_file(str(APP), default_timeout=60).run()


def test_app_opens_on_the_project_brief_without_errors():
    app = run_app()
    assert not app.exception
    assert any("Project brief" in block.value for block in app.markdown)


def test_navigation_uses_plain_page_names_on_the_main_screen():
    app = run_app()
    nav_labels = [
        button.label for button in app.button if (button.key or "").startswith("nav_")
    ]
    assert "Project brief" in nav_labels
    assert "Capacity & risk" in nav_labels
    assert "Team builder" not in nav_labels
    assert "Capability intelligence" not in nav_labels
    assert not any(label.startswith(("1 ·", "2 ·", "3 ·")) for label in nav_labels)
    assert not app.sidebar.button
    assert not app.sidebar.radio


def test_no_page_advertises_internal_step_numbering():
    app = run_app()
    for page in ["Project brief", "Team & skills", "Recommendations"]:
        app.button(key=f"nav_{page}").click().run(timeout=60)
        rendered = " ".join(block.value for block in app.markdown).lower()
        assert "step 1" not in rendered
        assert "step 2" not in rendered
        assert "step 3" not in rendered


def test_every_page_renders_without_exception():
    for page in [
        "Project brief",
        "Team & skills",
        "Recommendations",
        "Capacity & risk",
        "Ask Copilot",
    ]:
        app = run_app()
        app.button(key=f"nav_{page}").click().run(timeout=60)
        assert not app.exception, f"{page} raised an exception"


def test_manual_weights_must_total_one_hundred_percent():
    app = run_app()
    app.button(key="nav_Team & skills").click().run(timeout=60)
    app.checkbox[0].set_value(True).run(timeout=60)
    assert not app.exception
    assert app.number_input
    app.number_input(key="weight_capacity").set_value(80).run(timeout=60)
    assert not app.exception
    assert any("100%" in message.value for message in app.error)
    match_button = [
        button for button in app.button if button.label == "Find matching people"
    ][0]
    assert match_button.disabled


def test_moving_between_pages_does_not_break_session_state():
    app = run_app()
    save_buttons = [
        button for button in app.button if button.label.startswith("Save and continue")
    ]
    assert save_buttons
    save_buttons[0].click().run(timeout=60)
    assert not app.exception
    assert app.session_state["page"] == "Team & skills"


def test_running_a_match_produces_recommendations():
    app = run_app()
    match_buttons = [button for button in app.button if button.label == "Find matching people"]
    if not match_buttons:
        app.button(key="nav_Team & skills").click().run(timeout=60)
        match_buttons = [
            button for button in app.button if button.label == "Find matching people"
        ]
    assert match_buttons
    match_buttons[0].click().run(timeout=60)
    assert not app.exception
    assert app.session_state["page"] == "Recommendations"
    assert app.session_state["results"] is not None


def test_capacity_and_risk_views_survive_a_single_team_filter():
    app = run_app()
    app.button(key="nav_Capacity & risk").click().run(timeout=60)
    assert not app.exception
    teams = app.multiselect[0]
    teams.set_value([teams.options[0]]).run(timeout=60)
    assert not app.exception
    views = app.radio[0]
    for option in views.options:
        views.set_value(option).run(timeout=60)
        assert not app.exception, f"{option} raised with a single-team filter"


def test_empty_copilot_search_warns_instead_of_crashing():
    app = run_app()
    app.button(key="nav_Ask Copilot").click().run(timeout=60)
    search_buttons = [button for button in app.button if button.label == "Search"]
    assert search_buttons
    search_buttons[0].click().run(timeout=60)
    assert not app.exception
    assert app.warning
