from pathlib import Path

from streamlit.testing.v1 import AppTest


APP = Path(__file__).resolve().parents[1] / "app.py"


def test_app_initial_render_has_no_uncaught_exception():
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    assert not app.exception
    assert any("CSEC RM Copilot" in title.value for title in app.markdown)


def test_empty_copilot_query_is_handled_without_crashing():
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    app.button(key="example_0")  # Stable keyed widgets are discoverable.
    search_buttons = [button for button in app.button if button.label == "Search capability network"]
    assert search_buttons
    search_buttons[0].click().run(timeout=30)
    assert not app.exception
    assert app.warning
