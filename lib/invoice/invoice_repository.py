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



class InvoiceRepository:
    """Repository for invoice operations"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create_invoice(self, invoice_data: Dict[str, Any]) -> Invoice:
        """Create a new invoice"""
        try:
            invoice = Invoice(**invoice_data)
            self.session.add(invoice)
            self.session.flush()
            return invoice
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to create invoice: {e}")
            raise DatabaseException(f"Invoice creation failed: {e}")
    
    def get_invoice_by_id(self, invoice_id: int) -> Optional[Invoice]:
        """Get invoice by ID with related data"""
        try:
            return self.session.query(Invoice).options(
                joinedload(Invoice.payment),
                joinedload(Invoice.placed_order),
                joinedload(Invoice.cart),
                joinedload(Invoice.additional_fee)
            ).filter(Invoice.invoice_id == invoice_id).first()
        except Exception as e:
            logger.error(f"Failed to get invoice {invoice_id}: {e}")
            return None
    
    def get_invoices_by_user(self, user_id: int, status: Optional[str] = None) -> List[Invoice]:
        """Get invoices for a user"""
        try:
            query = self.session.query(Invoice).join(
                Cart, Invoice.cart
            ).filter(Cart.cart_client_user == user_id)
            
            if status:
                query = query.filter(Invoice.invoice_status == status)
            
            return query.order_by(desc(Invoice.invoice_created_at)).all()
        except Exception as e:
            logger.error(f"Failed to get invoices for user {user_id}: {e}")
            return []
    
    def update_invoice_status(self, invoice_id: int, status: str) -> Optional[Invoice]:
        """Update invoice status"""
        try:
            invoice = self.session.query(Invoice).filter(
                Invoice.invoice_id == invoice_id
            ).first()
            
            if not invoice:
                return None
            
            invoice.invoice_status = status
            invoice.invoice_updated_at = datetime.now()
            
            self.session.flush()
            return invoice
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to update invoice {invoice_id}: {e}")
            return None
    
    def get_invoice_totals(self, invoice_id: int) -> Dict[str, Any]:
        """Get invoice totals including paid amount"""
        try:
            invoice = self.session.query(Invoice).filter(
                Invoice.invoice_id == invoice_id
            ).first()
            
            if not invoice:
                return {}
            
            # Get all payments for this invoice
            payments = self.session.query(Payment).filter(
                Payment.payment_invoice_id == invoice_id,
                Payment.payment_status == 'completed'
            ).all()
            
            total_paid = sum(p.payment_amount for p in payments)
            
            return {
                'invoice_id': invoice_id,
                'invoice_number': invoice.invoice_number,
                'total_amount': float(invoice.invoice_total_amount) if invoice.invoice_total_amount else 0.0,
                'total_paid': float(total_paid) if total_paid else 0.0,
                'balance_due': max(0, float(invoice.invoice_total_amount or 0) - float(total_paid or 0)),
                'status': invoice.invoice_status,
                'due_date': invoice.invoice_due_date.isoformat() if invoice.invoice_due_date else None,
            }
        except Exception as e:
            logger.error(f"Failed to get invoice totals: {e}")
            return {}
    
    def get_overdue_invoices(self) -> List[Invoice]:
        """Get overdue invoices"""
        try:
            today = date.today()
            return self.session.query(Invoice).filter(
                Invoice.invoice_due_date < today,
                Invoice.invoice_status.in_(['unpaid', 'partially_paid'])
            ).order_by(Invoice.invoice_due_date).all()
        except Exception as e:
            logger.error(f"Failed to get overdue invoices: {e}")
            return []

