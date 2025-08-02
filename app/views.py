from datetime import date

from dateutil.relativedelta import relativedelta
from django.db.models import Sum
from pydantic import ValidationError
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

from .models import Customer, Loan
from .schemas import CheckEligibilitySchema, CreateLoanSchema, RegisterCustomerSchema
from .serializers import (
    CustomerSerializer,
    LoanDetailSerializer,
    LoanSerializer,
    ViewLoansSerializer,
)


@api_view(["POST"])
def register_customer(request: Request) -> Response:
    if not isinstance(request.data, dict):
        return Response(
            {"error": "Invalid data format"}, status=status.HTTP_400_BAD_REQUEST
        )
    try:
        validated_data = RegisterCustomerSchema(**request.data)
    except ValidationError as e:
        return Response(e.errors(), status=status.HTTP_400_BAD_REQUEST)

    approved_limit = round(36 * validated_data.monthly_income / 100000) * 100000

    customer_data = {
        "first_name": validated_data.first_name,
        "last_name": validated_data.last_name,
        "age": validated_data.age,
        "phone_number": validated_data.phone_number,
        "monthly_salary": validated_data.monthly_income,
        "approved_limit": approved_limit,
    }

    serializer = CustomerSerializer(data=customer_data)

    if serializer.is_valid():
        customer = serializer.save()
        response_data = {
            "customer_id": customer.customer_id,
            "name": f"{customer.first_name} {customer.last_name}",
            "age": customer.age,
            "monthly_income": customer.monthly_salary,
            "approved_limit": customer.approved_limit,
            "phone_number": customer.phone_number,
        }
        return Response(response_data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


def calculate_credit_score(customer: Customer) -> int:
    """
    Calculates the credit score for a given customer.
    """
    loans = Loan.objects.filter(customer=customer)

    # Sum of current loans vs approved limit (Hard rejection)
    current_loans = loans.filter(end_date__gte=date.today())
    current_loan_sum_agg = current_loans.aggregate(total=Sum("loan_amount"))
    current_loan_sum = current_loan_sum_agg.get("total") or 0
    if current_loan_sum > customer.approved_limit:
        return 0

    # Past Loans paid on time
    paid_on_time_emis_agg = loans.aggregate(total=Sum("emis_paid_on_time"))
    paid_on_time_emis = paid_on_time_emis_agg.get("total") or 0
    total_emis_agg = loans.aggregate(total=Sum("tenure"))
    total_emis = total_emis_agg.get("total") or 0
    paid_on_time_weight = (paid_on_time_emis / total_emis) * 30 if total_emis > 0 else 0

    # No of loans taken in past
    num_loans = loans.count()
    num_loans_weight = min(num_loans * 5, 20)

    # Loan activity in current year
    current_year = date.today().year
    loan_activity_weight = min(
        loans.filter(start_date__year=current_year).count() * 5, 20
    )

    # Loan approved volume
    total_loan_amount_agg = loans.aggregate(total=Sum("loan_amount"))
    total_loan_amount = total_loan_amount_agg.get("total") or 0
    loan_volume_weight = 0
    if customer.approved_limit > 0 and total_loan_amount <= customer.approved_limit:
        loan_volume_weight = min((total_loan_amount / customer.approved_limit) * 15, 15)

    # Start with a baseline score so new customers are eligible.
    base_score = 25

    credit_score = (
        base_score
        + paid_on_time_weight
        + num_loans_weight
        + loan_activity_weight
        + loan_volume_weight
    )

    return round(credit_score)


def calculate_monthly_installment(
    loan_amount: float, interest_rate: float, tenure: int
) -> float:
    if tenure == 0:
        return float("inf")

    monthly_interest_rate = (interest_rate / 100) / 12
    if monthly_interest_rate == 0:
        return loan_amount / tenure

    numerator = (
        loan_amount * monthly_interest_rate * ((1 + monthly_interest_rate) ** tenure)
    )
    denominator = ((1 + monthly_interest_rate) ** tenure) - 1

    if denominator == 0:
        return float("inf")

    return numerator / denominator


def get_eligibility_status(
    customer: Customer, loan_amount: float, interest_rate: float, tenure: int
) -> dict:
    current_emis_agg = Loan.objects.filter(
        customer=customer, end_date__gte=date.today()
    ).aggregate(total=Sum("monthly_repayment"))
    current_emis = current_emis_agg.get("total") or 0

    if current_emis > customer.monthly_salary * 0.5:
        return {
            "approval": False,
            "corrected_interest_rate": interest_rate,
            "monthly_installment": 0,
        }

    credit_score = calculate_credit_score(customer)
    approval = False
    corrected_interest_rate = interest_rate

    if credit_score > 50:
        approval = True
    elif 30 < credit_score <= 50:
        approval = True
        corrected_interest_rate = max(interest_rate, 12.0)
    elif 10 < credit_score <= 30:
        approval = True
        corrected_interest_rate = max(interest_rate, 16.0)
    else:  # credit_score <= 10
        approval = False

    monthly_installment = 0
    if approval:
        monthly_installment = calculate_monthly_installment(
            loan_amount, corrected_interest_rate, tenure
        )

    return {
        "approval": approval,
        "corrected_interest_rate": corrected_interest_rate,
        "monthly_installment": round(monthly_installment, 2),
    }


@api_view(["POST"])
def check_eligibility(request: Request) -> Response:
    try:
        validated_data = CheckEligibilitySchema(**request.data)
    except ValidationError as e:
        return Response(e.errors(), status=status.HTTP_400_BAD_REQUEST)

    try:
        customer = Customer.objects.get(pk=validated_data.customer_id)
    except Customer.DoesNotExist:
        return Response(
            {"error": "Customer not found"}, status=status.HTTP_404_NOT_FOUND
        )

    eligibility = get_eligibility_status(
        customer,
        validated_data.loan_amount,
        validated_data.interest_rate,
        validated_data.tenure,
    )

    response_data = {
        "customer_id": validated_data.customer_id,
        "approval": eligibility["approval"],
        "interest_rate": validated_data.interest_rate,
        "corrected_interest_rate": eligibility["corrected_interest_rate"]
        if eligibility["approval"]
        else None,
        "tenure": validated_data.tenure,
        "monthly_installment": eligibility["monthly_installment"],
    }
    return Response(response_data, status=status.HTTP_200_OK)


@api_view(["POST"])
def create_loan(request: Request) -> Response:
    try:
        validated_data = CreateLoanSchema(**request.data)
    except ValidationError as e:
        return Response(e.errors(), status=status.HTTP_400_BAD_REQUEST)

    try:
        customer = Customer.objects.get(pk=validated_data.customer_id)
    except Customer.DoesNotExist:
        return Response(
            {"error": "Customer not found"}, status=status.HTTP_404_NOT_FOUND
        )

    eligibility = get_eligibility_status(
        customer,
        validated_data.loan_amount,
        validated_data.interest_rate,
        validated_data.tenure,
    )

    if not eligibility["approval"]:
        return Response(
            {
                "loan_id": None,
                "customer_id": validated_data.customer_id,
                "loan_approved": False,
                "message": "Loan not approved based on eligibility check.",
                "monthly_installment": 0,
            },
            status=status.HTTP_200_OK,
        )

    start_date = date.today()
    end_date = start_date + relativedelta(months=validated_data.tenure)

    loan_data = {
        "customer": customer.pk,
        "loan_amount": validated_data.loan_amount,
        "interest_rate": eligibility["corrected_interest_rate"],
        "tenure": validated_data.tenure,
        "monthly_repayment": eligibility["monthly_installment"],
        "emis_paid_on_time": 0,  # New loan
        "start_date": start_date,
        "end_date": end_date,
    }

    serializer = LoanSerializer(data=loan_data)
    if serializer.is_valid():
        loan = serializer.save()
        return Response(
            {
                "loan_id": loan.loan_id,
                "customer_id": validated_data.customer_id,
                "loan_approved": True,
                "message": "Loan approved successfully!",
                "monthly_installment": eligibility["monthly_installment"],
            },
            status=status.HTTP_201_CREATED,
        )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
def view_loan(request: Request, loan_id: int) -> Response:
    try:
        loan = Loan.objects.select_related("customer").get(pk=loan_id)
    except Loan.DoesNotExist:
        return Response({"error": "Loan not found"}, status=status.HTTP_404_NOT_FOUND)

    serializer = LoanDetailSerializer(loan)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET"])
def view_customer_loans(request: Request, customer_id: int) -> Response:
    if not Customer.objects.filter(pk=customer_id).exists():
        return Response(
            {"error": "Customer not found"}, status=status.HTTP_404_NOT_FOUND
        )

    loans = Loan.objects.filter(customer_id=customer_id)
    serializer = ViewLoansSerializer(loans, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)
