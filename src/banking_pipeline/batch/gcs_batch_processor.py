
import csv
import io
from pathlib import Path
from decimal import Decimal, InvalidOperation
import uuid

from google.cloud import storage


# GCP configuration
PROJECT_ID = "banking-data-platform-rahul"
BUCKET_NAME = "realtime-buckets"
# Batch selection: use the verified ingestion run
INGESTION_DATE = "2026-11-21"
RUN_ID = "aa4e592a1b9646b9ae0816af0c10f62e"
PROCESSING_RUN_ID = uuid.uuid4().hex

# GCS folders
RAW_PREFIX = "raw"
PROCESSED_PREFIX = "processed"

# Local temporary processing directory
PROJECT_ROOT = Path(__file__).resolve().parents[3]
TEMP_DIR = PROJECT_ROOT / "data" / "processed"


def create_gcs_client():
    """Create an authenticated GCS client."""
    return storage.Client(project=PROJECT_ID)


def download_csv(bucket, source_path):
    """Download a CSV file from GCS and return its records."""
    blob = bucket.blob(source_path)

    if not blob.exists():
        raise FileNotFoundError(
            f"Source object not found: {source_path}"
        )

    csv_content = blob.download_as_text(encoding="utf-8")

    reader = csv.DictReader(io.StringIO(csv_content))
    records = list(reader)

    print(f"Downloaded: {source_path}")
    print(f"Records: {len(records)}")

    return records


def upload_csv(bucket, destination_path, records):
    """Upload processed records to GCS as CSV."""
    if not records:
        raise ValueError(
            f"No valid records to upload: {destination_path}"
        )

    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=list(records[0].keys())
    )

    writer.writeheader()
    writer.writerows(records)

    blob = bucket.blob(destination_path)

    blob.upload_from_string(
        output.getvalue(),
        content_type="text/csv",
        if_generation_match=0
    )

    print(f"Processed file uploaded: {destination_path}")
    print(f"Valid records: {len(records)}")


def validate_required_fields(records, required_fields, dataset):
    valid_records = []
    rejected_records = []

    for record in records:
        missing = [
            field for field in required_fields
            if not record.get(field, "").strip()
        ]

        if missing:
            record["_rejection_reason"] = (
                f"Missing required fields: {missing}"
            )
            rejected_records.append(record)
        else:
            valid_records.append(record)

    return valid_records, rejected_records


def validate_unique_ids(records, id_field, dataset):
    valid_records = []
    rejected_records = []
    seen_ids = set()

    for record in records:
        record_id = record[id_field]

        if record_id in seen_ids:
            record["_rejection_reason"] = (
                f"Duplicate {id_field}: {record_id}"
            )
            rejected_records.append(record)
        else:
            seen_ids.add(record_id)
            valid_records.append(record)

    return valid_records, rejected_records


def validate_foreign_keys(
    records, child_field, valid_parent_ids, dataset
):
    valid_records = []
    rejected_records = []

    for record in records:
        reference = record[child_field]

        if reference not in valid_parent_ids:
            record["_rejection_reason"] = (
                f"Invalid {child_field}: {reference}"
            )
            rejected_records.append(record)
        else:
            valid_records.append(record)

    return valid_records, rejected_records


def validate_numeric_field(
    records, field, dataset, allow_zero
):
    valid_records = []
    rejected_records = []

    for record in records:
        try:
            value = Decimal(record[field])

            if not value.is_finite():
                raise InvalidOperation

            if allow_zero and value < 0:
                raise InvalidOperation

            if not allow_zero and value <= 0:
                raise InvalidOperation

            valid_records.append(record)

        except (InvalidOperation, ValueError):
            record["_rejection_reason"] = (
                f"Invalid numeric value for {field}: "
                f"{record[field]}"
            )
            rejected_records.append(record)

    return valid_records, rejected_records


def merge_rejections(*rejection_groups):
    result = []

    for group in rejection_groups:
        result.extend(group)

    return result



def main():
    print("Starting GCS batch processing...")

    client = create_gcs_client()
    bucket = client.bucket(BUCKET_NAME)

    datasets = {
        "customers": "customers.csv",
        "accounts": "accounts.csv",
        "transactions": "transactions.csv"
    }

    downloaded_data = {}

    for folder, filename in datasets.items():
        source_path = (
            f"{RAW_PREFIX}/{folder}/"
            f"ingestion_date={INGESTION_DATE}/"
            f"run_id={RUN_ID}/{filename}"
        )

        downloaded_data[folder] = download_csv(
            bucket, source_path
        )

    print("\nStarting data-quality validation...")

    # CUSTOMERS
    customers, rejected_customers_required = (
        validate_required_fields(
            downloaded_data["customers"],
            ["customer_id", "first_name", "last_name",
             "city", "email", "created_at"],
            "customers"
        )
    )

    customers, rejected_customers_duplicates = (
        validate_unique_ids(
            customers, "customer_id", "customers"
        )
    )

    rejected_customers = merge_rejections(
        rejected_customers_required,
        rejected_customers_duplicates
    )

    # ACCOUNTS
    accounts, rejected_accounts_required = (
        validate_required_fields(
            downloaded_data["accounts"],
            ["account_id", "customer_id",
             "account_type", "balance", "account_status"],
            "accounts"
        )
    )

    accounts, rejected_accounts_duplicates = (
        validate_unique_ids(
            accounts, "account_id", "accounts"
        )
    )

    valid_customer_ids = {
        record["customer_id"] for record in customers
    }

    accounts, rejected_accounts_fk = validate_foreign_keys(
        accounts, "customer_id",
        valid_customer_ids, "accounts"
    )

    accounts, rejected_accounts_balance = validate_numeric_field(
        accounts, "balance", "accounts", allow_zero=True
    )

    rejected_accounts = merge_rejections(
        rejected_accounts_required,
        rejected_accounts_duplicates,
        rejected_accounts_fk,
        rejected_accounts_balance
    )

    # TRANSACTIONS
    transactions, rejected_transactions_required = (
        validate_required_fields(
            downloaded_data["transactions"],
            ["transaction_id", "account_id",
             "transaction_type", "amount",
             "transaction_date", "currency", "status"],
            "transactions"
        )
    )

    transactions, rejected_transactions_duplicates = (
        validate_unique_ids(
            transactions, "transaction_id", "transactions"
        )
    )

    valid_account_ids = {
        record["account_id"] for record in accounts
    }

    transactions, rejected_transactions_fk = (
        validate_foreign_keys(
            transactions, "account_id",
            valid_account_ids, "transactions"
        )
    )

    transactions, rejected_transactions_amount = (
        validate_numeric_field(
            transactions, "amount",
            "transactions", allow_zero=False
        )
    )

    rejected_transactions = merge_rejections(
        rejected_transactions_required,
        rejected_transactions_duplicates,
        rejected_transactions_fk,
        rejected_transactions_amount
    )

    # FINAL REPORT
    print("\nDATA QUALITY REPORT")

    results = {
        "customers": (customers, rejected_customers),
        "accounts": (accounts, rejected_accounts),
        "transactions": (transactions, rejected_transactions)
    }

    for name, (valid, rejected) in results.items():
        print(f"\n{name.upper()}")
        print(f"Valid records: {len(valid)}")
        print(f"Rejected records: {len(rejected)}")

    total_valid = sum(
        len(valid) for valid, rejected in results.values()
    )

    total_rejected = sum(
        len(rejected) for valid, rejected in results.values()
    )

    print("\nFINAL SUMMARY")
    print(f"Total valid: {total_valid}")
    print(f"Total rejected: {total_rejected}")

    print("\nData-quality validation completed.")


    # UPLOAD VALID RECORDS TO GCS PROCESSED ZONE
    print("\nUploading valid records to GCS...")

    for dataset_name, (valid, rejected) in results.items():

        destination_path = (
            f"{PROCESSED_PREFIX}/{dataset_name}/"
            f"ingestion_date={INGESTION_DATE}/"
            f"processing_run_id={PROCESSING_RUN_ID}/{dataset_name}.csv"
        )

        if valid:
            upload_csv(bucket, destination_path, valid)

    print("\nAll valid datasets uploaded successfully.")

    # UPLOAD REJECTED RECORDS TO GCS QUARANTINE ZONE
    print("\nUploading rejected records to GCS Quarantine...")

    for dataset_name, (valid, rejected) in results.items():

        destination_path = (
            f"quarantine/{dataset_name}/"
            f"ingestion_date={INGESTION_DATE}/"
            f"processing_run_id={PROCESSING_RUN_ID}/{dataset_name}_rejected.csv"
        )

        if rejected:
            upload_csv(bucket, destination_path, rejected)
        else:
            print(
                f"{dataset_name}: No rejected records. "
                "Quarantine upload skipped."
            )

    print("\nQuarantine processing completed.")




if __name__ == "__main__":
    main()

