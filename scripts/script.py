# Any script inside retail_project/scripts/
import sys, os
sys.path.insert(0, os.path.join(os.path.expanduser("~"), "Desktop", "retail_project"))

from config.paths import RAW_CSV, DATA_PROCESSED
import pandas as pd

print(f"► Loading dataset from:\n   {RAW_CSV}\n")
df = pd.read_csv(RAW_CSV)