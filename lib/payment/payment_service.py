# services/payment_service.py - Final Fixed Version

import decimal
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from core.models import ProductProvider, Wallet, Payment, Invoice
from core.exceptions.handler import APIException, DatabaseException
from core.messages import *
import logging
import uuid

from lib.invoice.invoice_repository import InvoiceRepository
from lib.payment.payment_repo import PaymentRepository
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
        """Create a pending payment for an invoice."""
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
                    status_code=409,
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
            
            # Create payment record with pending status - NO payment_user_id
            payment_data = {
                'payment_invoice_id': invoice_id,
                'payment_amount': amount,
                'payment_method': payment_method,
                'payment_status': 'pending',
                'payment_reference': f"PAY-{uuid.uuid4().hex[:8].upper()}",
                'payment_notes': notes,
                'payment_type': payment_type,
                'payment_created_at': datetime.now(),
                'payment_updated_at': datetime.now()
            }
            
            payment = self.payment_repo.create_payment(payment_data)
            
            return {
                'id': payment.payment_id,
                'invoice_id': invoice_id,
                'user_id': user_id,  # Return user_id in response but not stored
                'amount': amount,
                'payment_method': payment_method,
                'status': 'pending',
                'payment_type': payment_type,
                'notes': notes,
                'created_at': payment.payment_created_at.isoformat() if payment.payment_created_at else None,
                'updated_at': None,
                'transactions': [],
                'refunds': []
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
        """Confirm a pending payment and process transactions."""
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
                    status_code=409,
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
            
            # Get user from invoice (Payment model doesn't have user_id)
            user_id = None
            if invoice.cart:
                user_id = invoice.cart.cart_client_user
            if not user_id and invoice.placed_order:
                user_id = invoice.placed_order.ordering_user_id
            
            # Process payment based on method
            transactions = []
            
            if payment.payment_method in ['wallet', 'deposit']:
                if not user_id:
                    raise APIException(
                        status_code=400,
                        error_code="USER_NOT_FOUND",
                        message="Could not determine user from invoice"
                    )
                
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
                        status_code=409,
                        error_code="INSUFFICIENT_BALANCE",
                        message=f"Insufficient wallet balance. Available: {wallet.wallet_balance}"
                    )
                
                # Deduct from wallet
                self.wallet_repo.update_wallet_balance(
                    wallet.id_wallet, payment.payment_amount, operation='subtract'
                )
                
                # Create transaction
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
                    'id': transaction.id_money_transaction,
                    'wallet_id': wallet.id_wallet,
                    'amount': float(payment.payment_amount),
                    'transaction_type': 'debit',
                    'status': 'completed',
                    'reference': transaction.money_transaction_reference,
                    'created_at': transaction.money_transaction_creation.isoformat() if transaction.money_transaction_creation else None
                })
            
            elif payment.payment_method in ['cash', 'card', 'bank_transfer', 'mobile_money']:
                # Get provider wallet
                provider_id = None
                if invoice.cart:
                    provider_id = invoice.cart.cart_product_provider_id
                
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
                    'id': transaction.id_money_transaction,
                    'wallet_id': transaction.money_transaction_wallet_destination_id,
                    'amount': float(payment.payment_amount),
                    'transaction_type': 'credit',
                    'status': 'completed',
                    'reference': transaction.money_transaction_reference,
                    'created_at': transaction.money_transaction_creation.isoformat() if transaction.money_transaction_creation else None
                })
            
            # Update payment status
            self.payment_repo.update_payment_status(payment_id, 'completed')
            
            # Update invoice status
            payment_summary = self.invoice_repo.get_invoice_totals(payment.payment_invoice_id)
            total_paid = decimal.Decimal(str(payment_summary.get('total_paid', 0))) + decimal.Decimal(str(payment.payment_amount))
            
            if total_paid >= invoice.invoice_total_amount:
                invoice_status = 'paid'
            else:
                invoice_status = 'partially_paid'
            
            self.invoice_repo.update_invoice_status(payment.payment_invoice_id, invoice_status)
            
            return {
                'id': payment_id,
                'invoice_id': payment.payment_invoice_id,
                'user_id': user_id,
                'amount': float(payment.payment_amount) if payment.payment_amount else 0,
                'payment_method': payment.payment_method,
                'status': 'completed',
                'payment_type': payment.payment_type,
                'notes': payment.payment_notes,
                'created_at': payment.payment_created_at.isoformat() if payment.payment_created_at else None,
                'updated_at': datetime.now().isoformat(),
                'transactions': transactions,
                'refunds': []
            }
            
        except APIException:
            raise
        except Exception as e:
            self.session.rollback()
            logger.error(f"Payment confirmation failed: {e}")
            raise DatabaseException(f"Payment confirmation failed: {str(e)}")
    
    def reject_payment(self, payment_id: int, reason: str) -> Dict[str, Any]:
        """Reject a pending payment."""
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
                    status_code=409,
                    error_code="PAYMENT_NOT_PENDING",
                    message=f"Payment status is {payment.payment_status}, not pending"
                )
            
            # Get user from invoice
            invoice = self.invoice_repo.get_invoice_by_id(payment.payment_invoice_id)
            user_id = None
            if invoice and invoice.cart:
                user_id = invoice.cart.cart_client_user
            
            # Update payment status to failed
            self.payment_repo.update_payment_status(
                payment_id, 'failed',
                reference=f"REJ-{uuid.uuid4().hex[:8].upper()}"
            )
            
            return {
                'id': payment_id,
                'invoice_id': payment.payment_invoice_id,
                'user_id': user_id,
                'amount': float(payment.payment_amount) if payment.payment_amount else 0,
                'payment_method': payment.payment_method,
                'status': 'failed',
                'payment_type': payment.payment_type,
                'notes': payment.payment_notes,
                'created_at': payment.payment_created_at.isoformat() if payment.payment_created_at else None,
                'updated_at': datetime.now().isoformat(),
                'transactions': [],
                'refunds': []
            }
            
        except APIException:
            raise
        except Exception as e:
            self.session.rollback()
            logger.error(f"Payment rejection failed: {e}")
            raise DatabaseException(f"Payment rejection failed: {str(e)}")
    
    def get_payment_by_id(self, payment_id: int) -> Dict[str, Any]:
        """Get payment details with transactions."""
        try:
            payment = self.payment_repo.get_payment_by_id(payment_id)
            if not payment:
                raise APIException(
                    status_code=404,
                    error_code="PAYMENT_NOT_FOUND",
                    message=f"Payment {payment_id} not found"
                )
            
            # Get user from invoice
            invoice = self.invoice_repo.get_invoice_by_id(payment.payment_invoice_id)
            user_id = None
            if invoice and invoice.cart:
                user_id = invoice.cart.cart_client_user
            if not user_id and invoice and invoice.placed_order:
                user_id = invoice.placed_order.ordering_user_id
            
            # Get transactions for this payment
            transactions = self.transaction_repo.get_transactions_by_payment(payment_id)
            
            return {
                'id': payment.payment_id,
                'invoice_id': payment.payment_invoice_id,
                'user_id': user_id,
                'amount': float(payment.payment_amount) if payment.payment_amount else 0,
                'payment_method': payment.payment_method,
                'status': payment.payment_status,
                'payment_type': payment.payment_type,
                'notes': payment.payment_notes,
                'created_at': payment.payment_created_at.isoformat() if payment.payment_created_at else None,
                'updated_at': payment.payment_updated_at.isoformat() if payment.payment_updated_at else None,
                'transactions': [
                    {
                        'id': t.id_money_transaction,
                        'wallet_id': t.money_transaction_wallet_source_id or t.money_transaction_wallet_destination_id,
                        'amount': float(t.money_transaction_amount) if t.money_transaction_amount else 0,
                        'transaction_type': 'debit' if t.money_transaction_wallet_source_id else 'credit',
                        'status': t.money_transaction_status,
                        'reference': t.money_transaction_reference,
                        'created_at': t.money_transaction_creation.isoformat() if t.money_transaction_creation else None
                    }
                    for t in transactions
                ],
                'refunds': []
            }
            
        except APIException:
            raise
        except Exception as e:
            logger.error(f"Failed to get payment: {e}")
            raise DatabaseException(f"Failed to get payment: {str(e)}")
    
    def get_invoice_payments(self, invoice_id: int) -> Dict[str, Any]:
        """Get all payments for an invoice."""
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
            
            # Get user_id from invoice for each payment
            user_id = None
            if invoice.cart:
                user_id = invoice.cart.cart_client_user
            if not user_id and invoice.placed_order:
                user_id = invoice.placed_order.ordering_user_id
            
            return {
                'invoice_id': invoice_id,
                'total_amount': float(invoice.invoice_total_amount) if invoice.invoice_total_amount else 0,
                'total_paid': float(summary.get('total_paid', 0)),
                'remaining_amount': float(summary.get('balance_due', 0)),
                'status': invoice.invoice_status,
                'payments': [
                    {
                        'id': p.payment_id,
                        'invoice_id': p.payment_invoice_id,
                        'user_id': user_id,
                        'amount': float(p.payment_amount) if p.payment_amount else 0,
                        'payment_method': p.payment_method,
                        'status': p.payment_status,
                        'payment_type': p.payment_type,
                        'notes': p.payment_notes,
                        'created_at': p.payment_created_at.isoformat() if p.payment_created_at else None,
                        'updated_at': p.payment_updated_at.isoformat() if p.payment_updated_at else None,
                        'transactions': []
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
        """Process a refund for a completed payment."""
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
                    status_code=409,
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
            if not user_id and invoice and invoice.placed_order:
                user_id = invoice.placed_order.ordering_user_id
            
            # Process refund
            transactions = []
            
            if payment.payment_method in ['wallet', 'deposit'] and user_id:
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
                        'id': transaction.id_money_transaction,
                        'wallet_id': wallet.id_wallet,
                        'amount': float(amount),
                        'transaction_type': 'refund',
                        'status': 'refunded',
                        'reference': transaction.money_transaction_reference,
                        'created_at': transaction.money_transaction_creation.isoformat() if transaction.money_transaction_creation else None
                    })
            
            # Update invoice status
            payment_summary = self.invoice_repo.get_invoice_totals(payment.payment_invoice_id)
            total_paid = payment_summary.get('total_paid', 0) - amount
            
            if total_paid <= 0:
                invoice_status = 'unpaid'
            elif invoice and total_paid < invoice.invoice_total_amount:
                invoice_status = 'partially_paid'
            else:
                invoice_status = 'paid'
            
            self.invoice_repo.update_invoice_status(payment.payment_invoice_id, invoice_status)
            
            return {
                'id': payment_id,
                'invoice_id': payment.payment_invoice_id,
                'user_id': user_id,
                'amount': float(amount),
                'payment_method': payment.payment_method,
                'status': 'refunded',
                'payment_type': payment.payment_type,
                'notes': payment.payment_notes,
                'created_at': payment.payment_created_at.isoformat() if payment.payment_created_at else None,
                'updated_at': datetime.now().isoformat(),
                'transactions': transactions,
                'refunds': [{
                    'amount': float(amount),
                    'reason': reason,
                    'refunded_at': datetime.now().isoformat()
                }]
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
            provider = self.session.query(ProductProvider).filter(
                ProductProvider.id_product_provider == provider_id
            ).first()
            
            if provider and provider.product_provider_wallet_id:
                return provider.product_provider_wallet_id
        
        return self._get_system_wallet_id()