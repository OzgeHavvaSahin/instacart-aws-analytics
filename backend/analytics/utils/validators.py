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
