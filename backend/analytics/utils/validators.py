def validate_limit(value, default=10):
    if value is None:
        return default

    try:
        limit = int(value)
    except (TypeError, ValueError):
        raise ValueError(
            "limit must be an integer"
        )

    if not 1 <= limit <= 100:
        raise ValueError(
            "limit must be between 1 and 100"
        )

    return limit


def parse_positive_int(value, name):
    if value is None or value == "":
        return None

    if not str(value).isdigit() or int(value) < 1:
        raise ValueError(
            f"{name} must be a positive integer"
        )

    return int(value)


def parse_optional_bool(value, name):
    if value is None or value == "":
        return None

    if value == "true":
        return True

    if value == "false":
        return False

    raise ValueError(
        f"{name} must be true or false"
    )


def validate_products_filters(params):
    allowed_sort_fields = {
        "units_sold",
        "estimated_revenue",
        "reorder_rate",
        "product_name",
    }

    sort_by = params.get("sort_by", "units_sold")
    sort_order = params.get("sort_order", "desc")

    if sort_by not in allowed_sort_fields:
        raise ValueError("Invalid sort_by")

    if sort_order not in {"asc", "desc"}:
        raise ValueError("Invalid sort_order")

    date_from = parse_iso_date(
        params.get("date_from"),
        "date_from"
    )

    date_to = parse_iso_date(
        params.get("date_to"),
        "date_to"
    )

    if date_from and date_to and date_from > date_to:
        raise ValueError(
            "date_from cannot be after date_to"
        )

    return {
        "department_id": parse_positive_int(
            params.get("department_id"),
            "department_id"
        ),
        "aisle_id": parse_positive_int(
            params.get("aisle_id"),
            "aisle_id"
        ),
        "reordered": parse_optional_bool(
            params.get("reordered"),
            "reordered"
        ),
        "date_from": date_from,
        "date_to": date_to,
        "sort_by": sort_by,
        "sort_order": sort_order,
        "limit": validate_limit(
            params.get("limit"),
            default=20
        ),
    }


from datetime import date


def parse_iso_date(value, name):
    if value is None or value == "":
        return None

    try:
        parsed = date.fromisoformat(value)
    except (ValueError, TypeError):
        raise ValueError(
            f"{name} must use YYYY-MM-DD format"
        )

    if parsed.isoformat() != value:
        raise ValueError(
            f"{name} must use YYYY-MM-DD format"
        )

    return parsed.isoformat()


def validate_overview_filters(params):
    date_from = parse_iso_date(
        params.get("date_from"),
        "date_from"
    )

    date_to = parse_iso_date(
        params.get("date_to"),
        "date_to"
    )

    if date_from and date_to:
        if date_from > date_to:
            raise ValueError(
                "date_from cannot be after date_to"
            )

    return {
        "date_from": date_from,
        "date_to": date_to,
        "department_id": parse_positive_int(
            params.get("department_id"),
            "department_id"
        ),
        "aisle_id": parse_positive_int(
            params.get("aisle_id"),
            "aisle_id"
        ),
        "reordered": parse_optional_bool(
            params.get("reordered"),
            "reordered"
        ),
    }
