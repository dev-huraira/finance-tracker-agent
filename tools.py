from datetime import date, timedelta
from langchain_core.tools import tool
from database import SessionLocal
from models import Expense
from logging_config import logger


@tool
def add_expense(category: str, amount: float, expense_date: str, description: str = "") -> str:
    """
    Log a new expense. Use this when the user says they spent money.
    category: e.g. 'Food', 'Transport', 'Rent'.
    amount: the amount spent, must be a positive number.
    expense_date: the date the expense happened, format YYYY-MM-DD.
    description: optional short note about the expense.
    """
    if amount <= 0:
        logger.error(f"Rejected add_expense: non-positive amount={amount}")
        return "Error: amount must be a positive number."

    try:
        parsed_date = date.fromisoformat(expense_date)
    except ValueError:
        logger.error(f"Rejected add_expense: invalid date={expense_date}")
        return "Error: expense_date must be in YYYY-MM-DD format."

    db = SessionLocal()
    try:
        new_expense = Expense(
            category=category,
            amount=amount,
            date=parsed_date,
            description=description,
        )
        db.add(new_expense)
        db.commit()
        db.refresh(new_expense)
        logger.info(f"Expense added: id={new_expense.id}, category={category}, amount={amount}, date={parsed_date}")
        return f"Logged expense: {amount} on {category} ({parsed_date})."
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to add expense: {str(e)}")
        return f"Error saving expense: {str(e)}"
    finally:
        db.close()


@tool
def query_expenses(category: str = "", start_date: str = "", end_date: str = "") -> str:
    """
    Retrieve logged expenses, optionally filtered by category and/or date range.
    category: optional, e.g. 'Food'. Leave empty to include all categories.
    start_date: optional, format YYYY-MM-DD. Leave empty for no lower bound.
    end_date: optional, format YYYY-MM-DD. Leave empty for no upper bound.
    """
    db = SessionLocal()
    try:
        query = db.query(Expense)

        if category:
            query = query.filter(Expense.category.ilike(category))

        if start_date:
            query = query.filter(Expense.date >= date.fromisoformat(start_date))

        if end_date:
            query = query.filter(Expense.date <= date.fromisoformat(end_date))

        results = query.order_by(Expense.date.desc()).all()

        logger.info(f"query_expenses: category='{category}', start={start_date}, end={end_date}, results={len(results)}")

        if not results:
            return "No expenses found matching those filters."

        lines = [
            f"{r.date} | {r.category} | {r.amount} | {r.description or '-'}"
            for r in results
        ]
        return "\n".join(lines)
    except ValueError:
        logger.error(f"query_expenses: invalid date format start={start_date}, end={end_date}")
        return "Error: dates must be in YYYY-MM-DD format."
    finally:
        db.close()


@tool
def budget_summary(start_date: str, end_date: str) -> str:
    """
    Summarize total spending per category between two dates.
    start_date: format YYYY-MM-DD.
    end_date: format YYYY-MM-DD.
    """
    db = SessionLocal()
    try:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)

        results = (
            db.query(Expense)
            .filter(Expense.date >= start, Expense.date <= end)
            .all()
        )

        logger.info(f"budget_summary: start={start_date}, end={end_date}, rows={len(results)}")

        if not results:
            return "No expenses found in that date range."

        totals = {}
        for r in results:
            totals[r.category] = totals.get(r.category, 0) + r.amount

        lines = [f"{cat}: {amt:.2f}" for cat, amt in totals.items()]
        grand_total = sum(totals.values())
        lines.append(f"Total: {grand_total:.2f}")
        return "\n".join(lines)
    except ValueError:
        logger.error(f"budget_summary: invalid date format start={start_date}, end={end_date}")
        return "Error: dates must be in YYYY-MM-DD format."
    finally:
        db.close()


@tool
def weekly_limit_check(weekly_budget: float) -> str:
    """
    Check how much of the user's weekly budget has been spent so far this week,
    and how much remains.
    weekly_budget: the user's total budget for the current week.
    """
    db = SessionLocal()
    try:
        today = date.today()
        start_of_week = today - timedelta(days=today.weekday())

        results = (
            db.query(Expense)
            .filter(Expense.date >= start_of_week, Expense.date <= today)
            .all()
        )

        spent = sum(r.amount for r in results)
        remaining = weekly_budget - spent

        logger.info(f"weekly_limit_check: budget={weekly_budget}, spent={spent}, remaining={remaining}")

        if remaining < 0:
            return f"You've spent {spent:.2f} this week, which is {abs(remaining):.2f} over your {weekly_budget:.2f} budget."
        return f"You've spent {spent:.2f} of your {weekly_budget:.2f} weekly budget. {remaining:.2f} remaining."
    finally:
        db.close()