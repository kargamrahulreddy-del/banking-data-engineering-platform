
import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

# Keep generated random data reproducible
random.seed(42)

# Find the project root directory
PROJECT_ROOT = Path(__file__).resolve().parents[3]

# Define where generated CSV files will be stored
OUTPUT_DIR = PROJECT_ROOT / "data" / "generated"

# Create the output directory if it does not exist
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def generate_customers(count=1000):
    customers = []

    for customer_id in range(1, count + 1):
        customer = {
            "customer_id": f"CUST{customer_id:05d}",
            "first_name": random.choice(
                ["Rahul", "Amit", "Priya", "Sneha", "Arjun"]
            ),
            "last_name": random.choice(
                ["Reddy", "Sharma", "Kumar", "Patel", "Rao"]
            ),
            "city": random.choice(
                ["Hyderabad", "Bangalore", "Mumbai", "Chennai"]
            ),
            "email": f"customer{customer_id}@example.com",
            "created_at": datetime.now().strftime("%Y-%m-%d")
        }

        customers.append(customer)

    return customers


def generate_accounts(customers):
    accounts = []

    for index, customer in enumerate(customers, start=1):
        account = {
            "account_id": f"ACC{index:05d}",
            "customer_id": customer["customer_id"],
            "account_type": random.choice(["SAVINGS", "CURRENT"]),
            "balance": round(random.uniform(1000, 200000), 2),
            "account_status": random.choice(
                ["ACTIVE", "ACTIVE", "ACTIVE", "INACTIVE"]
            )
        }

        accounts.append(account)

    return accounts


def generate_transactions(accounts, count=5000):
    transactions = []

    for transaction_id in range(1, count + 1):
        account = random.choice(accounts)

        transaction_date = datetime.now() - timedelta(
            days=random.randint(0, 90)
        )

        transaction = {
            "transaction_id": f"TXN{transaction_id:07d}",
            "account_id": account["account_id"],
            "transaction_type": random.choice(["CREDIT", "DEBIT"]),
            "amount": round(random.uniform(100, 50000), 2),
            "transaction_date": transaction_date.strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "currency": "INR",
            "status": random.choice(
                ["SUCCESS", "SUCCESS", "SUCCESS", "FAILED"]
            )
        }

        transactions.append(transaction)

    return transactions


def write_csv(filename, records):
    if not records:
        raise ValueError(f"No records available for {filename}")

    file_path = OUTPUT_DIR / filename

    with open(file_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=records[0].keys()
        )

        writer.writeheader()
        writer.writerows(records)

    print(f"Created: {file_path} | Rows: {len(records)}")


def main():
    customers = generate_customers()
    accounts = generate_accounts(customers)
    transactions = generate_transactions(accounts)

    write_csv("customers.csv", customers)
    write_csv("accounts.csv", accounts)
    write_csv("transactions.csv", transactions)

    print("\nBanking source data generation completed.")


if __name__ == "__main__":
    main()
