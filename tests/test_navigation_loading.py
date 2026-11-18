import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.mark.skipif(not shutil.which("node"), reason="Node.js is required")
def test_back_navigation_shows_spinner_until_render_finishes():
    source = (Path(__file__).resolve().parent.parent / "app.py").read_text(
        encoding="utf-8-sig"
    )
    start = source.index("        if (!host.__zovixNavigationSpinnerInstalled) {")
    end = source.index(
        '        if (!host.document.getElementById("zovix-workspace-top-spacing-v2"))',
        start,
    )
    script = r"""
const vm = require("node:vm");
const assert = require("node:assert/strict");
let source = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", chunk => source += chunk);
process.stdin.on("end", () => {
    let now = 1000;
    let observer;
    let rendering = false;
    let nextTimer = 0;
    const timers = new Map();
    const elements = new Map();
    const listeners = {};
    const hostListeners = {};
    const body = {
        appendChild(element) { elements.set(element.id, element); },
    };
    const document = {
        body,
        createElement() {
            return {
                id: "",
                className: "",
                classList: {add() {}},
                setAttribute() {},
                appendChild() {},
                remove() { elements.delete(this.id); },
            };
        },
        getElementById(id) { return elements.get(id) || null; },
        querySelector(selector) {
            if (selector.includes("stStatusWidgetRunningIcon")) return rendering ? {} : null;
            return null;
        },
        addEventListener(name, callback) {
            (listeners[name] ||= []).push(callback);
        },
    };
    const host = {
        document,
        location: new URL("http://localhost:8501/?page=ghost_engine"),
        addEventListener(name, callback) {
            (hostListeners[name] ||= []).push(callback);
        },
        setTimeout(callback, delay) {
            const id = ++nextTimer;
            timers.set(id, {callback, delay});
            return id;
        },
        clearTimeout(id) { timers.delete(id); },
        setInterval() {},
    };
    host.history = {
        state: null,
        pushState(_state, _title, url) { host.location = new URL(url); },
    };
    class MutationObserver {
        constructor(callback) { observer = callback; }
        observe() {}
    }
    const FakeDate = class extends Date { static now() { return now; } };
    vm.runInNewContext(source, {
        host, URL, URLSearchParams, MutationObserver, Date: FakeDate,
        syncBrowserPage() {},
    });

    function clickBack(key, page) {
        host.location = new URL(`http://localhost:8501/?page=${page}`);
        const widget = {classList: [key]};
        const button = {closest: () => widget};
        const target = {
            closest(selector) { return selector === "button" ? button : null; },
        };
        listeners.click[0]({
            target, button: 0, ctrlKey: false, metaKey: false,
            shiftKey: false, altKey: false,
        });
        assert.ok(elements.has("zovix-navigation-loading-overlay"), key);
        assert.equal(host.location.search, "?page=studio");
        rendering = true;
        now += 10;
        observer();
        assert.ok(elements.has("zovix-navigation-loading-overlay"));
        rendering = false;
        now += 10;
        observer();
        now += 200;
        for (const [id, timer] of [...timers]) {
            if (timer.delay === 150) {
                timers.delete(id);
                timer.callback();
            }
        }
        assert.ok(!elements.has("zovix-navigation-loading-overlay"));
    }
    clickBack("st-key-ghost_engine_back_to_studio", "ghost_engine");
    clickBack("st-key-payments_back_to_studio", "payments");
    clickBack("st-key-profile_back_to_studio", "profile");
    clickBack("st-key-standalone_back_to_studio", "portfolio");
    clickBack("st-key-studio_change_mode_btn", "studio_mode");

    host.location = new URL("http://localhost:8501/?page=studio");
    hostListeners.popstate[0]();
    assert.ok(elements.has("zovix-navigation-loading-overlay"));
});
"""
    result = subprocess.run(
        [shutil.which("node"), "-e", script],
        input=source[start:end],
        text=True,
        capture_output=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
