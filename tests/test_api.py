"""
Run with: pytest -v
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check():
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# ---------- JSON ----------

def test_format_json_valid():
    messy = '{"b":2,"a":1,"nested":{"x":[1,2,3]}}'
    r = client.post("/api/v1/format/json", data={"raw_text": messy, "sort_keys": "true"})
    assert r.status_code == 200
    body = r.json()
    assert body["is_valid"] is True
    assert '"a": 1' in body["formatted_content"]
    # sort_keys=true should put "a" before "b" and "nested"
    assert body["formatted_content"].index('"a"') < body["formatted_content"].index('"b"')
    assert body["stats"]["root_type"] == "object"


def test_format_json_invalid_reports_location():
    broken = '{"a": 1, "b": }'
    r = client.post("/api/v1/format/json", data={"raw_text": broken})
    assert r.status_code == 200
    body = r.json()
    assert body["is_valid"] is False
    assert body["error"] is not None
    assert "line" in body["error"]


def test_format_json_minify():
    messy = '{\n  "a": 1,\n  "b": 2\n}'
    r = client.post("/api/v1/format/json", data={"raw_text": messy, "minify": "true"})
    body = r.json()
    assert body["formatted_content"] == '{"a":1,"b":2}'


# ---------- CSV ----------

def test_format_csv_aligned():
    csv_text = "name,age,city\nAlice,30,NYC\nBob,25,LA"
    r = client.post("/api/v1/format/csv", data={"raw_text": csv_text, "output_style": "aligned"})
    assert r.status_code == 200
    body = r.json()
    assert body["is_valid"] is True
    assert body["stats"]["delimiter_detected"] == ","
    assert body["stats"]["row_count"] == 2
    assert body["stats"]["column_count"] == 3
    assert len(body["preview_records"]) == 2
    assert body["preview_records"][0]["name"] == "Alice"


def test_format_csv_markdown():
    csv_text = "name,age\nAlice,30"
    r = client.post("/api/v1/format/csv", data={"raw_text": csv_text, "output_style": "markdown"})
    body = r.json()
    assert body["formatted_content"].startswith("| name | age |")
    assert "| --- | --- |" in body["formatted_content"]


def test_format_csv_detects_mismatched_rows():
    csv_text = "a,b,c\n1,2,3\n4,5\n6,7,8,9"
    r = client.post("/api/v1/format/csv", data={"raw_text": csv_text})
    body = r.json()
    assert body["stats"]["mismatched_rows"] == [3, 4]


def test_format_csv_tab_delimiter_autodetect():
    tsv_text = "name\tage\nAlice\t30\nBob\t25"
    r = client.post("/api/v1/format/csv", data={"raw_text": tsv_text})
    body = r.json()
    assert body["stats"]["delimiter_detected"] == "\t"


def test_format_csv_invalid_output_style_rejected():
    r = client.post(
        "/api/v1/format/csv",
        data={"raw_text": "a,b\n1,2", "output_style": "yaml"},
    )
    assert r.status_code == 400
    assert r.json()["code"] == "invalid_output_style"


# ---------- Text ----------

def test_format_text_collapses_blank_lines_and_trims_trailing_ws():
    messy = "Hello world   \n\n\n\nSecond line\t\n\n\nThird"
    r = client.post(
        "/api/v1/format/text",
        data={"raw_text": messy, "max_consecutive_blank_lines": "1"},
    )
    body = r.json()
    formatted = body["formatted_content"]
    assert "\n\n\n" not in formatted
    assert "   \n" not in formatted


def test_format_text_wrap_width():
    long_line = "word " * 30
    r = client.post(
        "/api/v1/format/text", data={"raw_text": long_line, "wrap_width": "20"}
    )
    body = r.json()
    for line in body["formatted_content"].splitlines():
        assert len(line) <= 20


# ---------- Auto detect ----------

def test_auto_detects_json():
    r = client.post("/api/v1/format/auto", data={"raw_text": '{"a": 1}'})
    assert r.json()["detected_format"] == "json"


def test_auto_detects_csv():
    r = client.post(
        "/api/v1/format/auto",
        data={"raw_text": "a,b,c\n1,2,3\n4,5,6\n7,8,9"},
    )
    assert r.json()["detected_format"] == "csv"


def test_auto_detects_text():
    r = client.post(
        "/api/v1/format/auto", data={"raw_text": "Just some plain prose, nothing structured here."}
    )
    assert r.json()["detected_format"] == "text"


def test_auto_detects_json_from_filename():
    r = client.post(
        "/api/v1/format/auto",
        files={"file": ("data.json", b'{"a": 1}', "application/json")},
    )
    body = r.json()
    assert body["detected_format"] == "json"
    assert body["filename"] == "data.json"


# ---------- Error handling ----------

def test_no_input_provided_rejected():
    r = client.post("/api/v1/format/json")
    assert r.status_code == 400
    assert r.json()["code"] == "no_input_provided"


def test_empty_raw_text_rejected():
    r = client.post("/api/v1/format/json", data={"raw_text": ""})
    assert r.status_code == 400


# ---------- Unified Endpoint ----------

def test_unified_format_auto_json():
    r = client.post("/api/v1/format", data={"raw_text": '{"b":2,"a":1}', "format": "auto"})
    assert r.status_code == 200
    body = r.json()
    assert body["detected_format"] == "json"
    assert '"a": 1' in body["formatted_content"]

def test_unified_format_explicit_json():
    # Even if it is valid json, force it to json
    r = client.post("/api/v1/format", data={"raw_text": '{"b":2,"a":1}', "format": "json"})
    assert r.status_code == 200
    body = r.json()
    assert body["detected_format"] == "json"
    # default JSON formatting shouldn't sort keys (which is default behavior)
    assert '"b": 2' in body["formatted_content"]

def test_unified_format_explicit_csv():
    r = client.post("/api/v1/format", data={"raw_text": "col1,col2\nval1,val2", "format": "csv"})
    assert r.status_code == 200
    body = r.json()
    assert body["detected_format"] == "csv"
    assert "col1" in body["formatted_content"]

def test_unified_format_explicit_text():
    r = client.post("/api/v1/format", data={"raw_text": "hello   \nworld", "format": "text"})
    assert r.status_code == 200
    body = r.json()
    assert body["detected_format"] == "text"
    # text formatting by default strips trailing spaces
    assert "hello\nworld" in body["formatted_content"]

def test_unified_format_invalid_option():
    r = client.post("/api/v1/format", data={"raw_text": "hello", "format": "invalid_format"})
    assert r.status_code == 400
    assert r.json()["code"] == "invalid_format_option"

def test_unified_format_json_with_options():
    r = client.post(
        "/api/v1/format",
        data={
            "raw_text": '{"b":2,"a":1}',
            "format": "json",
            "sort_keys": "true",
            "minify": "true"
        }
    )
    assert r.status_code == 200
    assert r.json()["formatted_content"] == '{"a":1,"b":2}'

def test_unified_format_csv_with_options():
    r = client.post(
        "/api/v1/format",
        data={
            "raw_text": "col1,col2\nval1,val2",
            "format": "csv",
            "output_style": "markdown"
        }
    )
    assert r.status_code == 200
    assert r.json()["formatted_content"].startswith("| col1 | col2 |")

def test_unified_format_text_with_options():
    r = client.post(
        "/api/v1/format",
        data={
            "raw_text": "this is a very long line that should wrap",
            "format": "text",
            "wrap_width": "10"
        }
    )
    assert r.status_code == 200
    for line in r.json()["formatted_content"].splitlines():
        assert len(line) <= 10


if __name__ == "__main__":
    import sys
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
