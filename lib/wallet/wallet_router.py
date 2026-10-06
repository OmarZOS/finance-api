# controllers/wallet_controller.py
"""
Wallet endpoints for the finance server.

Trusted-caller model: this router is called by other backend
services — the API server, admin tooling, webhook handlers — not by
end users. There is no per-user authorization here. Auth is
enforced at the network boundary (the finance server is not
internet-facing).

Two identifier styles, one set of operations:

  * By wallet id — the primitive. Callers that already have a
    wallet id use these. `/wallet/{id}`, `/wallet/credit`, etc.
  * By owner — convenience wrappers for callers that have a user
    or provider id but not a wallet id. `/wallet/user/{id}`,
    `/wallet/provider/{id}`.

Both styles hit the same `WalletService` primitives.
"""

from decimal import Decimal
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from core.exceptions.handler import APIException
from core.database import session_scope
from core.models import AppUser, ProductProvider, Wallet
from lib.wallet.wallet_service import WalletService

logger = logging.getLogger(__name__)


# ==================== ROUTER ====================

wallet_router = APIRouter()


# ==================== REQUEST MODELS ====================

class WalletCreditRequest(BaseModel):
    """Request to credit a wallet.

    The wallet is identified by id. Callers are trusted services
    inside the finance network; they already know which wallet they
    mean, usually because they resolved it once and reused the id.
    """
    wallet_id: int = Field(..., description="Wallet to credit.")
    amount: Decimal = Field(..., gt=0, description="Amount, positive.")
    intent: str = Field(
        ...,
        min_length=1,
        max_length=32,
        description=(
            "Why the money is being credited. Conventional values: "
            "'topup', 'refund', 'bonus', 'adjustment'."
        ),
    )
    reference: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Caller-generated reference for correlation.",
    )
    for_payment_id: Optional[int] = Field(
        None,
        description="Optional payment id this credit is tied to.",
    )
    status: Optional[str] = Field(
        "completed",
        description=(
            "Transaction status. Defaults to 'completed'. Refunds "
            "typically use 'refunded'."
        ),
    )


class WalletDebitRequest(BaseModel):
    """Request to debit a wallet.

    Same shape as credit. The service checks the balance and
    raises 409 when there isn't enough — the caller shouldn't check
    first, because checking then debiting is a race.
    """
    wallet_id: int = Field(..., description="Wallet to debit.")
    amount: Decimal = Field(..., gt=0)
    intent: str = Field(..., min_length=1, max_length=32)
    reference: str = Field(..., min_length=1, max_length=64)
    for_payment_id: Optional[int] = None


class WalletTransferRequest(BaseModel):
    """Request to move money between two wallets.

    The debit and the credit are one operation: two ledger rows are
    written inside the request's transaction. If either fails, both
    roll back. There is no window where money has left one wallet
    and hasn't arrived at the other.
    """
    source_wallet_id: int = Field(...)
    destination_wallet_id: int = Field(...)
    amount: Decimal = Field(..., gt=0)
    intent: str = Field(..., min_length=1, max_length=32)
    reference: str = Field(..., min_length=1, max_length=64)

    @field_validator("destination_wallet_id")
    @classmethod
    def _not_same_wallet(cls, v: int, info) -> int:
        src = info.data.get("source_wallet_id")
        if src is not None and v == src:
            raise ValueError(
                "source_wallet_id and destination_wallet_id must differ"
            )
        return v


# ==================== RESPONSE MODELS ====================

class WalletResponse(BaseModel):
    """Wallet state.

    `owner` is populated when the caller asked by owner, and left
    null when the caller asked by wallet id — the router doesn't
    resolve owners for the id-based path, because that would be
    extra work the caller didn't ask for.
    """
    id: int
    owner_type: Optional[str] = None
    owner_id: Optional[int] = None
    currency: str
    balance: Decimal
    status: str
    type: str


class TransactionResponse(BaseModel):
    """A single ledger entry."""
    id: int
    amount: Decimal
    direction: str  # "in" or "out" relative to the queried wallet
    status: str
    intent: Optional[str] = None
    reference: Optional[str] = None
    counterparty_wallet_id: Optional[int] = None
    for_payment_id: Optional[int] = None
    created_at: Optional[datetime] = None


class CreditResponse(BaseModel):
    wallet_id: int
    amount: Decimal
    balance_after: Decimal
    transaction: TransactionResponse


class DebitResponse(BaseModel):
    wallet_id: int
    amount: Decimal
    balance_after: Decimal
    transaction: TransactionResponse


class TransferResponse(BaseModel):
    source_wallet_id: int
    destination_wallet_id: int
    amount: Decimal
    source_balance_after: Decimal
    destination_balance_after: Decimal
    source_transaction: TransactionResponse
    destination_transaction: TransactionResponse


# ==================== ERROR MODELS ====================

class ErrorDetail(BaseModel):
    field: Optional[str] = None
    message: str
    code: Optional[str] = None


class ErrorResponse(BaseModel):
    detail: str
    status_code: int
    error_code: Optional[str] = None
    errors: Optional[List[ErrorDetail]] = None
    timestamp: str
    path: Optional[str] = None


# ==================== DEPENDENCIES ====================

def get_db() -> Session:
    """Session dependency, same shape as the payment controller."""
    with session_scope() as session:
        yield session


# ==================== ENDPOINTS ====================

# 1. HEALTH — must be first so it doesn't get caught by /{wallet_id}
@wallet_router.get(
    "/health",
    response_model=Dict[str, str],
    responses={
        200: {"description": "Health check passed"},
        500: {"description": "Health check failed"},
    },
)
async def wallet_health_check(db: Session = Depends(get_db)):
    """Health check for the wallet subsystem."""
    try:
        db.query(Wallet).first()
        return {
            "status": "healthy",
            "service": "wallet",
            "database": "connected",
        }
    except Exception as e:
        logger.error(f"Wallet health check failed: {e}")
        return {
            "status": "unhealthy",
            "service": "wallet",
            "database": "disconnected",
            "error": str(e),
        }


# 2. SYSTEM WALLET — before /{wallet_id} so "system" isn't parsed as int
@wallet_router.get(
    "/system",
    response_model=WalletResponse,
    responses={
        200: {"description": "System wallet retrieved"},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
async def get_system_wallet(db: Session = Depends(get_db)):
    """Get the system wallet.

    Created lazily if missing. Exposed for admin tooling that needs
    to audit the central account.
    """
    try:
        service = WalletService(db)
        wallet = service.get_system_wallet()
        return _wallet_response(wallet, owner_type="system")
    except Exception as e:
        logger.error(f"Failed to get system wallet: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get system wallet: {str(e)}",
        )


# 3. READ A USER'S WALLET (owner wrapper)
@wallet_router.get(
    "/user/{user_id}",
    response_model=WalletResponse,
    responses={
        200: {"description": "Wallet retrieved"},
        404: {"description": "Wallet not found", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
async def get_user_wallet(
    user_id: int,
    db: Session = Depends(get_db),
):
    """Resolve a user's wallet and return it.

    Convenience for callers that have a user id. Internally this
    walks `AppUser.app_user_wallet_id` and then fetches the wallet
    by id.
    """
    try:
        service = WalletService(db)
        wallet = _resolve_user_wallet(db, user_id)
        if wallet is None:
            raise APIException(
                status_code=404,
                error_code="WALLET_NOT_FOUND",
                message=f"No wallet for user {user_id}",
            )
        return _wallet_response(
            wallet, owner_type="user", owner_id=user_id,
        )
    except APIException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Failed to get user wallet: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user wallet: {str(e)}",
        )


# 4. READ A PROVIDER'S WALLET (owner wrapper)
@wallet_router.get(
    "/provider/{provider_id}",
    response_model=WalletResponse,
    responses={
        200: {"description": "Wallet retrieved"},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
async def get_provider_wallet(
    provider_id: int,
    db: Session = Depends(get_db),
):
    """Resolve a provider's wallet and return it.

    A provider without a wallet resolves to the system wallet —
    that's the service's behavior and it's returned as-is, with
    `owner_type` reflecting the resolved wallet's actual type.
    """
    try:
        service = WalletService(db)
        wallet = service.get_provider_wallet(provider_id)
        # The resolved wallet may be the system wallet; report what
        # actually answered, not what was asked for.
        return _wallet_response(
            wallet,
            owner_type=wallet.wallet_type,
            owner_id=(
                provider_id
                if wallet.wallet_type == "provider"
                else None
            ),
        )
    except APIException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Failed to get provider wallet: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get provider wallet: {str(e)}",
        )


# 5. READ A WALLET'S LEDGER (by wallet id)
@wallet_router.get(
    "/{wallet_id}/transactions",
    response_model=List[TransactionResponse],
    responses={
        200: {"description": "Transactions retrieved"},
        404: {"description": "Wallet not found", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
async def get_wallet_transactions(
    wallet_id: int,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Every transaction a wallet participated in.

    Newest first. Each entry carries a `direction` field relative to
    the queried wallet: `"in"` when the wallet was the destination,
    `"out"` when it was the source.
    """
    try:
        service = WalletService(db)
        # Confirm the wallet exists before listing; otherwise a
        # typo'd id returns an empty list, which reads as "no
        # transactions" rather than "no such wallet".
        wallet = service.wallet_repo.get_wallet_by_id(wallet_id)
        if wallet is None:
            raise APIException(
                status_code=404,
                error_code="WALLET_NOT_FOUND",
                message=f"Wallet {wallet_id} not found",
            )

        transactions = service.get_transactions_for_wallet(
            wallet_id, limit=limit, offset=offset,
        )
        return [
            _transaction_response(t, wallet_id=wallet_id)
            for t in transactions
        ]
    except APIException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Failed to get wallet transactions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get wallet transactions: {str(e)}",
        )

# 8. TRANSFER BETWEEN WALLETS
@wallet_router.post(
    "/transfer",
    response_model=TransferResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Transfer completed"},
        400: {"description": "Bad request", "model": ErrorResponse},
        404: {"description": "Wallet not found", "model": ErrorResponse},
        409: {"description": "Insufficient balance", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
async def transfer_between_wallets(
    payload: WalletTransferRequest,
    db: Session = Depends(get_db),
):
    """Transfer money between two wallets.

    Debits the source and credits the destination in one operation.
    Both ledger rows are written inside the request's transaction —
    if either fails, both roll back.

    Not exposed to end users; called by the API server for
    marketplace payouts, or any flow where two balances change
    together.
    """
    try:
        service = WalletService(db)
        source = service.wallet_repo.get_wallet_by_id(
            payload.source_wallet_id
        )
        destination = service.wallet_repo.get_wallet_by_id(
            payload.destination_wallet_id
        )

        if source is None:
            raise APIException(
                status_code=404,
                error_code="WALLET_NOT_FOUND",
                message=(
                    f"Source wallet {payload.source_wallet_id} "
                    f"not found"
                ),
            )
        if destination is None:
            raise APIException(
                status_code=404,
                error_code="WALLET_NOT_FOUND",
                message=(
                    f"Destination wallet "
                    f"{payload.destination_wallet_id} not found"
                ),
            )

        source_tx = service.debit(
            source,
            payload.amount,
            reference=f"{payload.reference}:out",
            destination_wallet=destination,
        )

        destination_tx = service.credit(
            destination,
            payload.amount,
            reference=f"{payload.reference}:in",
            source_wallet=source,
        )

        db.refresh(source)
        db.refresh(destination)

        logger.info(
            f"Wallet transfer: from={payload.source_wallet_id} "
            f"to={payload.destination_wallet_id} "
            f"amount={payload.amount} intent={payload.intent!r} "
            f"reference={payload.reference!r}"
        )

        return TransferResponse(
            source_wallet_id=source.id_wallet,
            destination_wallet_id=destination.id_wallet,
            amount=payload.amount,
            source_balance_after=Decimal(source.wallet_balance or 0),
            destination_balance_after=Decimal(
                destination.wallet_balance or 0
            ),
            source_transaction=_transaction_response(
                source_tx, wallet_id=source.id_wallet,
            ),
            destination_transaction=_transaction_response(
                destination_tx, wallet_id=destination.id_wallet,
            ),
        )
    except APIException as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        db.rollback()
        logger.error(f"Wallet transfer failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Wallet transfer failed: {str(e)}",
        )


# 9. READ A WALLET BY ID — last so /{wallet_id} doesn't shadow the
#    fixed paths above.
@wallet_router.get(
    "/{wallet_id}",
    response_model=WalletResponse,
    responses={
        200: {"description": "Wallet retrieved"},
        404: {"description": "Wallet not found", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
async def get_wallet(
    wallet_id: int,
    db: Session = Depends(get_db),
):
    """Get a wallet by id.

    The primitive read. Callers that already have a wallet id use
    this; callers that have a user or provider id use the owner
    endpoints.
    """
    try:
        service = WalletService(db)
        wallet = service.wallet_repo.get_wallet_by_id(wallet_id)
        if wallet is None:
            raise APIException(
                status_code=404,
                error_code="WALLET_NOT_FOUND",
                message=f"Wallet {wallet_id} not found",
            )
        return _wallet_response(wallet)
    except APIException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Failed to get wallet: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get wallet: {str(e)}",
        )


# ==================== INTERNAL FORMATTERS ====================

def _wallet_response(
    wallet,
    *,
    owner_type: Optional[str] = None,
    owner_id: Optional[int] = None,
) -> WalletResponse:
    """Shape a Wallet row into the response model.

    `owner_type` and `owner_id` are supplied by the caller when it
    knows them (owner-based endpoints). The id-based endpoints
    leave them null — resolving the owner would require the
    dispatch that the id-based path exists to avoid.
    """
    return WalletResponse(
        id=wallet.id_wallet,
        owner_type=owner_type,
        owner_id=owner_id,
        currency=wallet.wallet_currency or "DZD",
        balance=Decimal(wallet.wallet_balance or 0),
        status=wallet.wallet_status or "active",
        type=wallet.wallet_type or "user",
    )


def _transaction_response(transaction, *, wallet_id: int) -> TransactionResponse:
    """Shape a MoneyTransaction row into the response model.

    Adds a `direction` field relative to the queried wallet:
    `"in"` when the wallet was the destination, `"out"` when it
    was the source.
    """
    is_incoming = (
        transaction.money_transaction_wallet_destination_id
        == wallet_id
    )

    return TransactionResponse(
        id=transaction.id_money_transaction,
        amount=Decimal(transaction.money_transaction_amount or 0),
        direction="in" if is_incoming else "out",
        status=transaction.money_transaction_status or "completed",
        intent=getattr(
            transaction, "money_transaction_intent", None,
        ),
        reference=transaction.money_transaction_reference,
        counterparty_wallet_id=(
            transaction.money_transaction_wallet_source_id
            if is_incoming
            else transaction.money_transaction_wallet_destination_id
        ),
        for_payment_id=transaction.money_transaction_for_payment,
        created_at=transaction.money_transaction_creation,
    )


def _resolve_user_wallet(db: Session, user_id: int):
    """Resolve a user's wallet via the FK on AppUser.

    Returns the Wallet row or None.
    """
    user = (
        db.query(AppUser)
        .filter(AppUser.id_app_user == user_id)
        .first()
    )
    if user is None or user.app_user_wallet_id is None:
        return None
    return (
        db.query(Wallet)
        .filter(Wallet.id_wallet == user.app_user_wallet_id)
        .first()
    )