
from pathlib import Path
import pandas as pd

SOURCE = Path("data/synthetic_raw")
TARGET = Path("data/reference_parquet")

TARGET.mkdir(parents=True, exist_ok=True)

tables = [
    "products",
    "aisles",
    "departments"
]

for table in tables:
    csv_path = SOURCE / f"{table}.csv"
    parquet_path = TARGET / f"{table}.parquet"

    df = pd.read_csv(csv_path)

    df.to_parquet(
        parquet_path,
        engine="pyarrow",
        compression="snappy",
        index=False
    )

    print(f"{table}: {len(df):,} records")
    print(f"Columns: {df.columns.tolist()}")
    print(f"Created: {parquet_path}")
    print("-" * 40)
