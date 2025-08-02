from datetime import date

from dateutil.relativedelta import relativedelta
from rest_framework import serializers

from .models import Customer, Loan


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = "__all__"


class LoanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Loan
        fields = "__all__"


class LoanDetailSerializer(serializers.ModelSerializer):
    # Nest the customer details in the response
    customer = CustomerSerializer()

    class Meta:
        model = Loan
        fields = [
            "loan_id",
            "customer",
            "loan_amount",
            "interest_rate",
            "monthly_repayment",
            "tenure",
        ]


class ViewLoansSerializer(serializers.ModelSerializer):
    repayments_left = serializers.SerializerMethodField()

    class Meta:
        model = Loan
        fields = [
            "loan_id",
            "loan_amount",
            "interest_rate",
            "monthly_repayment",
            "repayments_left",
        ]

    def get_repayments_left(self, obj: Loan) -> int:
        # Calculate the number of EMIs left to be paid.
        today = date.today()
        end_date = obj.end_date

        if today > end_date:
            return 0

        # Calculate the difference in months
        delta = relativedelta(end_date, today)
        months_left = delta.years * 12 + delta.months

        if delta.days > 0:
            months_left += 1

        return months_left
