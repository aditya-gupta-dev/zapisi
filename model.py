from dataclasses import dataclass, field
from datetime import date
from typing import Optional
from enum import Enum
import uuid


class TransactionType(str, Enum):
    EXPENSE         = "expense"
    INCOME          = "income"
    LOAN_GIVEN      = "loan_given"          # you gave money to someone
    LOAN_REPAID_TO_YOU  = "loan_repaid_to_you"  # they paid you back
    LOAN_TAKEN      = "loan_taken"          # you borrowed money from someone
    LOAN_REPAID_BY_YOU  = "loan_repaid_by_you"  # you paid them back


class PaymentMode(str, Enum):
    CASH       = "cash"
    UPI        = "UPI"
    CARD       = "card"
    NETBANKING = "netbanking"
    WALLET     = "wallet"
    CRYPTO     = "crypto"
    OTHER      = "other" 


class LoanStatus(str, Enum):
    PENDING   = "pending" # entirely pending
    PARTIAL   = "partial" # paid some amount 
    SETTLED   = "settled" # entire process completed 
    DEFAULTED = "defaulted" # failed to pay on time 


class Category(str, Enum):
    FOOD           = "food"
    TRAVEL         = "travel"
    STUDY          = "study"
    RENT           = "rent"
    MEDICAL        = "medical"
    ENTERTAINMENT  = "entertainment"
    PERSONAL       = "personal"
    INCOME         = "income"
    MONEY_GIVEN    = "money_given"
    MONEY_BORROWED = "money_borrowed"
    MISC           = "misc"


@dataclass
class FinanceRecord:
    transaction_type: TransactionType
    amount:           float
    payment_mode:     PaymentMode
    category:         Category
    description:      str

    currency:         str                  = "INR"
    subcategory:      Optional[str]        = None
    tags:             list[str]            = field(default_factory=list)
    official_txn_id:  Optional[str]        = None   

    linked_loan_id:   Optional[str]        = None   # points to original loan_given/loan_taken
    loan_status:      Optional[LoanStatus] = None
    amount_remaining: Optional[float]      = None
    due_date:         Optional[date]       = None

    notes:            str                  = ""
    created_at:       date                 = field(default_factory=date.today)
    updated_at:       date                 = field(default_factory=date.today)
    id:               str                  = field(default_factory=lambda: str(uuid.uuid4()))

    def to_csv_row(self) -> dict:
        """Flatten the record to a dict suitable for csv.DictWriter."""
        return {
            "id":               self.id,
            "amount":           self.amount,
            "currency":         self.currency,
            "transaction_type": self.transaction_type.value,
            "payment_mode":     self.payment_mode.value,
            "official_txn_id":  self.official_txn_id or "",
            "category":         self.category.value,
            "subcategory":      self.subcategory or "",
            "description":      self.description,
            "tags":             "|".join(self.tags),    # pipe-separated so CSV stays clean
            "linked_loan_id":   self.linked_loan_id or "",
            "loan_status":      self.loan_status.value if self.loan_status else "",
            "amount_remaining": self.amount_remaining if self.amount_remaining is not None else "",
            "due_date":         self.due_date.isoformat() if self.due_date else "",
            "notes":            self.notes,
            "created_at":       self.created_at.isoformat(),
            "updated_at":       self.updated_at.isoformat(),
        }
    

    @classmethod
    def from_csv_row(cls, row: dict) -> "FinanceRecord":
        """Reconstruct a FinanceRecord from a csv.DictReader row."""
        return cls(
            id               = row["id"],
            amount           = float(row["amount"]),
            currency         = row["currency"],
            transaction_type = TransactionType(row["transaction_type"]),
            payment_mode     = PaymentMode(row["payment_mode"]),
            official_txn_id  = row["official_txn_id"] or None,
            category         = Category(row["category"]),
            subcategory      = row["subcategory"] or None,
            description      = row["description"],
            tags             = row["tags"].split("|") if row["tags"] else [],
            linked_loan_id   = row["linked_loan_id"] or None,
            loan_status      = LoanStatus(row["loan_status"]) if row["loan_status"] else None,
            amount_remaining = float(row["amount_remaining"]) if row["amount_remaining"] else None,
            due_date         = date.fromisoformat(row["due_date"]) if row["due_date"] else None,
            notes            = row["notes"],
            created_at       = date.fromisoformat(row["created_at"]),
            updated_at       = date.fromisoformat(row["updated_at"]),
        )


    @classmethod
    def csv_fieldnames(cls) -> list[str]:
        return [
            "id", "amount", "currency", "transaction_type", "payment_mode",
            "official_txn_id", "category", "subcategory", "description", "tags",
            "party_name", "party_type", "linked_loan_id", "loan_status",
            "amount_remaining", "due_date", "notes", "created_at", "updated_at",
        ]
