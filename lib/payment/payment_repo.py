# repositories/payment_repository.py

from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import and_, or_, desc, func, between
from core.models import (
    Cart, Payment, Invoice, Wallet, MoneyTransaction, 
    AppUser, Plan
)
from core.exceptions.handler import DatabaseException, APIException
from core.messages import *
import logging

logger = logging.getLogger(__name__)


class PaymentRepository:
    """Repository for payment-related operations"""
    
    def __init__(self, session: Session):
        self.session = session
    
    # ==================== Payment Methods ====================
    
    def create_payment(self, payment_data: Dict[str, Any]) -> Payment:
        """Create a new payment record"""
        try:
            payment = Payment(**payment_data)
            self.session.add(payment)
            self.session.flush()
            return payment
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to create payment: {e}")
            raise DatabaseException(f"Payment creation failed: {e}")
    
    def get_payment_by_id(self, payment_id: int) -> Optional[Payment]:
        """Get payment by ID with related data"""
        try:
            return self.session.query(Payment).options(
                joinedload(Payment.payment_invoice),
                joinedload(Payment.money_transaction)
            ).filter(Payment.payment_id == payment_id).first()
        except Exception as e:
            logger.error(f"Failed to get payment {payment_id}: {e}")
            return None
    
    def get_payments_by_invoice(self, invoice_id: int) -> List[Payment]:
        """Get all payments for an invoice"""
        try:
            return self.session.query(Payment).filter(
                Payment.payment_invoice_id == invoice_id
            ).order_by(desc(Payment.payment_created_at)).all()
        except Exception as e:
            logger.error(f"Failed to get payments for invoice {invoice_id}: {e}")
            return []
    
    def get_payments_by_status(self, status: str, limit: int = 100) -> List[Payment]:
        """Get payments by status"""
        try:
            return self.session.query(Payment).filter(
                Payment.payment_status == status
            ).order_by(desc(Payment.payment_created_at)).limit(limit).all()
        except Exception as e:
            logger.error(f"Failed to get payments by status {status}: {e}")
            return []
    
    def update_payment_status(self, payment_id: int, status: str, 
                             reference: Optional[str] = None) -> Optional[Payment]:
        """Update payment status"""
        try:
            payment = self.session.query(Payment).filter(
                Payment.payment_id == payment_id
            ).first()
            
            if not payment:
                return None
            
            payment.payment_status = status
            if reference:
                payment.payment_reference = reference
            payment.payment_updated_at = datetime.now()
            
            self.session.flush()
            return payment
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to update payment {payment_id}: {e}")
            return None
    
    def get_payment_summary_by_invoice(self, invoice_id: int) -> Dict[str, Any]:
        """Get payment summary for an invoice"""
        try:
            payments = self.session.query(Payment).filter(
                Payment.payment_invoice_id == invoice_id
            ).all()
            
            total_paid = sum(p.payment_amount for p in payments if p.payment_status == 'completed')
            total_pending = sum(p.payment_amount for p in payments if p.payment_status == 'pending')
            
            return {
                'invoice_id': invoice_id,
                'total_paid': float(total_paid) if total_paid else 0.0,
                'total_pending': float(total_pending) if total_pending else 0.0,
                'payment_count': len(payments),
                'completed_count': sum(1 for p in payments if p.payment_status == 'completed'),
                'pending_count': sum(1 for p in payments if p.payment_status == 'pending'),
                'failed_count': sum(1 for p in payments if p.payment_status == 'failed'),
            }
        except Exception as e:
            logger.error(f"Failed to get payment summary for invoice {invoice_id}: {e}")
            return {}
    
    def get_daily_payment_stats(self, date: Optional[date] = None) -> Dict[str, Any]:
        """Get daily payment statistics"""
        try:
            target_date = date or datetime.now().date()
            start_of_day = datetime.combine(target_date, datetime.min.time())
            end_of_day = datetime.combine(target_date, datetime.max.time())
            
            payments = self.session.query(Payment).filter(
                between(Payment.payment_created_at, start_of_day, end_of_day)
            ).all()
            
            total_amount = sum(p.payment_amount for p in payments if p.payment_status == 'completed')
            
            return {
                'date': target_date.isoformat(),
                'total_payments': len(payments),
                'total_amount': float(total_amount) if total_amount else 0.0,
                'completed_count': sum(1 for p in payments if p.payment_status == 'completed'),
                'pending_count': sum(1 for p in payments if p.payment_status == 'pending'),
                'failed_count': sum(1 for p in payments if p.payment_status == 'failed'),
            }
        except Exception as e:
            logger.error(f"Failed to get daily payment stats: {e}")
            return {}






