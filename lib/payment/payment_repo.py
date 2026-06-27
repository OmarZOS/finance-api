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
                joinedload(Invoice.delivery),
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


class WalletRepository:
    """Repository for wallet operations"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def get_wallet_by_id(self, wallet_id: int) -> Optional[Wallet]:
        """Get wallet by ID"""
        try:
            return self.session.query(Wallet).filter(
                Wallet.id_wallet == wallet_id
            ).first()
        except Exception as e:
            logger.error(f"Failed to get wallet {wallet_id}: {e}")
            return None
    
    def get_wallet_by_user(self, user_id: int) -> Optional[Wallet]:
        """Get wallet for a user"""
        try:
            return self.session.query(Wallet).join(
                AppUser, AppUser.app_user_wallet_id == Wallet.id_wallet
            ).filter(AppUser.id_app_user == user_id).first()
        except Exception as e:
            logger.error(f"Failed to get wallet for user {user_id}: {e}")
            return None
    
    def update_wallet_balance(self, wallet_id: int, amount: float, 
                             operation: str = 'add') -> Optional[Wallet]:
        """Update wallet balance (add or subtract)"""
        try:
            wallet = self.session.query(Wallet).filter(
                Wallet.id_wallet == wallet_id
            ).first()
            
            if not wallet:
                return None
            
            current_balance = wallet.wallet_balance or 0.0
            if operation == 'add':
                wallet.wallet_balance = current_balance + amount
            elif operation == 'subtract':
                if current_balance < amount:
                    raise ValueError("Insufficient balance")
                wallet.wallet_balance = current_balance - amount
            else:
                raise ValueError(f"Invalid operation: {operation}")
            
            self.session.flush()
            return wallet
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to update wallet {wallet_id}: {e}")
            raise
    
    def create_wallet(self, wallet_data: Dict[str, Any]) -> Wallet:
        """Create a new wallet"""
        try:
            wallet = Wallet(**wallet_data)
            self.session.add(wallet)
            self.session.flush()
            return wallet
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to create wallet: {e}")
            raise DatabaseException(f"Wallet creation failed: {e}")
    
    def get_wallet_transactions(self, wallet_id: int, limit: int = 50) -> List[MoneyTransaction]:
        """Get wallet transactions"""
        try:
            return self.session.query(MoneyTransaction).filter(
                or_(
                    MoneyTransaction.money_transaction_wallet_source_id == wallet_id,
                    MoneyTransaction.money_transaction_wallet_destination_id == wallet_id
                )
            ).order_by(desc(MoneyTransaction.money_transaction_creation)).limit(limit).all()
        except Exception as e:
            logger.error(f"Failed to get wallet transactions: {e}")
            return []


class SubscriptionRepository:
    """Repository for subscription operations"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def get_plan_by_id(self, plan_id: int) -> Optional[Plan]:
        """Get plan by ID"""
        try:
            return self.session.query(Plan).filter(
                Plan.id_plan == plan_id
            ).first()
        except Exception as e:
            logger.error(f"Failed to get plan {plan_id}: {e}")
            return None
    
    def get_all_plans(self, plan_type: Optional[str] = None) -> List[Plan]:
        """Get all plans, optionally filtered by type"""
        try:
            query = self.session.query(Plan)
            if plan_type:
                query = query.filter(Plan.plan_type == plan_type)
            return query.order_by(Plan.plan_price).all()
        except Exception as e:
            logger.error(f"Failed to get plans: {e}")
            return []
    
    def get_user_subscription(self, user_id: int) -> Optional[Plan]:
        """Get user's current subscription plan"""
        try:
            user = self.session.query(AppUser).filter(
                AppUser.id_app_user == user_id
            ).first()
            
            if not user or not user.app_user_subscription_ref:
                return None
            
            return self.get_plan_by_id(user.app_user_subscription_ref)
        except Exception as e:
            logger.error(f"Failed to get user subscription: {e}")
            return None
    
    def update_user_subscription(self, user_id: int, plan_id: int) -> Optional[AppUser]:
        """Update user's subscription plan"""
        try:
            user = self.session.query(AppUser).filter(
                AppUser.id_app_user == user_id
            ).first()
            
            if not user:
                return None
            
            plan = self.get_plan_by_id(plan_id)
            if not plan:
                return None
            
            user.app_user_subscription_ref = plan_id
            user.app_user_last_updated = datetime.now()
            
            self.session.flush()
            return user
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to update user subscription: {e}")
            return None
    
    def get_subscription_stats(self) -> Dict[str, Any]:
        """Get subscription statistics"""
        try:
            total_users = self.session.query(AppUser).count()
            subscribed_users = self.session.query(AppUser).filter(
                AppUser.app_user_subscription_ref.isnot(None)
            ).count()
            
            # Get plan distribution
            plan_distribution = self.session.query(
                Plan.plan_name,
                func.count(AppUser.id_app_user).label('count')
            ).join(AppUser, AppUser.app_user_subscription_ref == Plan.id_plan).group_by(
                Plan.id_plan
            ).all()
            
            return {
                'total_users': total_users,
                'subscribed_users': subscribed_users,
                'subscription_rate': (subscribed_users / total_users * 100) if total_users > 0 else 0,
                'plan_distribution': [
                    {'plan': p[0], 'count': p[1]} for p in plan_distribution
                ]
            }
        except Exception as e:
            logger.error(f"Failed to get subscription stats: {e}")
            return {}


class MoneyTransactionRepository:
    """Repository for money transaction operations"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create_transaction(self, transaction_data: Dict[str, Any]) -> MoneyTransaction:
        """Create a new money transaction"""
        try:
            transaction = MoneyTransaction(**transaction_data)
            self.session.add(transaction)
            self.session.flush()
            return transaction
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to create transaction: {e}")
            raise DatabaseException(f"Transaction creation failed: {e}")
    
    def get_transaction_by_id(self, transaction_id: int) -> Optional[MoneyTransaction]:
        """Get transaction by ID"""
        try:
            return self.session.query(MoneyTransaction).options(
                joinedload(MoneyTransaction.money_transaction_wallet_source),
                joinedload(MoneyTransaction.money_transaction_wallet_destination),
                joinedload(MoneyTransaction.payment)
            ).filter(MoneyTransaction.id_money_transaction == transaction_id).first()
        except Exception as e:
            logger.error(f"Failed to get transaction {transaction_id}: {e}")
            return None
    
    def get_transactions_by_wallet(self, wallet_id: int, 
                                  status: Optional[str] = None,
                                  limit: int = 50) -> List[MoneyTransaction]:
        """Get transactions for a wallet"""
        try:
            query = self.session.query(MoneyTransaction).filter(
                or_(
                    MoneyTransaction.money_transaction_wallet_source_id == wallet_id,
                    MoneyTransaction.money_transaction_wallet_destination_id == wallet_id
                )
            )
            
            if status:
                query = query.filter(MoneyTransaction.money_transaction_status == status)
            
            return query.order_by(
                desc(MoneyTransaction.money_transaction_creation)
            ).limit(limit).all()
        except Exception as e:
            logger.error(f"Failed to get wallet transactions: {e}")
            return []
    
    def update_transaction_status(self, transaction_id: int, 
                                 status: str) -> Optional[MoneyTransaction]:
        """Update transaction status"""
        try:
            transaction = self.session.query(MoneyTransaction).filter(
                MoneyTransaction.id_money_transaction == transaction_id
            ).first()
            
            if not transaction:
                return None
            
            transaction.money_transaction_status = status
            transaction.money_transaction_last_updated = datetime.now()
            
            self.session.flush()
            return transaction
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to update transaction {transaction_id}: {e}")
            return None