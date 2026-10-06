# services/payment_service.py
"""
Payment service.

Owns the `Payment` lifecycle: create a pending payment, confirm or
reject it, refund it. Moving money is `WalletService`'s job — this
service asks it to debit or credit, and reads the transaction rows
back for the response.

The two services share a `Session`. A debit and the payment-status
update that follows are in the same transaction: if the payment
update fails, the wallet movement rolls back with it.
"""

import decimal
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from core.exceptions.handler import APIException, DatabaseException
from lib.invoice.invoice_repository import InvoiceRepository
from lib.payment.payment_repo import PaymentRepository
from lib.wallet.wallet_service import WalletService

logger = logging.getLogger(__name__)

class PaymentService:
    """Payment lifecycle and money movement coordination."""

    def __init__(self, session: Session):
        self.session = session
        self.payment_repo = PaymentRepository(session)
        self.invoice_repo = InvoiceRepository(session)
        self.wallet_service = WalletService(session)

    # ==================== Create ====================

    def create_payment(
        self,
        invoice_id: int,
        amount: decimal.Decimal,
        payment_method: str,
        user_id: int,
        notes: Optional[str] = None,
        payment_type: str = "payment",
    ) -> Dict[str, Any]:
        """Create a pending payment for an invoice.

        No money moves yet. Confirming the payment is what triggers
        the wallet debit or credit.
        """
        try:
            invoice = self.invoice_repo.get_invoice_by_id(invoice_id)
            if not invoice:
                raise APIException(
                    status_code=404,
                    error_code="INVOICE_NOT_FOUND",
                    message=f"Invoice {invoice_id} not found",
                )

            if invoice.invoice_status == "paid":
                raise APIException(
                    status_code=409,
                    error_code="INVOICE_ALREADY_PAID",
                    message="Invoice is already paid",
                )

            summary = self.invoice_repo.get_invoice_totals(invoice_id)
            balance_due = summary.get(
                "balance_due", invoice.invoice_total_amount or 0
            )
            if amount > balance_due:
                raise APIException(
                    status_code=400,
                    error_code="PAYMENT_EXCEEDS_BALANCE",
                    message=(
                        f"Payment amount {amount} exceeds balance "
                        f"due {balance_due}"
                    ),
                )

            payment = self.payment_repo.create_payment({
                "payment_invoice_id": invoice_id,
                "payment_amount": amount,
                "payment_method": payment_method,
                "payment_status": "pending",
                "payment_reference":
                    f"PAY-{uuid.uuid4().hex[:8].upper()}",
                "payment_notes": notes,
                "payment_type": payment_type,
                "payment_created_at": datetime.now(),
                "payment_updated_at": datetime.now(),
            })

            return self._format_payment(payment, user_id=user_id)

        except APIException:
            raise
        except Exception as e:
            logger.error(f"Payment creation failed: {e}")
            raise DatabaseException(
                f"Payment creation failed: {str(e)}"
            )

    # ==================== Confirm ====================

    def confirm_payment(
        self,
        payment_id: int,
        transaction_details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Confirm a pending payment.

        Two paths:

          * wallet / deposit — debit the user's wallet. The money
            flows from the user to the system wallet.
          * cash / card / bank_transfer / mobile_money — credit
            the provider's wallet. The money flows from the
            system wallet to the provider.

        Both paths end with the payment marked completed and the
        invoice status recomputed.
        """
        try:
            payment = self._load_pending_payment(payment_id)
            invoice = self._load_invoice_for(payment)
            user_id = self._resolve_user_id(
                invoice, transaction_details
            )

            transactions = []

            if payment.payment_method in ("wallet", "deposit"):
                transactions.append(
                    self._confirm_wallet_payment(
                        payment, invoice, user_id
                    )
                )
            elif payment.payment_method in (
                "cash", "card", "bank_transfer", "mobile_money",
            ):
                transactions.append(
                    self._confirm_external_payment(payment, invoice)
                )

            self.payment_repo.update_payment_status(
                payment_id, "completed"
            )
            self._recompute_invoice_status(payment, invoice)

            return self._format_payment(
                payment,
                user_id=user_id,
                status="completed",
                transactions=transactions,
            )

        except APIException:
            raise
        except Exception as e:
            self.session.rollback()
            logger.error(f"Payment confirmation failed: {e}")
            raise DatabaseException(
                f"Payment confirmation failed: {str(e)}"
            )

    def _confirm_wallet_payment(self, payment, invoice, user_id):
        """Debit the user's wallet, credit the system wallet."""
        if not user_id:
            raise APIException(
                status_code=400,
                error_code="USER_NOT_FOUND",
                message="Could not determine user from invoice",
            )

        wallet = self.wallet_service.get_user_wallet(user_id)
        transaction = self.wallet_service.debit(
            wallet,
            payment.payment_amount,
            reference=payment.payment_reference,
            for_payment_id=payment.payment_id,
        )
        return self._format_transaction(transaction, kind="debit")

    def _confirm_external_payment(self, payment, invoice):
        """Credit the provider's wallet, debit the system wallet."""
        provider_id = None
        if invoice.cart:
            provider_id = invoice.cart[0].cart_product_provider_id

        provider_wallet = self.wallet_service.get_provider_wallet(
            provider_id
        )
        transaction = self.wallet_service.credit(
            provider_wallet,
            payment.payment_amount,
            reference=payment.payment_reference,
            for_payment_id=payment.payment_id,
        )
        return self._format_transaction(transaction, kind="credit")

    # ==================== Reject ====================

    def reject_payment(
        self, payment_id: int, reason: str,
    ) -> Dict[str, Any]:
        """Reject a pending payment.

        No money moves — the payment was pending, so nothing has
        been debited or credited yet. This is a status change only.
        """
        try:
            payment = self._load_pending_payment(payment_id)
            invoice = self._load_invoice_for(payment)
            user_id = self._resolve_user_id(invoice, None)

            self.payment_repo.update_payment_status(
                payment_id,
                "failed",
                reference=f"REJ-{uuid.uuid4().hex[:8].upper()}",
            )

            return self._format_payment(
                payment,
                user_id=user_id,
                status="failed",
            )

        except APIException:
            raise
        except Exception as e:
            self.session.rollback()
            logger.error(f"Payment rejection failed: {e}")
            raise DatabaseException(
                f"Payment rejection failed: {str(e)}"
            )

    # ==================== Read ====================

    def get_payment_by_id(self, payment_id: int) -> Dict[str, Any]:
        """Get payment details with its transaction ledger."""
        try:
            payment = self.payment_repo.get_payment_by_id(payment_id)
            if not payment:
                raise APIException(
                    status_code=404,
                    error_code="PAYMENT_NOT_FOUND",
                    message=f"Payment {payment_id} not found",
                )

            invoice = self.invoice_repo.get_invoice_by_id(
                payment.payment_invoice_id
            )
            user_id = self._resolve_user_id(invoice, None)

            transactions = (
                self.wallet_service.get_transactions_for_payment(
                    payment_id
                )
            )

            return self._format_payment(
                payment,
                user_id=user_id,
                transactions=[
                    self._format_transaction(t) for t in transactions
                ],
            )

        except APIException:
            raise
        except Exception as e:
            logger.error(f"Failed to get payment: {e}")
            raise DatabaseException(f"Failed to get payment: {str(e)}")

    def get_invoice_payments(
        self, invoice_id: int,
    ) -> Dict[str, Any]:
        """All payments for an invoice, with totals."""
        try:
            invoice = self.invoice_repo.get_invoice_by_id(invoice_id)
            if not invoice:
                raise APIException(
                    status_code=404,
                    error_code="INVOICE_NOT_FOUND",
                    message=f"Invoice {invoice_id} not found",
                )

            payments = self.payment_repo.get_payments_by_invoice(
                invoice_id
            )
            summary = self.invoice_repo.get_invoice_totals(invoice_id)
            user_id = self._resolve_user_id(invoice, None)

            return {
                "invoice_id": invoice_id,
                "total_amount": decimal.Decimal(invoice.invoice_total_amount or 0),
                "total_paid": decimal.Decimal(summary.get("total_paid", 0)),
                "remaining_amount": decimal.Decimal(
                    summary.get("balance_due", 0)
                ),
                "status": invoice.invoice_status,
                "payments": [
                    self._format_payment(p, user_id=user_id)
                    for p in payments
                ],
            }

        except APIException:
            raise
        except Exception as e:
            logger.error(f"Failed to get invoice payments: {e}")
            raise DatabaseException(
                f"Failed to get invoice payments: {str(e)}"
            )

    # ==================== Refund ====================

    def process_refund(
        self,
        payment_id: int,
        reason: str,
        refund_amount: Optional[decimal.Decimal] = None,
    ) -> Dict[str, Any]:
        """Refund a completed payment.

        For wallet/deposit payments, the money goes back to the
        user's wallet. For external payments, there is nothing to
        reverse on the wallet side — the money was debited from the
        system and credited to the provider; a real refund would be
        the provider's responsibility. This method marks the payment
        refunded and updates the invoice.
        """
        try:
            payment = self.payment_repo.get_payment_by_id(payment_id)
            if not payment:
                raise APIException(
                    status_code=404,
                    error_code="PAYMENT_NOT_FOUND",
                    message=f"Payment {payment_id} not found",
                )

            if payment.payment_status != "completed":
                raise APIException(
                    status_code=409,
                    error_code="PAYMENT_NOT_COMPLETED",
                    message="Only completed payments can be refunded",
                )

            amount = refund_amount or payment.payment_amount
            if amount > payment.payment_amount:
                raise APIException(
                    status_code=400,
                    error_code="INVALID_REFUND_AMOUNT",
                    message=(
                        f"Refund amount {amount} exceeds payment "
                        f"amount {payment.payment_amount}"
                    ),
                )

            self.payment_repo.update_payment_status(
                payment_id,
                "refunded",
                reference=f"REF-{uuid.uuid4().hex[:8].upper()}",
            )

            invoice = self.invoice_repo.get_invoice_by_id(
                payment.payment_invoice_id
            )
            user_id = self._resolve_user_id(invoice, None)

            transactions = []
            if (
                payment.payment_method in ("wallet", "deposit")
                and user_id
            ):
                wallet = self.wallet_service.find_user_wallet(user_id)
                if wallet:
                    transaction = self.wallet_service.credit(
                        wallet,
                        amount,
                        reference=f"REF-{uuid.uuid4().hex[:8].upper()}",
                        for_payment_id=payment_id,
                        status="refunded",
                    )
                    transactions.append(
                        self._format_transaction(
                            transaction, kind="refund",
                        )
                    )

            self._recompute_invoice_status(
                payment, invoice, refunded=amount,
            )

            return self._format_payment(
                payment,
                user_id=user_id,
                status="refunded",
                transactions=transactions,
                refunds=[{
                    "amount": decimal.Decimal(amount),
                    "reason": reason,
                    "refunded_at": datetime.now().isoformat(),
                }],
            )

        except APIException:
            raise
        except Exception as e:
            self.session.rollback()
            logger.error(f"Refund failed: {e}")
            raise DatabaseException(f"Refund failed: {str(e)}")

    # ==================== Internals ====================

    def _load_pending_payment(self, payment_id: int):
        payment = self.payment_repo.get_payment_by_id(payment_id)
        if not payment:
            raise APIException(
                status_code=404,
                error_code="PAYMENT_NOT_FOUND",
                message=f"Payment {payment_id} not found",
            )
        if payment.payment_status != "pending":
            raise APIException(
                status_code=409,
                error_code="PAYMENT_NOT_PENDING",
                message=(
                    f"Payment status is {payment.payment_status}, "
                    f"not pending"
                ),
            )
        return payment

    def _load_invoice_for(self, payment):
        invoice = self.invoice_repo.get_invoice_by_id(
            payment.payment_invoice_id
        )
        if not invoice:
            raise APIException(
                status_code=404,
                error_code="INVOICE_NOT_FOUND",
                message="Associated invoice not found",
            )
        return invoice

    def _resolve_user_id(self, invoice, transaction_details):
        """Resolve the user id from the transaction details or the
        invoice's cart/order.

        The `Payment` table doesn't carry a user id — the money
        belongs to whoever owns the invoice. Cart is the primary
        source; placed orders are the fallback.
        """
        if transaction_details:
            user_id = transaction_details.get("user_id")
            if user_id:
                return user_id

        if invoice is None:
            return None

        if invoice.cart:
            user_id = invoice.cart[0].cart_client_user
            if user_id:
                return user_id

        if invoice.placed_order:
            return invoice.placed_order[0].ordering_user_id

        return None

    def _recompute_invoice_status(
        self, payment, invoice, refunded: decimal.Decimal = 0,
    ) -> None:
        """Update the invoice status based on totals paid."""
        summary = self.invoice_repo.get_invoice_totals(
            payment.payment_invoice_id
        )
        total_paid = (
            decimal.Decimal(str(summary.get("total_paid", 0)))
            + decimal.Decimal(str(payment.payment_amount))
            - decimal.Decimal(str(refunded))
        )

        if total_paid <= 0:
            status = "unpaid"
        elif total_paid >= invoice.invoice_total_amount:
            status = "paid"
        else:
            status = "partially_paid"

        self.invoice_repo.update_invoice_status(
            payment.payment_invoice_id, status,
        )

    def _format_payment(
        self,
        payment,
        *,
        user_id=None,
        status=None,
        transactions=None,
        refunds=None,
    ) -> Dict[str, Any]:
        """Shape the payment row into the response dict."""
        return {
            "id": payment.payment_id,
            "invoice_id": payment.payment_invoice_id,
            "user_id": user_id,
            "amount": (
                decimal.Decimal(payment.payment_amount)
                if payment.payment_amount else 0
            ),
            "payment_method": payment.payment_method,
            "status": status or payment.payment_status,
            "payment_type": payment.payment_type,
            "notes": payment.payment_notes,
            "created_at": (
                payment.payment_created_at.isoformat()
                if payment.payment_created_at else None
            ),
            "updated_at": (
                payment.payment_updated_at.isoformat()
                if payment.payment_updated_at else None
            ),
            "transactions": transactions or [],
            "refunds": refunds or [],
        }

    def _format_transaction(self, t, kind=None) -> Dict[str, Any]:
        """Shape a MoneyTransaction row into the response dict."""
        if kind is None:
            # Infer from which side of the transaction the wallet is
            # on. Destination wallet means credit; source wallet
            # means debit.
            kind = (
                "credit"
                if t.money_transaction_wallet_destination_id
                else "debit"
            )

        wallet_id = (
            t.money_transaction_wallet_source_id
            or t.money_transaction_wallet_destination_id
        )

        return {
            "id": t.id_money_transaction,
            "wallet_id": wallet_id,
            "amount": (
                decimal.Decimal(t.money_transaction_amount)
                if t.money_transaction_amount else 0
            ),
            "transaction_type": kind,
            "status": t.money_transaction_status,
            "reference": t.money_transaction_reference,
            "created_at": (
                t.money_transaction_creation.isoformat()
                if t.money_transaction_creation else None
            ),
        }