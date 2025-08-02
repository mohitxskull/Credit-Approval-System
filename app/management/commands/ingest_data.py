from typing import Any

import pandas as pd
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from app.models import Customer, Loan


class Command(BaseCommand):
    help = "Ingest data from Excel files into the database"

    def handle(self, *args: Any, **kwargs: Any) -> None:
        # Define file paths
        customer_file = "customer_data.xlsx - Sheet1.csv"
        loan_file = "loan_data.xlsx - Sheet1.csv"

        # Ingest Customer Data
        try:
            self.stdout.write(f"Reading customer data from {customer_file}...")
            # Use read_excel for .xlsx files
            customer_df = pd.read_excel("customer_data.xlsx", sheet_name="Sheet1")

            # Standardize column names
            customer_df.columns = customer_df.columns.str.strip()

            customers_to_create = []
            for _, row in customer_df.iterrows():
                customers_to_create.append(
                    Customer(
                        customer_id=row["Customer ID"],
                        first_name=row["First Name"],
                        last_name=row["Last Name"],
                        age=row["Age"],
                        phone_number=row["Phone Number"],
                        monthly_salary=row["Monthly Salary"],
                        approved_limit=row["Approved Limit"],
                    )
                )

            Customer.objects.bulk_create(customers_to_create, ignore_conflicts=True)
            self.stdout.write(
                self.style.SUCCESS("Successfully ingested customer data.")
            )

            self.stdout.write("Resetting customer ID sequence...")
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT setval(pg_get_serial_sequence('app_customer', 'customer_id'), COALESCE((SELECT MAX(customer_id) FROM app_customer), 1));"
                )
            self.stdout.write(self.style.SUCCESS("Customer ID sequence reset."))

        except FileNotFoundError:
            raise CommandError(f"Error: {customer_file} not found.")
        except Exception as e:
            raise CommandError(f"An error occurred during customer data ingestion: {e}")

        try:
            self.stdout.write(f"Reading loan data from {loan_file}...")
            # Use read_excel for .xlsx files
            loan_df = pd.read_excel("loan_data.xlsx", sheet_name="Sheet1")

            loan_df.columns = loan_df.columns.str.strip()

            loans_to_create = []
            for _, row in loan_df.iterrows():
                if Customer.objects.filter(customer_id=row["Customer ID"]).exists():
                    loans_to_create.append(
                        Loan(
                            loan_id=row["Loan ID"],
                            customer_id=row["Customer ID"],
                            loan_amount=row["Loan Amount"],
                            tenure=row["Tenure"],
                            interest_rate=row["Interest Rate"],
                            monthly_repayment=row["Monthly payment"],
                            emis_paid_on_time=row["EMIs paid on Time"],
                            start_date=row["Date of Approval"],
                            end_date=row["End Date"],
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Customer with ID {row['Customer ID']} not found. Skipping loan {row['Loan ID']}."
                        )
                    )

            Loan.objects.bulk_create(loans_to_create, ignore_conflicts=True)
            self.stdout.write(self.style.SUCCESS("Successfully ingested loan data."))

            self.stdout.write("Resetting loan ID sequence...")
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT setval(pg_get_serial_sequence('app_loan', 'loan_id'), COALESCE((SELECT MAX(loan_id) FROM app_loan), 1));"
                )
            self.stdout.write(self.style.SUCCESS("Loan ID sequence reset."))

        except FileNotFoundError:
            raise CommandError(f"Error: {loan_file} not found.")
        except Exception as e:
            raise CommandError(f"An error occurred during loan data ingestion: {e}")
