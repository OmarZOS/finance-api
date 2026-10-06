# schemas/payment_schemas.py

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from decimal import Decimal

class API_Resolution(BaseModel):
    """Standard API response wrapper"""
    status: int = Field(..., description="HTTP status code")
    error_code: str = Field(..., description="Error code identifier")
    message: str = Field(..., description="Human readable message")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": 200,
                "error_code": "SUCCESS",
                "message": "Operation completed successfully"
            }
        }
    )

class PaymentCreate(BaseModel):
    invoice_id: int = Field(..., description="Existing invoice ID")
    amount: Decimal = Field(..., gt=0, description="Payment amount")
    payment_method: str = Field(..., description="cash, card, bank_transfer, mobile_money, wallet, deposit")
    user_id: int = Field(..., description="User making the payment")
    notes: Optional[str] = None
    payment_type: Optional[str] = Field("payment", description="payment, deposit, refund")


class PaymentConfirm(BaseModel):
    transaction_details: Optional[Dict[str, Any]] = Field(None, description="Additional transaction details")


class PaymentRefund(BaseModel):
    reason: str = Field(..., description="Refund reason")
    amount: Optional[Decimal] = Field(None, description="Refund amount (defaults to full payment)")


class TransactionResponse(BaseModel):
    id: int
    source_wallet: int
    destination_wallet: int
    amount: Decimal
    reference: str
    status: str
    created_at: Optional[str] = None


class PaymentResponse(BaseModel):
    payment_id: int
    invoice_id: int
    amount: Decimal
    payment_method: Optional[str] = None
    status: str
    reference: str
    type: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    invoice_status: Optional[str] = None
    balance_due: Optional[Decimal] = None
    transactions: Optional[List[TransactionResponse]] = []
    message: Optional[str] = None
    reason: Optional[str] = None


class PaymentSummary(BaseModel):
    invoice_id: int
    total_amount: Decimal
    total_paid: Decimal
    balance_due: Decimal
    status: str
    due_date: Optional[str] = None


class InvoicePaymentResponse(BaseModel):
    invoice_id: int
    invoice_status: str
    total_amount: Decimal
    summary: Dict[str, Any]
    payments: List[Dict[str, Any]]