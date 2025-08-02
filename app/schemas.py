from pydantic import BaseModel, Field


class RegisterCustomerSchema(BaseModel):
    first_name: str
    last_name: str
    age: int = Field(..., gt=0)
    monthly_income: float = Field(..., gt=0)
    phone_number: int


class CheckEligibilitySchema(BaseModel):
    customer_id: int
    loan_amount: float = Field(..., gt=0)
    interest_rate: float = Field(..., ge=0)
    tenure: int = Field(..., gt=0)


class CreateLoanSchema(BaseModel):
    customer_id: int
    loan_amount: float = Field(..., gt=0)
    interest_rate: float = Field(..., ge=0)
    tenure: int = Field(..., gt=0)
