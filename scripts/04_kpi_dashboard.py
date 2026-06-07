"""
fix_asset1_kpi.py
==================
Drop-in replacement for asset_1_executive_kpi().
Run this standalone to regenerate ONLY the KPI dashboard PNG.

Place in ~/Desktop/retail_project/ and run:
    python3 fix_asset1_kpi.py
"""

import os
import sys
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
from datetime import datetime, timedelta

warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.expanduser("~/Desktop/retail_project"))
try:
    import config as cfg
except ModuleNotFoundError:
    print("  ✘ config.py not found in ~/Desktop/retail_project")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def fmt_currency(value, symbol=None):
    sym = symbol or cfg.CURRENCY_SYMBOL
    if abs(value) >= 1_000_000:
        return f"{sym}{value/1_000_000:.2f}M"
    elif abs(value) >= 1_000:
        return f"{sym}{value/1_000:.1f}K"
    return f"{sym}{value:,.0f}"


def add_watermark(fig, text="CONFIDENTIAL — EXECUTIVE USE ONLY"):
    fig.text(0.99, 0.01, text, ha="right", va="bottom",
             fontsize=7, color=cfg.MID_GRAY, alpha=0.5, style="italic")


def kpi_card(ax, x, y, w, h, title, value, subtitle="", value_color=None, bg_color=None):
    """Draw a single KPI card as a rounded rectangle with title/value/subtitle."""
    bg = bg_color or cfg.WHITE
    vc = value_color or cfg.NAVY

    # Card background
    fancy = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.02",
        facecolor=bg, edgecolor=cfg.MID_GRAY,
        linewidth=1.2, zorder=2,
        transform=ax.transAxes, clip_on=False
    )
    ax.add_patch(fancy)

    cx = x + w / 2
    # Title
    ax.text(cx, y + h - 0.055, title.upper(),
            transform=ax.transAxes, ha="center", va="top",
            fontsize=8.5, color=cfg.MID_GRAY, fontweight="bold",
            zorder=3, clip_on=False)
    # Value
    ax.text(cx, y + h / 2 + 0.01, value,
            transform=ax.transAxes, ha="center", va="center",
            fontsize=19, color=vc, fontweight="bold",
            zorder=3, clip_on=False)
    # Subtitle
    if subtitle:
        ax.text(cx, y + 0.05, subtitle,
                transform=ax.transAxes, ha="center", va="bottom",
                fontsize=8, color=cfg.MID_GRAY, style="italic",
                zorder=3, clip_on=False)


# ---------------------------------------------------------------------------
# Load & compute KPIs
# ---------------------------------------------------------------------------

def load_kpis():
    path = cfg.DATA_CLEAN
    if not os.path.isfile(path):
        print(f"  ✘ Clean dataset not found: {path}")
        sys.exit(1)

    df = pd.read_csv(path, low_memory=False, encoding="utf-8")
    df[cfg.COL_DATE]   = pd.to_datetime(df[cfg.COL_DATE], errors="coerce")
    df[cfg.COL_QTY]    = pd.to_numeric(df[cfg.COL_QTY],   errors="coerce").fillna(0)
    df[cfg.COL_PRICE]  = pd.to_numeric(df[cfg.COL_PRICE],  errors="coerce").fillna(0)

    if cfg.COL_REVENUE not in df.columns:
        df[cfg.COL_REVENUE] = df[cfg.COL_QTY] * df[cfg.COL_PRICE]
    df[cfg.COL_REVENUE] = pd.to_numeric(df[cfg.COL_REVENUE], errors="coerce").fillna(0)

    df = df.dropna(subset=[cfg.COL_DATE])
    df_valid = df[df[cfg.COL_STATUS] == cfg.VALID_SALE_STATUS].copy()

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

    vip          = rfm[rfm["monetary"] >= cfg.VIP_SPEND_THRESHOLD]
    inactive_vip = vip[vip["recency"]  >= cfg.INACTIVITY_DAYS]

    total_revenue        = df_valid[cfg.COL_REVENUE].sum()
    churn_revenue        = inactive_vip["monetary"].sum()
    churn_pct            = (churn_revenue / total_revenue * 100) if total_revenue else 0
    unique_inactive_vip  = len(inactive_vip)
    avg_clv              = rfm["monetary"].mean()
    total_transactions   = len(df_valid)
    cancellations        = (df[cfg.COL_STATUS] == cfg.RETURN_STATUS).sum()
    cancel_rate          = cancellations / len(df) * 100
    top_country          = df_valid[cfg.COL_COUNTRY].value_counts().idxmax() \
                           if cfg.COL_COUNTRY in df_valid.columns else "N/A"
    avg_order_value      = df_valid[cfg.COL_REVENUE].mean()
    unique_customers     = df_valid[cfg.COL_CUSTOMER].nunique()

    return dict(
        total_revenue=total_revenue,
        churn_revenue=churn_revenue,
        churn_pct=churn_pct,
        unique_inactive_vip=unique_inactive_vip,
        avg_clv=avg_clv,
        total_transactions=total_transactions,
        cancellations=cancellations,
        cancel_rate=cancel_rate,
        top_country=top_country,
        avg_order_value=avg_order_value,
        unique_customers=unique_customers,
        rfm=rfm,
        inactive_vip=inactive_vip,
        data_date=df[cfg.COL_DATE].max().strftime("%d %b %Y"),
    )


# ---------------------------------------------------------------------------
# Build the KPI PNG
# ---------------------------------------------------------------------------

def build_kpi_png(kpis):
    fig = plt.figure(figsize=(20, 11), facecolor=cfg.NAVY)

    # ── Header band ──────────────────────────────────────────────────────────
    header_ax = fig.add_axes([0, 0.88, 1, 0.12], facecolor=cfg.NAVY)
    header_ax.axis("off")
    header_ax.text(0.5, 0.72,
                   "ENTERPRISE RETAIL — EXECUTIVE KPI COMMAND CENTER",
                   ha="center", va="center", fontsize=22, fontweight="bold",
                   color=cfg.WHITE, transform=header_ax.transAxes)
    header_ax.text(0.5, 0.22,
                   f"Reporting Period up to: {kpis['data_date']}   |   "
                   f"Generated: {datetime.now().strftime('%d %b %Y  %H:%M')}   |   "
                   f"CONFIDENTIAL — C-SUITE DISTRIBUTION ONLY",
                   ha="center", va="center", fontsize=9,
                   color=cfg.MID_GRAY, transform=header_ax.transAxes)

    # Thin gold separator
    sep_ax = fig.add_axes([0.03, 0.865, 0.94, 0.004], facecolor=cfg.GOLD)
    sep_ax.axis("off")

    # ── KPI card canvas ──────────────────────────────────────────────────────
    card_ax = fig.add_axes([0.02, 0.34, 0.96, 0.50], facecolor=cfg.NAVY)
    card_ax.axis("off")

    # Row 1 — 5 primary KPI cards
    row1_cards = [
        ("Total Net Revenue",       fmt_currency(kpis["total_revenue"]),
         "Valid sales only",                  cfg.NAVY,      cfg.WHITE),
        ("Revenue at Churn Risk",   fmt_currency(kpis["churn_revenue"]),
         f"{kpis['churn_pct']:.1f}% of total revenue",      cfg.ALERT_RED, "#FFF0EE"),
        ("Inactive VIP Accounts",   f"{kpis['unique_inactive_vip']:,}",
         f"Silent >{cfg.INACTIVITY_DAYS}d & spend >{fmt_currency(cfg.VIP_SPEND_THRESHOLD)}",
         cfg.ALERT_RED, "#FFF0EE"),
        ("Avg Customer Lifetime\nValue", fmt_currency(kpis["avg_clv"]),
         "Across all RFM profiles",          cfg.SLATE,     cfg.LIGHT_GRAY),
        ("Avg Order Value",         fmt_currency(kpis["avg_order_value"]),
         "Per valid transaction",            cfg.SLATE,     cfg.LIGHT_GRAY),
    ]

    card_w, card_h = 0.175, 0.44
    gap            = 0.016
    start_x        = 0.01

    for i, (title, value, sub, vc, bg) in enumerate(row1_cards):
        x = start_x + i * (card_w + gap)
        kpi_card(card_ax, x, 0.52, card_w, card_h,
                 title, value, sub, value_color=vc, bg_color=bg)

    # Row 2 — 4 secondary metric cards
    row2_cards = [
        ("Total Transactions",  f"{kpis['total_transactions']:,}",
         "Valid sale records",              cfg.NAVY,  cfg.WHITE),
        ("Unique Customers",    f"{kpis['unique_customers']:,}",
         "Active buyer accounts",          cfg.NAVY,  cfg.WHITE),
        ("Cancellation Rate",   f"{kpis['cancel_rate']:.2f}%",
         f"{kpis['cancellations']:,} orders returned",
         cfg.ALERT_RED, "#FFF0EE"),
        ("Top Market",          kpis["top_country"],
         "Highest revenue country",        cfg.GOLD,  "#FFFBEE"),
    ]

    card_w2 = 0.225
    gap2    = 0.018
    start_x2 = 0.015

    for i, (title, value, sub, vc, bg) in enumerate(row2_cards):
        x = start_x2 + i * (card_w2 + gap2)
        kpi_card(card_ax, x, 0.03, card_w2, 0.42,
                 title, value, sub, value_color=vc, bg_color=bg)

    # ── Mini bar chart — Top 5 countries by revenue ───────────────────────
    chart_ax = fig.add_axes([0.03, 0.05, 0.94, 0.27], facecolor="#131E2E")
    chart_ax.set_facecolor("#131E2E")

    # Load quick country data
    # Load full CSV and detect revenue column flexibly
    df = pd.read_csv(cfg.DATA_CLEAN, low_memory=False)
    # Detect revenue column — fallback to computing from qty x price
    if cfg.COL_REVENUE in df.columns:
        rev_col = cfg.COL_REVENUE
    elif "Net_Revenue" in df.columns:
        rev_col = "Net_Revenue"
    else:
        df["_revenue"] = (
            pd.to_numeric(df.get(cfg.COL_QTY, 0), errors="coerce").fillna(0) *
            pd.to_numeric(df.get(cfg.COL_PRICE, 0), errors="coerce").fillna(0)
        )
        rev_col = "_revenue"
    df[cfg.COL_REVENUE] = pd.to_numeric(df[rev_col], errors="coerce").fillna(0)
    top5 = (
        df[df[cfg.COL_STATUS] == cfg.VALID_SALE_STATUS]
        .groupby(cfg.COL_COUNTRY)[cfg.COL_REVENUE]
        .sum()
        .nlargest(7)
    )

    bar_colors = [cfg.GOLD if i == 0 else cfg.SLATE for i in range(len(top5))]
    bars = chart_ax.barh(
        range(len(top5)), top5.values,
        color=bar_colors, edgecolor="none", height=0.55, zorder=3
    )
    for bar, val in zip(bars, top5.values):
        chart_ax.text(
            bar.get_width() + top5.values.max() * 0.005,
            bar.get_y() + bar.get_height() / 2,
            fmt_currency(val), va="center", ha="left",
            fontsize=8.5, color=cfg.WHITE
        )

    chart_ax.set_yticks(range(len(top5)))
    chart_ax.set_yticklabels(top5.index, fontsize=9, color=cfg.WHITE)
    chart_ax.invert_yaxis()
    chart_ax.set_xlabel(f"Net Revenue ({cfg.CURRENCY_SYMBOL})",
                        fontsize=9, color=cfg.MID_GRAY)
    chart_ax.xaxis.set_major_formatter(
        plt.FuncFormatter(lambda x, _: fmt_currency(x)))
    chart_ax.tick_params(colors=cfg.MID_GRAY, labelsize=8)
    chart_ax.spines[:].set_visible(False)
    chart_ax.grid(axis="x", color=cfg.MID_GRAY, alpha=0.2, linestyle="--")

    chart_ax.text(
        0.99, 0.97, "TOP 7 MARKETS BY NET REVENUE",
        transform=chart_ax.transAxes, ha="right", va="top",
        fontsize=8.5, color=cfg.GOLD, fontweight="bold"
    )

    add_watermark(fig)

    out_path = os.path.join(cfg.OUTPUT_DIR, "asset_01_executive_kpi_dashboard.png")
    fig.savefig(out_path, dpi=cfg.DPI, bbox_inches="tight", facecolor=cfg.NAVY)
    plt.close(fig)
    size_kb = os.path.getsize(out_path) / 1024
    print(f"  ✔  Saved → {out_path}  ({size_kb:.1f} KB)")


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print()
    print("=" * 60)
    print("   ASSET 1 — Executive KPI Dashboard (PNG)")
    print("=" * 60)
    print("  ► Computing KPIs from clean dataset ...")
    kpis = load_kpis()
    print(f"  ✔  KPIs computed successfully")
    print(f"     Total Revenue      : {fmt_currency(kpis['total_revenue'])}")
    print(f"     Churn Risk Revenue : {fmt_currency(kpis['churn_revenue'])}")
    print(f"     Inactive VIP Accts : {kpis['unique_inactive_vip']:,}")
    print(f"     Avg CLV            : {fmt_currency(kpis['avg_clv'])}")
    print()
    print("  ► Building KPI dashboard PNG ...")
    build_kpi_png(kpis)
    print()
    print("  Pipeline done.")
    print("=" * 60)
    print()
