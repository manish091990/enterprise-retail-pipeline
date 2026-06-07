# config/paths.py  ─ single source of truth for all paths
import os

# ── Root of the project (always Desktop/retail_project) ──────────────────────
ROOT = os.path.join(os.path.expanduser("~"), "Desktop", "retail_project")

# ── Data ─────────────────────────────────────────────────────────────────────
DATA_RAW       = os.path.join(ROOT, "data", "raw")
DATA_PROCESSED = os.path.join(ROOT, "data", "processed")
DATA_EXPORTS   = os.path.join(ROOT, "data", "exports")

# ── Outputs ──────────────────────────────────────────────────────────────────
LOGS           = os.path.join(ROOT, "logs")
REPORTS        = os.path.join(ROOT, "reports")
MODELS         = os.path.join(ROOT, "models")

# ── Key files ────────────────────────────────────────────────────────────────
RAW_CSV        = os.path.join(DATA_RAW, "enterprise_retail_raw.csv")