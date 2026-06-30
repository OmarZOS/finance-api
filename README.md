# **Finance API** 

# Payment Service - Complete Workflow Guide

## Overview
The Payment Service is a comprehensive payment processing system that handles invoice payments, wallet transactions, and refunds. It integrates with the existing invoice and wallet systems to provide a complete payment lifecycle.

---

## 1. System Architecture

### Components
```
┌─────────────────────────────────────────────────────────────┐
│                     Payment Service                         │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │  Payment    │  │   Wallet    │  │   Money Transaction │ │
│  │  Repository │  │  Repository │  │    Repository       │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Invoice Repository                      │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Database Layer                         │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────┐  ┌─────────┐  ┌──────────┐  ┌──────────────┐ │
│  │ Invoice │  │ Payment │  │  Wallet  │  │ MoneyTransaction│ │
│  └─────────┘  └─────────┘  └──────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Database Models
| Model | Purpose |
|-------|---------|
| `Invoice` | Stores invoice details and status |
| `Payment` | Tracks payment records and status |
| `Wallet` | User/provider wallet balances |
| `MoneyTransaction` | Records all money movements |

---

## 2. Payment Lifecycle

### 2.1 Payment States
```
                    ┌──────────┐
                    │ PENDING  │
                    └────┬─────┘
                         │
              ┌──────────┴──────────┐
              │                     │
              ▼                     ▼
         ┌─────────┐          ┌─────────┐
         │COMPLETED│          │ FAILED  │
         └────┬────┘          └─────────┘
              │
              ▼
         ┌─────────┐
         │REFUNDED │
         └─────────┘
```

### 2.2 State Transitions
| From | To | Trigger |
|------|-----|---------|
| PENDING → COMPLETED | Payment confirmed |
| PENDING → FAILED | Payment rejected |
| COMPLETED → REFUNDED | Refund processed |

---

## 3. Detailed Workflows

### 3.1 Create Payment Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                   1. CREATE PAYMENT                         │
└─────────────────────────────────────────────────────────────┘

1. Client Request
   POST /payments/payment
   {
     "invoice_id": 4,
     "amount": 567.80,
     "payment_method": "bank_transfer",
     "user_id": 5,
     "notes": "Pharmacy order payment",
     "payment_type": "payment"
   }

2. Validate Invoice
   ✓ Check if invoice exists
   ✓ Check if invoice is already paid
   ✓ Check if payment amount exceeds balance due

3. Create Payment Record
   {
     "payment_invoice_id": 4,
     "payment_amount": 567.80,
     "payment_method": "bank_transfer",
     "payment_status": "pending",
     "payment_reference": "PAY-ABC12345",
     "payment_notes": "Pharmacy order payment",
     "payment_type": "payment"
   }

4. Return Response
   {
     "id": 4,
     "invoice_id": 4,
     "user_id": 5,
     "amount": 567.80,
     "status": "pending",
     "payment_method": "bank_transfer",
     "reference": "PAY-ABC12345"
   }
```

### 3.2 Confirm Payment Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                  2. CONFIRM PAYMENT                         │
└─────────────────────────────────────────────────────────────┘

1. Client Request
   POST /payments/confirm/{payment_id}
   {
     "transaction_details": {
       "reference": "REF-4-20240630022429",
       "bank_reference": "BANK-4",
       "notes": "Payment 4 confirmed successfully"
     }
   }

2. Validate Payment
   ✓ Check if payment exists
   ✓ Check if payment is in 'pending' state
   ✓ Get associated invoice

3. Determine Payment Method & Process
   ┌──────────────────────────────────────┐
   │      PAYMENT METHOD BRANCH           │
   ├──────────────────────────────────────┤
   │  Wallet/Deposit:                     │
   │  • Check user wallet balance         │
   │  • Deduct from user wallet           │
   │  • Create transaction: User→System   │
   │                                      │
   │  Card/Cash/Bank Transfer:            │
   │  • Get provider wallet               │
   │  • Create transaction: System→Provider│
   └──────────────────────────────────────┘

4. Update Payment Status
   status: 'pending' → 'completed'

5. Update Invoice Status
   Calculate total paid amount
   If total_paid >= invoice_total: 'paid'
   Else: 'partially_paid'

6. Create Transaction Record
   {
     "source_wallet": "user_wallet",
     "destination_wallet": "system_wallet",
     "amount": 567.80,
     "reference": "PAY-ABC12345",
     "status": "completed"
   }

7. Return Response
   {
     "id": 4,
     "status": "completed",
     "invoice_id": 4,
     "amount": 567.80,
     "transactions": [...]
   }
```

### 3.3 Reject Payment Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                  3. REJECT PAYMENT                          │
└─────────────────────────────────────────────────────────────┘

1. Client Request
   POST /payments/reject/{payment_id}
   {
     "reason": "Insufficient funds"
   }

2. Validate Payment
   ✓ Check if payment exists
   ✓ Check if payment is in 'pending' state

3. Update Payment Status
   status: 'pending' → 'failed'

4. Return Response
   {
     "id": 7,
     "invoice_id": 8,
     "amount": 230.50,
     "status": "failed",
     "reason": "Insufficient funds"
   }

Note: No transactions are created for rejected payments.
```

### 3.4 Refund Payment Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                  4. REFUND PAYMENT                          │
└─────────────────────────────────────────────────────────────┘

1. Client Request
   POST /payments/refund/{payment_id}
   {
     "amount": 567.80,
     "reason": "Refund requested by customer"
   }

2. Validate Payment
   ✓ Check if payment exists
   ✓ Check if payment is in 'completed' state
   ✓ Check if refund amount is valid

3. Update Payment Status
   status: 'completed' → 'refunded'

4. Process Refund
   ┌──────────────────────────────────────┐
   │      REFUND PROCESSING               │
   ├──────────────────────────────────────┤
   │  Wallet/Deposit:                     │
   │  • Get user wallet                   │
   │  • Add funds back to wallet          │
   │  • Create refund transaction         │
   │                                      │
   │  Other Methods:                      │
   │  • Mark payment as refunded          │
   │  • No wallet transaction             │
   └──────────────────────────────────────┘

5. Update Invoice Status
   Calculate remaining total paid
   If total_paid <= 0: 'unpaid'
   Else if total_paid < invoice_total: 'partially_paid'
   Else: 'paid'

6. Create Refund Transaction
   {
     "source_wallet": "system_wallet",
     "destination_wallet": "user_wallet",
     "amount": 567.80,
     "reference": "REF-XXXX1234",
     "status": "refunded"
   }

7. Return Response
   {
     "id": 4,
     "status": "refunded",
     "amount": 567.80,
     "transactions": [...],
     "refunds": [{
       "amount": 567.80,
       "reason": "Refund requested by customer"
     }]
   }
```

---

## 4. API Endpoints Summary

### 4.1 Payment Operations
| Method | Endpoint | Description | Request Body | Response |
|--------|----------|-------------|--------------|----------|
| POST | `/payment` | Create new payment | `PaymentCreate` | `PaymentResponse` |
| POST | `/confirm/{id}` | Confirm pending payment | `PaymentConfirm` | `PaymentResponse` |
| POST | `/reject/{id}` | Reject pending payment | `{reason}` | `PaymentResponse` |
| POST | `/refund/{id}` | Refund completed payment | `PaymentRefund` | `PaymentResponse` |

### 4.2 Query Operations
| Method | Endpoint | Description | Response |
|--------|----------|-------------|----------|
| GET | `/{id}` | Get payment details | `PaymentResponse` |
| GET | `/invoice/{id}` | Get invoice payments | `InvoicePaymentSummary` |
| GET | `/stats/daily` | Get daily statistics | `DailyPaymentStats` |
| GET | `/health` | Health check | `{status}` |

---

## 5. Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         COMPLETE FLOW                              │
└─────────────────────────────────────────────────────────────────────┘

Client                    Payment Service                    Database
  │                            │                               │
  │  1. Create Payment        │                               │
  │──────────────────────────►│                               │
  │                           │  1.1 Get Invoice              │
  │                           │──────────────────────────────►│
  │                           │  1.2 Validate Status         │
  │                           │◄──────────────────────────────│
  │                           │  1.3 Create Payment          │
  │                           │──────────────────────────────►│
  │  2. Confirm Payment       │                               │
  │──────────────────────────►│                               │
  │                           │  2.1 Get Payment              │
  │                           │──────────────────────────────►│
  │                           │  2.2 Check Status            │
  │                           │◄──────────────────────────────│
  │                           │  2.3 Get Wallet              │
  │                           │──────────────────────────────►│
  │                           │  2.4 Update Wallet Balance   │
  │                           │──────────────────────────────►│
  │                           │  2.5 Create Transaction      │
  │                           │──────────────────────────────►│
  │                           │  2.6 Update Payment          │
  │                           │──────────────────────────────►│
  │                           │  2.7 Update Invoice          │
  │                           │──────────────────────────────►│
  │  3. Return Response      │                               │
  │◄──────────────────────────│                               │
  │                           │                               │
```

---

## 6. Error Handling

### 6.1 HTTP Status Codes
| Status Code | Description | Scenario |
|-------------|-------------|----------|
| 200 | Success | Operation completed successfully |
| 400 | Bad Request | Invalid request format or data |
| 404 | Not Found | Resource not found (invoice/payment) |
| 409 | Conflict | Business rule violation (already paid) |
| 422 | Validation Error | Invalid input data |
| 500 | Server Error | Internal server error |

### 6.2 Error Response Format
```json
{
    "detail": "Invoice 99999 not found",
    "status_code": 404,
    "error_code": "INVOICE_NOT_FOUND",
    "timestamp": "2024-06-30T02:24:30.426Z"
}
```

### 6.3 Common Errors
| Error Code | Description | HTTP Status |
|------------|-------------|-------------|
| `INVOICE_NOT_FOUND` | Invoice doesn't exist | 404 |
| `INVOICE_ALREADY_PAID` | Invoice already fully paid | 409 |
| `PAYMENT_NOT_FOUND` | Payment doesn't exist | 404 |
| `PAYMENT_NOT_PENDING` | Payment not in pending state | 409 |
| `PAYMENT_NOT_COMPLETED` | Payment not completed for refund | 409 |
| `PAYMENT_EXCEEDS_BALANCE` | Amount exceeds balance due | 400 |
| `INSUFFICIENT_BALANCE` | Insufficient wallet balance | 409 |
| `WALLET_NOT_FOUND` | User wallet not found | 404 |
| `USER_NOT_FOUND` | User not found | 400 |
| `INVALID_REFUND_AMOUNT` | Refund amount exceeds payment | 400 |

---

## 7. Security Considerations

### 7.1 Authentication
- All endpoints should be protected with authentication
- User ID is passed in the request and validated

### 7.2 Authorization
- Users can only access their own payments
- Invoice ownership is verified
- Provider access is restricted

### 7.3 Idempotency
- Payment creation should be idempotent
- Use unique references to prevent duplicate payments

### 7.4 Audit Trail
- All transactions are recorded
- Payment status changes are tracked
- Refund reasons are logged

---

## 8. Performance Characteristics

### 8.1 Response Times
| Operation | Average Time |
|-----------|--------------|
| Create Payment | ~50-100ms |
| Confirm Payment | ~100-200ms |
| Get Payment | ~20-50ms |
| Get Invoice Payments | ~50-100ms |
| Daily Stats | ~100-200ms |

### 8.2 Database Queries
- All operations use indexed fields
- Proper joins with eager loading
- No N+1 query problems

### 8.3 Concurrency
- Atomic updates for wallet balances
- Transaction isolation for consistency
- No race conditions in payment processing

---

## 9. Testing Workflow

### 9.1 Test Scenarios
| Test | Description | Expected Result |
|------|-------------|-----------------|
| Health Check | Verify service health | 200 OK |
| Create Payment | Create new payment | 200 OK |
| Create Payment (Paid Invoice) | Try paying paid invoice | 409 Conflict |
| Create Payment (Invalid Invoice) | Try non-existent invoice | 404 Not Found |
| Confirm Payment | Confirm pending payment | 200 OK |
| Reject Payment | Reject pending payment | 200 OK |
| Refund Payment | Refund completed payment | 200 OK |
| Get Payment Details | Get single payment | 200 OK |
| Get Invoice Payments | Get all invoice payments | 200 OK |
| Daily Statistics | Get daily stats | 200 OK |
| Error Scenarios | Test various errors | Appropriate 4xx |

---

## 10. Deployment Workflow

### 10.1 Development
1. Write code and tests
2. Run tests locally
3. Review code changes
4. Merge to development branch

### 10.2 Staging
1. Deploy to staging environment
2. Run integration tests
3. Validate with sample data
4. Performance testing

### 10.3 Production
1. Deploy to production
2. Monitor logs and metrics
3. Validate with real data
4. Monitor for errors

---

## 11. Monitoring & Alerts

### 11.1 Key Metrics
| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| Payment Success Rate | % of successful payments | < 95% |
| Response Time | API response time | > 1s |
| Error Rate | % of 5xx errors | > 1% |
| Payment Volume | Number of payments | Significant drop |

### 11.2 Logging
- All payment creation/update logs
- Error logs with stack traces
- Performance logs for slow queries
- Audit logs for compliance

---

## 12. Future Enhancements

### 12.1 Planned Features
- Payment gateway integration
- Webhook notifications
- Payment reminders
- Recurring payments
- Multiple currency support
- Payment splitting

### 12.2 Optimizations
- Caching for frequent queries
- Asynchronous processing
- Batch operations
- Pagination for large datasets

---

## 13. Quick Reference

### 13.1 Common cURL Commands
```bash
# Create Payment
curl -X POST http://localhost:9098/payments/payment \
  -H "Content-Type: application/json" \
  -d '{"invoice_id": 4, "amount": 567.80, "payment_method": "bank_transfer", "user_id": 5}'

# Confirm Payment
curl -X POST http://localhost:9098/payments/confirm/4 \
  -H "Content-Type: application/json" \
  -d '{"transaction_details": {"reference": "REF-123"}}'

# Get Payment Details
curl -X GET http://localhost:9098/payments/4

# Get Invoice Payments
curl -X GET http://localhost:9098/payments/invoice/4

# Daily Stats
curl -X GET http://localhost:9098/payments/stats/daily?date=2024-06-30

# Health Check
curl -X GET http://localhost:9098/payments/health
```

### 13.2 Environment Variables
```bash
# Database
DATABASE_URL=mysql://user:pass@localhost:3306/db

# Service
API_PREFIX=/payments
PORT=9098
DEBUG=False

# Security
SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
```

---

This workflow provides a complete understanding of the Payment Service from end to end, covering all operations, data flows, error handling, and deployment considerations.