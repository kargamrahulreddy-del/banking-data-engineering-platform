
import csv
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data" / "generated"


def load_csv(filename):
    file_path = DATA_DIR / filename

    with open(file_path, "r", newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def check_required_values(records, columns, dataset_name):
    errors = []

    for row_number, record in enumerate(records, start=2):
        for column in columns:
            if not record.get(column, "").strip():
                errors.append(
                    f"{dataset_name}: Missing {column} at CSV row {row_number}"
                )

    return errors


def check_duplicates(records, column, dataset_name):
    errors = []
    seen = set()

    for record in records:
        value = record[column]

        if value in seen:
            errors.append(
                f"{dataset_name}: Duplicate {column}: {value}"
            )
        else:
            seen.add(value)

    return errors


def check_foreign_keys(child_records, child_column, parent_records,
                       parent_column, dataset_name):
    errors = []

    valid_parent_ids = {
        record[parent_column] for record in parent_records
    }

    for record in child_records:
        value = record[child_column]

        if value not in valid_parent_ids:
            errors.append(
                f"{dataset_name}: Invalid reference {child_column}: {value}"
            )

    return errors


def check_positive_amounts(transactions):
    errors = []

    for record in transactions:
        try:
            amount = float(record["amount"])

            if amount <= 0:
                errors.append(
                    f"Invalid transaction amount: {record['transaction_id']}"
                )

        except ValueError:
            errors.append(
                f"Non-numeric transaction amount: {record['transaction_id']}"
            )

    return errors


def main():
    print("Starting banking data-quality validation...\n")

    customers = load_csv("customers.csv")
    accounts = load_csv("accounts.csv")
    transactions = load_csv("transactions.csv")

    errors = []

    # 1. Required field checks
    errors += check_required_values(
        customers,
        ["customer_id", "first_name", "last_name", "email"],
        "Customers"
    )

    errors += check_required_values(
        accounts,
        ["account_id", "customer_id", "account_type"],
        "Accounts"
    )

    errors += check_required_values(
        transactions,
        ["transaction_id", "account_id", "amount"],
        "Transactions"
    )

    # 2. Duplicate primary-key checks
    errors += check_duplicates(
        customers, "customer_id", "Customers"
    )

    errors += check_duplicates(
        accounts, "account_id", "Accounts"
    )

    errors += check_duplicates(
        transactions, "transaction_id", "Transactions"
    )

    # 3. Relationship checks
    errors += check_foreign_keys(
        accounts, "customer_id",
        customers, "customer_id",
        "Accounts"
    )

    errors += check_foreign_keys(
        transactions, "account_id",
        accounts, "account_id",
        "Transactions"
    )

    # 4. Financial amount checks
    errors += check_positive_amounts(transactions)

    # 5. Final result
    print(f"Customers checked: {len(customers)}")
    print(f"Accounts checked: {len(accounts)}")
    print(f"Transactions checked: {len(transactions)}")

    print(f"\nTotal validation errors: {len(errors)}")

    if errors:
        print("\nVALIDATION FAILED")

        for error in errors:
            print(f"ERROR: {error}")

        raise SystemExit(1)

    print("\nVALIDATION PASSED")
    print("All source datasets passed the implemented checks.")


if __name__ == "__main__":
    main()
