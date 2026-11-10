
import os

# AWS Region
AWS_REGION = os.getenv(
    "AWS_REGION",
    "eu-north-1"
)

# Athena Database
ATHENA_DATABASE = os.getenv(
    "ATHENA_DATABASE",
    "instacart_db"
)

# Athena Workgroup
ATHENA_WORKGROUP = os.getenv(
    "ATHENA_WORKGROUP",
    "instacart-workgroup"
)

# Athena Query Results S3 Location
ATHENA_OUTPUT_LOCATION = os.getenv(
    "ATHENA_OUTPUT_LOCATION",
    "s3://instacart-ecom-data-raw/athena-results/"
)
