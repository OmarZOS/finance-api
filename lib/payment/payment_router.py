# controllers/payment_controller.py

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session
from core.exceptions.handler import APIException
from core.messages import *
import logging

from core.schemas.payment_schemas import (
    InvoicePaymentResponse, 
    PaymentConfirm, 
    PaymentCreate, 
    PaymentRefund, 
    PaymentResponse
)
from core.database import get_engine, session_scope
from lib.payment.payment_service import PaymentService

logger = logging.getLogger(__name__)

router = APIRouter()


def get_db() -> Session:
    """Get database session dependency"""
    with session_scope() as session:
        yield session


@router.post("/payment", response_model=PaymentResponse)
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
        return result
    except APIException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Payment creation failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/confirm/{payment_id}", response_model=PaymentResponse)
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
        return result
    except APIException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Payment confirmation failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/reject/{payment_id}", response_model=PaymentResponse)
async def reject_payment(
    payment_id: int,
    reason: str = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    """
    Reject a pending payment.
    No transactions are created.
    """
    try:
        service = PaymentService(db)
        result = service.reject_payment(payment_id, reason)
        return result
    except APIException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Payment rejection failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/invoice/{invoice_id}", response_model=InvoicePaymentResponse)
async def get_invoice_payments(
    invoice_id: int,
    db: Session = Depends(get_db)
):
    """Get all payments for an invoice"""
    try:
        service = PaymentService(db)
        return service.get_invoice_payments(invoice_id)
    except APIException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Failed to get invoice payments: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/refund/{payment_id}", response_model=PaymentResponse)
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
        return result
    except APIException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Refund failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/stats/daily", response_model=Dict[str, Any])
async def get_daily_payment_stats(
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format"),
    db: Session = Depends(get_db)
):
    """Get daily payment statistics"""
    try:
        from datetime import datetime
        target_date = datetime.strptime(date, "%Y-%m-%d").date() if date else datetime.now().date()
        
        service = PaymentService(db)
        stats = service.payment_repo.get_daily_payment_stats(target_date)
        return stats
    except Exception as e:
        logger.error(f"Failed to get payment stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: int,
    db: Session = Depends(get_db)
):
    """Get payment details with transactions"""
    try:
        service = PaymentService(db)
        return service.get_payment_by_id(payment_id)
    except APIException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Failed to get payment: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")