
"""
Instacart Daily Batch Generator

Input:
    data/synthetic_raw/orders.csv
    data/synthetic_raw/order_products__prior.csv
    data/synthetic_raw/order_products__train.csv

Output:
    data/batches/batch_0001/
        orders.csv
        order_items.csv
        _READY.json

Her batch en fazla 10.000 siparis icerir.
Son batch sunum icin ayrilir.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd


# ==========================================
# CONFIGURATION
# ==========================================

BASE_DIR = Path(__file__).resolve().parents[1]

INPUT_DIR = BASE_DIR / "data" / "synthetic_raw"
OUTPUT_DIR = BASE_DIR / "data" / "batches"

ORDER_COLUMNS = [
    "order_id",
    "user_id",
    "eval_set",
    "order_number",
    "order_dow",
    "order_hour_of_day",
    "days_since_prior_order",
    "synthetic_order_timestamp",
]

ITEM_COLUMNS = [
    "order_id",
    "product_id",
    "add_to_cart_order",
    "reordered",
]


# ==========================================
# FILE VALIDATION
# ==========================================

def sha256_file(path: Path) -> str:
    """Dosyanin SHA256 hash degerini hesaplar."""

    digest = hashlib.sha256()

    with path.open("rb") as file:
        for block in iter(
            lambda: file.read(1024 * 1024), b""
        ):
            digest.update(block)

    return digest.hexdigest()


# ==========================================
# CREATE DAILY BATCHES
# ==========================================

def create_batches(
    batch_size: int,
    chunk_size: int,
    demo_batches: int,
    overwrite: bool,
):

    if batch_size < 1 or chunk_size < 1:
        raise ValueError(
            "Batch size and chunk size must be positive."
        )

    if demo_batches < 0:
        raise ValueError(
            "Demo batch count cannot be negative."
        )

    required_files = [
        INPUT_DIR / "orders.csv",
        INPUT_DIR / "order_products__prior.csv",
        INPUT_DIR / "order_products__train.csv",
    ]

    missing_files = [
        str(path)
        for path in required_files
        if not path.exists()
    ]

    if missing_files:
        raise FileNotFoundError(
            f"Missing files: {missing_files}"
        )

    if OUTPUT_DIR.exists() and any(OUTPUT_DIR.iterdir()):

        if not overwrite:
            raise FileExistsError(
                "Batch output directory is not empty. "
                "Use --overwrite to regenerate."
            )

        shutil.rmtree(OUTPUT_DIR)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ======================================
    # 1. LOAD ORDERS
    # ======================================

    print("\n[1/4] Loading orders...")

    orders = pd.read_csv(
        INPUT_DIR / "orders.csv",
        usecols=ORDER_COLUMNS,
        dtype={
            "order_id": "int32",
            "user_id": "int32",
            "order_number": "int16",
            "order_dow": "int8",
            "order_hour_of_day": "int8",
            "eval_set": "category",
        },
        parse_dates=["synthetic_order_timestamp"],
    )

    if orders["order_id"].duplicated().any():
        raise ValueError("Duplicate order_id detected.")

    # Test siparislerinin urun bilgisi yok.
    orders = orders[
        orders["eval_set"].isin(["prior", "train"])
    ].copy()

    if (
        orders.empty
        or orders["synthetic_order_timestamp"].isna().any()
    ):
        raise ValueError(
            "No usable orders or invalid timestamps."
        )

    # Musterinin siparis sirasi korunuyor mu?
    chronological = orders.sort_values(
        ["user_id", "order_number"],
        kind="stable",
    )

    previous_time = chronological.groupby(
        "user_id",
        sort=False,
    )["synthetic_order_timestamp"].shift()

    invalid = (
        chronological["synthetic_order_timestamp"]
        < previous_time
    )

    if invalid.any():
        raise ValueError(
            "Synthetic timestamps violate order chronology."
        )

    del chronological, previous_time

    # Tarihe gore sirala.
    orders = orders.sort_values(
        ["synthetic_order_timestamp", "order_id"],
        kind="stable",
    ).reset_index(drop=True)

    # Her batch en fazla batch_size siparis.
    orders["_batch_number"] = (
        np.arange(len(orders), dtype=np.int64)
        // batch_size
        + 1
    ).astype("int32")

    total_batches = int(
        orders["_batch_number"].max()
    )

    if demo_batches >= total_batches:
        raise ValueError(
            "Demo batch count must be smaller "
            "than total batch count."
        )

    print(f"Total orders: {len(orders):,}")
    print(f"Total batches: {total_batches:,}")

    # order_id -> batch_number
    max_order_id = int(orders["order_id"].max())

    batch_lookup = np.zeros(
        max_order_id + 1,
        dtype=np.int32,
    )

    batch_lookup[
        orders["order_id"].to_numpy(dtype=np.int64)
    ] = orders["_batch_number"].to_numpy()

    order_counts = np.zeros(
        total_batches + 1,
        dtype=np.int64,
    )

    item_counts = np.zeros(
        total_batches + 1,
        dtype=np.int64,
    )

    date_bounds = {}

    # ======================================
    # 2. GENERATE ORDER BATCHES
    # ======================================

    print("\n[2/4] Creating order batches...")

    for batch_number, group in orders.groupby(
        "_batch_number",
        sort=True,
    ):

        batch_number = int(batch_number)

        batch_name = f"batch_{batch_number:04d}"

        batch_dir = OUTPUT_DIR / batch_name

        batch_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        result = group.drop(
            columns=["_batch_number"]
        ).copy()

        result["synthetic_order_timestamp"] = (
            result["synthetic_order_timestamp"]
            .dt.strftime("%Y-%m-%d %H:%M:%S")
        )

        result.to_csv(
            batch_dir / "orders.csv",
            index=False,
        )

        # Item dosyasinin basligini olustur.
        pd.DataFrame(
            columns=ITEM_COLUMNS
        ).to_csv(
            batch_dir / "order_items.csv",
            index=False,
        )

        order_counts[batch_number] = len(result)

        date_bounds[batch_number] = (
            result["synthetic_order_timestamp"].min(),
            result["synthetic_order_timestamp"].max(),
        )

    del orders

    # ======================================
    # 3. DISTRIBUTE ORDER ITEMS
    # ======================================

    print("\n[3/4] Distributing order items...")

    sources = [
        "order_products__prior.csv",
        "order_products__train.csv",
    ]

    for filename in sources:

        print(f"Reading: {filename}")

        reader = pd.read_csv(
            INPUT_DIR / filename,
            usecols=ITEM_COLUMNS,
            dtype={
                "order_id": "int32",
                "product_id": "int32",
                "add_to_cart_order": "int16",
                "reordered": "int8",
            },
            chunksize=chunk_size,
        )

        for chunk in reader:

            order_ids = chunk[
                "order_id"
            ].to_numpy(dtype=np.int64)

            within = order_ids <= max_order_id

            batch_numbers = np.zeros(
                len(order_ids),
                dtype=np.int32,
            )

            batch_numbers[within] = batch_lookup[
                order_ids[within]
            ]

            if (batch_numbers == 0).any():
                raise ValueError(
                    "Order item without matching order."
                )

            chunk["_batch_number"] = batch_numbers

            for batch_number, group in chunk.groupby(
                "_batch_number",
                sort=False,
            ):

                batch_number = int(batch_number)

                batch_name = (
                    f"batch_{batch_number:04d}"
                )

                output_file = (
                    OUTPUT_DIR
                    / batch_name
                    / "order_items.csv"
                )

                group[ITEM_COLUMNS].to_csv(
                    output_file,
                    mode="a",
                    header=False,
                    index=False,
                )

                item_counts[batch_number] += len(group)

    # ======================================
    # 4. CREATE READY MANIFESTS
    # ======================================

    print("\n[4/4] Creating READY manifests...")

    for batch_number in range(
        1,
        total_batches + 1,
    ):

        batch_name = f"batch_{batch_number:04d}"

        batch_dir = OUTPUT_DIR / batch_name

        orders_file = batch_dir / "orders.csv"
        items_file = batch_dir / "order_items.csv"

        if item_counts[batch_number] == 0:
            raise ValueError(
                f"{batch_name} has no order items."
            )

        is_demo = (
            batch_number
            > total_batches - demo_batches
        )

        manifest = {
            "schema_version": 1,
            "batch_id": batch_name,
            "status": (
                "RESERVED_FOR_PRESENTATION"
                if is_demo
                else "PENDING"
            ),
            "order_count": int(
                order_counts[batch_number]
            ),
            "item_count": int(
                item_counts[batch_number]
            ),
            "synthetic_timestamp_min": (
                date_bounds[batch_number][0]
            ),
            "synthetic_timestamp_max": (
                date_bounds[batch_number][1]
            ),
            "files": {
                "orders.csv": {
                    "bytes": orders_file.stat().st_size,
                    "sha256": sha256_file(orders_file),
                },
                "order_items.csv": {
                    "bytes": items_file.stat().st_size,
                    "sha256": sha256_file(items_file),
                },
            },
        }

        with (
            batch_dir / "_READY.json"
        ).open("w", encoding="utf-8") as file:
            json.dump(
                manifest,
                file,
                indent=2,
                ensure_ascii=False,
            )

    summary = {
        "batch_size": batch_size,
        "total_batches": total_batches,
        "regular_batches": (
            total_batches - demo_batches
        ),
        "presentation_batches": demo_batches,
        "total_orders": int(order_counts.sum()),
        "total_order_items": int(item_counts.sum()),
        "batch_sequence_is_upload_order_not_calendar_day": True,
    }

    with (
        OUTPUT_DIR / "batch_summary.json"
    ).open("w", encoding="utf-8") as file:
        json.dump(summary, file, indent=2)

    print("\nBatch generation completed!")
    print(json.dumps(summary, indent=2))


# ==========================================
# MAIN
# ==========================================

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--batch-size",
        type=int,
        default=10000,
    )

    parser.add_argument(
        "--chunk-size",
        type=int,
        default=200000,
    )

    parser.add_argument(
        "--demo-batches",
        type=int,
        default=1,
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
    )

    args = parser.parse_args()

    create_batches(
        batch_size=args.batch_size,
        chunk_size=args.chunk_size,
        demo_batches=args.demo_batches,
        overwrite=args.overwrite,
    )


if __name__ == "__main__":
    main()
