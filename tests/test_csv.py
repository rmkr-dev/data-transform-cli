from data_transform.csv_io import escape_csv_field, parse_csv, parse_csv_rows, stringify_csv


def test_escape_csv_field_quotes_special_characters():
    assert escape_csv_field("plain") == "plain"
    assert escape_csv_field("a,b") == '"a,b"'
    assert escape_csv_field('say "hi"') == '"say ""hi"""'
    assert escape_csv_field("a\nb") == '"a\nb"'
    assert escape_csv_field(None) == ""


def test_parses_quoted_commas_and_newlines(fixture_text):
    rows = parse_csv(fixture_text("sample.csv"))
    assert len(rows) == 2
    assert rows[0]["name"] == "alpha"
    assert rows[0]["note"] == "hello, world"
    assert rows[1]["note"] == "line1\nline2"


def test_round_trips_object_rows():
    data = [
        {"id": "1", "name": "alpha", "note": "hello, world"},
        {"id": "2", "name": "beta", "note": "line1\nline2"},
    ]
    csv_text = stringify_csv(data)
    parsed = parse_csv(csv_text)
    assert parsed == data


def test_parses_raw_rows_without_header():
    rows = parse_csv_rows("a,b\n1,2\n")
    assert rows == [
        ["a", "b"],
        ["1", "2"],
    ]


def test_handles_empty_input():
    assert parse_csv("") == []
    assert stringify_csv([]) == ""
