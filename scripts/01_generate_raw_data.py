"""
generate_enterprise_retail_raw.py
==================================
Principal Data Engineer Script
--------------------------------
Reads OnlineRetail.csv, samples 55,000 rows, and intentionally injects
7 real-world enterprise data quality issues to produce
'enterprise_retail_raw.csv'.

Usage:
    python3 generate_enterprise_retail_raw.py
    python3 generate_enterprise_retail_raw.py --input "OnlineRetail.csv"
    python3 generate_enterprise_retail_raw.py --input "OnlineRetail.csv" --seed 99
"""

import argparse
import os
import sys
import logging
import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SAMPLE_SIZE         = 55_000
DUPLICATE_COUNT     = 250
FUTURE_TS_COUNT     = 150
CURRENCY_PCT        = 0.03   # 3%  — UnitPrice INR-scale anomalies
NEGATIVE_QTY_PCT    = 0.02   # 2%  — negative / zero Quantity
STRING_ANOMALY_PCT  = 0.10   # 10% — Description string corruptions
CUSTOMER_POLLUT_PCT = 0.05   # 5%  — CustomerID pollutants
OUTPUT_FILE         = "enterprise_retail_raw.csv"

CANDIDATE_INPUTS    = ["OnlineRetail.csv", "Online Retail.csv", "data.csv"]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def resolve_input_file(hint):
    """Return the first readable CSV path from candidates."""
    candidates = [hint] if hint else CANDIDATE_INPUTS
    for path in candidates:
        if path and os.path.isfile(path):
            log.info("Found input file: %s", path)
            return path
    raise FileNotFoundError(
        "No input file found. Tried: {}\n"
        "Place OnlineRetail.csv in the same folder as this script and re-run.".format(candidates)
    )


def load_and_sample(path, n, seed):
    """Load CSV and sample n rows (with replacement if source is smaller)."""
    log.info("Loading dataset ...")
    df = pd.read_csv(path, encoding="ISO-8859-1", low_memory=False)
    log.info("Source shape: %d rows x %d cols", df.shape[0], df.shape[1])

    replace = len(df) < n
    if replace:
        log.warning(
            "Source has only %d rows — sampling WITH replacement to reach %d.",
            len(df), n,
        )
    sample = df.sample(n=n, replace=replace, random_state=seed).reset_index(drop=True)
    log.info("Sampled %d rows.", len(sample))
    return sample


# ---------------------------------------------------------------------------
# Issue injectors
# ---------------------------------------------------------------------------

def inject_currency_anomalies(df, rng):
    """
    Issue 1 — Currency Issues
    Convert 3% of UnitPrice values to INR scale without changing
    currency notation, creating massive pricing anomalies.
    """
    col = "UnitPrice"
    if col not in df.columns:
        log.warning("Column '%s' not found — skipping currency injection.", col)
        return df

    df[col] = pd.to_numeric(df[col], errors="coerce")
    n_corrupt = int(len(df) * CURRENCY_PCT)
    idx = rng.choice(df.index, size=n_corrupt, replace=False)

    inr_multipliers = rng.uniform(83.0, 90.0, size=n_corrupt)
    df.loc[idx, col] = (df.loc[idx, col] * inr_multipliers).round(2)

    log.info("Issue 1 ok  Currency anomalies injected into %d rows.", n_corrupt)
    return df


def inject_negative_quantities(df, rng):
    """
    Issue 2 — Negative Values
    Force 2% of Quantity rows to negative integers or zero.
    """
    col = "Quantity"
    if col not in df.columns:
        log.warning("Column '%s' not found — skipping negative qty injection.", col)
        return df

    df[col] = pd.to_numeric(df[col], errors="coerce")
    n_corrupt = int(len(df) * NEGATIVE_QTY_PCT)
    idx = rng.choice(df.index, size=n_corrupt, replace=False)

    zero_mask = rng.random(n_corrupt) < 0.25
    values = np.where(zero_mask, 0, -rng.integers(1, 200, size=n_corrupt))
    df.loc[idx, col] = values

    log.info("Issue 2 ok  Negative/zero Quantity injected into %d rows.", n_corrupt)
    return df


def inject_string_anomalies(df, rng):
    """
    Issue 3 — String Anomalies
    Corrupt 10% of Description strings with leading/trailing spaces
    and URL-encoded characters. Safely handles NaN/empty values.
    """
    col = "Description"
    if col not in df.columns:
        log.warning("Column '%s' not found — skipping string anomaly injection.", col)
        return df

    # Fill NaN with empty string first to avoid float len() error
    df[col] = df[col].fillna("").astype(str)

    # Only corrupt rows that actually have content
    has_content = df[col].str.strip() != ""
    eligible_idx = df.index[has_content].to_numpy()

    n_corrupt = int(len(df) * STRING_ANOMALY_PCT)
    n_corrupt = min(n_corrupt, len(eligible_idx))  # can't corrupt more than available
    idx = rng.choice(eligible_idx, size=n_corrupt, replace=False)

    url_tokens = ["%20", "%26", "%2F", "%3A", "%3D"]

    def corrupt_string(s, style):
        if not s or not s.strip():
            return s
        mode = style % 3
        if mode == 0:
            return "  " + s
        elif mode == 1:
            return s + "   "
        else:
            token = url_tokens[style % len(url_tokens)]
            mid = max(1, len(s) // 2)
            return s[:mid] + token + s[mid:]

    styles = rng.integers(0, 6, size=n_corrupt)
    df.loc[idx, col] = [
        corrupt_string(str(df.at[i, col]), int(styles[k]))
        for k, i in enumerate(idx)
    ]

    log.info("Issue 3 ok  String anomalies injected into %d rows.", n_corrupt)
    return df


def inject_duplicate_rows(df, rng):
    """
    Issue 4 — Double-Click Duplicates
    Append 250 identical duplicate rows mimicking payment gateway double-submits.
    """
    idx = rng.choice(df.index, size=DUPLICATE_COUNT, replace=True)
    duplicates = df.loc[idx].copy()
    df = pd.concat([df, duplicates], ignore_index=True)

    log.info("Issue 4 ok  %d duplicate rows appended.", DUPLICATE_COUNT)
    return df


def inject_location_inconsistencies(df, rng):
    """
    Issue 5 — Location Inconsistencies
    Replace United Kingdom entries with mixed-format variants.
    """
    col = "Country"
    if col not in df.columns:
        log.warning("Column '%s' not found — skipping location injection.", col)
        return df

    uk_variants = ["United Kingdom", "UK", "U.K.", "Great Britain"]
    uk_mask = df[col].astype(str).str.strip().str.lower() == "united kingdom"
    uk_idx  = df.index[uk_mask].to_numpy()

    if len(uk_idx) == 0:
        log.warning("No 'United Kingdom' rows found — skipping location injection.")
        return df

    chosen_variants = rng.choice(uk_variants, size=len(uk_idx))
    df.loc[uk_idx, col] = chosen_variants

    unique_counts = pd.Series(chosen_variants).value_counts().to_dict()
    log.info("Issue 5 ok  UK location variants assigned: %s", unique_counts)
    return df


def inject_future_timestamps(df, rng):
    """
    Issue 6 — Future Timestamps
    Corrupt 150 InvoiceDate rows by replacing the year with 2027 or 2030.
    """
    col = "InvoiceDate"
    if col not in df.columns:
        log.warning("Column '%s' not found — skipping future timestamp injection.", col)
        return df

    idx          = rng.choice(df.index, size=FUTURE_TS_COUNT, replace=False)
    future_years = rng.choice([2027, 2030], size=FUTURE_TS_COUNT)

    def replace_year(date_str, year):
        try:
            dt = pd.to_datetime(date_str, dayfirst=True, errors="coerce")
            if pd.isna(dt):
                return date_str
            return dt.replace(year=year).strftime("%d/%m/%Y %H:%M")
        except Exception:
            return date_str

    df.loc[idx, col] = [
        replace_year(str(df.at[i, col]), int(future_years[k]))
        for k, i in enumerate(idx)
    ]

    log.info(
        "Issue 6 ok  Future timestamps injected into %d rows (years: 2027/2030).",
        FUTURE_TS_COUNT,
    )
    return df


def inject_customer_id_pollutants(df, rng):
    """
    Issue 7 — CustomerID Pollutants
    Replace 5% of CustomerIDs with NaN, NULL, unknown, or empty string.
    """
    col = "CustomerID"
    if col not in df.columns:
        log.warning("Column '%s' not found — skipping CustomerID injection.", col)
        return df

    df[col] = df[col].astype(str)
    n_corrupt  = int(len(df) * CUSTOMER_POLLUT_PCT)
    idx        = rng.choice(df.index, size=n_corrupt, replace=False)
    pollutants = ["NaN", "NULL", "unknown", ""]
    chosen     = rng.choice(pollutants, size=n_corrupt)
    df.loc[idx, col] = chosen

    unique_counts = pd.Series(chosen).value_counts().to_dict()
    log.info("Issue 7 ok  CustomerID pollutants injected: %s", unique_counts)
    return df


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def main(input_hint, seed):
    log.info("=" * 60)
    log.info("Enterprise Retail Raw Data Generator")
    log.info("Seed: %d  |  Target rows: %d", seed, SAMPLE_SIZE)
    log.info("=" * 60)

    rng = np.random.default_rng(seed)

    input_path = resolve_input_file(input_hint)
    df = load_and_sample(input_path, SAMPLE_SIZE, seed)

    df = inject_currency_anomalies(df, rng)
    df = inject_negative_quantities(df, rng)
    df = inject_string_anomalies(df, rng)
    df = inject_duplicate_rows(df, rng)
    df = inject_location_inconsistencies(df, rng)
    df = inject_future_timestamps(df, rng)
    df = inject_customer_id_pollutants(df, rng)

    # Shuffle so corruptions are not clustered at predictable offsets
    df = df.sample(frac=1, random_state=seed).reset_index(drop=True)

    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")
    log.info("-" * 60)
    log.info("Output written -> %s", os.path.abspath(OUTPUT_FILE))
    log.info("Final shape    : %d rows x %d columns", df.shape[0], df.shape[1])
    log.info("=" * 60)
    log.info("Data quality issues injected — ready for pipeline validation.")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate enterprise_retail_raw.csv with intentional data issues."
    )
    parser.add_argument(
        "--input", "-i",
        default=None,
        help="Path to source CSV (default: auto-detects OnlineRetail.csv)",
    )
    parser.add_argument(
        "--seed", "-s",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)",
    )
    args = parser.parse_args()

    try:
        main(args.input, args.seed)
    except FileNotFoundError as e:
        log.error("%s", e)
        sys.exit(1)
    except Exception as e:
        log.exception("Unexpected error: %s", e)
        sys.exit(2)
