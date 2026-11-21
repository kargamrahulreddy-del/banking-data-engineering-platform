
from banking_pipeline.batch.gcs_batch_processor import (
    validate_numeric_field,
    validate_unique_ids,
    validate_foreign_keys,
)


def test_negative_transaction_amount():
    transactions = [
        {"transaction_id": "TXN001", "amount": "500"},
        {"transaction_id": "TXN002", "amount": "-200"},
        {"transaction_id": "TXN003", "amount": "0"},
        {"transaction_id": "TXN004", "amount": "1500"},
    ]

    valid, rejected = validate_numeric_field(
        transactions,
        "amount",
        "transactions",
        allow_zero=False
    )

    assert len(valid) == 2
    assert len(rejected) == 2
    assert rejected[0]["_rejection_reason"]


def test_duplicate_transaction_id():
    transactions = [
        {"transaction_id": "TXN001"},
        {"transaction_id": "TXN001"},
        {"transaction_id": "TXN002"},
    ]

    valid, rejected = validate_unique_ids(
        transactions,
        "transaction_id",
        "transactions"
    )

    assert len(valid) == 2
    assert len(rejected) == 1


def test_invalid_account_reference():
    transactions = [
        {"transaction_id": "TXN001", "account_id": "ACC001"},
        {"transaction_id": "TXN002", "account_id": "ACC999"},
    ]

    valid, rejected = validate_foreign_keys(
        transactions,
        "account_id",
        {"ACC001", "ACC002"},
        "transactions"
    )

    assert len(valid) == 1
    assert len(rejected) == 1


if __name__ == "__main__":
    test_negative_transaction_amount()
    test_duplicate_transaction_id()
    test_invalid_account_reference()

    print("All 3 negative validation tests passed.")
