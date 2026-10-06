# services/wallet_service.py
"""
Wallet and money-movement service.

Owns four things:

  * Finding a wallet — by user, by provider, or the system wallet
  * Debiting a wallet — money out, with a ledger entry
  * Crediting a wallet — money in, with a ledger entry
  * The transaction ledger — every mutation of a wallet's balance
    produces a `MoneyTransaction` row

`PaymentService` composes this. It never touches `Wallet` or
`MoneyTransaction` directly.

The service takes a `Session` and shares it with its caller, so a
debit and the payment-status update that follows are in the same
transaction. If the payment update fails, the wallet movement rolls
back with it.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from core.exceptions.handler import APIException
from core.models import MoneyTransaction, ProductProvider, Wallet
from lib.wallet.money_transaction_repository import (
    MoneyTransactionRepository,
)
from lib.wallet.wallet_repository import WalletRepository

import logging

logger = logging.getLogger(__name__)


class WalletService:
    """Read and write access to wallets and their transaction ledger."""

    def __init__(self, session: Session):
        self.session = session
        self.wallet_repo = WalletRepository(session)
        self.transaction_repo = MoneyTransactionRepository(session)

    # ==================== Lookups ====================

    def get_user_wallet(self, user_id: int) -> Wallet:
        """Return the user's wallet, or raise 404.

        Callers that want to handle the missing-wallet case
        themselves should use `find_user_wallet`.
        """
        wallet = self.wallet_repo.get_wallet_by_user(user_id)
        if not wallet:
            raise APIException(
                status_code=404,
                error_code="WALLET_NOT_FOUND",
                message="User wallet not found",
            )
        return wallet

    def find_user_wallet(self, user_id: int) -> Optional[Wallet]:
        """Return the user's wallet, or None."""
        return self.wallet_repo.get_wallet_by_user(user_id)

    def get_provider_wallet(self, provider_id: Optional[int]) -> Wallet:
        """Return the provider's wallet, or the system wallet.

        A provider without a wallet is not an error — the caller
        may be creating the wallet lazily, or the provider may be a
        system-owned entity whose money is accounted for
        centrally. In both cases, resolving to the system wallet is
        the safe default.
        """
        if provider_id is not None:
            provider = (
                self.session.query(ProductProvider)
                .filter(ProductProvider.id_product_provider == provider_id)
                .first()
            )
            if provider and provider.product_provider_wallet_id:
                wallet = self.wallet_repo.get_wallet_by_id(
                    provider.product_provider_wallet_id
                )
                if wallet:
                    return wallet

        return self.get_system_wallet()

    def get_system_wallet(self) -> Wallet:
        """Return the system wallet, creating it if it doesn't
        exist.

        The system wallet is the counterparty for every external
        payment and the sink for money that hasn't been routed to a
        real wallet yet. Exactly one row should have
        `wallet_type == 'system'`; if more than one exists, this
        returns the first — a data-integrity problem the caller
        should investigate.
        """
        wallet = (
            self.session.query(Wallet)
            .filter(Wallet.wallet_type == "system")
            .first()
        )
        if wallet:
            return wallet

        # Create it. The creation is idempotent-ish: two concurrent
        # callers could both see None and both attempt to insert.
        # The database's unique constraint on `wallet_type` (if
        # present) rejects the second, and `create_wallet` raises.
        logger.info("Creating system wallet")
        wallet = self.wallet_repo.create_wallet({
            "wallet_type": "system",
            "wallet_currency": "DZD",
            "wallet_balance": 0.0,
            "wallet_status": "active",
        })
        return wallet

    # ==================== Movements ====================

    def debit(
        self,
        wallet: Wallet,
        amount: Decimal,
        *,
        reference: str,
        for_payment_id: Optional[int] = None,
        destination_wallet: Optional[Wallet] = None,
    ) -> MoneyTransaction:
        """Take `amount` out of `wallet`.

        The wallet's balance decreases by `amount`, and a
        `MoneyTransaction` row records the movement. The row's
        destination is `destination_wallet` when supplied, or the
        system wallet otherwise — money never leaves the ledger.

        Raises 409 when the wallet's balance is below `amount`.
        The check and the mutation are in the same DB transaction;
        they're not atomic against concurrent debits, but the
        caller's transaction boundary is what matters here.
        """
        if amount <= 0:
            raise APIException(
                status_code=400,
                error_code="INVALID_AMOUNT",
                message="Debit amount must be positive",
            )

        if wallet.wallet_balance < amount:
            raise APIException(
                status_code=409,
                error_code="INSUFFICIENT_BALANCE",
                message=(
                    f"Insufficient wallet balance. "
                    f"Available: {wallet.wallet_balance}"
                ),
            )

        self.wallet_repo.update_wallet_balance(
            wallet.id_wallet, amount, operation="subtract"
        )

        destination = destination_wallet or self.get_system_wallet()

        return self.transaction_repo.create_transaction({
            "money_transaction_wallet_source_id": wallet.id_wallet,
            "money_transaction_wallet_destination_id":
                destination.id_wallet,
            "money_transaction_amount": amount,
            "money_transaction_reference": reference,
            "money_transaction_status": "completed",
            "money_transaction_for_payment": for_payment_id,
            "money_transaction_creation": datetime.now(),
            "money_transaction_last_updated": datetime.now(),
        })

    def credit(
        self,
        wallet: Wallet,
        amount: Decimal,
        *,
        reference: str,
        for_payment_id: Optional[int] = None,
        source_wallet: Optional[Wallet] = None,
        status: str = "completed",
    ) -> MoneyTransaction:
        """Put `amount` into `wallet`.

        The wallet's balance increases, and a `MoneyTransaction`
        records where the money came from. Source is
        `source_wallet` when supplied, or the system wallet
        otherwise.

        `status` defaults to `"completed"` — the normal case for a
        successful credit. Refunds pass `status="refunded"` so the
        ledger distinguishes money in from a sale (revenue) from
        money in from a return (reversal).
        """
        if amount <= 0:
            raise APIException(
                status_code=400,
                error_code="INVALID_AMOUNT",
                message="Credit amount must be positive",
            )

        self.wallet_repo.update_wallet_balance(
            wallet.id_wallet, amount, operation="add"
        )

        source = source_wallet or self.get_system_wallet()

        return self.transaction_repo.create_transaction({
            "money_transaction_wallet_source_id": source.id_wallet,
            "money_transaction_wallet_destination_id": wallet.id_wallet,
            "money_transaction_amount": amount,
            "money_transaction_reference": reference,
            "money_transaction_status": status,
            "money_transaction_for_payment": for_payment_id,
            "money_transaction_creation": datetime.now(),
            "money_transaction_last_updated": datetime.now(),
        })

    # ==================== Ledger reads ====================

    def get_transactions_for_payment(
        self, payment_id: int,
    ) -> list[MoneyTransaction]:
        """Every transaction tied to a payment.

        Used by `PaymentService` when rendering a payment's history.
        """
        return self.transaction_repo.get_transactions_by_payment(
            payment_id
        )

    def get_transactions_for_wallet(
        self,
        wallet_id: int,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[MoneyTransaction]:
        """A wallet's ledger, newest first.

        Includes transactions where the wallet is the source (money
        out) and where it's the destination (money in). Callers
        distinguish the two by comparing the transaction's source
        and destination against `wallet_id`.
        """
        return self.transaction_repo.get_transactions_by_wallet(
            wallet_id, limit=limit, offset=offset,
        )