"""Download the fixed 5,000-row Maryland CMS sample used by the notebook."""

from __future__ import annotations

import json
import sys
from http.client import HTTPException
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd


ENDPOINT = (
    "https://data.cms.gov/data-api/v1/dataset/"
    "92396110-2aed-4d63-a6a2-5d6207d46a29/data"
)
FIELDS = [
    "Rndrng_NPI",
    "Rndrng_Prvdr_State_Abrvtn",
    "Rndrng_Prvdr_Type",
    "Place_Of_Srvc",
    "Tot_Benes",
    "Tot_Srvcs",
    "Tot_Bene_Day_Srvcs",
    "Avg_Sbmtd_Chrg",
    "Avg_Mdcr_Alowd_Amt",
    "Avg_Mdcr_Pymt_Amt",
    "Avg_Mdcr_Stdzd_Amt",
]
NUMERIC_FIELDS = FIELDS[4:]
STATE_FIELD = "Rndrng_Prvdr_State_Abrvtn"
EXPECTED_MD_ROWS = 228_520
BLOCK_SIZE = 1_000
OFFSETS = (0, 45_000, 90_000, 135_000, 180_000)
TIMEOUT_SECONDS = 60
OUTPUT_PATH = Path(__file__).resolve().parent / "data" / "cms_md_2024_sample.csv"


def build_url(base_url: str, params: list[tuple[str, str]]) -> str:
    """Build a CMS API URL while preserving its bracketed parameter names."""
    return f"{base_url}?{urlencode(params)}"


def fetch_json(url: str) -> object:
    request = Request(url, headers={"Accept": "application/json"})
    with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        return json.loads(response.read())


def parse_found_rows(payload: object) -> int:
    if not isinstance(payload, dict) or "found_rows" not in payload:
        raise ValueError("CMS stats response is missing found_rows")
    try:
        return int(payload["found_rows"])
    except (TypeError, ValueError) as exc:
        raise ValueError("CMS stats response has an invalid found_rows value") from exc


def validate_block(payload: object, offset: int) -> pd.DataFrame:
    """Check one response block and convert the requested numeric fields."""
    if not isinstance(payload, list) or len(payload) != BLOCK_SIZE:
        received = len(payload) if isinstance(payload, list) else "non-list"
        raise ValueError(f"Offset {offset}: expected 1000 records, received {received}")
    if any(not isinstance(row, dict) for row in payload):
        raise ValueError(f"Offset {offset}: response contains a non-object record")

    expected = set(FIELDS)
    for row_number, row in enumerate(payload):
        if set(row) != expected:
            raise ValueError(f"Offset {offset}, row {row_number}: field names do not match")
        if row[STATE_FIELD] != "MD":
            raise ValueError(f"Offset {offset}, row {row_number}: state is not MD")

    frame = pd.DataFrame(payload, columns=FIELDS)
    frame = frame.replace(r"^\s*$", pd.NA, regex=True)
    frame["Rndrng_NPI"] = frame["Rndrng_NPI"].astype("string")
    for field in NUMERIC_FIELDS:
        original = frame[field]
        converted = pd.to_numeric(original, errors="coerce")
        failures = int((original.notna() & converted.isna()).sum())
        if failures:
            raise ValueError(f"Offset {offset}: {failures} numeric conversion failures in {field}")
        frame[field] = converted
    return frame


def main() -> int:
    if OUTPUT_PATH.exists():
        print(f"Sample already exists; leaving it unchanged: {OUTPUT_PATH}")
        return 0

    stats_url = build_url(
        f"{ENDPOINT}/stats", [(f"filter[{STATE_FIELD}]", "MD")]
    )
    try:
        found_rows = parse_found_rows(fetch_json(stats_url))
        print(f"Maryland rows reported by CMS: {found_rows:,}")
        if found_rows != EXPECTED_MD_ROWS:
            raise ValueError(
                f"CMS Maryland row count changed (expected {EXPECTED_MD_ROWS:,}, "
                f"received {found_rows:,}); stopping without changing the sampling plan."
            )

        blocks = []
        for offset in OFFSETS:
            params = [
                ("column", ",".join(FIELDS)),
                (f"filter[{STATE_FIELD}]", "MD"),
                ("sort", "Rndrng_NPI"),
                ("size", str(BLOCK_SIZE)),
                ("offset", str(offset)),
            ]
            block = validate_block(fetch_json(build_url(ENDPOINT, params)), offset)
            block["sample_offset_block"] = offset
            blocks.append(block)

        sample = pd.concat(blocks, ignore_index=True)
        if len(sample) != 5_000 or not sample[STATE_FIELD].eq("MD").all():
            raise ValueError("Combined sample failed row-count or Maryland validation")
        if sample["sample_offset_block"].value_counts().to_dict() != {
            offset: BLOCK_SIZE for offset in OFFSETS
        }:
            raise ValueError("Combined sample failed offset-block validation")

        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with OUTPUT_PATH.open("x", encoding="utf-8", newline="") as output_file:
            sample.to_csv(output_file, index=False)
    except FileExistsError:
        print(f"Sample appeared before saving; leaving it unchanged: {OUTPUT_PATH}")
        return 0
    except HTTPError as exc:
        print(f"CMS HTTP error: {exc.code} {exc.reason}", file=sys.stderr)
        return 1
    except (URLError, TimeoutError, HTTPException, json.JSONDecodeError, UnicodeDecodeError) as exc:
        print(f"CMS request or JSON error: {exc}", file=sys.stderr)
        return 1
    except (OSError, ValueError) as exc:
        print(f"Download stopped: {exc}", file=sys.stderr)
        return 1

    print(f"Rows saved: {len(sample):,}")
    print(f"Distinct NPIs: {sample['Rndrng_NPI'].nunique(dropna=True):,}")
    print(f"Field count: {len(sample.columns)}")
    print(
        "Method: five 1,000-row Maryland-filtered blocks, sorted by NPI, "
        f"at offsets {list(OFFSETS)}. Ties in sort order or later CMS changes "
        "may affect exact sample reproduction."
    )
    print(f"Saved: {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
