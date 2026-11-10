import ast
import logging
import os
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest

import comfyui_engine
from workshop_prompt import WORKSHOP_ENHANCEMENT_SYSTEM_PROMPT, build_workshop_prompt


APP_PATH = Path(__file__).resolve().parent.parent / "app.py"


def _app_function(name, namespace):
    module = ast.parse(APP_PATH.read_text(encoding="utf-8-sig"))
    node = next(
        node for node in module.body
        if isinstance(node, ast.FunctionDef) and node.name == name
    )
    code = ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[]))
    exec(compile(code, str(APP_PATH), "exec"), namespace)
    return namespace[name]


def test_original_request_is_preserved_and_intentional_damage_is_allowed():
    original = "A ruined temple, टूटी दीवारें, blue lantern, no people, watercolor."
    prompt = build_workshop_prompt(original, "A temple at dusk.")
    assert original in prompt
    assert "A temple at dusk." in prompt
    assert "preserve the original request" in prompt
    assert "intentional damage" in prompt
    assert "consistent perspective" in prompt
    assert "watercolor" in prompt


def test_no_optimization_does_not_duplicate_original():
    assert build_workshop_prompt("A forest", "A forest").count("A forest") == 1
    assert build_workshop_prompt("A forest").count("A forest") == 1
    with pytest.raises(ValueError):
        build_workshop_prompt("  ")


def test_prompt_enhancement_request_preserves_style_and_negatives():
    calls = {}

    def post(url, **kwargs):
        calls.update(kwargs["json"])
        return SimpleNamespace(
            status_code=200,
            json=lambda: {"choices": [{"message": {"content": "Watercolor forest"}}]},
        )

    enhance = _app_function("_enhance_workshop_prompt_gpt4o", {
        "get_system_secret": lambda key: "test",
        "requests": SimpleNamespace(post=post),
        "WORKSHOP_ENHANCEMENT_SYSTEM_PROMPT": WORKSHOP_ENHANCEMENT_SYSTEM_PROMPT,
    })
    assert enhance("Watercolor forest", "no buildings") == "Watercolor forest"
    assert "preserve all" in calls["messages"][0]["content"].lower()
    assert "surrealism" in calls["messages"][0]["content"]
    assert "no buildings" in calls["messages"][1]["content"]
    assert calls["temperature"] == 0.3


@pytest.mark.parametrize("provider", ["replicate", "stability", "comfyui"])
def test_workshop_guidance_reaches_each_provider(tmp_path, monkeypatch, provider):
    monkeypatch.chdir(tmp_path)
    calls = {}
    prompt = build_workshop_prompt("A futuristic city with blue towers", "City at dawn")

    def replicate(value, *_args, **_kwargs):
        calls["replicate"] = value
        if provider != "replicate":
            raise RuntimeError("unavailable")
        path = tmp_path / "replicate.png"
        path.write_bytes(b"image")
        return str(path)

    def post(_url, **kwargs):
        calls["stability"] = kwargs["files"]
        return SimpleNamespace(status_code=200, content=b"x" * 10001, text="")

    def comfy(value, **kwargs):
        calls["comfyui"] = (value, kwargs)
        path = tmp_path / "comfy.png"
        path.write_bytes(b"image")
        return str(path)

    monkeypatch.setattr(comfyui_engine, "generate_workshop_image", comfy)
    namespace = {
        "Path": Path, "os": os, "uuid": uuid, "logger": logging.getLogger("test"),
        "st": SimpleNamespace(session_state={}),
        "_generate_replicate_workshop_image": replicate,
        "_ReplicateWorkshopHTTPError": type("WorkshopError", (RuntimeError,), {}),
        "WORKSHOP_MODEL_BY_QUALITY": {"Standard": ("model", "label")},
        "STABILITY_API_KEY": "test" if provider == "stability" else "",
        "get_system_secret": lambda key: "",
        "requests": SimpleNamespace(post=post),
    }
    monkeypatch.delenv("STABILITY_API_KEY", raising=False)
    generate = _app_function("generate_pro_image", namespace)
    result = generate(prompt, "16:9", "no cars", "Standard")
    assert Path(result).is_file()
    if provider == "replicate":
        assert calls["replicate"] == prompt
    elif provider == "stability":
        assert prompt in calls["stability"]["prompt"][1]
        assert calls["stability"]["negative_prompt"][1] == "no cars"
    else:
        assert calls["comfyui"][0] == prompt
        assert calls["comfyui"][1]["negative_prompt"] == "no cars"


def test_workshop_ui_passes_original_and_enhanced_prompts():
    source = APP_PATH.read_text(encoding="utf-8-sig")
    module = ast.parse(source)
    function = next(
        node for node in module.body
        if isinstance(node, ast.FunctionDef) and node.name == "run_creative_workshop"
    )
    calls = [
        node for node in ast.walk(function)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        and node.func.id == "generate_pro_image"
    ]
    assert len(calls) == 1
    prompt = calls[0].args[0]
    assert isinstance(prompt, ast.Call)
    assert isinstance(prompt.func, ast.Name) and prompt.func.id == "build_workshop_prompt"
    assert [arg.id for arg in prompt.args] == ["workshop_prompt_str", "enhanced_workshop_prompt"]
