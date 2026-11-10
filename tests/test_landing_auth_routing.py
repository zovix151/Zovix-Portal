import ast
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.mark.parametrize("requested_page", ["login", "studio"])
def test_unauthenticated_studio_entry_opens_login(requested_page):
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
    st = SimpleNamespace(session_state={"is_logged_in": False}, query_params={"page": requested_page})
    code = ast.fix_missing_locations(ast.Module(body=[routing], type_ignores=[]))
    exec(compile(code, "app.py", "exec"), {"st": st, "requested_page": requested_page})

    assert st.session_state["current_page"] == "landing"
    assert st.session_state["auth_redirect_mode"] == "Cinematic Engine"
    assert st.query_params["page"] == "landing"
