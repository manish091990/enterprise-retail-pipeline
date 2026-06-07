"""
advanced_cleaning_pipeline.py
===============================
Principal Data Engineer & Senior Analytics Architect
-----------------------------------------------------
Production-ready, modular data cleaning pipeline for the
enterprise_retail_raw.csv dataset (55,250 rows).

Fixes 7 specific corporate data anomalies while preserving
all original raw columns. Outputs enterprise_retail_clean.csv.

Usage:
    python3 advanced_cleaning_pipeline.py
    python3 advanced_cleaning_pipeline.py --input ~/Desktop/enterprise_retail_raw.csv
    python3 advanced_cleaning_pipeline.py --input ~/Desktop/enterprise_retail_raw.csv --output ~/Desktop/enterprise_retail_clean.csv
"""

import argparse
import os
import re
import sys
import numpy as np
import pandas as pd
from datetime import datetime

# ---------------------------------------------------------------------------
# Default paths
# ---------------------------------------------------------------------------
DEFAULT_INPUT  = os.path.expanduser("~/Desktop/enterprise_retail_raw.csv")
DEFAULT_OUTPUT = os.path.expanduser("~/Desktop/enterprise_retail_clean.csv")

# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------

def print_banner():
    print()
    print("=" * 65)
    print("   ENTERPRISE RETAIL — ADVANCED DATA CLEANING PIPELINE")
    print("   Principal Data Engineer | Senior Analytics Architect")
    print("=" * 65)
    print(f"   Started  : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 65)
    print()


def print_section(number, title):
    print()
    print(f"  ┌─────────────────────────────────────────────────────────┐")
    print(f"  │  FIX {number} » {title:<51}│")
    print(f"  └─────────────────────────────────────────────────────────┘")


def print_result(label, count, total, note=""):
    pct = (count / total * 100) if total > 0 else 0
    note_str = f"  ↳ {note}" if note else ""
    print(f"    ✔  {label:<35} {count:>6,} rows  ({pct:.2f}%){note_str}")


def print_summary_table(results, total):
    print()
    print("=" * 65)
    print("   PIPELINE SUMMARY — ROWS REPAIRED PER ISSUE")
    print("=" * 65)
    print(f"   {'Issue':<45} {'Rows':>7}  {'%':>6}")
    print("   " + "-" * 60)
    grand = 0
    for label, count in results.items():
        pct = (count / total * 100) if total > 0 else 0
        print(f"   {label:<45} {count:>7,}  {pct:>5.2f}%")
        grand += count
    print("   " + "-" * 60)
    print(f"   {'TOTAL CELLS / FLAGS REPAIRED':<45} {grand:>7,}")
    print("=" * 65)
    print()


# ---------------------------------------------------------------------------
# LOADER
# ---------------------------------------------------------------------------

def load_data(path):
    print(f"  ► Loading dataset from:\n    {path}\n")
    if not os.path.isfile(path):
        print(f"  ✘ ERROR: File not found → {path}")
        sys.exit(1)
    df = pd.read_csv(path, encoding="utf-8", low_memory=False)
    print(f"  ✔  Loaded successfully")
    print(f"     Rows    : {len(df):,}")
    print(f"     Columns : {len(df.columns)}")
    print(f"     Columns : {list(df.columns)}")
    return df


# ---------------------------------------------------------------------------
# FIX 1 — Currency Anomalies
# ---------------------------------------------------------------------------

def fix_currency_anomalies(df):
    """
    Detect UnitPrice values that are 75-80x higher than the median price
    for the same StockCode (item profile). These were accidentally scaled
    to INR without changing the currency label.
    Normalize them back by dividing by the INR-to-GBP rate (≈ 83–90).
    Stores result in 'clean_unit_price' and flags in 'price_anomaly_flag'.
    """
    print_section("1", "Currency Anomalies — UnitPrice Normalization")

    col = "UnitPrice"
    df[col] = pd.to_numeric(df[col], errors="coerce")
    df["clean_unit_price"]    = df[col].copy()
    df["price_anomaly_flag"]  = False

    if "StockCode" not in df.columns:
        print("    ⚠  StockCode column missing — using global median fallback.")
        group_col = None
    else:
        group_col = "StockCode"

    INR_RATE       = 86.5   # midpoint of 83–90 injection range
    OUTLIER_FACTOR = 50     # flag if price > 50x the item's median

    if group_col:
        item_median = df.groupby(group_col)[col].transform("median")
    else:
        item_median = df[col].median()

    # Avoid division by zero — replace 0 medians with global median
    global_median = df[col].median()
    if group_col:
        item_median = item_median.replace(0, global_median).fillna(global_median)

    ratio_mask = (df[col] / item_median) > OUTLIER_FACTOR
    anomaly_mask = ratio_mask & df[col].notna()

    df.loc[anomaly_mask, "clean_unit_price"]   = (df.loc[anomaly_mask, col] / INR_RATE).round(2)
    df.loc[anomaly_mask, "price_anomaly_flag"] = True

    count = anomaly_mask.sum()
    print_result("UnitPrice anomalies normalized", count, len(df),
                 f"divided by INR rate {INR_RATE}")
    return df, count


# ---------------------------------------------------------------------------
# FIX 2 — Negative / Zero Quantities
# ---------------------------------------------------------------------------

def fix_negative_quantities(df):
    """
    Classify Quantity column:
      - Negative  → 'Cancellation/Return'
      - Zero      → 'System Error'
      - Positive  → 'Valid Sale'
    Stores absolute value in 'clean_quantity'.
    Stores classification in 'order_status'.
    """
    print_section("2", "Negative/Zero Quantities — Order Status Classification")

    col = "Quantity"
    df[col] = pd.to_numeric(df[col], errors="coerce")

    neg_mask  = df[col] < 0
    zero_mask = df[col] == 0
    pos_mask  = df[col] > 0

    df["order_status"]  = "Valid Sale"
    df.loc[neg_mask,  "order_status"] = "Cancellation/Return"
    df.loc[zero_mask, "order_status"] = "System Error"

    df["clean_quantity"] = df[col].abs()

    neg_count  = neg_mask.sum()
    zero_count = zero_mask.sum()
    total_fixed = neg_count + zero_count

    print_result("Cancellation/Return (negative qty)", neg_count,  len(df))
    print_result("System Error (zero qty)",            zero_count, len(df))
    print_result("Valid Sale rows (unchanged)",        pos_mask.sum(), len(df))
    return df, total_fixed


# ---------------------------------------------------------------------------
# FIX 3 — Description String Corruptions
# ---------------------------------------------------------------------------

def fix_description_strings(df):
    """
    Clean Description column:
      - Strip leading and trailing whitespace
      - Decode URL-encoded characters (%20 → space, %26 → &, etc.)
      - Remove any residual non-printable characters
    Stores result in 'clean_description'.
    """
    print_section("3", "Description String Corruptions — Text Normalization")

    col = "Description"
    if col not in df.columns:
        print("    ⚠  Description column not found — skipping.")
        df["clean_description"] = np.nan
        return df, 0

    original = df[col].fillna("").astype(str)

    def clean_text(s):
        # URL-decode common encoded characters
        url_map = {
            "%20": " ", "%26": "&", "%2F": "/",
            "%3A": ":", "%3D": "=", "%A0": " ",
            "%2C": ",", "%21": "!", "%27": "'",
        }
        for encoded, decoded in url_map.items():
            s = s.replace(encoded, decoded)
        # Strip leading/trailing whitespace
        s = s.strip()
        # Remove non-printable characters
        s = re.sub(r"[^\x20-\x7E]", "", s)
        return s

    df["clean_description"] = original.apply(clean_text)

    # Count rows where cleaning actually changed the value
    changed_mask = df["clean_description"] != original
    count = changed_mask.sum()

    print_result("Description strings cleaned", count, len(df),
                 "whitespace stripped + URL chars decoded")
    return df, count


# ---------------------------------------------------------------------------
# FIX 4 — Double-Click Duplicates
# ---------------------------------------------------------------------------

def fix_duplicate_rows(df):
    """
    Identify exact transaction duplicates using the combination of:
      CustomerID + InvoiceDate + UnitPrice
    Flags duplicates (all occurrences after the first) in 'is_duplicate'.
    """
    print_section("4", "Double-Click Duplicates — Exact Transaction Flagging")

    key_cols = ["CustomerID", "InvoiceDate", "UnitPrice"]
    available = [c for c in key_cols if c in df.columns]

    if len(available) < 2:
        print(f"    ⚠  Not enough key columns found ({available}) — skipping.")
        df["is_duplicate"] = False
        return df, 0

    df["is_duplicate"] = df.duplicated(subset=available, keep="first")

    count = df["is_duplicate"].sum()
    print_result("Duplicate rows flagged", count, len(df),
                 f"keys used: {available}")
    return df, count


# ---------------------------------------------------------------------------
# FIX 5 — Location Inconsistencies
# ---------------------------------------------------------------------------

def fix_location_inconsistencies(df):
    """
    Standardize all UK country name variants into 'United Kingdom'.
    Variants handled: 'UK', 'U.K.', 'Great Britain', 'united kingdom' (any case).
    Stores result in 'standardized_country'.
    """
    print_section("5", "Location Inconsistencies — Country Standardization")

    col = "Country"
    if col not in df.columns:
        print("    ⚠  Country column not found — skipping.")
        df["standardized_country"] = np.nan
        return df, 0

    df["standardized_country"] = df[col].astype(str).str.strip()

    uk_variants_pattern = re.compile(
        r"^(uk|u\.k\.|great britain|united kingdom)$",
        re.IGNORECASE
    )

    uk_mask = df["standardized_country"].str.match(uk_variants_pattern, na=False)
    df.loc[uk_mask, "standardized_country"] = "United Kingdom"

    count = uk_mask.sum()
    non_uk_standardized = (~uk_mask).sum()
    print_result("UK variants → 'United Kingdom'", count, len(df),
                 "UK / U.K. / Great Britain all unified")
    print(f"    ℹ  Non-UK country rows preserved as-is : {non_uk_standardized:,}")
    return df, count


# ---------------------------------------------------------------------------
# FIX 6 — Future Timestamps
# ---------------------------------------------------------------------------

def fix_future_timestamps(df):
    """
    Parse InvoiceDate to datetime.
    Any row where year > 2023 (reasonable max for this retail dataset)
    is treated as a clock sync error.
    Strategy: roll back exactly 1 year. If still > 2023, set to NaT.
    Stores result in 'clean_invoice_date'.
    """
    print_section("6", "Future Timestamps — Clock Sync Error Correction")

    col = "InvoiceDate"
    if col not in df.columns:
        print("    ⚠  InvoiceDate column not found — skipping.")
        df["clean_invoice_date"] = pd.NaT
        return df, 0

    df["clean_invoice_date"] = pd.to_datetime(
        df[col], dayfirst=True, errors="coerce"
    )

    MAX_VALID_YEAR = 2023
    future_mask = df["clean_invoice_date"].dt.year > MAX_VALID_YEAR

    future_count = future_mask.sum()

    # Roll back 1 year for future timestamps
    df.loc[future_mask, "clean_invoice_date"] = (
        df.loc[future_mask, "clean_invoice_date"] - pd.DateOffset(years=1)
    )

    # If still in the future after rollback, set to NaT
    still_future = df["clean_invoice_date"].dt.year > MAX_VALID_YEAR
    df.loc[still_future, "clean_invoice_date"] = pd.NaT
    nat_count = still_future.sum()

    print_result("Future timestamps rolled back 1 year",
                 future_count - nat_count, len(df))
    print_result("Timestamps set to NaT (still invalid after rollback)",
                 nat_count, len(df))
    print(f"    ℹ  Max valid year threshold set to     : {MAX_VALID_YEAR}")
    return df, future_count


# ---------------------------------------------------------------------------
# FIX 7 — CustomerID Pollutants
# ---------------------------------------------------------------------------

def fix_customer_id_pollutants(df):
    """
    Scan CustomerID for string pollutants:
      'NaN', 'NULL', 'unknown', '', 'nan', 'null', 'none', 'None'
    Convert all of these to actual np.nan (system missing value).
    Stores result in 'cleaned_customer_id'.
    """
    print_section("7", "CustomerID Pollutants — Missing Value Standardization")

    col = "CustomerID"
    if col not in df.columns:
        print("    ⚠  CustomerID column not found — skipping.")
        df["cleaned_customer_id"] = np.nan
        return df, 0

    df["cleaned_customer_id"] = df[col].astype(str).str.strip()

    POLLUTANTS = {"nan", "null", "unknown", "none", "na", "n/a", "", "0"}

    pollutant_mask = df["cleaned_customer_id"].str.lower().isin(POLLUTANTS)
    df.loc[pollutant_mask, "cleaned_customer_id"] = np.nan

    # Also convert numeric-looking IDs back to clean format
    valid_mask = ~pollutant_mask
    df.loc[valid_mask, "cleaned_customer_id"] = (
        df.loc[valid_mask, "cleaned_customer_id"]
        .str.replace(r"\.0$", "", regex=True)  # remove trailing .0 from floats
        .str.strip()
    )

    count = pollutant_mask.sum()
    valid_count = valid_mask.sum()

    print_result("CustomerID pollutants → np.nan", count, len(df),
                 "NaN / NULL / unknown / empty all unified")
    print(f"    ℹ  Valid CustomerID rows preserved      : {valid_count:,}")
    return df, count


# ---------------------------------------------------------------------------
# EXPORTER
# ---------------------------------------------------------------------------

def export_data(df, path):
    print()
    print("  ► Exporting cleaned dataset ...")
    df.to_csv(path, index=False, encoding="utf-8")
    size_mb = os.path.getsize(path) / (1024 * 1024)
    print(f"  ✔  File saved successfully")
    print(f"     Path    : {path}")
    print(f"     Rows    : {len(df):,}")
    print(f"     Columns : {len(df.columns)}")
    print(f"     Size    : {size_mb:.2f} MB")


# ---------------------------------------------------------------------------
# COLUMN INVENTORY
# ---------------------------------------------------------------------------

def print_column_inventory(df):
    print()
    print("  ► New columns added by this pipeline:")
    new_cols = [
        ("clean_unit_price",     "FIX 1 — Normalized UnitPrice (INR anomalies corrected)"),
        ("price_anomaly_flag",   "FIX 1 — True if row had a currency anomaly"),
        ("clean_quantity",       "FIX 2 — Absolute value of Quantity"),
        ("order_status",         "FIX 2 — Valid Sale / Cancellation/Return / System Error"),
        ("clean_description",    "FIX 3 — Stripped and URL-decoded Description"),
        ("is_duplicate",         "FIX 4 — True if row is a downstream duplicate"),
        ("standardized_country", "FIX 5 — Unified country name (UK variants → United Kingdom)"),
        ("clean_invoice_date",   "FIX 6 — Parsed datetime (future dates rolled back or NaT)"),
        ("cleaned_customer_id",  "FIX 7 — CustomerID with pollutants replaced by np.nan"),
    ]
    for col, desc in new_cols:
        exists = "✔" if col in df.columns else "✘"
        print(f"    {exists}  {col:<28}  {desc}")


# ---------------------------------------------------------------------------
# MAIN PIPELINE
# ---------------------------------------------------------------------------

def main(input_path, output_path):
    print_banner()

    # Load
    df = load_data(input_path)
    total_rows = len(df)
    repair_log = {}

    # Run all 7 fixers
    df, c1 = fix_currency_anomalies(df)
    repair_log["Fix 1 — Currency Anomalies (UnitPrice)"] = c1

    df, c2 = fix_negative_quantities(df)
    repair_log["Fix 2 — Negative/Zero Quantities"] = c2

    df, c3 = fix_description_strings(df)
    repair_log["Fix 3 — Description String Corruptions"] = c3

    df, c4 = fix_duplicate_rows(df)
    repair_log["Fix 4 — Double-Click Duplicates Flagged"] = c4

    df, c5 = fix_location_inconsistencies(df)
    repair_log["Fix 5 — Location Inconsistencies (UK)"] = c5

    df, c6 = fix_future_timestamps(df)
    repair_log["Fix 6 — Future Timestamps Corrected"] = c6

    df, c7 = fix_customer_id_pollutants(df)
    repair_log["Fix 7 — CustomerID Pollutants → NaN"] = c7

    # Column inventory
    print_column_inventory(df)

    # Export
    export_data(df, output_path)

    # Final summary table
    print_summary_table(repair_log, total_rows)

    print(f"  Pipeline completed at : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Output file ready     : {output_path}")
    print()
    print("=" * 65)
    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Advanced Data Cleaning Pipeline — Enterprise Retail Dataset"
    )
    parser.add_argument(
        "--input", "-i",
        default=DEFAULT_INPUT,
        help=f"Path to raw CSV (default: {DEFAULT_INPUT})",
    )
    parser.add_argument(
        "--output", "-o",
        default=DEFAULT_OUTPUT,
        help=f"Path for cleaned CSV output (default: {DEFAULT_OUTPUT})",
    )
    args = parser.parse_args()

    try:
        main(
            input_path=os.path.expanduser(args.input),
            output_path=os.path.expanduser(args.output),
        )
    except KeyboardInterrupt:
        print("\n  ✘ Pipeline interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n  ✘ Unexpected error: {e}")
        raise
