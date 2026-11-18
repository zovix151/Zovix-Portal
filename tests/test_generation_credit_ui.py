import ast
from pathlib import Path
from types import SimpleNamespace

import pytest
from streamlit.testing.v1 import AppTest

import generation_credit_ui


class CreditPlaceholder:
    def __init__(self):
        self.message = None

    def info(self, message):
        self.message = message

    def empty(self):
        self.message = None


@pytest.mark.parametrize("fails", [False, True])
def test_credit_notice_visible_during_generation_and_cleared_afterward(monkeypatch, fails):
    placeholder = CreditPlaceholder()
    monkeypatch.setattr(
        generation_credit_ui,
        "st",
        SimpleNamespace(
            empty=lambda: placeholder,
            session_state={"user_credits": 84.5},
        ),
    )

    def generate():
        with generation_credit_ui.generation_credit_progress("Ghost Engine", 15):
            assert placeholder.message == (
                "Ghost Engine: 15 credits deducted · 84.50 credits remaining."
            )
            if fails:
                raise RuntimeError("Generation failed")

    if fails:
        with pytest.raises(RuntimeError, match="Generation failed"):
            generate()
    else:
        generate()
    assert placeholder.message is None


def test_pending_charge_is_not_reported_as_already_deducted():
    message = generation_credit_ui.generation_credit_message(
        "Video Editor", 3, 10, pending=True
    )
    assert "3 credits will be deducted on success" in message
    assert "10.00 credits current balance" in message


@pytest.mark.parametrize("fails", [False, True])
def test_streamlit_clears_notice_after_generation(fails):
    app = AppTest.from_string(
        f"""
import streamlit as st
from generation_credit_ui import generation_credit_progress
st.session_state["user_credits"] = 84.5
try:
    with generation_credit_progress("Ghost Engine", 15):
        if {fails}:
            raise RuntimeError("Generation failed")
except RuntimeError:
    st.error("Generation failed")
st.write("Finished")
"""
    ).run()
    assert not app.exception
    assert not app.info
    assert len(app.error) == int(fails)


@pytest.mark.parametrize("status", ["Processing", "Completed", "Failed"])
def test_background_cinematic_credit_notice_only_while_running(status):
    source = (Path(__file__).resolve().parent.parent / "app.py").read_text(
        encoding="utf-8-sig"
    )
    module = ast.parse(source)
    node = next(
        child
        for parent in module.body if isinstance(parent, ast.If)
        for child in parent.body
        if isinstance(child, ast.FunctionDef) and child.name == "render_cinematic_job_status"
    )
    node.decorator_list = []
    code = ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[]))
    notices = []
    session = {"cinematic_job_id": "job", "user_credits": 84.5}
    job = {
        "status": status,
        "credits_deducted": 15,
        "video_path": "output.mp4",
        "error": "failed",
    }

    class Rerun(Exception):
        pass

    def rerun():
        raise Rerun()

    st = SimpleNamespace(
        session_state=session,
        markdown=lambda *args, **kwargs: None,
        info=notices.append,
        error=lambda message: None,
        rerun=rerun,
    )
    namespace = {
        "st": st,
        "_get_cinematic_job": lambda job_id: job,
        "_record_generation_credit_usage": lambda *args: None,
        "_show_generation_success": lambda: None,
        "generation_credit_message": generation_credit_ui.generation_credit_message,
    }
    exec(compile(code, "app.py", "exec"), namespace)
    if status == "Processing":
        namespace["render_cinematic_job_status"]()
        assert any("15 credits deducted" in notice for notice in notices)
    else:
        with pytest.raises(Rerun):
            namespace["render_cinematic_job_status"]()
        assert not notices
