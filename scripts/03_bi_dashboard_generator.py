"""
bi_dashboard_generator.py
==========================
Principal BI Architect & Senior Data Scientist
-----------------------------------------------
Enterprise-grade visualization and reporting suite.
Generates 9 executive-level BI assets from the clean retail dataset.

Reads all paths and design tokens from config.py.
Saves all charts as 300-DPI PNG files to the project root.

Usage:
    python3 bi_dashboard_generator.py
"""

import os
import sys
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")                          # non-interactive backend for file export
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
from datetime import datetime, timedelta

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Import config
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.expanduser("~/Desktop/retail_project"))
try:
    import config as cfg
except ModuleNotFoundError:
    print("  ✘ config.py not found in ~/Desktop/retail_project")
    print("    Place config.py in that folder and re-run.")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Global matplotlib style
# ---------------------------------------------------------------------------

def apply_corporate_style():
    plt.rcParams.update({
        "figure.facecolor"      : cfg.WHITE,
        "axes.facecolor"        : cfg.LIGHT_GRAY,
        "axes.edgecolor"        : cfg.CHARCOAL,
        "axes.labelcolor"       : cfg.NAVY,
        "axes.titlecolor"       : cfg.NAVY,
        "axes.grid"             : True,
        "grid.color"            : cfg.MID_GRAY,
        "grid.alpha"            : 0.3,
        "grid.linestyle"        : "--",
        "xtick.color"           : cfg.CHARCOAL,
        "ytick.color"           : cfg.CHARCOAL,
        "text.color"            : cfg.NAVY,
        "font.family"           : "DejaVu Sans",
        "font.size"             : 11,
        "axes.titlesize"        : 14,
        "axes.labelsize"        : 12,
        "legend.framealpha"     : 0.9,
        "legend.edgecolor"      : cfg.MID_GRAY,
        "savefig.dpi"           : cfg.DPI,
        "savefig.bbox"          : "tight",
        "savefig.facecolor"     : cfg.WHITE,
    })

# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def fmt_currency(value, symbol=None):
    sym = symbol or cfg.CURRENCY_SYMBOL
    if abs(value) >= 1_000_000:
        return f"{sym}{value/1_000_000:.2f}M"
    elif abs(value) >= 1_000:
        return f"{sym}{value/1_000:.1f}K"
    return f"{sym}{value:,.0f}"


def save_chart(fig, filename):
    path = os.path.join(cfg.OUTPUT_DIR, filename)
    fig.savefig(path, dpi=cfg.DPI, bbox_inches="tight", facecolor=cfg.WHITE)
    plt.close(fig)
    print(f"    ✔  Saved → {path}")


def add_watermark(fig, text="CONFIDENTIAL — EXECUTIVE USE ONLY"):
    fig.text(
        0.99, 0.01, text,
        ha="right", va="bottom",
        fontsize=7, color=cfg.MID_GRAY, alpha=0.6,
        style="italic"
    )


def add_chart_header(fig, title, subtitle=""):
    fig.text(
        0.5, 0.98, title,
        ha="center", va="top",
        fontsize=16, fontweight="bold", color=cfg.NAVY
    )
    if subtitle:
        fig.text(
            0.5, 0.955, subtitle,
            ha="center", va="top",
            fontsize=10, color=cfg.MID_GRAY, style="italic"
        )


def section_banner(number, title):
    print()
    print(f"  ┌{'─'*61}┐")
    print(f"  │  ASSET {number} » {title:<53}│")
    print(f"  └{'─'*61}┘")


# ---------------------------------------------------------------------------
# DATA LOADER & ENRICHMENT
# ---------------------------------------------------------------------------

def load_and_enrich(path):
    print(f"\n  ► Loading clean dataset from:\n    {path}\n")
    if not os.path.isfile(path):
        print(f"  ✘ File not found: {path}")
        sys.exit(1)

    df = pd.read_csv(path, low_memory=False, encoding="utf-8")
    print(f"  ✔  Loaded  {len(df):,} rows × {len(df.columns)} columns")

    # --- Parse date ---
    df[cfg.COL_DATE] = pd.to_datetime(df[cfg.COL_DATE], errors="coerce")
    df = df.dropna(subset=[cfg.COL_DATE])

    # --- Numeric coercion ---
    df[cfg.COL_QTY]   = pd.to_numeric(df[cfg.COL_QTY],   errors="coerce").fillna(0)
    df[cfg.COL_PRICE] = pd.to_numeric(df[cfg.COL_PRICE],  errors="coerce").fillna(0)

    # --- Net Revenue: fallback if column missing ---
    if cfg.COL_REVENUE not in df.columns:
        df[cfg.COL_REVENUE] = df[cfg.COL_QTY] * df[cfg.COL_PRICE]
        print("  ℹ  Net_Revenue column not found — computed as qty × price")

    df[cfg.COL_REVENUE] = pd.to_numeric(df[cfg.COL_REVENUE], errors="coerce").fillna(0)

    # --- Segment fallback ---
    if cfg.COL_SEGMENT not in df.columns:
        seg_map = {
            "United Kingdom": "Corporate", "Germany": "Consumer",
            "France": "Consumer",          "EIRE": "Home Office",
        }
        df[cfg.COL_SEGMENT] = df[cfg.COL_COUNTRY].map(seg_map).fillna("Consumer")
        print("  ℹ  Cleaned_Segment not found — inferred from Country")

    # --- Payment Method fallback ---
    if cfg.COL_PAYMENT not in df.columns:
        rng = np.random.default_rng(42)
        df[cfg.COL_PAYMENT] = rng.choice(
            ["UPI", "Credit Card", "Cash", "Net Banking"],
            size=len(df), p=[0.35, 0.40, 0.15, 0.10]
        )
        print("  ℹ  Payment_Method not found — simulated proportionally")

    # --- Category from description ---
    if "standardized_category" not in df.columns:
        def infer_category(desc):
            d = str(desc).lower()
            if any(k in d for k in ["bag", "box", "case", "tin"]):        return "Packaging"
            if any(k in d for k in ["card", "sign", "print", "poster"]):  return "Stationery"
            if any(k in d for k in ["light", "lamp", "candle", "holder"]): return "Lighting"
            if any(k in d for k in ["set", "kit", "bundle", "pack"]):     return "Bundles"
            if any(k in d for k in ["heart", "love", "gift"]):            return "Gifts"
            return "General"
        df["standardized_category"] = df[cfg.COL_DESC].apply(infer_category)

    # --- Month period for time series ---
    df["month_period"] = df[cfg.COL_DATE].dt.to_period("M")

    # --- Premium tier ---
    price_80 = df[cfg.COL_PRICE].quantile(cfg.PREMIUM_PERCENTILE / 100)
    df["price_tier"] = np.where(df[cfg.COL_PRICE] >= price_80, "Premium", "General")

    # --- Valid sales only subset ---
    df_valid = df[df[cfg.COL_STATUS] == cfg.VALID_SALE_STATUS].copy()

    # --- RFM base (reference date = 1 day after max date) ---
    ref_date = df[cfg.COL_DATE].max() + timedelta(days=1)
    rfm = (
        df_valid[df_valid[cfg.COL_CUSTOMER].notna()]
        .groupby(cfg.COL_CUSTOMER)
        .agg(
            recency  =(cfg.COL_DATE,    lambda x: (ref_date - x.max()).days),
            frequency=(cfg.COL_DATE,    "count"),
            monetary =(cfg.COL_REVENUE, "sum"),
        )
        .reset_index()
    )
    rfm = rfm[rfm["monetary"] > 0]

    print(f"  ✔  Enrichment complete | Valid sales: {len(df_valid):,} | RFM profiles: {len(rfm):,}")
    print(f"  ✔  Premium price threshold (80th pct): {fmt_currency(price_80)}")
    print()
    return df, df_valid, rfm, price_80


# ---------------------------------------------------------------------------
# ASSET 1 — Executive KPI Terminal Dashboard
# ---------------------------------------------------------------------------

def asset_1_executive_kpi(df, df_valid, rfm):
    section_banner("1", "Executive KPI Terminal Dashboard")

    # VIPs: monetary >= threshold AND recency >= inactivity window
    vip = rfm[rfm["monetary"] >= cfg.VIP_SPEND_THRESHOLD]
    inactive_vip = vip[vip["recency"] >= cfg.INACTIVITY_DAYS]

    total_revenue       = df_valid[cfg.COL_REVENUE].sum()
    churn_revenue       = inactive_vip["monetary"].sum()
    churn_pct           = (churn_revenue / total_revenue * 100) if total_revenue else 0
    unique_inactive_vip = len(inactive_vip)
    avg_clv             = rfm["monetary"].mean()
    total_transactions  = len(df_valid)
    cancellations       = (df[cfg.COL_STATUS] == cfg.RETURN_STATUS).sum()
    cancel_rate         = cancellations / len(df) * 100

    width = 66
    bar   = "═" * width

    lines = [
        "",
        f"  ╔{bar}╗",
        f"  ║{'ENTERPRISE RETAIL — EXECUTIVE KPI COMMAND CENTER':^{width}}║",
        f"  ║{'Generated: ' + datetime.now().strftime('%d %b %Y  %H:%M'):^{width}}║",
        f"  ╠{bar}╣",
        f"  ║{'':^{width}}║",
        f"  ║  {'REVENUE AT CHURN RISK':<30}  {fmt_currency(churn_revenue):>12}   ({churn_pct:.1f}% of total)  ║",
        f"  ║  {'TOTAL NET REVENUE (VALID SALES)':<30}  {fmt_currency(total_revenue):>12}{'':>18}║",
        f"  ║  {'TOTAL TRANSACTIONS PROCESSED':<30}  {total_transactions:>12,}{'':>18}║",
        f"  ║{'':^{width}}║",
        f"  ╠{bar}╣",
        f"  ║{'':^{width}}║",
        f"  ║  {'UNIQUE INACTIVE VIP ACCOUNTS':<30}  {unique_inactive_vip:>12,}   (>{cfg.INACTIVITY_DAYS}d silent)    ║",
        f"  ║  {'VIP QUALIFICATION THRESHOLD':<30}  {fmt_currency(cfg.VIP_SPEND_THRESHOLD):>12}   (min lifetime)   ║",
        f"  ║  {'AVG CUSTOMER HISTORICAL VALUE':<30}  {fmt_currency(avg_clv):>12}{'':>18}║",
        f"  ║{'':^{width}}║",
        f"  ╠{bar}╣",
        f"  ║{'':^{width}}║",
        f"  ║  {'CANCELLATION / RETURN RATE':<30}  {cancel_rate:>11.2f}%   ({cancellations:,} orders)   ║",
        f"  ║  {'RFM PROFILES ANALYZED':<30}  {len(rfm):>12,}{'':>18}║",
        f"  ║{'':^{width}}║",
        f"  ╚{bar}╝",
        "",
    ]
    for line in lines:
        print(line)

    print(f"    ✔  KPI dashboard printed to terminal")
    return {
        "churn_revenue": churn_revenue,
        "inactive_vip": inactive_vip,
        "total_revenue": total_revenue,
        "avg_clv": avg_clv,
    }


# ---------------------------------------------------------------------------
# ASSET 2 — Customer Defection Landscape (RFM Scatter)
# ---------------------------------------------------------------------------

def asset_2_defection_scatter(rfm, kpis):
    section_banner("2", "Customer Defection Landscape — RFM Scatter")

    med_recency  = rfm["recency"].median()
    med_monetary = rfm["monetary"].median()

    fig, ax = plt.subplots(figsize=cfg.FIG_SIZE_WIDE)
    fig.patch.set_facecolor(cfg.WHITE)

    # Color by churn risk
    colors = np.where(
        (rfm["recency"] >= cfg.INACTIVITY_DAYS) & (rfm["monetary"] >= cfg.VIP_SPEND_THRESHOLD),
        cfg.ALERT_RED,
        np.where(rfm["recency"] >= cfg.INACTIVITY_DAYS, "#E67E22", cfg.SLATE)
    )
    sizes = np.clip(rfm["monetary"] / rfm["monetary"].max() * 300, 10, 300)

    sc = ax.scatter(
        rfm["recency"], rfm["monetary"],
        c=colors, s=sizes, alpha=0.65,
        edgecolors=cfg.CHARCOAL, linewidths=0.3, zorder=3
    )

    # Quadrant lines
    ax.axvline(med_recency,  color=cfg.CHARCOAL, lw=1.2, ls="--", alpha=0.6)
    ax.axhline(med_monetary, color=cfg.CHARCOAL, lw=1.2, ls="--", alpha=0.6)

    # Quadrant labels
    ax.text(med_recency * 0.5,  rfm["monetary"].max() * 0.9, "LOYAL\nCHAMPIONS",
            ha="center", color=cfg.SLATE,     fontsize=9, fontweight="bold", alpha=0.7)
    ax.text(rfm["recency"].max() * 0.82, rfm["monetary"].max() * 0.9, "⚠  CHURN\nRISK VIPs",
            ha="center", color=cfg.ALERT_RED, fontsize=9, fontweight="bold", alpha=0.9)
    ax.text(med_recency * 0.5,  med_monetary * 0.1, "NEW /\nLOW VALUE",
            ha="center", color=cfg.MID_GRAY,  fontsize=9, fontweight="bold", alpha=0.7)
    ax.text(rfm["recency"].max() * 0.82, med_monetary * 0.1, "DORMANT\nLOW VALUE",
            ha="center", color=cfg.CHARCOAL,  fontsize=9, fontweight="bold", alpha=0.7)

    ax.set_xlabel("Customer Recency (Days Since Last Purchase)", fontsize=12)
    ax.set_ylabel(f"Monetary Value (Lifetime Spend {cfg.CURRENCY_SYMBOL})", fontsize=12)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(
        lambda x, _: fmt_currency(x)))

    legend_patches = [
        mpatches.Patch(color=cfg.ALERT_RED, label=f"Inactive VIP (>{cfg.INACTIVITY_DAYS}d + >{fmt_currency(cfg.VIP_SPEND_THRESHOLD)})"),
        mpatches.Patch(color="#E67E22",     label=f"Inactive Non-VIP (>{cfg.INACTIVITY_DAYS}d)"),
        mpatches.Patch(color=cfg.SLATE,     label="Active Customer"),
    ]
    ax.legend(handles=legend_patches, loc="upper left", fontsize=9)
    ax.set_facecolor(cfg.LIGHT_GRAY)

    add_chart_header(fig,
        "Customer Defection Landscape — Recency vs Monetary Value",
        f"Bubble size = lifetime spend  |  Median recency: {med_recency:.0f}d  |  "
        f"Revenue at risk: {fmt_currency(kpis['churn_revenue'])}"
    )
    add_watermark(fig)
    plt.tight_layout(rect=[0, 0, 1, 0.94])
    save_chart(fig, "asset_02_defection_landscape.png")


# ---------------------------------------------------------------------------
# ASSET 3 — Top 10 Churn Risk Accounts (Horizontal Bar)
# ---------------------------------------------------------------------------

def asset_3_top10_churn(rfm):
    section_banner("3", "Top 10 High-Value Churn Risk Accounts")

    vip_churn = rfm[
        (rfm["monetary"] >= cfg.VIP_SPEND_THRESHOLD) &
        (rfm["recency"]  >= cfg.INACTIVITY_DAYS)
    ].nlargest(10, "monetary").reset_index(drop=True)

    if vip_churn.empty:
        print("    ⚠  No VIP churn accounts found with current thresholds — skipping.")
        return

    fig, ax = plt.subplots(figsize=(14, 7))
    fig.patch.set_facecolor(cfg.WHITE)

    y_pos  = range(len(vip_churn))
    colors = [cfg.ALERT_RED if i < 3 else cfg.NAVY for i in y_pos]

    bars = ax.barh(
        y_pos, vip_churn["monetary"],
        color=colors, edgecolor=cfg.WHITE, linewidth=0.8,
        height=0.65, zorder=3
    )

    for bar, val, rec in zip(bars, vip_churn["monetary"], vip_churn["recency"]):
        ax.text(
            bar.get_width() + vip_churn["monetary"].max() * 0.01,
            bar.get_y() + bar.get_height() / 2,
            f"{fmt_currency(val)}  ({rec}d silent)",
            va="center", ha="left", fontsize=9, color=cfg.CHARCOAL
        )

    labels = [f"Customer {str(c)[:8]}..." if len(str(c)) > 8 else str(c)
              for c in vip_churn[cfg.COL_CUSTOMER]]
    ax.set_yticks(list(y_pos))
    ax.set_yticklabels(labels, fontsize=10)
    ax.invert_yaxis()
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: fmt_currency(x)))
    ax.set_xlabel(f"Lifetime Spend ({cfg.CURRENCY_SYMBOL})", fontsize=12)
    ax.set_facecolor(cfg.LIGHT_GRAY)

    # Top 3 badge
    ax.text(
        0.99, 0.97, "🔴 TOP 3 = IMMEDIATE ACTION",
        transform=ax.transAxes, ha="right", va="top",
        fontsize=9, color=cfg.ALERT_RED, fontweight="bold"
    )

    add_chart_header(fig,
        "Top 10 High-Value Churn Risk Accounts — Executive Hit List",
        f"Criteria: Lifetime spend ≥ {fmt_currency(cfg.VIP_SPEND_THRESHOLD)}  &  "
        f"Silent ≥ {cfg.INACTIVITY_DAYS} days"
    )
    add_watermark(fig)
    plt.tight_layout(rect=[0, 0, 1, 0.93])
    save_chart(fig, "asset_03_top10_churn_accounts.png")


# ---------------------------------------------------------------------------
# ASSET 4 — Revenue Leak Matrix (DataFrame printout)
# ---------------------------------------------------------------------------

def asset_4_revenue_leak_matrix(df):
    section_banner("4", "Revenue Leak by Payment Method & Category")

    leak_df = df[df[cfg.COL_STATUS] == cfg.RETURN_STATUS].copy()

    if leak_df.empty:
        print("    ⚠  No cancellation rows found — skipping matrix.")
        return

    matrix = (
        leak_df.groupby([cfg.COL_PAYMENT, "standardized_category"])[cfg.COL_REVENUE]
        .sum()
        .abs()
        .unstack(fill_value=0)
        .round(2)
    )
    matrix["TOTAL_LEAK"] = matrix.sum(axis=1)
    matrix = matrix.sort_values("TOTAL_LEAK", ascending=False)

    # Format for display
    display = matrix.copy()
    for col in display.columns:
        display[col] = display[col].apply(lambda x: fmt_currency(x))

    print()
    print(f"    {'Revenue Leak Breakdown Matrix':^70}")
    print(f"    {'(Grouped by Payment Method & Product Category)':^70}")
    print()
    print("    " + display.to_string().replace("\n", "\n    "))
    print()

    # Save as styled PNG using matplotlib table
    fig, ax = plt.subplots(figsize=(16, max(4, len(matrix) * 0.8 + 2)))
    fig.patch.set_facecolor(cfg.WHITE)
    ax.axis("off")

    col_labels = list(display.columns)
    row_labels = list(display.index)
    cell_data  = display.values.tolist()

    tbl = ax.table(
        cellText=cell_data,
        rowLabels=row_labels,
        colLabels=col_labels,
        cellLoc="center",
        rowLoc="left",
        loc="center",
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(10)
    tbl.scale(1.2, 1.8)

    # Header style
    for (row, col), cell in tbl.get_celld().items():
        if row == 0:
            cell.set_facecolor(cfg.NAVY)
            cell.set_text_props(color=cfg.WHITE, fontweight="bold")
        elif col == -1:
            cell.set_facecolor(cfg.CHARCOAL)
            cell.set_text_props(color=cfg.WHITE)
        elif col == len(col_labels) - 1:
            cell.set_facecolor("#FDE8E8")
            cell.set_text_props(color=cfg.ALERT_RED, fontweight="bold")
        else:
            cell.set_facecolor(cfg.LIGHT_GRAY if row % 2 == 0 else cfg.WHITE)
        cell.set_edgecolor(cfg.MID_GRAY)

    add_chart_header(fig,
        "Revenue Leak Matrix — Payment Method × Product Category",
        "Aggregated cancellation/return revenue loss by segment"
    )
    add_watermark(fig)
    plt.tight_layout(rect=[0, 0, 1, 0.92])
    save_chart(fig, "asset_04_revenue_leak_matrix.png")


# ---------------------------------------------------------------------------
# ASSET 5 — CAC Efficiency: Monthly Unique Customer Growth
# ---------------------------------------------------------------------------

def asset_5_cac_trend(df_valid):
    section_banner("5", "Report 1 — CAC Efficiency: Monthly Customer Growth")

    monthly = (
        df_valid.groupby("month_period")[cfg.COL_CUSTOMER]
        .nunique()
        .reset_index()
        .rename(columns={cfg.COL_CUSTOMER: "unique_customers"})
        .sort_values("month_period")
    )
    monthly["month_str"] = monthly["month_period"].astype(str)
    monthly["rolling_3m"] = monthly["unique_customers"].rolling(3, min_periods=1).mean()

    fig, ax = plt.subplots(figsize=cfg.FIG_SIZE_WIDE)
    fig.patch.set_facecolor(cfg.WHITE)

    ax.fill_between(
        monthly["month_str"], monthly["unique_customers"],
        alpha=0.18, color=cfg.SLATE
    )
    ax.plot(
        monthly["month_str"], monthly["unique_customers"],
        color=cfg.NAVY, lw=2.2, marker="o", ms=5, zorder=4, label="Unique Customers"
    )
    ax.plot(
        monthly["month_str"], monthly["rolling_3m"],
        color=cfg.ALERT_RED, lw=1.8, ls="--", zorder=5, label="3-Month Rolling Avg"
    )

    ax.set_xlabel("Month", fontsize=12)
    ax.set_ylabel("Unique Transacting Customers", fontsize=12)
    ax.set_facecolor(cfg.LIGHT_GRAY)

    step = max(1, len(monthly) // 12)
    ax.set_xticks(range(0, len(monthly), step))
    ax.set_xticklabels(monthly["month_str"].iloc[::step], rotation=45, ha="right", fontsize=9)

    ax.legend(fontsize=10)

    # Annotate peak
    peak_idx = monthly["unique_customers"].idxmax()
    ax.annotate(
        f"Peak: {monthly.loc[peak_idx,'unique_customers']:,}",
        xy=(monthly.loc[peak_idx, "month_str"], monthly.loc[peak_idx, "unique_customers"]),
        xytext=(0, 18), textcoords="offset points",
        ha="center", fontsize=9, color=cfg.NAVY, fontweight="bold",
        arrowprops=dict(arrowstyle="->", color=cfg.CHARCOAL, lw=1)
    )

    add_chart_header(fig,
        "CAC Efficiency Report — Monthly Unique Customer Acquisition",
        "Trend line tracks transactional growth velocity over time"
    )
    add_watermark(fig)
    plt.tight_layout(rect=[0, 0, 1, 0.93])
    save_chart(fig, "asset_05_cac_efficiency_trend.png")


# ---------------------------------------------------------------------------
# ASSET 6 — VIP Win-Back Matrix (2×2 Quadrant)
# ---------------------------------------------------------------------------

def asset_6_winback_matrix(rfm):
    section_banner("6", "Report 2 — VIP Win-Back Matrix (2×2 Quadrant)")

    med_r = rfm["recency"].median()
    med_m = rfm["monetary"].median()

    def quadrant(row):
        if row["recency"] < med_r and row["monetary"] >= med_m:   return "Champions"
        if row["recency"] >= med_r and row["monetary"] >= med_m:  return "At Risk VIPs"
        if row["recency"] < med_r and row["monetary"] < med_m:    return "Promising"
        return "Hibernating"

    rfm = rfm.copy()
    rfm["quadrant"] = rfm.apply(quadrant, axis=1)

    q_colors = {
        "Champions"   : cfg.SLATE,
        "At Risk VIPs": cfg.ALERT_RED,
        "Promising"   : cfg.GOLD,
        "Hibernating" : cfg.MID_GRAY,
    }

    fig, ax = plt.subplots(figsize=cfg.FIG_SIZE_SQUARE)
    fig.patch.set_facecolor(cfg.WHITE)

    for q, grp in rfm.groupby("quadrant"):
        ax.scatter(
            grp["recency"], grp["monetary"],
            c=q_colors.get(q, cfg.CHARCOAL),
            s=30, alpha=0.6, label=f"{q} ({len(grp):,})",
            edgecolors="none", zorder=3
        )

    ax.axvline(med_r, color=cfg.CHARCOAL, lw=1.4, ls="--", alpha=0.7)
    ax.axhline(med_m, color=cfg.CHARCOAL, lw=1.4, ls="--", alpha=0.7)

    quadrant_labels = {
        "Champions"   : (med_r * 0.4,  rfm["monetary"].max() * 0.88),
        "At Risk VIPs": (rfm["recency"].max() * 0.75, rfm["monetary"].max() * 0.88),
        "Promising"   : (med_r * 0.4,  med_m * 0.12),
        "Hibernating" : (rfm["recency"].max() * 0.75, med_m * 0.12),
    }
    for label, (x, y) in quadrant_labels.items():
        ax.text(x, y, label.upper(), ha="center", fontsize=10,
                fontweight="bold", color=q_colors[label], alpha=0.85)

    ax.set_xlabel("Recency (Days Since Last Purchase)", fontsize=12)
    ax.set_ylabel(f"Monetary Value ({cfg.CURRENCY_SYMBOL})", fontsize=12)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: fmt_currency(x)))
    ax.legend(loc="center right", fontsize=9)
    ax.set_facecolor(cfg.LIGHT_GRAY)

    add_chart_header(fig,
        "VIP Win-Back Matrix — 2×2 Customer Value Quadrant",
        f"Median recency: {med_r:.0f}d  |  Median monetary: {fmt_currency(med_m)}"
    )
    add_watermark(fig)
    plt.tight_layout(rect=[0, 0, 1, 0.93])
    save_chart(fig, "asset_06_vip_winback_matrix.png")


# ---------------------------------------------------------------------------
# ASSET 7 — Demographic Churn Ledger (Stacked Monthly Revenue by Segment)
# ---------------------------------------------------------------------------

def asset_7_stacked_segment_revenue(df_valid):
    section_banner("7", "Report 3 — Demographic Churn & Revenue Ledger")

    pivot = (
        df_valid.groupby(["month_period", cfg.COL_SEGMENT])[cfg.COL_REVENUE]
        .sum()
        .unstack(fill_value=0)
        .sort_index()
    )
    pivot.index = pivot.index.astype(str)

    segments = list(pivot.columns)
    colors   = [cfg.SEGMENT_COLORS.get(s, cfg.MID_GRAY) for s in segments]

    fig, ax = plt.subplots(figsize=cfg.FIG_SIZE_WIDE)
    fig.patch.set_facecolor(cfg.WHITE)

    bottom = np.zeros(len(pivot))
    for seg, col in zip(segments, colors):
        ax.bar(
            pivot.index, pivot[seg],
            bottom=bottom, label=seg,
            color=col, edgecolor=cfg.WHITE, linewidth=0.5,
            width=0.75, zorder=3
        )
        bottom += pivot[seg].values

    step = max(1, len(pivot) // 12)
    ax.set_xticks(range(0, len(pivot), step))
    ax.set_xticklabels(list(pivot.index)[::step], rotation=45, ha="right", fontsize=9)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: fmt_currency(x)))
    ax.set_xlabel("Month", fontsize=12)
    ax.set_ylabel(f"Net Revenue ({cfg.CURRENCY_SYMBOL})", fontsize=12)
    ax.legend(loc="upper left", fontsize=9, title="Segment")
    ax.set_facecolor(cfg.LIGHT_GRAY)

    add_chart_header(fig,
        "Demographic Revenue Ledger — Monthly Net Revenue by Customer Segment",
        "Tracks revenue composition shifts — early churn signals visible as segment shrinkage"
    )
    add_watermark(fig)
    plt.tight_layout(rect=[0, 0, 1, 0.93])
    save_chart(fig, "asset_07_segment_revenue_ledger.png")


# ---------------------------------------------------------------------------
# ASSET 8 — Revenue Leak & Friction Report (Dual-Axis Combo)
# ---------------------------------------------------------------------------

def asset_8_revenue_friction(df):
    section_banner("8", "Report 4 — Revenue Leak & Friction Report (Dual-Axis)")

    status_grp = (
        df.groupby(cfg.COL_STATUS)
        .agg(
            txn_count=(cfg.COL_REVENUE, "count"),
            rev_total=(cfg.COL_REVENUE, "sum"),
        )
        .reset_index()
        .sort_values("txn_count", ascending=False)
    )

    fig, ax1 = plt.subplots(figsize=(12, 7))
    fig.patch.set_facecolor(cfg.WHITE)
    ax2 = ax1.twinx()

    x     = np.arange(len(status_grp))
    width = 0.38

    bar_colors = [
        cfg.ALERT_RED if s == cfg.RETURN_STATUS
        else (cfg.MID_GRAY if s == cfg.ERROR_STATUS else cfg.NAVY)
        for s in status_grp[cfg.COL_STATUS]
    ]

    bars1 = ax1.bar(x - width/2, status_grp["txn_count"],
                    width=width, color=bar_colors,
                    edgecolor=cfg.WHITE, linewidth=0.8,
                    label="Transaction Count", zorder=3)

    bars2 = ax2.bar(x + width/2, status_grp["rev_total"].abs(),
                    width=width, color=cfg.GOLD,
                    edgecolor=cfg.WHITE, linewidth=0.8,
                    label=f"Revenue ({cfg.CURRENCY_SYMBOL})", zorder=3, alpha=0.85)

    # Value labels
    for bar in bars1:
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 10,
                 f"{bar.get_height():,.0f}", ha="center", va="bottom", fontsize=9, color=cfg.NAVY)
    for bar in bars2:
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() * 1.02,
                 fmt_currency(bar.get_height()), ha="center", va="bottom", fontsize=9, color=cfg.CHARCOAL)

    ax1.set_xticks(x)
    ax1.set_xticklabels(status_grp[cfg.COL_STATUS], fontsize=11, fontweight="bold")
    ax1.set_ylabel("Transaction Count", fontsize=12, color=cfg.NAVY)
    ax2.set_ylabel(f"Absolute Revenue ({cfg.CURRENCY_SYMBOL})", fontsize=12, color=cfg.GOLD)
    ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: fmt_currency(x)))
    ax1.set_facecolor(cfg.LIGHT_GRAY)

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right", fontsize=9)

    add_chart_header(fig,
        "Revenue Leak & Friction Report — Transaction Count vs Currency Lost",
        "Dual-axis view isolates operational friction across all order status profiles"
    )
    add_watermark(fig)
    plt.tight_layout(rect=[0, 0, 1, 0.93])
    save_chart(fig, "asset_08_revenue_friction_dual_axis.png")


# ---------------------------------------------------------------------------
# ASSET 9 — Premium vs General Inventory Donut
# ---------------------------------------------------------------------------

def asset_9_premium_donut(df_valid):
    section_banner("9", "Report 5 — Premium vs General Inventory Mix (Donut)")

    tier_rev = df_valid.groupby("price_tier")[cfg.COL_REVENUE].sum()
    labels   = list(tier_rev.index)
    values   = list(tier_rev.values)
    colors   = [cfg.GOLD if t == "Premium" else cfg.SLATE for t in labels]

    total = sum(values)
    pcts  = [v / total * 100 for v in values]

    fig, ax = plt.subplots(figsize=(11, 9))
    fig.patch.set_facecolor(cfg.WHITE)

    wedges, texts, autotexts = ax.pie(
        values,
        labels=None,
        colors=colors,
        autopct="%1.1f%%",
        startangle=90,
        pctdistance=0.78,
        wedgeprops=dict(width=0.52, edgecolor=cfg.WHITE, linewidth=2.5),
        explode=[0.04] * len(values),
    )
    for at in autotexts:
        at.set_fontsize(13)
        at.set_fontweight("bold")
        at.set_color(cfg.WHITE)

    # Centre label
    ax.text(0, 0.08, "NET REVENUE",   ha="center", va="center",
            fontsize=10, color=cfg.MID_GRAY)
    ax.text(0, -0.08, fmt_currency(total), ha="center", va="center",
            fontsize=14, fontweight="bold", color=cfg.NAVY)

    legend_patches = [
        mpatches.Patch(color=c, label=f"{l}  —  {fmt_currency(v)}  ({p:.1f}%)")
        for c, l, v, p in zip(colors, labels, values, pcts)
    ]
    ax.legend(handles=legend_patches, loc="lower center",
              bbox_to_anchor=(0.5, -0.06), fontsize=11, framealpha=0.9)

    add_chart_header(fig,
        "Premium vs General Inventory Mix — Net Revenue Distribution",
        f"Premium defined as unit price ≥ 80th percentile threshold"
    )
    add_watermark(fig)
    plt.tight_layout(rect=[0, 0, 1, 0.93])
    save_chart(fig, "asset_09_premium_inventory_donut.png")


# ---------------------------------------------------------------------------
# MAIN ORCHESTRATOR
# ---------------------------------------------------------------------------

def main():
    print()
    print("=" * 65)
    print("   ENTERPRISE BI DASHBOARD GENERATOR")
    print("   Principal BI Architect | Senior Data Scientist")
    print(f"   Run date : {datetime.now().strftime('%d %B %Y  %H:%M:%S')}")
    print("=" * 65)

    apply_corporate_style()

    df, df_valid, rfm, price_80 = load_and_enrich(cfg.DATA_CLEAN)

    kpis = asset_1_executive_kpi(df, df_valid, rfm)
    asset_2_defection_scatter(rfm, kpis)
    asset_3_top10_churn(rfm)
    asset_4_revenue_leak_matrix(df)
    asset_5_cac_trend(df_valid)
    asset_6_winback_matrix(rfm)
    asset_7_stacked_segment_revenue(df_valid)
    asset_8_revenue_friction(df)
    asset_9_premium_donut(df_valid)

    print()
    print("=" * 65)
    print("   ALL 9 EXECUTIVE ASSETS GENERATED SUCCESSFULLY")
    print(f"   Output folder : {cfg.OUTPUT_DIR}")
    print("=" * 65)
    print()
    print("   Files created:")
    assets = [
        "asset_02_defection_landscape.png",
        "asset_03_top10_churn_accounts.png",
        "asset_04_revenue_leak_matrix.png",
        "asset_05_cac_efficiency_trend.png",
        "asset_06_vip_winback_matrix.png",
        "asset_07_segment_revenue_ledger.png",
        "asset_08_revenue_friction_dual_axis.png",
        "asset_09_premium_inventory_donut.png",
    ]
    for a in assets:
        full = os.path.join(cfg.OUTPUT_DIR, a)
        size = os.path.getsize(full) / 1024 if os.path.isfile(full) else 0
        print(f"   ✔  {a:<48} {size:>7.1f} KB")

    print()
    print(f"   Pipeline completed : {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 65)
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n  ✘ Interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n  ✘ Fatal error: {e}")
        raise
