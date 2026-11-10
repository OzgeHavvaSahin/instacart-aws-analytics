
import time
import logging

import boto3

from config import (
    AWS_REGION,
    ATHENA_DATABASE,
    ATHENA_WORKGROUP,
    ATHENA_OUTPUT_LOCATION
)

logger = logging.getLogger(__name__)

athena = boto3.client(
    "athena",
    region_name=AWS_REGION
)

QUERY_TIMEOUT = 25
POLL_INTERVAL = 0.5
MAX_RESULT_ROWS = 1000


def run_query(sql, max_rows=MAX_RESULT_ROWS):
    """
    Athena SQL sorgusunu calistirir.
    Sonucu list[dict] formatinda dondurur.
    """

    if not isinstance(sql, str) or not sql.strip():
        raise ValueError("SQL query cannot be empty")

    if not 1 <= max_rows <= MAX_RESULT_ROWS:
        raise ValueError("Invalid max_rows")

    # 1. Start Athena query
    response = athena.start_query_execution(
        QueryString=sql,
        QueryExecutionContext={
            "Database": ATHENA_DATABASE,
            "Catalog": "AwsDataCatalog"
        },
        WorkGroup=ATHENA_WORKGROUP,
        ResultConfiguration={
            "OutputLocation": ATHENA_OUTPUT_LOCATION
        }
    )

    query_id = response["QueryExecutionId"]

    logger.info("Athena query started: %s", query_id)

    # 2. Wait for query completion
    deadline = time.monotonic() + QUERY_TIMEOUT

    while True:
        execution = athena.get_query_execution(
            QueryExecutionId=query_id
        )

        status = execution["QueryExecution"]["Status"]
        state = status["State"]

        if state == "SUCCEEDED":
            break

        if state in ("FAILED", "CANCELLED"):
            reason = status.get(
                "StateChangeReason",
                "Unknown reason"
            )
            raise RuntimeError(
                f"Athena query {state}: {reason}"
            )

        if time.monotonic() >= deadline:
            athena.stop_query_execution(
                QueryExecutionId=query_id
            )
            raise TimeoutError(
                f"Athena query timeout: {query_id}"
            )

        time.sleep(POLL_INTERVAL)

    logger.info("Athena query succeeded: %s", query_id)

    # 3. Fetch result pages
    rows = []
    columns = None
    next_token = None
    first_page = True

    while len(rows) < max_rows:
        params = {
            "QueryExecutionId": query_id,
            "MaxResults": min(1000, max_rows + 1)
        }

        if next_token:
            params["NextToken"] = next_token

        result = athena.get_query_results(**params)

        if columns is None:
            columns = [
                col["Name"]
                for col in result["ResultSet"][
                    "ResultSetMetadata"
                ]["ColumnInfo"]
            ]

        page_rows = result["ResultSet"]["Rows"]

        # Athena SELECT results include a header row
        if first_page:
            page_rows = page_rows[1:]
            first_page = False

        for row in page_rows:
            values = [
                cell.get("VarCharValue")
                for cell in row.get("Data", [])
            ]

            record = dict(zip(columns, values))
            rows.append(record)

            if len(rows) >= max_rows:
                break

        next_token = result.get("NextToken")

        if not next_token:
            break

    return {
        "query_id": query_id,
        "rows": rows,
        "row_count": len(rows)
    }
