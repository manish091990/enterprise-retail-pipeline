"""
config.py
=========
Central configuration file for the Enterprise Retail BI Pipeline.
All paths, constants, and design tokens live here.
"""

import os

# ---------------------------------------------------------------------------
# BASE PATHS
# ---------------------------------------------------------------------------
PROJECT_ROOT   = os.path.expanduser("~/Desktop/retail_project")
DATA_RAW       = os.path.join(PROJECT_ROOT, "enterprise_retail_raw.csv")
DATA_CLEAN     = os.path.join(PROJECT_ROOT, "data", "processed", "enterprise_retail_clean.csv")
OUTPUT_DIR     = PROJECT_ROOT   # all charts saved here

# ---------------------------------------------------------------------------
# COLUMN NAMES  (match enterprise_retail_clean.csv schema exactly)
# ---------------------------------------------------------------------------
COL_DATE        = "clean_invoice_date"
COL_CUSTOMER    = "cleaned_customer_id"
COL_COUNTRY     = "standardized_country"
COL_DESC        = "clean_description"
COL_QTY         = "clean_quantity"
COL_PRICE       = "clean_unit_price"
COL_STATUS      = "order_status"
COL_SEGMENT     = "Cleaned_Segment"
COL_REVENUE     = "Net_Revenue"
COL_PAYMENT     = "Payment_Method"
COL_DUPLICATE   = "is_duplicate"

# ---------------------------------------------------------------------------
# BUSINESS RULES
# ---------------------------------------------------------------------------
CURRENCY_SYMBOL         = "₹"
PREMIUM_PERCENTILE      = 80          # UnitPrice >= 80th percentile → Premium
VIP_SPEND_THRESHOLD     = 100         # adjusted to match actual data scale
INACTIVITY_DAYS         = 60          # adjusted to catch more inactive customers
VALID_SALE_STATUS       = "Valid Sale"
RETURN_STATUS           = "Cancellation/Return"
ERROR_STATUS            = "System Error"

# ---------------------------------------------------------------------------
# CORPORATE DESIGN PALETTE
# ---------------------------------------------------------------------------
NAVY            = "#0D1B2A"     # deep navy — primary background / bars
CHARCOAL        = "#2E3B4E"     # charcoal — secondary elements
SLATE           = "#4A6FA5"     # slate blue — accent / highlights
ALERT_RED       = "#C0392B"     # muted alert red — risk / churn flags
GOLD            = "#D4A017"     # gold — premium tier
LIGHT_GRAY      = "#F0F4F8"     # light gray — backgrounds
MID_GRAY        = "#8A9BB0"     # mid gray — gridlines / annotations
WHITE           = "#FFFFFF"
SEGMENT_COLORS  = {
    "Corporate"     : "#4A6FA5",
    "Consumer"      : "#D4A017",
    "Home Office"   : "#2E8B57",
    "Small Business": "#C0392B",
    "Unknown"       : "#8A9BB0",
}

# ---------------------------------------------------------------------------
# CHART EXPORT SETTINGS
# ---------------------------------------------------------------------------
DPI             = 300
FIG_SIZE_WIDE   = (16, 9)
FIG_SIZE_SQUARE = (12, 10)
FIG_SIZE_TALL   = (14, 10)
