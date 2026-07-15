from __future__ import annotations

import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from pa_agent.config.settings import load_settings
from pa_agent.webui.api import settings as settings_api


@pytest.fixture
def client(tmp_path, monkeypatch):
    settings_path = tmp_path / "settings.json"
    monkeypatch.setattr("pa_agent.config.paths.SETTINGS_JSON_PATH", settings_path)
    app = FastAPI()
    app.include_router(settings_api.router, prefix="/api")
    with TestClient(app) as c:
        yield c, settings_path


def test_get_provider_never_echoes_plaintext_key(client):
    c, settings_path = client
    settings = load_settings(settings_path)
    settings.provider.api_key = "sk-super-secret-value-123456"
    settings.provider.api_key_encrypted = "legacy-cipher-blob"
    from pa_agent.config.settings import save_settings

    save_settings(settings, settings_path)

    resp = c.get("/api/settings/provider")
    assert resp.status_code == 200
    body = resp.json()
    assert "api_key" not in body
    assert "api_key_encrypted" not in body
    assert "sk-super-secret-value-123456" not in json.dumps(body)
    assert body["api_key_masked"].endswith("3456")
    assert body["api_key_set"] is True


def test_put_provider_with_null_api_key_leaves_value_unchanged(client):
    c, settings_path = client
    settings = load_settings(settings_path)
    settings.provider.api_key = "sk-existing-key-abcd"
    from pa_agent.config.settings import save_settings

    save_settings(settings, settings_path)

    resp = c.put("/api/settings/provider", json={"model": "deepseek-chat", "api_key": None})
    assert resp.status_code == 200
    assert resp.json()["model"] == "deepseek-chat"

    reloaded = load_settings(settings_path)
    assert reloaded.provider.api_key == "sk-existing-key-abcd"
    assert reloaded.provider.model == "deepseek-chat"


def test_put_provider_empty_string_clears_api_key(client):
    c, settings_path = client
    settings = load_settings(settings_path)
    settings.provider.api_key = "sk-existing-key-abcd"
    from pa_agent.config.settings import save_settings

    save_settings(settings, settings_path)

    resp = c.put("/api/settings/provider", json={"api_key": ""})
    assert resp.status_code == 200
    reloaded = load_settings(settings_path)
    assert reloaded.provider.api_key == ""


def test_general_section_roundtrip(client):
    c, _ = client
    resp = c.get("/api/settings/general")
    assert resp.status_code == 200
    assert "analysis_bar_count" in resp.json()

    resp = c.put("/api/settings/general", json={"analysis_bar_count": 250})
    assert resp.status_code == 200
    assert resp.json()["analysis_bar_count"] == 250


def test_feishu_and_pushplus_secrets_masked(client):
    c, settings_path = client
    settings = load_settings(settings_path)
    settings.feishu.secret = "feishu-secret-value"
    settings.pushplus.token = "pushplus-token-value"
    from pa_agent.config.settings import save_settings

    save_settings(settings, settings_path)

    feishu_body = c.get("/api/settings/feishu").json()
    assert "feishu-secret-value" not in json.dumps(feishu_body)
    assert feishu_body["secret_set"] is True

    pushplus_body = c.get("/api/settings/pushplus").json()
    assert "pushplus-token-value" not in json.dumps(pushplus_body)
    assert pushplus_body["token_set"] is True


def test_okx_secrets_masked_and_roundtrip(client):
    c, settings_path = client
    resp = c.get("/api/settings/okx")
    assert resp.status_code == 200
    body = resp.json()
    assert body["api_key_set"] is False

    resp = c.put(
        "/api/settings/okx",
        json={"api_key": "okx-key-value", "api_secret": "okx-secret-value", "passphrase": "okx-pass-value"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "okx-key-value" not in json.dumps(body)
    assert "okx-secret-value" not in json.dumps(body)
    assert body["api_key_set"] is True
    assert body["api_secret_set"] is True
    assert body["passphrase_set"] is True

    from pa_agent.config.settings import load_settings as _load

    reloaded = _load(settings_path)
    assert reloaded.okx.api_key == "okx-key-value"

    # PUT with null leaves existing values unchanged
    resp2 = c.put("/api/settings/okx", json={"api_key": None})
    assert resp2.status_code == 200
    reloaded2 = _load(settings_path)
    assert reloaded2.okx.api_key == "okx-key-value"


def test_unknown_section_404(client):
    c, _ = client
    assert c.get("/api/settings/nope").status_code == 404
    assert c.put("/api/settings/nope", json={}).status_code == 404
