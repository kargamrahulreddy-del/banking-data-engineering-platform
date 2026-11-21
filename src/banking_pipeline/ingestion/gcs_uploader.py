
import uuid
from datetime import datetime, timezone
from pathlib import Path

from google.cloud import storage


# GCP configuration
PROJECT_ID = "banking-data-platform-rahul"
BUCKET_NAME = "realtime-buckets"

# Locate project and generated data
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data" / "generated"

# Files to upload and their GCS folders
FILES = {
    "customers.csv": "customers",
    "accounts.csv": "accounts",
    "transactions.csv": "transactions"
}


def create_gcs_client():
    """Create an authenticated GCS client."""

    return storage.Client(project=PROJECT_ID)


def upload_file(bucket, local_file, destination):
    """Upload one file without overwriting an existing object."""

    blob = bucket.blob(destination)

    blob.upload_from_filename(
        str(local_file),
        content_type="text/csv",
        if_generation_match=0
    )

    # Reload metadata from GCS
    blob.reload()

    local_size = local_file.stat().st_size
    cloud_size = blob.size

    if local_size != cloud_size:
        raise ValueError(
            f"Size mismatch for {destination}: "
            f"local={local_size}, cloud={cloud_size}"
        )

    print(f"UPLOAD SUCCESS: {destination}")
    print(f"File size: {cloud_size} bytes")
    print(f"Generation: {blob.generation}")


def main():

    # Unique identifier for this ingestion execution
    run_id = uuid.uuid4().hex

    # Current UTC ingestion date
    ingestion_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    print("Starting automated GCS ingestion...")
    print(f"Ingestion date: {ingestion_date}")
    print(f"Run ID: {run_id}")

    # Connect to GCS
    client = create_gcs_client()
    bucket = client.bucket(BUCKET_NAME)

    # Verify bucket access
    if not bucket.exists():
        raise RuntimeError(
            f"Bucket not found or inaccessible: {BUCKET_NAME}"
        )

    print(f"\nConnected to bucket: {BUCKET_NAME}")

    # Upload each dataset
    for filename, folder in FILES.items():

        local_file = DATA_DIR / filename

        if not local_file.is_file():
            raise FileNotFoundError(
                f"Local file not found: {local_file}"
            )

        destination = (
            f"raw/{folder}/"
            f"ingestion_date={ingestion_date}/"
            f"run_id={run_id}/"
            f"{filename}"
        )

        upload_file(bucket, local_file, destination)

    print("\nAll files uploaded and verified successfully.")


if __name__ == "__main__":
    main()
