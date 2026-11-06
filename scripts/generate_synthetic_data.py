
from pathlib import Path
from datetime import date, timedelta
import shutil
import zlib

import numpy as np
import pandas as pd


# ==========================================
# CONFIGURATION
# ==========================================

BASE_DIR = Path(__file__).resolve().parents[1]

INPUT_DIR = BASE_DIR / "data" / "raw"
OUTPUT_DIR = BASE_DIR / "data" / "synthetic_raw"

# Sabit tarih: tekrar çalıştırıldığında değişmez.
LATEST_ORDER_DATE = date(2026, 11, 1)

# Müşterilerin son siparişlerini 90 güne yayacağız.
MAX_STAGGER_DAYS = 90

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ==========================================
# 1. SYNTHETIC PRODUCT PRICES
# ==========================================

# USD cinsinden, sentetik fiyat aralıkları.
# Bunlar gerçek Instacart fiyatları değildir.

PRICE_RANGES = {
    "produce": (0.79, 12.99),
    "dairy eggs": (1.49, 15.99),
    "meat seafood": (3.99, 39.99),
    "bakery": (1.49, 14.99),
    "beverages": (0.99, 19.99),
    "snacks": (0.79, 12.99),
    "frozen": (1.99, 19.99),
    "pantry": (0.99, 24.99),
    "breakfast": (1.49, 15.99),
    "canned goods": (0.79, 9.99),
    "dry goods pasta": (0.99, 13.99),
    "deli": (1.99, 19.99),
    "household": (2.49, 39.99),
    "personal care": (1.99, 29.99),
    "babies": (2.99, 49.99),
    "pets": (2.99, 49.99),
    "alcohol": (4.99, 49.99),
    "bulk": (2.99, 29.99),
    "international": (1.49, 19.99),
    "missing": (1.99, 14.99),
    "other": (1.99, 14.99),
}


def stable_fraction(value: str) -> float:
    """Aynı metin için her zaman aynı 0-1 değerini üretir."""
    number = zlib.crc32(value.encode("utf-8"))
    return number / 4294967295


def generate_price(product_id, product_name, department):
    department = str(department).lower().strip()

    min_price, max_price = PRICE_RANGES.get(
        department, (1.99, 19.99)
    )

    key = f"{product_id}|{product_name}|price_v1"
    fraction = stable_fraction(key)

    min_cents = round(min_price * 100)
    max_cents = round(max_price * 100)

    cents = min_cents + int(
        fraction * (max_cents - min_cents)
    )

    return round(cents / 100, 2)


def generate_product_prices():
    print("\n[1/3] Generating synthetic product prices...")

    products = pd.read_csv(INPUT_DIR / "products.csv")
    departments = pd.read_csv(INPUT_DIR / "departments.csv")

    merged = products.merge(
        departments,
        on="department_id",
        how="left",
        validate="many_to_one"
    )

    merged["unit_price"] = [
        generate_price(pid, name, dept)
        for pid, name, dept in zip(
            merged["product_id"],
            merged["product_name"],
            merged["department"]
        )
    ]

    # Orijinal products kolonları + unit_price.
    result = merged[
        list(products.columns) + ["unit_price"]
    ]

    result.to_csv(
        OUTPUT_DIR / "products.csv",
        index=False,
        float_format="%.2f"
    )

    print(f"Products processed: {len(result):,}")
    print(
        "Price range: "
        f"${result['unit_price'].min():.2f} - "
        f"${result['unit_price'].max():.2f}"
    )


# ==========================================
# 2. SYNTHETIC ORDER TIMESTAMPS
# ==========================================

def generate_order_timestamps():
    print("\n[2/3] Generating synthetic order timestamps...")

    orders = pd.read_csv(
        INPUT_DIR / "orders.csv",
        dtype={
            "order_id": "int32",
            "user_id": "int32",
            "order_number": "int16",
            "order_dow": "int8",
            "order_hour_of_day": "int8",
            "days_since_prior_order": "float32",
            "eval_set": "category",
        }
    )

    original_columns = list(orders.columns)

    # Aynı müşterinin siparişlerini kronolojik sıraya koy.
    orders = orders.sort_values(
        ["user_id", "order_number"]
    ).reset_index(drop=True)

    group = orders.groupby("user_id", sort=False)

    # Bir önceki siparişin haftanın günü.
    previous_dow = group["order_dow"].shift()

    # İlk siparişin önceki siparişi bulunmaz.
    gaps = (
        orders["days_since_prior_order"]
        .fillna(0)
        .astype("int32")
        .to_numpy()
    )

    current_dow = orders["order_dow"].to_numpy()
    prev_dow = previous_dow.fillna(0).to_numpy().astype("int32")

    # Instacart'ta 30 gün değeri 30 veya daha fazlası
    # anlamına gelebilir.
    # 30 gün olarak görünen aralığı, gün koduyla
    # tutarlı olacak en yakın 30-36 gün değerine getir.
    capped = (
        (gaps == 30)
        & previous_dow.notna().to_numpy()
    )

    expected_diff = (current_dow - prev_dow) % 7
    adjustment = (expected_diff - 30) % 7

    gaps[capped] += adjustment[capped]

    orders["_gap"] = gaps

    # Her müşteri için toplam geçmiş gün farkı.
    running_days = (
        orders.groupby("user_id", sort=False)["_gap"]
        .cumsum()
    )

    total_days = (
        running_days.groupby(orders["user_id"])
        .transform("max")
    )

    days_before_last = total_days - running_days

    # Müşterinin en son siparişindeki gün kodu.
    last_dow = (
        orders.groupby("user_id", sort=False)["order_dow"]
        .transform("last")
    )

    # Son siparişler aynı güne yığılmasın.
    # Her müşteri için sabit, deterministik dağılım.
    stagger = (
        (
            orders["user_id"].astype("int64") * 2654435761
        ) % (MAX_STAGGER_DAYS + 1)
    )

    base = pd.Timestamp(LATEST_ORDER_DATE)
    candidate = (
        base - pd.to_timedelta(stagger, unit="D")
    )

    # Varsayım: Instacart order_dow kodunda 0 = Pazar.
    # Pandas weekday: Pazartesi=0, Pazar=6.
    candidate_dow = (candidate.dt.dayofweek + 1) % 7

    weekday_adjustment = (
        candidate_dow - last_dow
    ) % 7

    latest_dates = (
        candidate -
        pd.to_timedelta(weekday_adjustment, unit="D")
    )

    order_dates = (
        latest_dates -
        pd.to_timedelta(days_before_last, unit="D")
    )

    # Orijinal saat bilgisini koruyoruz.
    timestamps = (
        order_dates +
        pd.to_timedelta(
            orders["order_hour_of_day"],
            unit="h"
        )
    )

    orders["synthetic_order_timestamp"] = (
        timestamps.dt.strftime("%Y-%m-%d %H:%M:%S")
    )

    # Orijinal gün koduyla tutarlılık kontrolü.
    generated_dow = (timestamps.dt.dayofweek + 1) % 7
    mismatches = int(
        (generated_dow != orders["order_dow"]).sum()
    )

    if mismatches:
        raise ValueError(
            f"Weekday mismatch detected in {mismatches} orders. "
            "Review the original gap/day fields."
        )

    # Yardımcı sütunları çıktıdan çıkar.
    result = orders[
        original_columns + ["synthetic_order_timestamp"]
    ]

    # Orijinal order_id sırasına dön.
    result = result.sort_values("order_id")

    output_path = OUTPUT_DIR / "orders.csv"

    result.to_csv(output_path, index=False)

    print(f"Orders processed: {len(result):,}")
    print(
        "Date range: "
        f"{timestamps.min()} -> {timestamps.max()}"
    )
    print(f"Weekday mismatches: {mismatches}")


# ==========================================
# 3. COPY UNCHANGED REFERENCE/ITEM FILES
# ==========================================

def copy_unchanged_files():
    print("\n[3/3] Copying unchanged files...")

    filenames = [
        "aisles.csv",
        "departments.csv",
        "order_products__prior.csv",
        "order_products__train.csv",
    ]

    for filename in filenames:
        source = INPUT_DIR / filename
        destination = OUTPUT_DIR / filename

        shutil.copy2(source, destination)
        print(f"Copied: {filename}")


# ==========================================
# RUN
# ==========================================

def main():
    required_files = [
        "orders.csv",
        "products.csv",
        "departments.csv",
        "aisles.csv",
        "order_products__prior.csv",
        "order_products__train.csv",
    ]

    missing = [
        name for name in required_files
        if not (INPUT_DIR / name).exists()
    ]

    if missing:
        raise FileNotFoundError(
            f"Missing input files: {missing}"
        )

    generate_product_prices()
    generate_order_timestamps()
    copy_unchanged_files()

    print("\nSynthetic dataset generated successfully.")
    print(f"Output directory: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
