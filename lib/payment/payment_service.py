
# services/payment_service.py

from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from core.models import ProductProvider, Wallet
from core.exceptions.handler import APIException, DatabaseException
from core.messages import *
import logging
import uuid

from lib.invoice.invoice_repository import InvoiceRepository
from lib.payment.payment_repo import  PaymentRepository
from lib.wallet.money_transaction_repository import MoneyTransactionRepository
from lib.wallet.wallet_repository import WalletRepository

logger = logging.getLogger(__name__)


class PaymentService:
    """Service for payment operations"""
    
    def __init__(self, session: Session):
        self.session = session
        self.payment_repo = PaymentRepository(session)
        self.invoice_repo = InvoiceRepository(session)
        self.wallet_repo = WalletRepository(session)
        self.transaction_repo = MoneyTransactionRepository(session)
    
    def create_payment(
        self, 
        invoice_id: int, 
        amount: float, 
        payment_method: str,
        user_id: int,
        notes: Optional[str] = None,
        payment_type: str = 'payment'
    ) -> Dict[str, Any]:
        """
        Create a pending payment for an invoice.
        The invoice must already exist in the database.
        """
        try:
            # Get existing invoice
            invoice = self.invoice_repo.get_invoice_by_id(invoice_id)
            if not invoice:
                raise APIException(
                    status_code=404,
                    error_code="INVOICE_NOT_FOUND",
                    message=f"Invoice {invoice_id} not found"
                )
            
            # Check if invoice is already paid
            if invoice.invoice_status == 'paid':
                raise APIException(
                    status_code=400,
                    error_code="INVOICE_ALREADY_PAID",
                    message="Invoice is already paid"
                )
            
            # Get payment summary
            payment_summary = self.invoice_repo.get_invoice_totals(invoice_id)
            balance_due = payment_summary.get('balance_due', invoice.invoice_total_amount or 0)
            
            if amount > balance_due:
                raise APIException(
                    status_code=400,
                    error_code="PAYMENT_EXCEEDS_BALANCE",
                    message=f"Payment amount {amount} exceeds balance due {balance_due}"
                )
            
            # Create payment record with pending status
            payment_data = {
                'payment_invoice_id': invoice_id,
                'payment_amount': amount,
                'payment_method': payment_method,
                'payment_status': 'pending',  # Always starts as pending
                'payment_reference': f"PAY-{uuid.uuid4().hex[:8].upper()}",
                'payment_notes': notes,
                'payment_type': payment_type,
                'payment_created_at': datetime.now(),
                'payment_updated_at': datetime.now()
            }
            
            payment = self.payment_repo.create_payment(payment_data)
            
            # Return payment details (still pending)
            return {
                'payment_id': payment.payment_id,
                'invoice_id': invoice_id,
                'amount': amount,
                'payment_method': payment_method,
                'status': 'pending',
                'reference': payment.payment_reference,
                'balance_due': balance_due - amount,
                'created_at': payment.payment_created_at.isoformat() if payment.payment_created_at else None,
                'message': 'Payment created successfully. Awaiting confirmation.'
            }
            
        except APIException:
            raise
        except Exception as e:
            logger.error(f"Payment creation failed: {e}")
            raise DatabaseException(f"Payment creation failed: {str(e)}")
    
    def confirm_payment(
        self, 
        payment_id: int,
        transaction_details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Confirm a pending payment and process transactions.
        Creates money transactions for wallet transfers.
        """
        try:
            # Get payment
            payment = self.payment_repo.get_payment_by_id(payment_id)
            if not payment:
                raise APIException(
                    status_code=404,
                    error_code="PAYMENT_NOT_FOUND",
                    message=f"Payment {payment_id} not found"
                )
            
            if payment.payment_status != 'pending':
                raise APIException(
                    status_code=400,
                    error_code="PAYMENT_NOT_PENDING",
                    message=f"Payment status is {payment.payment_status}, not pending"
                )
            
            # Get invoice
            invoice = self.invoice_repo.get_invoice_by_id(payment.payment_invoice_id)
            if not invoice:
                raise APIException(
                    status_code=404,
                    error_code="INVOICE_NOT_FOUND",
                    message="Associated invoice not found"
                )
            
            # Get user from invoice
            user_id = None
            if invoice.cart:
                user_id = invoice.cart.cart_client_user
            elif invoice.placed_order:
                user_id = invoice.placed_order.ordering_user_id
            
            if not user_id:
                raise APIException(
                    status_code=400,
                    error_code="USER_NOT_FOUND",
                    message="Could not determine user from invoice"
                )
            
            # Process payment based on method
            transactions = []
            
            if payment.payment_method in ['wallet', 'deposit']:
                # Wallet payment - transfer from user's wallet
                wallet = self.wallet_repo.get_wallet_by_user(user_id)
                if not wallet:
                    raise APIException(
                        status_code=404,
                        error_code="WALLET_NOT_FOUND",
                        message="User wallet not found"
                    )
                
                # Check wallet balance
                if wallet.wallet_balance < payment.payment_amount:
                    raise APIException(
                        status_code=400,
                        error_code="INSUFFICIENT_BALANCE",
                        message=f"Insufficient wallet balance. Available: {wallet.wallet_balance}"
                    )
                
                # Deduct from wallet
                self.wallet_repo.update_wallet_balance(
                    wallet.id_wallet, payment.payment_amount, operation='subtract'
                )
                
                # Create transaction: User -> System
                transaction_data = {
                    'money_transaction_wallet_source_id': wallet.id_wallet,
                    'money_transaction_wallet_destination_id': self._get_system_wallet_id(),
                    'money_transaction_amount': payment.payment_amount,
                    'money_transaction_reference': payment.payment_reference,
                    'money_transaction_status': 'completed',
                    'money_transaction_for_payment': payment_id,
                    'money_transaction_creation': datetime.now(),
                    'money_transaction_last_updated': datetime.now()
                }
                transaction = self.transaction_repo.create_transaction(transaction_data)
                transactions.append({
                    'type': 'debit',
                    'wallet_id': wallet.id_wallet,
                    'amount': payment.payment_amount,
                    'reference': transaction.money_transaction_reference,
                    'status': 'completed'
                })
            
            elif payment.payment_method in ['cash', 'card', 'bank_transfer', 'mobile_money']:
                # External payment - create transaction from system to provider
                # Get provider wallet
                provider_id = None
                if invoice.cart:
                    provider_id = invoice.cart.cart_product_provider_id
                elif invoice.placed_order:
                    # Get provider from order
                    pass
                
                # Create transaction: System -> Provider
                transaction_data = {
                    'money_transaction_wallet_source_id': self._get_system_wallet_id(),
                    'money_transaction_wallet_destination_id': self._get_provider_wallet_id(provider_id),
                    'money_transaction_amount': payment.payment_amount,
                    'money_transaction_reference': payment.payment_reference,
                    'money_transaction_status': 'completed',
                    'money_transaction_for_payment': payment_id,
                    'money_transaction_creation': datetime.now(),
                    'money_transaction_last_updated': datetime.now()
                }
                transaction = self.transaction_repo.create_transaction(transaction_data)
                transactions.append({
                    'type': 'credit',
                    'wallet_id': transaction.money_transaction_wallet_destination_id,
                    'amount': payment.payment_amount,
                    'reference': transaction.money_transaction_reference,
                    'status': 'completed'
                })
                
                # Also create user -> system transaction if deposit
                if transaction_details and transaction_details.get('is_deposit'):
                    # Get user wallet
                    wallet = self.wallet_repo.get_wallet_by_user(user_id)
                    if wallet:
                        deposit_data = {
                            'money_transaction_wallet_source_id': wallet.id_wallet,
                            'money_transaction_wallet_destination_id': self._get_system_wallet_id(),
                            'money_transaction_amount': payment.payment_amount,
                            'money_transaction_reference': f"DEP-{uuid.uuid4().hex[:8].upper()}",
                            'money_transaction_status': 'completed',
                            'money_transaction_for_payment': payment_id,
                            'money_transaction_creation': datetime.now(),
                            'money_transaction_last_updated': datetime.now()
                        }
                        deposit_transaction = self.transaction_repo.create_transaction(deposit_data)
                        transactions.append({
                            'type': 'deposit',
                            'wallet_id': wallet.id_wallet,
                            'amount': payment.payment_amount,
                            'reference': deposit_transaction.money_transaction_reference,
                            'status': 'completed'
                        })
            
            # Update payment status to completed
            self.payment_repo.update_payment_status(
                payment_id, 'completed',
                reference=payment.payment_reference
            )
            
            # Update invoice status
            payment_summary = self.invoice_repo.get_invoice_totals(payment.payment_invoice_id)
            total_paid = payment_summary.get('total_paid', 0) + payment.payment_amount
            
            if total_paid >= invoice.invoice_total_amount:
                invoice_status = 'paid'
            else:
                invoice_status = 'partially_paid'
            
            self.invoice_repo.update_invoice_status(payment.payment_invoice_id, invoice_status)
            
            return {
                'payment_id': payment_id,
                'invoice_id': payment.payment_invoice_id,
                'status': 'completed',
                'amount': float(payment.payment_amount) if payment.payment_amount else 0,
                'reference': payment.payment_reference,
                'invoice_status': invoice_status,
                'transactions': transactions,
                'confirmed_at': datetime.now().isoformat()
            }
            
        except APIException:
            raise
        except Exception as e:
            self.session.rollback()
            logger.error(f"Payment confirmation failed: {e}")
            raise DatabaseException(f"Payment confirmation failed: {str(e)}")
    
    def reject_payment(self, payment_id: int, reason: str) -> Dict[str, Any]:
        """
        Reject a pending payment.
        No transactions are created for rejected payments.
        """
        try:
            payment = self.payment_repo.get_payment_by_id(payment_id)
            if not payment:
                raise APIException(
                    status_code=404,
                    error_code="PAYMENT_NOT_FOUND",
                    message=f"Payment {payment_id} not found"
                )
            
            if payment.payment_status != 'pending':
                raise APIException(
                    status_code=400,
                    error_code="PAYMENT_NOT_PENDING",
                    message=f"Payment status is {payment.payment_status}, not pending"
                )
            
            # Update payment status to failed
            self.payment_repo.update_payment_status(
                payment_id, 'failed',
                reference=f"REJ-{uuid.uuid4().hex[:8].upper()}"
            )
            
            return {
                'payment_id': payment_id,
                'status': 'failed',
                'reason': reason,
                'rejected_at': datetime.now().isoformat()
            }
            
        except APIException:
            raise
        except Exception as e:
            self.session.rollback()
            logger.error(f"Payment rejection failed: {e}")
            raise DatabaseException(f"Payment rejection failed: {str(e)}")
    
    def get_payment_by_id(self, payment_id: int) -> Dict[str, Any]:
        """Get payment details with transactions"""
        try:
            payment = self.payment_repo.get_payment_by_id(payment_id)
            if not payment:
                raise APIException(
                    status_code=404,
                    error_code="PAYMENT_NOT_FOUND",
                    message=f"Payment {payment_id} not found"
                )
            
            # Get transactions for this payment
            transactions = self.transaction_repo.get_transactions_by_payment(payment_id)
            
            return {
                'payment_id': payment.payment_id,
                'invoice_id': payment.payment_invoice_id,
                'amount': float(payment.payment_amount) if payment.payment_amount else 0,
                'payment_method': payment.payment_method,
                'status': payment.payment_status,
                'reference': payment.payment_reference,
                'type': payment.payment_type,
                'notes': payment.payment_notes,
                'created_at': payment.payment_created_at.isoformat() if payment.payment_created_at else None,
                'updated_at': payment.payment_updated_at.isoformat() if payment.payment_updated_at else None,
                'transactions': [
                    {
                        'id': t.id_money_transaction,
                        'source_wallet': t.money_transaction_wallet_source_id,
                        'destination_wallet': t.money_transaction_wallet_destination_id,
                        'amount': t.money_transaction_amount,
                        'reference': t.money_transaction_reference,
                        'status': t.money_transaction_status,
                        'created_at': t.money_transaction_creation.isoformat() if t.money_transaction_creation else None
                    }
                    for t in transactions
                ]
            }
            
        except APIException:
            raise
        except Exception as e:
            logger.error(f"Failed to get payment: {e}")
            raise DatabaseException(f"Failed to get payment: {str(e)}")
    
    def get_invoice_payments(self, invoice_id: int) -> Dict[str, Any]:
        """Get all payments for an invoice"""
        try:
            invoice = self.invoice_repo.get_invoice_by_id(invoice_id)
            if not invoice:
                raise APIException(
                    status_code=404,
                    error_code="INVOICE_NOT_FOUND",
                    message=f"Invoice {invoice_id} not found"
                )
            
            payments = self.payment_repo.get_payments_by_invoice(invoice_id)
            summary = self.invoice_repo.get_invoice_totals(invoice_id)
            
            return {
                'invoice_id': invoice_id,
                'invoice_status': invoice.invoice_status,
                'total_amount': float(invoice.invoice_total_amount) if invoice.invoice_total_amount else 0,
                'summary': summary,
                'payments': [
                    {
                        'payment_id': p.payment_id,
                        'amount': float(p.payment_amount) if p.payment_amount else 0,
                        'status': p.payment_status,
                        'method': p.payment_method,
                        'reference': p.payment_reference,
                        'type': p.payment_type,
                        'created_at': p.payment_created_at.isoformat() if p.payment_created_at else None,
                        'updated_at': p.payment_updated_at.isoformat() if p.payment_updated_at else None
                    }
                    for p in payments
                ]
            }
            
        except APIException:
            raise
        except Exception as e:
            logger.error(f"Failed to get invoice payments: {e}")
            raise DatabaseException(f"Failed to get invoice payments: {str(e)}")
    
    def process_refund(
        self, 
        payment_id: int, 
        reason: str,
        refund_amount: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Process a refund for a completed payment.
        Creates reverse transactions.
        """
        try:
            payment = self.payment_repo.get_payment_by_id(payment_id)
            if not payment:
                raise APIException(
                    status_code=404,
                    error_code="PAYMENT_NOT_FOUND",
                    message=f"Payment {payment_id} not found"
                )
            
            if payment.payment_status != 'completed':
                raise APIException(
                    status_code=400,
                    error_code="PAYMENT_NOT_COMPLETED",
                    message="Only completed payments can be refunded"
                )
            
            amount = refund_amount or payment.payment_amount
            
            if amount > payment.payment_amount:
                raise APIException(
                    status_code=400,
                    error_code="INVALID_REFUND_AMOUNT",
                    message=f"Refund amount {amount} exceeds payment amount {payment.payment_amount}"
                )
            
            # Update payment status
            self.payment_repo.update_payment_status(
                payment_id, 'refunded',
                reference=f"REF-{uuid.uuid4().hex[:8].upper()}"
            )
            
            # Get user from invoice
            invoice = self.invoice_repo.get_invoice_by_id(payment.payment_invoice_id)
            user_id = None
            if invoice and invoice.cart:
                user_id = invoice.cart.cart_client_user
            
            # Process refund based on original payment method
            transactions = []
            
            if payment.payment_method in ['wallet', 'deposit'] and user_id:
                # Refund to user's wallet
                wallet = self.wallet_repo.get_wallet_by_user(user_id)
                if wallet:
                    # Add funds back to wallet
                    self.wallet_repo.update_wallet_balance(
                        wallet.id_wallet, amount, operation='add'
                    )
                    
                    # Create refund transaction
                    transaction_data = {
                        'money_transaction_wallet_source_id': self._get_system_wallet_id(),
                        'money_transaction_wallet_destination_id': wallet.id_wallet,
                        'money_transaction_amount': amount,
                        'money_transaction_reference': f"REF-{uuid.uuid4().hex[:8].upper()}",
                        'money_transaction_status': 'refunded',
                        'money_transaction_for_payment': payment_id,
                        'money_transaction_creation': datetime.now(),
                        'money_transaction_last_updated': datetime.now()
                    }
                    transaction = self.transaction_repo.create_transaction(transaction_data)
                    transactions.append({
                        'type': 'refund',
                        'wallet_id': wallet.id_wallet,
                        'amount': amount,
                        'reference': transaction.money_transaction_reference,
                        'status': 'refunded'
                    })
            
            # Update invoice status
            payment_summary = self.invoice_repo.get_invoice_totals(payment.payment_invoice_id)
            total_paid = payment_summary.get('total_paid', 0) - amount
            
            if total_paid <= 0:
                invoice_status = 'unpaid'
            elif total_paid < invoice.invoice_total_amount:
                invoice_status = 'partially_paid'
            else:
                invoice_status = 'paid'
            
            self.invoice_repo.update_invoice_status(payment.payment_invoice_id, invoice_status)
            
            return {
                'payment_id': payment_id,
                'refund_amount': amount,
                'reason': reason,
                'status': 'refunded',
                'invoice_status': invoice_status,
                'transactions': transactions,
                'refunded_at': datetime.now().isoformat()
            }
            
        except APIException:
            raise
        except Exception as e:
            self.session.rollback()
            logger.error(f"Refund failed: {e}")
            raise DatabaseException(f"Refund failed: {str(e)}")
    
    def _get_system_wallet_id(self) -> int:
        """Get or create system wallet"""
        wallet = self.session.query(Wallet).filter(
            Wallet.wallet_type == 'system'
        ).first()
        
        if not wallet:
            wallet_data = {
                'wallet_type': 'system',
                'wallet_currency': 'DZD',
                'wallet_balance': 0.0,
                'wallet_status': 'active'
            }
            wallet = self.wallet_repo.create_wallet(wallet_data)
        
        return wallet.id_wallet
    
    def _get_provider_wallet_id(self, provider_id: Optional[int]) -> int:
        """Get provider's wallet ID"""
        if provider_id:
            # Get provider's wallet
            provider = self.session.query(ProductProvider).filter(
                ProductProvider.id_product_provider == provider_id
            ).first()
            
            if provider and provider.product_provider_wallet_id:
                return provider.product_provider_wallet_id
        
        # Fallback to system wallet
        return self._get_system_wallet_id()