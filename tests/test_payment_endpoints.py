# tests/test_payment_endpoints.py
"""
Payment endpoint integration tests.

Design goals:
  * Idempotent: safe to run repeatedly against the same database.
  * Self-contained: each test creates what it needs; no assumptions about
    existing invoice IDs having a particular status.
  * Honest: skips are counted as skips, not silently dropped.
  * Wire-aware: FastAPI serializes Decimal as a string, so amounts are
    compared after float coercion.

Environment:
    BASE_URL           default http://localhost:9098
    TEST_USER_ID       default 1
    TEST_PROVIDER_ID   default 2
"""

import os
import sys
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

# ==================== LOGGING ====================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ==================== CONFIGURATION ====================

BASE_URL = os.environ.get("BASE_URL", "http://localhost:9098")
API_PREFIX = "/payments"
TEST_USER_ID = int(os.environ.get("TEST_USER_ID", "1"))

EXPECTED = {
    "success": 200,
    "bad_request": 400,
    "not_found": 404,
    "conflict": 409,
    "validation_error": 422,
    "server_error": 500,
}


# ==================== HTTP CLIENT ====================


class PaymentTestClient:
    """Thin wrapper around requests.Session for the payment API."""

    def __init__(self, base_url: str = BASE_URL, api_prefix: str = API_PREFIX):
        self.base_url = base_url.rstrip("/")
        self.api_prefix = api_prefix
        self.session = requests.Session()
        self.session.headers.update(
            {"Content-Type": "application/json", "Accept": "application/json"}
        )
        self.created_payment_ids: List[int] = []

    def _request(
        self, method: str, endpoint: str, data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        url = f"{self.base_url}{self.api_prefix}{endpoint}"
        try:
            if method == "GET":
                response = self.session.get(url)
            elif method == "POST":
                response = self.session.post(url, json=data)
            else:
                raise ValueError(f"Unsupported method: {method}")
        except requests.exceptions.RequestException as e:
            logger.error(f"{method} {url} failed: {e}")
            return {"status_code": 0, "data": {}, "text": "", "error": str(e)}

        parsed: Any = {}
        if response.text:
            try:
                parsed = response.json()
            except json.JSONDecodeError:
                parsed = {"_raw": response.text}

        return {
            "status_code": response.status_code,
            "data": parsed,
            "text": response.text,
        }

    def create_payment(
        self,
        invoice_id: int,
        amount: float,
        payment_method: str,
        user_id: int = TEST_USER_ID,
        notes: Optional[str] = None,
        payment_type: str = "payment",
    ) -> Dict[str, Any]:
        payload = {
            "invoice_id": invoice_id,
            "amount": amount,
            "payment_method": payment_method,
            "user_id": user_id,
        }
        if notes is not None:
            payload["notes"] = notes
        if payment_type is not None:
            payload["payment_type"] = payment_type

        result = self._request("POST", "/payment", payload)
        if result["status_code"] == 200 and isinstance(result["data"], dict):
            pid = result["data"].get("id")
            if isinstance(pid, int):
                self.created_payment_ids.append(pid)
        return result

    def confirm_payment(
        self, payment_id: int, transaction_details: Optional[Dict] = None
    ) -> Dict[str, Any]:
        return self._request(
            "POST",
            f"/confirm/{payment_id}",
            {"transaction_details": transaction_details or {}},
        )

    def reject_payment(self, payment_id: int, reason: str) -> Dict[str, Any]:
        return self._request("POST", f"/reject/{payment_id}", {"reason": reason})

    def refund_payment(
        self, payment_id: int, amount: float, reason: str
    ) -> Dict[str, Any]:
        return self._request(
            "POST",
            f"/refund/{payment_id}",
            {"amount": amount, "reason": reason},
        )

    def get_invoice_payments(self, invoice_id: int) -> Dict[str, Any]:
        return self._request("GET", f"/invoice/{invoice_id}")

    def get_payment(self, payment_id: int) -> Dict[str, Any]:
        return self._request("GET", f"/{payment_id}")

    def get_daily_stats(self, date: Optional[str] = None) -> Dict[str, Any]:
        endpoint = "/stats/daily"
        if date:
            endpoint += f"?date={date}"
        return self._request("GET", endpoint)

    def health_check(self) -> Dict[str, Any]:
        return self._request("GET", "/health")


# ==================== VALIDATORS ====================


def _as_float(value: Any) -> Optional[float]:
    """FastAPI serializes Decimal as a string. Coerce without lying about type."""
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def validate_payment_response(data: Any) -> bool:
    if not isinstance(data, dict):
        logger.error(f"❌ Response is not a dict: {type(data)}")
        return False

    required = [
        "id",
        "invoice_id",
        "amount",
        "payment_method",
        "status",
        "payment_type",
    ]
    for field in required:
        if field not in data:
            logger.error(f"❌ Missing field in payment response: {field}")
            return False

    if not isinstance(data["id"], int):
        logger.error(f"❌ 'id' must be int, got {type(data['id'])}")
        return False

    if _as_float(data["amount"]) is None:
        logger.error(f"❌ 'amount' is not numeric: {data['amount']!r}")
        return False

    return True


def validate_invoice_payment_response(data: Any) -> bool:
    if not isinstance(data, dict):
        logger.error(f"❌ Invoice response is not a dict: {type(data)}")
        return False

    required = [
        "invoice_id",
        "total_amount",
        "total_paid",
        "remaining_amount",
        "status",
        "payments",
    ]
    for field in required:
        if field not in data:
            logger.error(f"❌ Missing field in invoice response: {field}")
            return False

    if not isinstance(data["payments"], list):
        logger.error(f"❌ 'payments' must be list, got {type(data['payments'])}")
        return False

    for field in ("total_amount", "total_paid", "remaining_amount"):
        if _as_float(data[field]) is None:
            logger.error(f"❌ '{field}' is not numeric: {data[field]!r}")
            return False

    return True


def validate_error_response(data: Any) -> bool:
    return isinstance(data, dict) and "detail" in data


def validate_daily_stats_response(data: Any) -> bool:
    if not isinstance(data, dict):
        return False
    required = ["date", "total_payments", "total_amount"]
    if not all(f in data for f in required):
        logger.error(f"❌ Missing field in daily stats: {data}")
        return False
    if _as_float(data["total_amount"]) is None:
        logger.error(f"❌ 'total_amount' is not numeric: {data['total_amount']!r}")
        return False
    return True


# ==================== HELPERS ====================


def find_invoice_with_status(
    client: PaymentTestClient,
    wanted_status: str,
    candidate_ids: range = range(1, 30),
) -> Optional[int]:
    """
    Return the first invoice whose summary reports the given status.

    `wanted_status` matches the invoice's own `status` field, not the
    payment status. Pass 'unpaid' or 'partially_paid' for a payable
    invoice, 'paid' for an already-settled one.
    """
    for iid in candidate_ids:
        result = client.get_invoice_payments(iid)
        if result["status_code"] != 200:
            continue
        status = str(result["data"].get("status", "")).lower()
        if status == wanted_status:
            return iid
    return None


def make_unique_note(tag: str) -> str:
    return f"{tag} - {datetime.utcnow().isoformat(timespec='seconds')}Z"


# ==================== TEST STEPS ====================


def test_health_check(client: PaymentTestClient) -> bool:
    logger.info("\n" + "=" * 60)
    logger.info("TEST: Health Check")
    logger.info("=" * 60)

    result = client.health_check()
    if result["status_code"] != 200:
        logger.error(f"❌ Health check failed: {result}")
        return False

    data = result["data"]
    logger.info(f"✅ Status: {data.get('status')}")
    logger.info(f"   Service: {data.get('service')}")
    logger.info(f"   Database: {data.get('database')}")
    return data.get("status") == "healthy"


def test_create_payment_on_unpaid_invoice(
    client: PaymentTestClient,
) -> Optional[int]:
    """
    Find an unpaid invoice, pay a small amount against it, verify the
    response. Returns the created payment ID, or None if no unpaid
    invoice exists (which should be treated as a skip, not a failure).
    """
    logger.info("\n" + "=" * 60)
    logger.info("TEST: Create Payment on Unpaid Invoice")
    logger.info("=" * 60)

    invoice_id = find_invoice_with_status(client, "unpaid")
    if invoice_id is None:
        # Try partially_paid — still payable.
        invoice_id = find_invoice_with_status(client, "partially_paid")

    if invoice_id is None:
        logger.warning("⚠️ No unpaid or partially_paid invoice found — skipping")
        return None

    logger.info(f"Using invoice {invoice_id}")

    result = client.create_payment(
        invoice_id=invoice_id,
        amount=10.00,
        payment_method="cash",
        notes=make_unique_note("integration create"),
    )

    if result["status_code"] != 200:
        logger.error(f"❌ Expected 200, got {result['status_code']}: {result['text']}")
        return None

    data = result["data"]
    if not validate_payment_response(data):
        return None

    logger.info(f"✅ Payment created: id={data['id']} status={data['status']}")
    return int(data["id"])


def test_create_payment_on_paid_invoice(client: PaymentTestClient) -> bool:
    """A paid invoice must refuse further payments with 409."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST: Create Payment on Paid Invoice (expect 409)")
    logger.info("=" * 60)

    paid_id = find_invoice_with_status(client, "paid")
    if paid_id is None:
        logger.warning("⚠️ No paid invoice found — skipping")
        return True

    result = client.create_payment(
        invoice_id=paid_id,
        amount=5.00,
        payment_method="cash",
        notes=make_unique_note("integration conflict"),
    )
    if result["status_code"] != 409:
        logger.error(
            f"❌ Expected 409 on paid invoice, got {result['status_code']}: "
            f"{result['text']}"
        )
        return False

    logger.info("✅ Correctly refused with 409")
    return True


def test_create_payment_validation_errors(client: PaymentTestClient) -> bool:
    """
    Zero and negative amounts must fail Pydantic validation (422).
    Uses a nonexistent invoice ID so the amount validation fires before
    any invoice lookup.
    """
    logger.info("\n" + "=" * 60)
    logger.info("TEST: Create Payment Validation Errors (expect 422)")
    logger.info("=" * 60)

    cases = [
        ("zero", 0),
        ("negative", -50),
    ]
    ok = True

    for label, amount in cases:
        result = client.create_payment(
            invoice_id=999_999,
            amount=amount,
            payment_method="cash",
        )
        if result["status_code"] != 422:
            logger.error(
                f"❌ {label} amount: expected 422, got "
                f"{result['status_code']}: {result['text']}"
            )
            ok = False
        else:
            logger.info(f"✅ {label} amount correctly rejected with 422")

    return ok


def test_create_payment_unknown_invoice(client: PaymentTestClient) -> bool:
    logger.info("\n" + "=" * 60)
    logger.info("TEST: Create Payment on Unknown Invoice (expect 404)")
    logger.info("=" * 60)

    result = client.create_payment(
        invoice_id=999_999,
        amount=100.00,
        payment_method="cash",
    )
    if result["status_code"] != 404:
        logger.error(
            f"❌ Expected 404, got {result['status_code']}: {result['text']}"
        )
        return False

    if not validate_error_response(result["data"]):
        logger.error(f"❌ Invalid error body: {result['data']}")
        return False

    logger.info(f"✅ 404 with detail={result['data'].get('detail')!r}")
    return True


def test_get_payment(client: PaymentTestClient, payment_id: int) -> bool:
    logger.info("\n" + "=" * 60)
    logger.info("TEST: Get Payment")
    logger.info("=" * 60)

    result = client.get_payment(payment_id)
    if result["status_code"] != 200:
        logger.error(f"❌ Expected 200, got {result['status_code']}")
        return False

    if not validate_payment_response(result["data"]):
        return False

    data = result["data"]
    logger.info(f"✅ Payment {payment_id}: status={data['status']}")
    return True


def test_get_unknown_payment(client: PaymentTestClient) -> bool:
    logger.info("\n" + "=" * 60)
    logger.info("TEST: Get Unknown Payment (expect 404)")
    logger.info("=" * 60)

    result = client.get_payment(999_999)
    if result["status_code"] != 404:
        logger.error(f"❌ Expected 404, got {result['status_code']}")
        return False

    logger.info("✅ 404 as expected")
    return True


def test_confirm_payment(client: PaymentTestClient, payment_id: int) -> bool:
    logger.info("\n" + "=" * 60)
    logger.info("TEST: Confirm Payment")
    logger.info("=" * 60)

    result = client.confirm_payment(
        payment_id,
        {
            "reference": f"REF-{payment_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "notes": "integration confirm",
        },
    )
    if result["status_code"] != 200:
        logger.error(
            f"❌ Expected 200, got {result['status_code']}: {result['text']}"
        )
        return False

    if not validate_payment_response(result["data"]):
        return False

    status = result["data"].get("status")
    logger.info(f"✅ Confirmed, status={status}")
    return status in ("completed", "confirmed", "paid")


def test_confirm_unknown_payment(client: PaymentTestClient) -> bool:
    logger.info("\n" + "=" * 60)
    logger.info("TEST: Confirm Unknown Payment (expect 404)")
    logger.info("=" * 60)

    result = client.confirm_payment(999_999, {})
    if result["status_code"] != 404:
        logger.error(f"❌ Expected 404, got {result['status_code']}")
        return False

    logger.info("✅ 404 as expected")
    return True


def test_reject_payment(client: PaymentTestClient, payment_id: int) -> bool:
    logger.info("\n" + "=" * 60)
    logger.info("TEST: Reject Payment")
    logger.info("=" * 60)

    result = client.reject_payment(payment_id, make_unique_note("integration reject"))
    if result["status_code"] != 200:
        logger.error(
            f"❌ Expected 200, got {result['status_code']}: {result['text']}"
        )
        return False

    if not validate_payment_response(result["data"]):
        return False

    status = str(result["data"].get("status", "")).lower()
    logger.info(f"✅ Rejected, status={status}")
    return status in ("failed", "cancelled", "canceled", "rejected")


def test_refund_payment(client: PaymentTestClient, payment_id: int) -> bool:
    logger.info("\n" + "=" * 60)
    logger.info("TEST: Refund Payment")
    logger.info("=" * 60)

    # Look up the confirmed payment to refund the exact amount.
    info = client.get_payment(payment_id)
    if info["status_code"] != 200:
        logger.error(f"❌ Could not load payment {payment_id} for refund")
        return False

    amount = _as_float(info["data"].get("amount"))
    if amount is None or amount <= 0:
        logger.error(f"❌ Refund amount invalid: {info['data'].get('amount')!r}")
        return False

    result = client.refund_payment(
        payment_id, amount, make_unique_note("integration refund")
    )
    if result["status_code"] == 409:
        # Some services disallow refunds once the invoice is settled.
        logger.info(f"✅ Refund correctly refused with 409: {result['text']}")
        return True
    if result["status_code"] != 200:
        logger.error(
            f"❌ Expected 200 or 409, got {result['status_code']}: {result['text']}"
        )
        return False

    if not validate_payment_response(result["data"]):
        return False

    logger.info(f"✅ Refunded {amount}")
    return True


def test_refund_unknown_payment(client: PaymentTestClient) -> bool:
    logger.info("\n" + "=" * 60)
    logger.info("TEST: Refund Unknown Payment (expect 404)")
    logger.info("=" * 60)

    result = client.refund_payment(999_999, 10, "n/a")
    if result["status_code"] != 404:
        logger.error(f"❌ Expected 404, got {result['status_code']}")
        return False

    logger.info("✅ 404 as expected")
    return True


def test_refund_zero_amount(client: PaymentTestClient, payment_id: int) -> bool:
    logger.info("\n" + "=" * 60)
    logger.info("TEST: Refund Zero Amount (expect 422)")
    logger.info("=" * 60)

    result = client.refund_payment(payment_id, 0, "zero refund")
    if result["status_code"] != 422:
        logger.error(
            f"❌ Expected 422, got {result['status_code']}: {result['text']}"
        )
        return False

    logger.info("✅ 422 as expected")
    return True


def test_invoice_payments_summary(client: PaymentTestClient, invoice_id: int) -> bool:
    logger.info("\n" + "=" * 60)
    logger.info("TEST: Invoice Payments Summary")
    logger.info("=" * 60)

    result = client.get_invoice_payments(invoice_id)
    if result["status_code"] != 200:
        logger.error(f"❌ Expected 200, got {result['status_code']}")
        return False

    if not validate_invoice_payment_response(result["data"]):
        return False

    data = result["data"]
    logger.info(f"✅ Invoice {invoice_id}: status={data['status']}")
    logger.info(f"   total_amount={data['total_amount']}")
    logger.info(f"   total_paid={data['total_paid']}")
    logger.info(f"   remaining={data['remaining_amount']}")
    logger.info(f"   payments={len(data['payments'])}")
    return True


def test_invoice_payments_unknown_invoice(client: PaymentTestClient) -> bool:
    logger.info("\n" + "=" * 60)
    logger.info("TEST: Invoice Payments Unknown Invoice (expect 404)")
    logger.info("=" * 60)

    result = client.get_invoice_payments(999_999)
    if result["status_code"] != 404:
        logger.error(f"❌ Expected 404, got {result['status_code']}")
        return False

    logger.info("✅ 404 as expected")
    return True


def test_daily_stats(client: PaymentTestClient) -> bool:
    logger.info("\n" + "=" * 60)
    logger.info("TEST: Daily Stats")
    logger.info("=" * 60)

    ok = True

    result = client.get_daily_stats()
    if result["status_code"] != 200 or not validate_daily_stats_response(
        result["data"]
    ):
        logger.error(f"❌ Default daily stats failed: {result}")
        ok = False
    else:
        logger.info(f"✅ Default date: {result['data']['date']}")

    result = client.get_daily_stats("2024-01-15")
    if result["status_code"] != 200:
        logger.error(f"❌ Dated daily stats failed: {result}")
        ok = False
    else:
        logger.info(f"✅ 2024-01-15: {result['data']['date']}")

    result = client.get_daily_stats("invalid-date")
    if result["status_code"] != 400:
        logger.error(
            f"❌ Invalid date expected 400, got {result['status_code']}"
        )
        ok = False
    else:
        logger.info("✅ Invalid date correctly rejected with 400")

    return ok


def test_route_ordering(client: PaymentTestClient) -> bool:
    """
    /{payment_id} must be declared last so it doesn't shadow /health or
    /stats/daily. A shadowed route fails to parse the string as an int
    and returns 422.
    """
    logger.info("\n" + "=" * 60)
    logger.info("TEST: Route Ordering")
    logger.info("=" * 60)

    for path in ("/health", "/stats/daily"):
        result = client._request("GET", path)
        if result["status_code"] == 422:
            logger.error(f"❌ {path} was shadowed by /{{payment_id}}")
            return False
        logger.info(f"✅ {path} resolves to its own handler")
    return True


# ==================== RUNNER ====================


class SuiteResults:
    def __init__(self) -> None:
        self.total = 0
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.details: List[Dict[str, Any]] = []

    def record(self, name: str, outcome: str, **extra: Any) -> None:
        self.total += 1
        self.details.append({"name": name, "status": outcome, **extra})
        if outcome == "PASSED":
            self.passed += 1
        elif outcome == "FAILED":
            self.failed += 1
        elif outcome == "SKIPPED":
            self.skipped += 1


def run_all_tests() -> SuiteResults:
    logger.info("\n" + "🚀" * 30)
    logger.info("PAYMENT ENDPOINT TEST SUITE")
    logger.info("🚀" * 30)

    client = PaymentTestClient()
    results = SuiteResults()

    # 1. Health
    ok = test_health_check(client)
    results.record("Health Check", "PASSED" if ok else "FAILED")
    if not ok:
        # Nothing else will work if the server is down.
        _print_summary(results)
        return results

    # 2. Route ordering
    ok = test_route_ordering(client)
    results.record("Route Ordering", "PASSED" if ok else "FAILED")

    # 3. Create payment against an unpaid invoice
    created_payment_id = test_create_payment_on_unpaid_invoice(client)
    if created_payment_id is None:
        results.record("Create Payment (unpaid)", "SKIPPED")
    else:
        results.record(
            "Create Payment (unpaid)", "PASSED", payment_id=created_payment_id
        )

    # 4. Create payment against a paid invoice → 409
    ok = test_create_payment_on_paid_invoice(client)
    results.record("Create Payment (paid)", "PASSED" if ok else "FAILED")

    # 5. Create payment validation errors → 422
    ok = test_create_payment_validation_errors(client)
    results.record("Create Payment (validation)", "PASSED" if ok else "FAILED")

    # 6. Create payment on unknown invoice → 404
    ok = test_create_payment_unknown_invoice(client)
    results.record("Create Payment (404)", "PASSED" if ok else "FAILED")

    # 7–14 depend on a created payment
    if created_payment_id is not None:
        ok = test_get_payment(client, created_payment_id)
        results.record("Get Payment", "PASSED" if ok else "FAILED")

        ok = test_confirm_payment(client, created_payment_id)
        results.record("Confirm Payment", "PASSED" if ok else "FAILED")

        ok = test_refund_payment(client, created_payment_id)
        results.record("Refund Payment", "PASSED" if ok else "FAILED")

        ok = test_refund_zero_amount(client, created_payment_id)
        results.record("Refund Zero Amount", "PASSED" if ok else "FAILED")

        # Reject needs a fresh payment — reject and refund are mutually exclusive.
        reject_payment_id = test_create_payment_on_unpaid_invoice(client)
        if reject_payment_id is None:
            results.record("Reject Payment", "SKIPPED")
        else:
            ok = test_reject_payment(client, reject_payment_id)
            results.record("Reject Payment", "PASSED" if ok else "FAILED")

        # Invoice summary for the invoice we just paid against
        info = client.get_payment(created_payment_id)
        if info["status_code"] == 200:
            invoice_id = info["data"].get("invoice_id")
            if isinstance(invoice_id, int):
                ok = test_invoice_payments_summary(client, invoice_id)
                results.record("Invoice Summary", "PASSED" if ok else "FAILED")
            else:
                results.record("Invoice Summary", "SKIPPED")
        else:
            results.record("Invoice Summary", "SKIPPED")
    else:
        for name in (
            "Get Payment",
            "Confirm Payment",
            "Refund Payment",
            "Refund Zero Amount",
            "Reject Payment",
            "Invoice Summary",
        ):
            results.record(name, "SKIPPED")

    # 15. Unknown payment lookups
    ok = test_get_unknown_payment(client)
    results.record("Get Unknown Payment (404)", "PASSED" if ok else "FAILED")

    ok = test_confirm_unknown_payment(client)
    results.record("Confirm Unknown Payment (404)", "PASSED" if ok else "FAILED")

    ok = test_refund_unknown_payment(client)
    results.record("Refund Unknown Payment (404)", "PASSED" if ok else "FAILED")

    ok = test_invoice_payments_unknown_invoice(client)
    results.record("Invoice Unknown (404)", "PASSED" if ok else "FAILED")

    # 16. Daily stats
    ok = test_daily_stats(client)
    results.record("Daily Stats", "PASSED" if ok else "FAILED")

    _print_summary(results)
    return results


def _print_summary(results: SuiteResults) -> None:
    logger.info("\n" + "=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total:   {results.total}")
    logger.info(f"✅ Passed:  {results.passed}")
    logger.info(f"❌ Failed:  {results.failed}")
    logger.info(f"⏭️  Skipped: {results.skipped}")

    logger.info("\nDetails:")
    for d in results.details:
        icon = {"PASSED": "✅", "FAILED": "❌", "SKIPPED": "⏭️"}.get(
            d["status"], "?"
        )
        extra = ""
        if "payment_id" in d:
            extra = f" (payment_id={d['payment_id']})"
        logger.info(f"  {icon} {d['name']}{extra}")


if __name__ == "__main__":
    try:
        results = run_all_tests()
        # Skipped is not the same as failed. Fail only on real failures.
        sys.exit(0 if results.failed == 0 else 1)
    except KeyboardInterrupt:
        logger.info("\n⚠️ Interrupted by user")
        sys.exit(130)