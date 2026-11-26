import ast
from pathlib import Path
from types import SimpleNamespace

import pytest


def run_auth_routing(requested_page, session_state):
    source = (Path(__file__).resolve().parent.parent / "app.py").read_text(encoding="utf-8-sig")
    module = ast.parse(source)
    routing = next(
        node for node in module.body
        if isinstance(node, ast.If)
        and isinstance(node.test, ast.Compare)
        and isinstance(node.test.left, ast.Name)
        and node.test.left.id == "requested_page"
        and isinstance(node.test.comparators[0], ast.Constant)
        and node.test.comparators[0].value == "login"
    )
    st = SimpleNamespace(session_state=session_state, query_params={"page": requested_page})
    code = ast.fix_missing_locations(ast.Module(body=[routing], type_ignores=[]))
    exec(compile(code, "app.py", "exec"), {"st": st, "requested_page": requested_page})

    return st


def test_unauthenticated_app_launch_stays_on_landing():
    state = {"is_logged_in": False, "auth_redirect_mode": "Cinematic Engine"}
    st = run_auth_routing("studio", state)

    assert st.session_state["current_page"] == "landing"
    assert "auth_redirect_mode" not in st.session_state
    assert st.query_params["page"] == "landing"

    st = run_auth_routing("landing", state)
    assert st.session_state["current_page"] == "landing"
    assert "auth_redirect_mode" not in st.session_state


def test_explicit_login_opens_login():
    st = run_auth_routing("login", {"is_logged_in": False})

    assert st.session_state["current_page"] == "landing"
    assert st.session_state["auth_redirect_mode"] == "Cinematic Engine"
    assert st.query_params["page"] == "landing"


@pytest.mark.parametrize("requested_page", ["studio", "login"])
def test_logged_in_studio_entry_remains_accessible(requested_page):
    st = run_auth_routing(requested_page, {"is_logged_in": True})

    assert st.session_state["current_page"] == "studio"
    assert st.query_params["page"] == "studio"
