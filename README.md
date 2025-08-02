# Credit Approval System

A Django REST API for managing customer credit approvals and loan processing.

## Features

- Customer registration with automatic credit limit calculation
- Credit score calculation based on loan history
- Loan eligibility checking
- Loan creation and management
- Customer loan history viewing

## Tech Stack

- **Backend**: Django + Django REST Framework
- **Database**: PostgreSQL 17
- **Validation**: Pydantic schemas
- **Containerization**: Docker & Docker Compose

## Quick Start with Docker

### Prerequisites

- Docker
- Docker Compose

### Running the Application

1. Clone the repository:
```bash
git clone https://github.com/mohitxskull/Credit-Approval-System
cd Credit-Approval-System
```

2. Start the services:
```bash
docker compose up --build
```

This will:
- Start PostgreSQL 17 database
- Build and run the Django application
- Automatically run migrations
- Expose the API on `http://localhost:8000`

3. The API will be available at:
- Base URL: `http://127.0.0.1:8000`
- Admin Panel: `http://127.0.0.1:8000/admin`

### Environment Variables

Copy `.env.example` to `.env` and modify as needed:
```bash
cp .env.example .env
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/register/` | Register a new customer |
| POST | `/api/check-eligibility/` | Check loan eligibility |
| POST | `/api/create-loan/` | Create a new loan |
| GET | `/api/view-loan/<loan_id>/` | View specific loan details |
| GET | `/api/view-loans/<customer_id>/` | View all loans for a customer |

## API Testing

Use the provided Yaak request files in the `yaak/` directory for API testing.

## Development Commands

### Docker Commands

```bash
# Start services
docker compose up

# Start services in background
docker compose up -d

# Rebuild and start
docker compose up --build

# Stop services
docker compose down

# View logs
docker compose logs web
docker compose logs db

# Execute commands in running container
docker compose exec web python manage.py shell
docker compose exec web python manage.py createsuperuser
```

### Database Commands

```bash
# Run migrations
docker compose exec web python manage.py migrate

# Create migrations
docker compose exec web python manage.py makemigrations

# Access PostgreSQL shell
docker compose exec db psql -U credit_user -d credit_db
```

## Project Structure

```
Credit Approval System/
├── app/                    # Main Django app
│   ├── models.py          # Database models
│   ├── views.py           # API views
│   ├── serializers.py     # DRF serializers
│   ├── schemas.py         # Pydantic schemas
│   └── urls.py            # App URLs
├── credit_approval_system/ # Django project
│   ├── settings.py        # Project settings
│   └── urls.py           # Main URLs
├── yaak/                  # API test requests
├── docker-compose.yml     # Docker services
├── Dockerfile            # Web service container
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

## Credit Score Algorithm

The system calculates credit scores based on:

1. **Current Loans vs Approved Limit** (Hard rejection if exceeded)
2. **Payment History** (30% weight) - EMIs paid on time
3. **Number of Loans** (Up to 20% weight) - Loan activity
4. **Current Year Activity** (Up to 20% weight) - Recent loans
5. **Loan Volume** (Up to 15% weight) - Total loan amount vs limit
6. **Base Score** (25%) - Ensures new customers are eligible

## Database Schema

### Customer
- `customer_id` (Primary Key)
- `first_name`, `last_name`
- `age`, `phone_number`
- `monthly_salary`, `approved_limit`
- `current_debt`

### Loan
- `loan_id` (Primary Key)
- `customer` (Foreign Key)
- `loan_amount`, `tenure`, `interest_rate`
- `monthly_repayment`, `emis_paid_on_time`
- `start_date`, `end_date`