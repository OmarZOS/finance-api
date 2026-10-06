# repositories/payment_repository.py

from decimal import Decimal
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
        """
        Create a new payment record.
        
        Args:
            payment_data: Dictionary containing payment fields
            
        Returns:
            Payment: The created payment object
            
        Raises:
            DatabaseException: If creation fails
        """
        try:
            payment = Payment(**payment_data)
            self.session.add(payment)
            self.session.flush()
            self.session.refresh(payment)  # Refresh to get generated ID
            return payment
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to create payment: {e}")
            raise DatabaseException(f"Payment creation failed: {e}")
    
    def get_payment_by_id(self, payment_id: int) -> Optional[Payment]:
        """
        Get payment by ID with related data.
        
        Args:
            payment_id: The payment ID
            
        Returns:
            Optional[Payment]: The payment object or None if not found
        """
        try:
            return self.session.query(Payment).options(
                joinedload(Payment.payment_invoice),
                joinedload(Payment.money_transaction)
            ).filter(Payment.payment_id == payment_id).first()
        except Exception as e:
            logger.error(f"Failed to get payment {payment_id}: {e}")
            return None
    
    def get_payments_by_invoice(self, invoice_id: int) -> List[Payment]:
        """
        Get all payments for an invoice.
        
        Args:
            invoice_id: The invoice ID
            
        Returns:
            List[Payment]: List of payments for the invoice
        """
        try:
            return self.session.query(Payment).filter(
                Payment.payment_invoice_id == invoice_id
            ).order_by(desc(Payment.payment_created_at)).all()
        except Exception as e:
            logger.error(f"Failed to get payments for invoice {invoice_id}: {e}")
            return []
    
    def get_payments_by_status(self, status: str, limit: int = 100) -> List[Payment]:
        """
        Get payments by status.
        
        Args:
            status: The payment status (pending, completed, failed, refunded)
            limit: Maximum number of records to return
            
        Returns:
            List[Payment]: List of payments with the given status
        """
        try:
            return self.session.query(Payment).filter(
                Payment.payment_status == status
            ).order_by(desc(Payment.payment_created_at)).limit(limit).all()
        except Exception as e:
            logger.error(f"Failed to get payments by status {status}: {e}")
            return []
    
    def update_payment_status(
        self, 
        payment_id: int, 
        status: str, 
        reference: Optional[str] = None
    ) -> Optional[Payment]:
        """
        Update payment status.
        
        Args:
            payment_id: The payment ID
            status: New status (pending, completed, failed, refunded)
            reference: Optional reference number
            
        Returns:
            Optional[Payment]: The updated payment object or None if not found
        """
        try:
            payment = self.session.query(Payment).filter(
                Payment.payment_id == payment_id
            ).first()
            
            if not payment:
                logger.warning(f"Payment {payment_id} not found for status update")
                return None
            
            payment.payment_status = status
            if reference:
                payment.payment_reference = reference
            payment.payment_updated_at = datetime.now()
            
            self.session.flush()
            self.session.refresh(payment)
            
            logger.info(f"Payment {payment_id} status updated to {status}")
            return payment
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to update payment {payment_id}: {e}")
            return None
    
    def get_payment_summary_by_invoice(self, invoice_id: int) -> Dict[str, Any]:
        """
        Get payment summary for an invoice.
        
        Args:
            invoice_id: The invoice ID
            
        Returns:
            Dict: Summary of payments for the invoice
        """
        try:
            payments = self.session.query(Payment).filter(
                Payment.payment_invoice_id == invoice_id
            ).all()
            
            total_paid = sum(p.payment_amount for p in payments if p.payment_status == 'completed')
            total_pending = sum(p.payment_amount for p in payments if p.payment_status == 'pending')
            total_refunded = sum(p.payment_amount for p in payments if p.payment_status == 'refunded')
            
            # Calculate remaining balance (total paid - total refunded)
            net_paid = total_paid - total_refunded
            
            return {
                'invoice_id': invoice_id,
                'total_paid': Decimal(net_paid) if net_paid else 0.0,
                'total_pending': Decimal(total_pending) if total_pending else 0.0,
                'total_refunded': Decimal(total_refunded) if total_refunded else 0.0,
                'payment_count': len(payments),
                'completed_count': sum(1 for p in payments if p.payment_status == 'completed'),
                'pending_count': sum(1 for p in payments if p.payment_status == 'pending'),
                'failed_count': sum(1 for p in payments if p.payment_status == 'failed'),
                'refunded_count': sum(1 for p in payments if p.payment_status == 'refunded'),
            }
        except Exception as e:
            logger.error(f"Failed to get payment summary for invoice {invoice_id}: {e}")
            return {}
    
    def get_daily_payment_stats(self, target_date: Optional[date] = None) -> Dict[str, Any]:
        """
        Get daily payment statistics.
        
        Args:
            target_date: The date to get stats for (defaults to today)
            
        Returns:
            Dict: Daily payment statistics including:
                - date: The date
                - total_payments: Total number of payments
                - total_amount: Total amount of completed payments
                - average_amount: Average amount of completed payments
                - by_status: Count of payments by status
                - by_method: Count of payments by method
        """
        try:
            target_date = target_date or datetime.now().date()
            start_of_day = datetime.combine(target_date, datetime.min.time())
            end_of_day = datetime.combine(target_date, datetime.max.time())
            
            payments = self.session.query(Payment).filter(
                between(Payment.payment_created_at, start_of_day, end_of_day)
            ).all()
            
            # Completed payments for amount calculations
            completed_payments = [p for p in payments if p.payment_status == 'completed']
            total_amount = sum(p.payment_amount for p in completed_payments) if completed_payments else 0
            
            # Calculate by status
            by_status = {}
            for p in payments:
                by_status[p.payment_status] = by_status.get(p.payment_status, 0) + 1
            
            # Calculate by method
            by_method = {}
            for p in payments:
                if p.payment_method:
                    by_method[p.payment_method] = by_method.get(p.payment_method, 0) + 1
            
            return {
                'date': target_date.isoformat(),
                'total_payments': len(payments),
                'total_amount': Decimal(total_amount) if total_amount else 0.0,
                'average_amount': Decimal(total_amount / len(completed_payments)) if completed_payments else 0.0,
                'by_status': by_status,
                'by_method': by_method,
                'completed_count': len(completed_payments),
                'pending_count': sum(1 for p in payments if p.payment_status == 'pending'),
                'failed_count': sum(1 for p in payments if p.payment_status == 'failed'),
                'refunded_count': sum(1 for p in payments if p.payment_status == 'refunded'),
            }
        except Exception as e:
            logger.error(f"Failed to get daily payment stats for {target_date}: {e}")
            # Return empty stats instead of raising
            return {
                'date': target_date.isoformat() if target_date else datetime.now().date().isoformat(),
                'total_payments': 0,
                'total_amount': 0.0,
                'average_amount': 0.0,
                'by_status': {},
                'by_method': {},
                'completed_count': 0,
                'pending_count': 0,
                'failed_count': 0,
                'refunded_count': 0,
            }
    
    def get_payments_by_date_range(
        self, 
        start_date: date, 
        end_date: date
    ) -> List[Payment]:
        """
        Get payments within a date range.
        
        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            
        Returns:
            List[Payment]: List of payments in the date range
        """
        try:
            start_datetime = datetime.combine(start_date, datetime.min.time())
            end_datetime = datetime.combine(end_date, datetime.max.time())
            
            return self.session.query(Payment).filter(
                between(Payment.payment_created_at, start_datetime, end_datetime)
            ).order_by(desc(Payment.payment_created_at)).all()
        except Exception as e:
            logger.error(f"Failed to get payments by date range: {e}")
            return []
    
    def get_payment_count_by_status(self, status: str) -> int:
        """
        Get count of payments by status.
        
        Args:
            status: The payment status
            
        Returns:
            int: Number of payments with the given status
        """
        try:
            return self.session.query(Payment).filter(
                Payment.payment_status == status
            ).count()
        except Exception as e:
            logger.error(f"Failed to get payment count for status {status}: {e}")
            return 0
    
    def get_total_revenue_by_date(self, target_date: Optional[date] = None) -> Decimal:
        """
        Get total revenue for a specific date.
        
        Args:
            target_date: The date to get revenue for (defaults to today)
            
        Returns:
            Decimal: Total revenue for the date
        """
        try:
            target_date = target_date or datetime.now().date()
            start_of_day = datetime.combine(target_date, datetime.min.time())
            end_of_day = datetime.combine(target_date, datetime.max.time())
            
            result = self.session.query(
                func.sum(Payment.payment_amount)
            ).filter(
                Payment.payment_status == 'completed',
                between(Payment.payment_created_at, start_of_day, end_of_day)
            ).scalar()
            
            return Decimal(result) if result else 0.0
        except Exception as e:
            logger.error(f"Failed to get total revenue for {target_date}: {e}")
            return 0.0