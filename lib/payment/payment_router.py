# controllers/payment_controller.py

from decimal import Decimal
from typing import Any, Dict, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from datetime import datetime
import logging

from core.exceptions.handler import APIException
from core.messages import *
from core.database import get_engine, session_scope
from lib.payment.payment_service import PaymentService

logger = logging.getLogger(__name__)

# ==================== ROUTER ====================
router = APIRouter()


# ==================== REQUEST MODELS ====================

class PaymentCreate(BaseModel):
    """Request model for creating a payment"""
    invoice_id: int = Field(..., description="ID of the invoice to pay")
    amount: Decimal = Field(..., gt=0, description="Payment amount")
    payment_method: str = Field(..., description="Payment method: card, cash, bank_transfer, etc.")
    user_id: int = Field(..., description="ID of the user making the payment")
    notes: Optional[str] = Field(None, description="Additional notes")
    payment_type: Optional[str] = Field('payment', description="Type of payment: payment, deposit, etc.")


class PaymentConfirm(BaseModel):
    """Request model for confirming a payment"""
    transaction_details: Dict[str, Any] = Field(
        default={}, 
        description="Transaction details from payment gateway"
    )


class PaymentRefund(BaseModel):
    """Request model for refunding a payment"""
    amount: Decimal = Field(..., gt=0, description="Amount to refund")
    reason: str = Field(..., min_length=1, description="Reason for refund")


# ==================== RESPONSE MODELS ====================

class TransactionResponse(BaseModel):
    """Transaction details in response"""
    id: int
    wallet_id: int
    amount: Decimal
    transaction_type: str
    status: str
    reference: Optional[str] = None
    created_at: Optional[datetime] = None


class PaymentResponse(BaseModel):
    """Response model for payment operations"""
    id: int
    invoice_id: int
    user_id: Optional[int] = None  # Make optional since not stored in Payment
    amount: Decimal
    payment_method: str
    status: str
    payment_type: str
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    transactions: List[TransactionResponse] = []
    refunds: List[Dict[str, Any]] = []


class InvoicePaymentSummary(BaseModel):
    """Summary of payments for an invoice"""
    invoice_id: int
    total_amount: Decimal
    total_paid: Decimal
    remaining_amount: Decimal
    status: str
    payments: List[PaymentResponse] = []


class DailyPaymentStats(BaseModel):
    """Daily payment statistics"""
    date: str
    total_payments: int
    total_amount: Decimal
    average_amount: Decimal = 0.0
    by_status: Dict[str, int] = {}
    by_method: Dict[str, int] = {}


class PaymentSuccessResponse(BaseModel):
    """Generic success response"""
    success: bool = True
    message: str
    data: Optional[Any] = None


# ==================== ERROR RESPONSE MODELS ====================

class ErrorDetail(BaseModel):
    """Detailed error information"""
    field: Optional[str] = Field(None, description="Field that caused the error")
    message: str = Field(..., description="Error message")
    code: Optional[str] = Field(None, description="Error code")


class ErrorResponse(BaseModel):
    """Standard error response model"""
    detail: str = Field(..., description="Main error message")
    status_code: int = Field(..., description="HTTP status code")
    error_code: Optional[str] = Field(None, description="Application error code")
    errors: Optional[List[ErrorDetail]] = Field(None, description="Detailed error list")
    timestamp: str = Field(..., description="Timestamp of the error")
    path: Optional[str] = Field(None, description="Request path")


# ==================== DEPENDENCIES ====================

def get_db() -> Session:
    """Get database session dependency"""
    with session_scope() as session:
        yield session


# ==================== ROUTER ENDPOINTS ====================
# IMPORTANT: Health check MUST be before the /{payment_id} route

# 1. HEALTH CHECK - MUST BE FIRST
@router.get(
    "/health",
    response_model=Dict[str, str],
    responses={
        200: {"description": "Health check passed"},
        500: {"description": "Health check failed"}
    }
)
async def payment_health_check(
    db: Session = Depends(get_db)
):
    """Health check endpoint for payment service"""
    try:
        from core.models import Invoice
        db.query(Invoice).first()
        
        return {
            "status": "healthy",
            "service": "payment",
            "database": "connected"
        }
    except Exception as e:
        logger.error(f"Payment health check failed: {e}")
        return {
            "status": "unhealthy",
            "service": "payment",
            "database": "disconnected",
            "error": str(e)
        }


# 2. CREATE PAYMENT
@router.post(
    "/payment",
    response_model=PaymentResponse,
    responses={
        200: {"description": "Payment created successfully", "model": PaymentResponse},
        400: {"description": "Bad request", "model": ErrorResponse},
        404: {"description": "Invoice not found", "model": ErrorResponse},
        409: {"description": "Conflict - invoice already paid", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)
async def create_payment(
    payment_data: PaymentCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new payment with pending status.
    The invoice must already exist.
    """
    try:
        service = PaymentService(db)
        result = service.create_payment(
            invoice_id=payment_data.invoice_id,
            amount=payment_data.amount,
            payment_method=payment_data.payment_method,
            user_id=payment_data.user_id,
            notes=payment_data.notes,
            payment_type=payment_data.payment_type or 'payment'
        )
        return PaymentResponse(**result)
    except APIException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Payment creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Payment creation failed: {str(e)}"
        )


# 3. CONFIRM PAYMENT
@router.post(
    "/confirm/{payment_id}",
    response_model=PaymentResponse,
    responses={
        200: {"description": "Payment confirmed successfully", "model": PaymentResponse},
        400: {"description": "Bad request", "model": ErrorResponse},
        404: {"description": "Payment not found", "model": ErrorResponse},
        409: {"description": "Conflict - payment already confirmed/rejected", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)
async def confirm_payment(
    payment_id: int,
    confirm_data: PaymentConfirm = Body(...),
    db: Session = Depends(get_db)
):
    """
    Confirm a pending payment.
    This creates money transactions for wallet transfers.
    """
    try:
        service = PaymentService(db)
        result = service.confirm_payment(
            payment_id=payment_id,
            transaction_details=confirm_data.transaction_details
        )
        return PaymentResponse(**result)
    except APIException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Payment confirmation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Payment confirmation failed: {str(e)}"
        )


# 4. REJECT PAYMENT
@router.post(
    "/reject/{payment_id}",
    response_model=PaymentResponse,
    responses={
        200: {"description": "Payment rejected successfully", "model": PaymentResponse},
        400: {"description": "Bad request", "model": ErrorResponse},
        404: {"description": "Payment not found", "model": ErrorResponse},
        409: {"description": "Conflict - payment already confirmed/rejected", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)
async def reject_payment(
    payment_id: int,
    reason: str = Body(..., embed=True, min_length=1),
    db: Session = Depends(get_db)
):
    """
    Reject a pending payment.
    No transactions are created.
    """
    try:
        service = PaymentService(db)
        result = service.reject_payment(payment_id, reason)
        return PaymentResponse(**result)
    except APIException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Payment rejection failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Payment rejection failed: {str(e)}"
        )


# 5. GET INVOICE PAYMENTS
@router.get(
    "/invoice/{invoice_id}",
    response_model=InvoicePaymentSummary,
    responses={
        200: {"description": "Invoice payments retrieved", "model": InvoicePaymentSummary},
        404: {"description": "Invoice not found", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)
async def get_invoice_payments(
    invoice_id: int,
    db: Session = Depends(get_db)
):
    """Get all payments for an invoice"""
    try:
        service = PaymentService(db)
        result = service.get_invoice_payments(invoice_id)
        return InvoicePaymentSummary(**result)
    except APIException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Failed to get invoice payments: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get invoice payments: {str(e)}"
        )


# 6. REFUND PAYMENT
@router.post(
    "/refund/{payment_id}",
    response_model=PaymentResponse,
    responses={
        200: {"description": "Refund processed successfully", "model": PaymentResponse},
        400: {"description": "Bad request", "model": ErrorResponse},
        404: {"description": "Payment not found", "model": ErrorResponse},
        409: {"description": "Conflict - payment not eligible for refund", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)
async def refund_payment(
    payment_id: int,
    refund_data: PaymentRefund,
    db: Session = Depends(get_db)
):
    """
    Refund a completed payment.
    Creates reverse transactions.
    """
    try:
        service = PaymentService(db)
        result = service.process_refund(
            payment_id=payment_id,
            reason=refund_data.reason,
            refund_amount=refund_data.amount
        )
        return PaymentResponse(**result)
    except APIException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Refund failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Refund failed: {str(e)}"
        )


# 7. DAILY STATS
@router.get(
    "/stats/daily",
    response_model=DailyPaymentStats,
    responses={
        200: {"description": "Daily payment stats retrieved", "model": DailyPaymentStats},
        400: {"description": "Invalid date format", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)
async def get_daily_payment_stats(
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format"),
    db: Session = Depends(get_db)
):
    """Get daily payment statistics"""
    try:
        # If date is provided, parse it
        if date:
            try:
                target_date = datetime.strptime(date, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid date format. Use YYYY-MM-DD"
                )
        else:
            target_date = datetime.now().date()
        
        service = PaymentService(db)
        stats = service.payment_repo.get_daily_payment_stats(target_date)
        return DailyPaymentStats(**stats)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get payment stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get payment stats: {str(e)}"
        )


# 8. GET PAYMENT - MUST BE LAST (catches all /{payment_id} routes)
@router.get(
    "/{payment_id}",
    response_model=PaymentResponse,
    responses={
        200: {"description": "Payment details retrieved", "model": PaymentResponse},
        404: {"description": "Payment not found", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)
async def get_payment(
    payment_id: int,
    db: Session = Depends(get_db)
):
    """Get payment details with transactions"""
    try:
        service = PaymentService(db)
        result = service.get_payment_by_id(payment_id)
        return PaymentResponse(**result)
    except APIException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Failed to get payment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get payment: {str(e)}"
        )