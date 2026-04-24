# generate_data.py
# Generates realistic loan application data - like what a real bank would have

import random
import numpy as np
import pandas as pd
from faker import Faker
from datetime import datetime, timedelta

fake = Faker('en_IN')  # Indian names/addresses for realism
random.seed(42)
np.random.seed(42)

def generate_loan_data(n=5000):
    """Generate n realistic loan records"""

    records = []

    for i in range(1, n + 1):

        # --- Applicant Demographics ---
        age = random.randint(21, 65)
        income = random.randint(200000, 2500000)  # Annual income in INR
        employment_years = random.randint(0, 30)

        # --- Loan Details ---
        loan_amount = random.choice([
            random.randint(50000, 500000),    # Small loans
            random.randint(500000, 2000000),   # Medium loans
            random.randint(2000000, 10000000)  # Large loans
        ])

        loan_purpose = random.choice([
            'Home Purchase', 'Vehicle', 'Education',
            'Business', 'Medical', 'Personal', 'Debt Consolidation'
        ])

        loan_term_months = random.choice([12, 24, 36, 48, 60, 84, 120])
        interest_rate = round(random.uniform(7.5, 18.5), 2)

        # --- Credit Profile ---
        credit_score = int(np.clip(
            np.random.normal(680, 80), 300, 900
        ))

        num_existing_loans = random.randint(0, 5)
        missed_payments = random.randint(0, 12)

        # --- Risk Logic (realistic) ---
        # Higher risk if: low credit score, high missed payments, high debt
        risk_score = 0

        if credit_score < 580:
            risk_score += 40
        elif credit_score < 670:
            risk_score += 20
        elif credit_score < 740:
            risk_score += 10

        if missed_payments > 5:
            risk_score += 30
        elif missed_payments > 2:
            risk_score += 15

        debt_to_income = round((loan_amount * 0.012) / (income / 12), 2)
        if debt_to_income > 0.5:
            risk_score += 20
        elif debt_to_income > 0.35:
            risk_score += 10

        if employment_years < 1:
            risk_score += 10

        # Add some randomness (real world is never perfect!)
        risk_score += random.randint(-10, 10)
        risk_score = max(0, min(100, risk_score))

        # Risk Category
        if risk_score >= 60:
            risk_category = 'HIGH'
        elif risk_score >= 30:
            risk_category = 'MEDIUM'
        else:
            risk_category = 'LOW'

        # Default Status (did they fail to repay?)
        default_probability = risk_score / 100
        is_defaulted = random.random() < default_probability * 0.4

        # Loan Status
        if is_defaulted:
            loan_status = 'Defaulted'
        elif risk_category == 'HIGH':
            loan_status = random.choice(['Active', 'Defaulted', 'Under Review'])
        else:
            loan_status = random.choice(['Active', 'Closed', 'Approved'])

        # Application Date
        app_date = fake.date_between(start_date='-3y', end_date='today')

        records.append({
            'loan_id': f'LN{str(i).zfill(6)}',
            'applicant_name': fake.name(),
            'age': age,
            'gender': random.choice(['Male', 'Female', 'Other']),
            'city': fake.city(),
            'state': fake.state(),
            'annual_income': income,
            'employment_type': random.choice([
                'Salaried', 'Self-Employed', 'Business Owner', 'Freelancer'
            ]),
            'employment_years': employment_years,
            'loan_amount': loan_amount,
            'loan_purpose': loan_purpose,
            'loan_term_months': loan_term_months,
            'interest_rate': interest_rate,
            'monthly_emi': round(loan_amount * interest_rate / (12 * 100), 2),
            'credit_score': credit_score,
            'num_existing_loans': num_existing_loans,
            'missed_payments_history': missed_payments,
            'debt_to_income_ratio': debt_to_income,
            'risk_score': risk_score,
            'risk_category': risk_category,
            'loan_status': loan_status,
            'application_date': app_date,
            'is_defaulted': int(is_defaulted)
        })

    return pd.DataFrame(records)


if __name__ == "__main__":
    print("🏦 Generating loan dataset...")
    df = generate_loan_data(5000)

    # Save raw data
    df.to_csv('data/raw/loan_applications.csv', index=False)
    print(f"✅ Generated {len(df)} loan records")
    print(f"📊 Default rate: {df['is_defaulted'].mean():.1%}")
    print(f"⚠️  High risk loans: {(df['risk_category']=='HIGH').sum()}")
    print("\nFirst 3 rows:")
    print(df.head(3).to_string())