
import uuid
import csv
import io
from datetime import datetime, timezone

from google.cloud import storage

from banking_pipeline.batch.gcs_batch_processor import (
    PROJECT_ID,
    BUCKET_NAME,
    validate_numeric_field,
    upload_csv,
)


def main():
    print("Starting quarantine integration test...")

    # 1. Create test transactions
    transactions = [
        {"transaction_id": "TEST001", "amount": "500"},
        {"transaction_id": "TEST002", "amount": "-200"},
        {"transaction_id": "TEST003", "amount": "0"},
    ]

    # 2. Run actual validation function
    valid, rejected = validate_numeric_field(
        transactions,
        "amount",
        "transactions",
        allow_zero=False
    )

    print(f"Valid records: {len(valid)}")
    print(f"Rejected records: {len(rejected)}")

    assert len(valid) == 1
    assert len(rejected) == 2

    # 3. Create unique test destination
    test_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    test_run_id = uuid.uuid4().hex

    destination = (
        f"quarantine/test_transactions/"
        f"test_date={test_date}/"
        f"test_run_id={test_run_id}/"
        f"transactions_rejected.csv"
    )

    # 4. Upload rejected records
    client = storage.Client(project=PROJECT_ID)
    bucket = client.bucket(BUCKET_NAME)

    upload_csv(bucket, destination, rejected)

    # 5. Download and verify uploaded file
    blob = bucket.blob(destination)
    downloaded_content = blob.download_as_text()

    reader = csv.DictReader(io.StringIO(downloaded_content))
    uploaded_records = list(reader)

    assert len(uploaded_records) == 2

    for record in uploaded_records:
        assert record.get("_rejection_reason")

    print(f"Verified quarantine records: {len(uploaded_records)}")
    print(f"GCS object: gs://{BUCKET_NAME}/{destination}")
    print("QUARANTINE INTEGRATION TEST PASSED")


if __name__ == "__main__":
    main()
