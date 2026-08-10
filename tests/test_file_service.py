import os
import tempfile

import msgspec
import pandas as pd
import pytest

from services.file_service import (
    FileValidationError,
    df_to_csv_bytes,
    get_data_summary,
    load_dataframe,
    validate_file,
)


def test_validate_file_invalid_extension():
    with tempfile.NamedTemporaryFile(suffix=".xyz", delete=False) as f:
        f.write(b"some content")
        temp_name = f.name

    try:
        with pytest.raises(FileValidationError) as excinfo:
            validate_file(temp_name)
        assert "Unsupported file type" in str(excinfo.value)
    finally:
        os.remove(temp_name)


def test_validate_file_empty():
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
        temp_name = f.name

    try:
        with pytest.raises(FileValidationError) as excinfo:
            validate_file(temp_name)
        assert "empty" in str(excinfo.value).lower()
    finally:
        os.remove(temp_name)


def test_load_dataframe_csv_success():
    with tempfile.NamedTemporaryFile(
        suffix=".csv", delete=False, mode="w", newline=""
    ) as f:
        f.write("A,B\n1,2\n3,4")
        temp_name = f.name

    try:
        df = load_dataframe(temp_name)
        assert len(df) == 2
        assert list(df.columns) == ["A", "B"]
    finally:
        os.remove(temp_name)


def test_load_dataframe_json_success():
    data = [{"X": 10, "Y": 20}, {"X": 30, "Y": 40}]
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="wb") as f:
        f.write(msgspec.json.encode(data))
        temp_name = f.name

    try:
        df = load_dataframe(temp_name)
        assert len(df) == 2
        assert list(df.columns) == ["X", "Y"]
    finally:
        os.remove(temp_name)


def test_load_dataframe_xml_success():
    xml_data = (
        "<data><row><X>100</X><Y>200</Y></row><row><X>300</X><Y>400</Y></row></data>"
    )
    with tempfile.NamedTemporaryFile(suffix=".xml", delete=False, mode="w") as f:
        f.write(xml_data)
        temp_name = f.name

    try:
        df = load_dataframe(temp_name)
        assert len(df) == 2
        assert list(df.columns) == ["X", "Y"]
        assert df.iloc[0]["X"] == 100
    finally:
        os.remove(temp_name)


def test_load_dataframe_stata_success():
    df_orig = pd.DataFrame({"X": [10, 30], "Y": [20, 40]})
    with tempfile.NamedTemporaryFile(suffix=".dta", delete=False) as f:
        temp_name = f.name

    try:
        df_orig.to_stata(temp_name, write_index=False)
        df = load_dataframe(temp_name)
        assert len(df) == 2
        assert list(df.columns) == ["X", "Y"]
        assert df.iloc[0]["X"] == 10
    finally:
        os.remove(temp_name)


def test_load_dataframe_tsv_success():
    tsv_data = "X\tY\n1000\t2000\n3000\t4000\n"
    with tempfile.NamedTemporaryFile(suffix=".tsv", delete=False, mode="w") as f:
        f.write(tsv_data)
        temp_name = f.name

    try:
        df = load_dataframe(temp_name)
        assert len(df) == 2
        assert list(df.columns) == ["X", "Y"]
        assert df.iloc[0]["X"] == 1000
    finally:
        os.remove(temp_name)


def test_load_dataframe_zip_success():
    import zipfile

    csv_data = "X,Y\n5,6\n7,8\n"

    # Write a zip archive containing a CSV file
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
        temp_name = f.name

    csv_temp_path = temp_name + ".csv"
    with open(csv_temp_path, "w") as f_csv:
        f_csv.write(csv_data)

    try:
        with zipfile.ZipFile(temp_name, "w") as zf:
            zf.write(csv_temp_path, arcname="dataset.csv")

        df = load_dataframe(temp_name)
        assert len(df) == 2
        assert list(df.columns) == ["X", "Y"]
        assert df.iloc[0]["X"] == 5
    finally:
        os.remove(temp_name)
        if os.path.exists(csv_temp_path):
            os.remove(csv_temp_path)


def test_load_dataframe_pickle_success():
    df_orig = pd.DataFrame({"X": [99, 101], "Y": [88, 77]})
    with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as f:
        temp_name = f.name

    try:
        df_orig.to_pickle(temp_name)
        df = load_dataframe(temp_name)
        assert len(df) == 2
        assert list(df.columns) == ["X", "Y"]
        assert df.iloc[0]["X"] == 99
    finally:
        os.remove(temp_name)


def test_get_data_summary():
    df = pd.DataFrame(
        {"Num": [1.5, 2.5, 3.5, None], "Cat": ["apple", "banana", "apple", "cherry"]}
    )

    summary = get_data_summary(df)
    assert summary["shape"] == {"rows": 4, "columns": 2}
    assert summary["columns"]["Num"] == "float64"
    assert summary["columns"]["Cat"] in {"object", "str"}
    assert summary["nulls"] == {"Num": 1, "Cat": 0}
    assert "Num" in summary["describe"]
    assert len(summary["head"]) == 4


def test_df_to_csv_bytes():
    df = pd.DataFrame({"A": [1, 2]})
    res = df_to_csv_bytes(df)
    assert isinstance(res, bytes)
    assert b"A\n1\n2\n" in res or b"A\r\n1\r\n2\r\n" in res
