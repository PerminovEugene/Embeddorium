"""Tests for GET /chunkers.

No DB/broker involved — the route only reads the in-process plugin registry.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.server.chunkers.router import router

_app = FastAPI()
_app.include_router(router)
client = TestClient(_app)


def test_list_chunkers_returns_builtins_with_camelcase_body():
    resp = client.get("/chunkers")
    assert resp.status_code == 200, resp.text

    body = resp.json()
    by_name = {entry["name"]: entry for entry in body}

    assert {
        "text_markdown",
        "text_section",
        "text_recursive",
        "text_fixed",
        "legal_xml",
    } <= set(by_name)

    markdown = by_name["text_markdown"]
    assert set(markdown) == {"name", "label", "description", "restrictions", "fields"}
    field_keys = {f["key"] for f in markdown["fields"]}
    assert field_keys == {"chunk_size", "chunk_overlap"}

    chunk_size_field = next(
        f for f in markdown["fields"] if f["key"] == "chunk_size"
    )
    # field keys stay snake_case; field-level object keys are camelCase.
    assert set(chunk_size_field) == {
        "key", "label", "type", "default", "min", "max", "options", "placeholder",
    }
    assert chunk_size_field["default"] == 1200
    assert chunk_size_field["min"] == 1


def test_legal_xml_declares_restrictions():
    resp = client.get("/chunkers")
    by_name = {entry["name"]: entry for entry in resp.json()}
    assert by_name["legal_xml"]["restrictions"]


def test_text_section_has_no_configurable_fields():
    resp = client.get("/chunkers")
    by_name = {entry["name"]: entry for entry in resp.json()}
    assert by_name["text_section"]["fields"] == []
