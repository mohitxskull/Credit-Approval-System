from datetime import date

from dateutil.relativedelta import relativedelta  # Import relativedelta
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Customer, Loan


class CustomerAPITests(APITestCase):
    def setUp(self):
        self.customer = Customer.objects.create(
            first_name="John",
            last_name="Doe",
            age=30,
            monthly_salary=50000,
            phone_number=1234567890,
            approved_limit=1800000,
        )
        self.loan = Loan.objects.create(
            customer=self.customer,
            loan_amount=10000,
            tenure=12,
            interest_rate=10,
            monthly_repayment=879.16,
            emis_paid_on_time=5,
            start_date=date.today() - relativedelta(months=6),
            end_date=date.today() + relativedelta(months=6),
        )

    def test_register_customer(self):
        url = reverse("register")
        data = {
            "first_name": "Jane",
            "last_name": "Doe",
            "age": 28,
            "monthly_income": 75000,
            "phone_number": 9876543210,
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Customer.objects.count(), 2)
        self.assertEqual(response.data["name"], "Jane Doe")
        self.assertEqual(response.data["approved_limit"], 2700000)

    def test_register_customer_invalid_data(self):
        url = reverse("register")
        data = {"first_name": "Jane", "last_name": "Doe", "age": -5}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_check_eligibility_approved(self):
        customer = Customer.objects.create(
            first_name="Test",
            last_name="User",
            age=40,
            monthly_salary=100000,
            phone_number=1111111111,
            approved_limit=5000000,
        )

        Loan.objects.create(
            customer=customer,
            loan_amount=50000,
            tenure=12,
            interest_rate=8,
            monthly_repayment=4349,
            emis_paid_on_time=12,
            start_date=date(2022, 1, 1),
            end_date=date(2022, 12, 31),
        )
        url = reverse("check-eligibility")
        data = {
            "customer_id": customer.customer_id,
            "loan_amount": 100000,
            "interest_rate": 10,
            "tenure": 24,
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["approval"])
        self.assertGreater(response.data["monthly_installment"], 0)

    def test_check_eligibility_corrected_interest(self):
        customer = Customer.objects.create(
            first_name="Mid",
            last_name="Tier",
            age=35,
            monthly_salary=60000,
            phone_number=2222222222,
            approved_limit=2000000,
        )
        url = reverse("check-eligibility")
        data = {
            "customer_id": customer.customer_id,
            "loan_amount": 150000,
            "interest_rate": 8,
            "tenure": 36,
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["approval"])
        self.assertGreater(response.data["corrected_interest_rate"], 8)

    def test_create_loan_approved(self):
        customer = Customer.objects.create(
            first_name="New",
            last_name="Borrower",
            age=30,
            monthly_salary=80000,
            phone_number=3333333333,
            approved_limit=2500000,
        )
        url = reverse("create-loan")
        data = {
            "customer_id": customer.customer_id,
            "loan_amount": 5000,
            "interest_rate": 12,
            "tenure": 6,
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["loan_approved"])
        self.assertIsNotNone(response.data["loan_id"])

    def test_create_loan_rejected(self):
        self.customer.monthly_salary = 1000
        self.customer.save()

        url = reverse("create-loan")
        data = {
            "customer_id": self.customer.customer_id,
            "loan_amount": 5000,
            "interest_rate": 12,
            "tenure": 6,
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["loan_approved"])
        self.assertIsNone(response.data["loan_id"])

    def test_view_loan(self):
        url = reverse("view-loan", kwargs={"loan_id": self.loan.loan_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["loan_id"], self.loan.loan_id)
        self.assertEqual(
            response.data["customer"]["customer_id"], self.customer.customer_id
        )

    def test_view_loan_not_found(self):
        url = reverse("view-loan", kwargs={"loan_id": 999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_view_customer_loans(self):
        url = reverse("view-loans", kwargs={"customer_id": self.customer.customer_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["loan_id"], self.loan.loan_id)
        self.assertIn("repayments_left", response.data[0])
