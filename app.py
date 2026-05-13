from __future__ import annotations

import json
import os
from datetime import date, datetime, time
from pathlib import Path
from typing import Any
import uuid

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
import libsql_client

from model import Category, FinanceRecord, PaymentMode, TransactionType
from queries import (
    CREATE_ACCOUNTS_TABLE,
    CREATE_FINANCE_RECORDS_TABLE,
    INSERT_ACCOUNT,
    INSERT_FINANCE_RECORD,
    SELECT_ACCOUNT_BY_NAME,
    SELECT_ALL_ACCOUNTS,
    SELECT_FINANCE_RECORDS,
    SELECT_RECENT_FINANCE_RECORDS,
)

# Load environment variables from .env if present
load_dotenv()

TURSO_URL = os.getenv("TURSO_LINK")
TURSO_AUTH_TOKEN = os.getenv("TURSO_SECRET")

app = Flask(__name__)

def get_db_client():
    if not TURSO_URL or not TURSO_AUTH_TOKEN:
        raise RuntimeError("TURSO_LINK and TURSO_SECRET environment variables must be set")
    return libsql_client.create_client_sync(url=TURSO_URL, auth_token=TURSO_AUTH_TOKEN)


def init_db() -> None:
    with get_db_client() as client:
        client.execute(CREATE_ACCOUNTS_TABLE)
        client.execute(CREATE_FINANCE_RECORDS_TABLE)


def parse_optional_date(raw_value: Any) -> date | None:
    if raw_value in (None, ""):
        return None
    if isinstance(raw_value, date):
        if isinstance(raw_value, datetime):
            return raw_value.date()
        return raw_value
    return date.fromisoformat(str(raw_value))


def parse_optional_datetime(raw_value: Any) -> datetime | None:
    if raw_value in (None, ""):
        return None
    if isinstance(raw_value, datetime):
        return raw_value
    if isinstance(raw_value, date):
        return datetime.combine(raw_value, time.min)

    raw_text = str(raw_value).strip()
    try:
        return datetime.fromisoformat(raw_text)
    except ValueError:
        return datetime.combine(date.fromisoformat(raw_text), time.min)


def require_non_empty_string(payload: dict[str, Any], field_name: str) -> str:
    value = str(payload.get(field_name, "")).strip()
    if not value:
        raise ValueError(f"{field_name} is required")
    return value


def to_dict(result_set: libsql_client.ResultSet) -> list[dict[str, Any]]:
    """Convert a libsql ResultSet to a list of dictionaries."""
    dicts = []
    for row in result_set.rows:
        dicts.append(dict(zip(result_set.columns, row)))
    return dicts


def fetch_accounts() -> list[dict[str, Any]]:
    with get_db_client() as client:
        result = client.execute(SELECT_ALL_ACCOUNTS)
    return to_dict(result)


def ensure_account(client: libsql_client.Client, account_name: str) -> dict[str, Any]:
    normalized_name = account_name.strip()
    result = client.execute(
        SELECT_ACCOUNT_BY_NAME,
        (normalized_name,),
    )
    accounts = to_dict(result)
    if accounts:
        return accounts[0]

    today = date.today().isoformat()
    account_id = str(uuid.uuid4())
    client.execute(
        INSERT_ACCOUNT,
        (account_id, normalized_name, today, today),
    )
    return {"id": account_id, "name": normalized_name}


def build_record(payload: dict[str, Any], account_id: str) -> FinanceRecord:
    now = datetime.now()
    created_at = parse_optional_datetime(payload.get("created_at")) or now

    return FinanceRecord(
        account_id=account_id,
        transaction_type=TransactionType(payload["transaction_type"]),
        amount=float(payload["amount"]),
        payment_mode=PaymentMode(payload["payment_mode"]),
        category=Category(payload["category"]),
        description=require_non_empty_string(payload, "description"),
        receiver=str(payload["receiver"]).strip() if payload.get("receiver") else None,
        currency=str(payload.get("currency") or "INR").strip(),
        subcategory=str(payload["subcategory"]).strip() if payload.get("subcategory") else None,
        official_txn_id=str(payload["official_txn_id"]).strip() if payload.get("official_txn_id") else None,
        created_at=created_at,
        updated_at=parse_optional_datetime(payload.get("updated_at")) or now,
    )


def insert_record(client: libsql_client.Client, record: FinanceRecord) -> None:
    client.execute(
        INSERT_FINANCE_RECORD,
        (
            record.id,
            record.account_id,
            record.transaction_type.value,
            record.amount,
            record.payment_mode.value,
            record.category.value,
            record.description,
            record.receiver,
            record.currency,
            record.subcategory,
            record.official_txn_id,
            record.created_at.isoformat(),
            record.updated_at.isoformat(),
        ),
    )


def fetch_recent_records(limit: int = 10) -> list[dict[str, Any]]:
    with get_db_client() as client:
        result = client.execute(
            SELECT_RECENT_FINANCE_RECORDS,
            (limit,),
        )
    return to_dict(result)


def fetch_records() -> list[dict[str, Any]]:
    with get_db_client() as client:
        result = client.execute(SELECT_FINANCE_RECORDS)
    return to_dict(result)


@app.get("/api/bootstrap")
def bootstrap():
    return jsonify(
        {
            "transaction_types": [item.value for item in TransactionType],
            "payment_modes": [item.value for item in PaymentMode],
            "categories": [item.value for item in Category],
            "accounts": fetch_accounts(),
            "records": fetch_records(),
            "recent_records": fetch_recent_records(12),
        }
    )


@app.post("/api/new")
def create_record():
    payload = request.get_json(silent=True)
    if payload is None:
        payload = request.form.to_dict()

    try:
        account_name = require_non_empty_string(payload, "account_name")
        with get_db_client() as client:
            account = ensure_account(client, account_name)
            record = build_record(payload, account["id"])
            insert_record(client, record)
    except KeyError as exc:
        return jsonify({"error": f"missing required field: {exc.args[0]}"}), 400
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"database error: {exc}"}), 400

    return jsonify(
        {
            "message": "record created",
            "id": record.id,
            "record": {
                "id": record.id,
                "transaction_type": record.transaction_type.value,
                "amount": record.amount,
                "payment_mode": record.payment_mode.value,
                "category": record.category.value,
                "account_id": record.account_id,
                "account_name": account["name"],
                "description": record.description,
                "receiver": record.receiver,
                "currency": record.currency,
                "created_at": record.created_at.isoformat(),
            },
        }
    ), 201


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/records")
def records_page():
    return render_template("records.html")


# Only initialize DB if environment variables are present
if TURSO_URL and TURSO_AUTH_TOKEN:
    init_db()


if __name__ == "__main__":
    app.run(debug=True)
