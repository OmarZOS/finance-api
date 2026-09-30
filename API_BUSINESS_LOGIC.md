# Finance API Business Logic

This document describes the behavior implemented by the current application code. It is based on `server.py`, `lib/payment/payment_router.py`, `lib/payment/payment_service.py`, the payment/invoice/wallet repositories, and the SQLAlchemy models.

## API Surface

The application is a FastAPI service mounted as follows:

- Payment routes: `/payments`
- OpenAPI document: `/finance/openapi.json`
- Swagger UI: `/finance/docs`
- ReDoc: `/finance/redoc`
- Metrics: `/metrics` (exposed by `prometheus_fastapi_instrumentator`)

The application permits all CORS origins, credentials, methods, and headers. There is no authentication or authorization dependency on the payment routes.

Every payment endpoint obtains a SQLAlchemy session through `get_db()`. The `session_scope()` context manager commits when the request completes successfully, rolls back on an exception, and closes the session.

## Route Map

| Method | Path | Purpose | Main service operation |
|---|---|---|---|
| GET | `/payments/health` | Check that the payment database can be queried | Direct `Invoice` query |
| POST | `/payments/payment` | Create a pending payment | `PaymentService.create_payment` |
| POST | `/payments/confirm/{payment_id}` | Confirm a pending payment and move money | `PaymentService.confirm_payment` |
| POST | `/payments/reject/{payment_id}` | Reject a pending payment | `PaymentService.reject_payment` |
| GET | `/payments/invoice/{invoice_id}` | List invoice payments and totals | `PaymentService.get_invoice_payments` |
| POST | `/payments/refund/{payment_id}` | Refund a completed payment | `PaymentService.process_refund` |
| GET | `/payments/stats/daily` | Calculate payment statistics for a date | `PaymentRepository.get_daily_payment_stats` |
| GET | `/payments/{payment_id}` | Retrieve one payment and its transactions | `PaymentService.get_payment_by_id` |

The static routes are declared before `/{payment_id}` so that `health`, `invoice/...`, and `stats/daily` are not interpreted as integer payment IDs.

## Shared Response and Error Behavior

Successful responses are converted to Pydantic response models in the router. Payment responses contain:

- Payment identity, invoice ID, amount, method, status, type, notes, and timestamps.
- A computed `user_id`; it is not stored on the `Payment` table.
- A list of money transactions where the service includes them.
- A `refunds` list. Refund records are response-only; there is no refund table or persisted refund reason.

Request validation is performed by Pydantic. The relevant constraints are:

- `amount` and refund `amount` must be greater than zero.
- Refund `reason` must contain at least one character.
- Payment IDs and invoice IDs must be integers.
- Daily stats dates must use `YYYY-MM-DD`.

The router converts `APIException` into FastAPI `HTTPException`; unexpected service failures are logged and returned as HTTP 500 errors. The application also defines a catch-all exception handler. The separate handler configuration in `core/exceptions/handler.py` is not called from `server.py`, so the response behavior there is not necessarily the behavior used by the running application.

## Payment Lifecycle

The intended lifecycle is:

```text
create -> pending -> confirm -> completed
                  \-> reject -> failed
completed -> refund -> refunded
```

Invoice status is recalculated during confirmation and refund:

- Confirmation sets `paid` when completed payments reach the invoice total.
- Otherwise confirmation sets `partially_paid`.
- Refund sets `unpaid` when the calculated paid total is zero, `partially_paid` when it is below the invoice total, and `paid` otherwise.

## Route Details

### `GET /payments/health`

The route opens a database session and executes `db.query(Invoice).first()`.

- Healthy response: `{"status": "healthy", "service": "payment", "database": "connected"}`.
- Query failure response: status `unhealthy`, database `disconnected`, plus the exception text.
- The handler returns the unhealthy payload rather than raising an HTTP 500, despite documenting a possible 500 response.

### `POST /payments/payment`

Request body:

```json
{
  "invoice_id": 123,
  "amount": 25.0,
  "payment_method": "card",
  "user_id": 7,
  "notes": "optional",
  "payment_type": "payment"
}
```

Processing:

1. Load the invoice.
2. Return 404 if it does not exist.
3. Return 409 if its status is already `paid`.
4. Calculate the balance as invoice total minus completed payments.
5. Return 400 if the requested amount exceeds that balance.
6. Insert a `Payment` row with status `pending` and a generated `PAY-XXXXXXXX` reference.
7. Return the pending payment. The supplied `user_id` is returned but is not persisted.

The invoice status and wallet balance are unchanged until confirmation.

### `POST /payments/confirm/{payment_id}`

Request body:

```json
{
  "transaction_details": {}
}
```

The transaction details are accepted but are not used in the current implementation.

Processing:

1. Load the payment; return 404 if absent.
2. Require status `pending`; otherwise return 409.
3. Load the associated invoice; return 404 if absent.
4. Derive the user from `invoice.cart.cart_client_user`, falling back to `invoice.placed_order.ordering_user_id`.
5. For `wallet` or `deposit` payments:
   - Require a derived user and that user's wallet.
   - Require sufficient wallet balance.
   - Subtract the payment amount from the user wallet.
   - Create a completed transaction from the user wallet to the system wallet.
6. For `cash`, `card`, `bank_transfer`, or `mobile_money` payments:
   - Resolve the cart's provider wallet.
   - Create a completed transaction from the system wallet to the provider wallet.
   - Fall back to the system wallet if no provider wallet is found.
7. Mark the payment `completed`.
8. Recalculate invoice payment totals and set the invoice to `paid` or `partially_paid`.

The service does not create a transaction for other model-supported methods such as `crypto` or `check`, but still marks those payments completed. The endpoint's transaction details therefore depend on the method.

### `POST /payments/reject/{payment_id}`

Request body:

```json
{
  "reason": "gateway declined"
}
```

The payment must exist and be `pending`. The service marks it `failed`, assigns a generated `REJ-XXXXXXXX` reference, and returns no transactions. The rejection reason is validated by the API but is not stored in the payment notes or another table. The invoice status is not changed.

### `GET /payments/invoice/{invoice_id}`

The invoice must exist. The response includes the invoice total, completed amount paid, remaining balance, current invoice status, and payments ordered newest first.

Only payments with status `completed` contribute to `total_paid` and `remaining_amount`. Pending, failed, and refunded payments are returned in the payment list but do not contribute to the invoice total calculation. The per-payment `transactions` arrays are empty in this route even when transactions exist.

### `POST /payments/refund/{payment_id}`

Request body:

```json
{
  "amount": 10.0,
  "reason": "customer request"
}
```

The payment must exist and have status `completed`. The refund amount defaults to the payment amount in the service, although the API request requires an amount. The amount cannot exceed the original payment amount.

Processing:

1. Mark the payment `refunded` and assign a generated `REF-XXXXXXXX` reference.
2. Resolve the user from the invoice.
3. For `wallet` or `deposit`, add the refund amount back to the user's wallet and create a `refunded` transaction from the system wallet to the user wallet.
4. Recalculate invoice status using the previous completed total minus the refund amount.
5. Return one response-only refund item containing amount, reason, and timestamp.

For non-wallet payment methods, the payment is still marked `refunded` and the invoice is recalculated, but no reverse money transaction is created. A partial refund also changes the entire payment status to `refunded`; the remaining refundable amount is not tracked separately.

### `GET /payments/stats/daily`

Optional query parameter: `date=YYYY-MM-DD`. Without it, the current local date is used.

The repository selects payments whose creation timestamp falls between the start and end of the date. It returns:

- `total_payments`: all payments created that day.
- `total_amount`: sum of completed payment amounts only.
- `average_amount`: completed amount divided by completed payment count.
- `by_status`: counts grouped by payment status.
- `by_method`: counts grouped by payment method.

The response model exposes the first five values above. The service/repository also computes completed, pending, failed, and refunded counts, but those extra fields are ignored by the response model.

### `GET /payments/{payment_id}`

The payment must exist. The response loads the associated invoice to derive the user, then loads up to 50 transactions for the payment, newest first.

Transaction type is inferred from the presence of a source wallet: a source wallet means `debit`; otherwise it is reported as `credit`. For a transaction with both source and destination wallets, the source wallet is the one shown in `wallet_id` and the transaction is reported as a debit.

## Persistence and Money Movement

The relevant database records are:

- `Invoice`: invoice total and lifecycle status.
- `Payment`: payment amount, method, status, reference, type, and notes.
- `Wallet`: user, provider, and system balances.
- `MoneyTransaction`: source wallet, destination wallet, amount, status, and payment reference.
- `Cart` and `PlacedOrder`: sources used to infer the payment user.

System wallets are looked up by `wallet_type == 'system'`. If none exists, confirmation or refund creates an active DZD system wallet with zero balance. Provider wallet resolution uses the cart's provider ID and falls back to the system wallet when a provider or provider wallet is unavailable.

Repositories flush changes immediately, while the request session commits at the end of a successful request. Service failures generally roll back the session; repository query failures often return empty results or `None` instead of raising.

## Implementation Risks and Gaps

These are current-code observations that should be treated as follow-up items if the API is intended for production:

1. The application allows unrestricted CORS and has no route-level authentication or authorization.
2. Payment creation accepts a `user_id` but does not verify it against the invoice or store it. Confirmation derives a different user from invoice relationships.
3. The payment service does not use the transaction decorators in `core/transaction.py`; atomicity relies on the request session and manual rollback paths.
4. Confirmation can debit a wallet before a later database operation fails. The request rollback normally protects the session, but concurrency and balance locking are not implemented.
5. Partial refunds are represented as a fully `refunded` payment, and repeated refunds are blocked only because the status is no longer `completed`.
6. Refunds for card, cash, bank transfer, and mobile money do not create reverse transactions.
7. Rejection reasons and gateway `transaction_details` are not persisted.
8. `crypto` and `check` are valid model enum values but have no confirmation transaction branch.
9. The global handler in `server.py` accesses `APIException` attributes named `status` and `code`, while the class defines `status_code` and `error_code`. Router-level conversion usually prevents this path for service exceptions, but the mismatch can break direct `APIException` handling.
10. The documented router response errors are richer than the actual `HTTPException` payloads produced by the route functions; normal FastAPI HTTP errors use a `detail` field.

## Source Trace

- Application setup and middleware: `server.py`
- Route definitions and request/response models: `lib/payment/payment_router.py`
- Business rules and state transitions: `lib/payment/payment_service.py`
- Payment queries and daily statistics: `lib/payment/payment_repo.py`
- Invoice totals and invoice status: `lib/invoice/invoice_repository.py`
- Wallet lookup and balance changes: `lib/wallet/wallet_repository.py`
- Money transaction persistence: `lib/wallet/money_transaction_repository.py`
- Database sessions and commit/rollback behavior: `core/database.py`
- Payment, invoice, wallet, and transaction schema: `core/models.py`