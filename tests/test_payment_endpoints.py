# tests/test_payment_endpoints.py

import requests
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging
import time
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== CONFIGURATION ====================

BASE_URL = "http://localhost:9098"  # Your server URL
API_PREFIX = "/payments"  # Payment API prefix

# Test data based on dummy data
TEST_INVOICE_IDS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17]
TEST_USER_IDS = [1, 2, 3, 5, 21, 22]

# Status codes we expect for different scenarios
EXPECTED = {
    'success': 200,
    'not_found': 404,
    'conflict': 409,
    'bad_request': 400,
    'validation_error': 422,
    'server_error': 500
}

# ==================== TEST CLIENT ====================

class PaymentTestClient:
    """Test client for payment endpoints"""
    
    def __init__(self, base_url: str = BASE_URL, api_prefix: str = API_PREFIX):
        self.base_url = base_url
        self.api_prefix = api_prefix
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        self.created_payment_ids = []
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """Make HTTP request and return JSON response"""
        url = f"{self.base_url}{self.api_prefix}{endpoint}"
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(url)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=data)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            logger.info(f"{method} {url} - Status: {response.status_code}")
            
            if response.status_code >= 400:
                logger.error(f"Error response: {response.text}")
            
            return {
                'status_code': response.status_code,
                'data': response.json() if response.text else {},
                'text': response.text
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            return {
                'status_code': 500,
                'data': {},
                'error': str(e)
            }
    
    # ==================== PAYMENT ENDPOINTS ====================
    
    def create_payment(self, invoice_id: int, amount: float, payment_method: str, 
                      user_id: int, notes: Optional[str] = None, 
                      payment_type: str = 'payment') -> Dict:
        """Create payment - POST /payments/payment"""
        data = {
            'invoice_id': invoice_id,
            'amount': amount,
            'payment_method': payment_method,
            'user_id': user_id,
        }
        if notes:
            data['notes'] = notes
        if payment_type:
            data['payment_type'] = payment_type
        
        result = self._make_request('POST', '/payment', data)
        
        # Track created payment IDs
        if result['status_code'] == 200 and result['data'].get('id'):
            self.created_payment_ids.append(result['data']['id'])
        
        return result
    
    def confirm_payment(self, payment_id: int, transaction_details: Optional[Dict] = None) -> Dict:
        """Confirm payment - POST /payments/confirm/{payment_id}"""
        data = {
            'transaction_details': transaction_details or {}
        }
        return self._make_request('POST', f'/confirm/{payment_id}', data)
    
    def reject_payment(self, payment_id: int, reason: str) -> Dict:
        """Reject payment - POST /payments/reject/{payment_id}"""
        data = {'reason': reason}
        return self._make_request('POST', f'/reject/{payment_id}', data)
    
    def refund_payment(self, payment_id: int, amount: float, reason: str) -> Dict:
        """Refund payment - POST /payments/refund/{payment_id}"""
        data = {
            'amount': amount,
            'reason': reason
        }
        return self._make_request('POST', f'/refund/{payment_id}', data)
    
    def get_invoice_payments(self, invoice_id: int) -> Dict:
        """Get invoice payments - GET /payments/invoice/{invoice_id}"""
        return self._make_request('GET', f'/invoice/{invoice_id}')
    
    def get_payment(self, payment_id: int) -> Dict:
        """Get payment - GET /payments/{payment_id}"""
        return self._make_request('GET', f'/{payment_id}')
    
    def get_daily_stats(self, date: Optional[str] = None) -> Dict:
        """Get daily stats - GET /payments/stats/daily"""
        endpoint = '/stats/daily'
        if date:
            endpoint += f'?date={date}'
        return self._make_request('GET', endpoint)
    
    def health_check(self) -> Dict:
        """Health check - GET /payments/health"""
        return self._make_request('GET', '/health')


# ==================== RESPONSE VALIDATORS ====================

def validate_payment_response(data: Dict) -> bool:
    """Validate payment response has expected fields"""
    required_fields = ['id', 'invoice_id', 'user_id', 'amount', 'payment_method', 
                      'status', 'payment_type']
    
    for field in required_fields:
        if field not in data:
            logger.error(f"❌ Missing required field in payment response: {field}")
            return False
    
    # Check data types
    if not isinstance(data.get('id'), int):
        logger.error(f"❌ 'id' should be an integer, got {type(data.get('id'))}")
        return False
    
    if not isinstance(data.get('amount'), (int, float)):
        logger.error(f"❌ 'amount' should be a number, got {type(data.get('amount'))}")
        return False
    
    return True


def validate_invoice_payment_response(data: Dict) -> bool:
    """Validate invoice payment response has expected fields"""
    required_fields = ['invoice_id', 'total_amount', 'total_paid', 
                      'remaining_amount', 'status', 'payments']
    
    for field in required_fields:
        if field not in data:
            logger.error(f"❌ Missing field in invoice payment response: {field}")
            return False
    
    # Check that payments is a list
    if not isinstance(data.get('payments'), list):
        logger.error(f"❌ 'payments' should be a list, got {type(data.get('payments'))}")
        return False
    
    return True


def validate_error_response(data: Dict) -> bool:
    """Validate error response has expected fields"""
    # Simple error responses might just have 'detail'
    if 'detail' in data:
        return True
    
    # Enhanced error responses have more fields
    expected_fields = ['detail', 'status_code']
    for field in expected_fields:
        if field not in data:
            logger.warning(f"⚠️ Missing field in error response: {field}")
            return False
    
    return True


def validate_daily_stats_response(data: Dict) -> bool:
    """Validate daily stats response has expected fields"""
    required_fields = ['date', 'total_payments', 'total_amount', 'average_amount']
    
    for field in required_fields:
        if field not in data:
            logger.error(f"❌ Missing field in daily stats response: {field}")
            return False
    
    return True


# ==================== TEST FUNCTIONS ====================

def test_health_check(client: PaymentTestClient) -> bool:
    """Test health check endpoint"""
    logger.info("\n" + "="*60)
    logger.info("TEST: Health Check")
    logger.info("="*60)
    
    result = client.health_check()
    
    if result['status_code'] == 200:
        data = result['data']
        logger.info(f"✅ Health check passed")
        logger.info(f"   Status: {data.get('status')}")
        logger.info(f"   Service: {data.get('service')}")
        logger.info(f"   Database: {data.get('database')}")
        return True
    else:
        logger.error(f"❌ Health check failed: {result.get('error', 'Unknown error')}")
        return False


def test_create_payment(client: PaymentTestClient) -> List[int]:
    """Test creating payments"""
    logger.info("\n" + "="*60)
    logger.info("TEST: Create Payment")
    logger.info("="*60)
    
    test_cases = [
        # (invoice_id, amount, payment_method, user_id, notes, payment_type, expected_status)
        (1, 1250.50, 'card', 1, 'Full payment for invoice 1', 'payment', EXPECTED['conflict']),  # Already paid
        (2, 350.75, 'cash', 2, 'Payment for consultation', 'payment', EXPECTED['conflict']),  # Already paid
        (4, 567.80, 'bank_transfer', 5, 'Pharmacy order payment', 'payment', EXPECTED['success']),
        (6, 430.00, 'cash', 22, 'X-Ray services payment', 'payment', EXPECTED['success']),
        (8, 230.50, 'card', 1, 'Follow-up visit payment', 'payment', EXPECTED['success']),
        (99999, 100.00, 'card', 1, 'Invalid invoice', 'payment', EXPECTED['not_found']),
    ]
    
    created_ids = []
    
    for invoice_id, amount, method, user_id, notes, payment_type, expected_status in test_cases:
        logger.info(f"\nCreating payment for invoice {invoice_id}...")
        result = client.create_payment(
            invoice_id=invoice_id,
            amount=amount,
            payment_method=method,
            user_id=user_id,
            notes=notes,
            payment_type=payment_type
        )
        
        if result['status_code'] == expected_status:
            if expected_status == EXPECTED['success']:
                data = result['data']
                if validate_payment_response(data):
                    logger.info(f"✅ Payment created: ID={data.get('id')}")
                    logger.info(f"   Status: {data.get('status')}")
                    logger.info(f"   Amount: {data.get('amount')}")
                    logger.info(f"   Method: {data.get('payment_method')}")
                    created_ids.append(data.get('id'))
                else:
                    logger.error(f"❌ Invalid response format")
            else:
                logger.info(f"✅ Correctly returned {expected_status} as expected")
        else:
            logger.error(f"❌ Expected {expected_status}, got {result['status_code']}")
            if result.get('data'):
                logger.error(f"   Response: {result['data']}")
    
    logger.info(f"\n✅ Created {len(created_ids)} payments")
    return created_ids


def test_confirm_payment(client: PaymentTestClient, payment_id: int) -> bool:
    """Test confirming a payment"""
    logger.info("\n" + "="*60)
    logger.info("TEST: Confirm Payment")
    logger.info("="*60)
    
    logger.info(f"Confirming payment {payment_id}...")
    
    transaction_details = {
        'reference': f'REF-{payment_id}-{datetime.now().strftime("%Y%m%d%H%M%S")}',
        'bank_reference': f'BANK-{payment_id}',
        'notes': f'Payment {payment_id} confirmed successfully'
    }
    
    result = client.confirm_payment(payment_id, transaction_details)
    
    if result['status_code'] == 200:
        data = result['data']
        if validate_payment_response(data):
            logger.info(f"✅ Payment {payment_id} confirmed")
            logger.info(f"   Status: {data.get('status')}")
            logger.info(f"   Transactions: {len(data.get('transactions', []))}")
            return True
    elif result['status_code'] == 404:
        logger.info(f"✅ Payment {payment_id} not found (expected)")
        return True
    elif result['status_code'] == 409:
        logger.info(f"✅ Payment {payment_id} already processed (expected)")
        return True
    else:
        logger.error(f"❌ Failed to confirm payment: {result.get('error', 'Unknown error')}")
    
    return False


def test_reject_payment(client: PaymentTestClient, payment_id: int) -> bool:
    """Test rejecting a payment"""
    logger.info("\n" + "="*60)
    logger.info("TEST: Reject Payment")
    logger.info("="*60)
    
    logger.info(f"Rejecting payment {payment_id}...")
    
    result = client.reject_payment(
        payment_id=payment_id,
        reason=f'Payment rejected - Insufficient funds - {datetime.now().strftime("%Y-%m-%d %H:%M")}'
    )
    
    if result['status_code'] == 200:
        data = result['data']
        if validate_payment_response(data):
            logger.info(f"✅ Payment {payment_id} rejected")
            logger.info(f"   Status: {data.get('status')}")
            return True
    elif result['status_code'] == 404:
        logger.info(f"✅ Payment {payment_id} not found (expected)")
        return True
    else:
        logger.error(f"❌ Failed to reject payment: {result.get('error', 'Unknown error')}")
    
    return False


def test_refund_payment(client: PaymentTestClient, payment_id: int) -> bool:
    """Test refunding a payment"""
    logger.info("\n" + "="*60)
    logger.info("TEST: Refund Payment")
    logger.info("="*60)
    
    logger.info(f"Refunding payment {payment_id}...")
    
    # Get payment details first
    payment_info = client.get_payment(payment_id)
    amount = payment_info.get('data', {}).get('amount', 100)
    
    result = client.refund_payment(
        payment_id=payment_id,
        amount=amount,
        reason=f'Refund requested by customer - {datetime.now().strftime("%Y-%m-%d %H:%M")}'
    )
    
    if result['status_code'] == 200:
        data = result['data']
        if validate_payment_response(data):
            logger.info(f"✅ Payment {payment_id} refunded")
            logger.info(f"   Status: {data.get('status')}")
            logger.info(f"   Refund amount: {data.get('amount')}")
            return True
    elif result['status_code'] == 404:
        logger.info(f"✅ Payment {payment_id} not found (expected)")
        return True
    elif result['status_code'] == 409:
        logger.info(f"✅ Payment {payment_id} not eligible for refund (expected)")
        return True
    else:
        logger.error(f"❌ Failed to refund payment: {result.get('error', 'Unknown error')}")
    
    return False


def test_get_invoice_payments(client: PaymentTestClient) -> bool:
    """Test getting payments for an invoice"""
    logger.info("\n" + "="*60)
    logger.info("TEST: Get Invoice Payments")
    logger.info("="*60)
    
    test_invoices = [1, 2, 4, 5, 6, 8, 12, 999]
    all_passed = True
    
    for invoice_id in test_invoices:
        logger.info(f"\nGetting payments for invoice {invoice_id}...")
        result = client.get_invoice_payments(invoice_id)
        
        if result['status_code'] == 200:
            data = result['data']
            if validate_invoice_payment_response(data):
                logger.info(f"✅ Invoice {invoice_id}:")
                logger.info(f"   Invoice Status: {data.get('status')}")
                logger.info(f"   Total Amount: {data.get('total_amount')}")
                logger.info(f"   Total Paid: {data.get('total_paid')}")
                logger.info(f"   Remaining: {data.get('remaining_amount')}")
                logger.info(f"   Payments: {len(data.get('payments', []))}")
            else:
                all_passed = False
        elif result['status_code'] == 404:
            logger.info(f"✅ Invoice {invoice_id} not found (expected)")
        else:
            logger.error(f"❌ Failed to get invoice payments: {result.get('error', 'Unknown error')}")
            all_passed = False
    
    return all_passed


def test_get_payment_details(client: PaymentTestClient, payment_id: int) -> bool:
    """Test getting payment details"""
    logger.info("\n" + "="*60)
    logger.info("TEST: Get Payment Details")
    logger.info("="*60)
    
    logger.info(f"Getting details for payment {payment_id}...")
    result = client.get_payment(payment_id)
    
    if result['status_code'] == 200:
        data = result['data']
        if validate_payment_response(data):
            logger.info(f"✅ Payment {payment_id}:")
            logger.info(f"   Invoice: {data.get('invoice_id')}")
            logger.info(f"   Amount: {data.get('amount')}")
            logger.info(f"   Status: {data.get('status')}")
            logger.info(f"   Method: {data.get('payment_method')}")
            logger.info(f"   Transactions: {len(data.get('transactions', []))}")
            return True
    elif result['status_code'] == 404:
        logger.info(f"✅ Payment {payment_id} not found (expected)")
        return True
    else:
        logger.error(f"❌ Failed to get payment details: {result.get('error', 'Unknown error')}")
    
    return False


def test_daily_stats(client: PaymentTestClient) -> bool:
    """Test daily payment statistics"""
    logger.info("\n" + "="*60)
    logger.info("TEST: Daily Payment Statistics")
    logger.info("="*60)
    
    test_dates = [
        None,  # Today
        '2024-01-15',
        '2024-01-20',
        '2024-02-01',
        '2024-02-14',
        '2024-02-15',
        '2024-02-16',
        'invalid-date',  # Invalid format
    ]
    
    all_passed = True
    
    for date in test_dates:
        logger.info(f"\nGetting stats for date: {date or 'today'}")
        result = client.get_daily_stats(date)
        
        if result['status_code'] == 200:
            data = result['data']
            if validate_daily_stats_response(data):
                logger.info(f"✅ Stats for {date or 'today'}:")
                for key, value in data.items():
                    if isinstance(value, dict):
                        logger.info(f"   {key}:")
                        for sub_key, sub_value in value.items():
                            logger.info(f"     - {sub_key}: {sub_value}")
                    else:
                        logger.info(f"   {key}: {value}")
            else:
                all_passed = False
        elif result['status_code'] == 400:
            logger.info(f"✅ Invalid date format (expected)")
        else:
            logger.error(f"❌ Failed to get stats: {result.get('error', 'Unknown error')}")
            all_passed = False
    
    return all_passed


def test_error_scenarios(client: PaymentTestClient) -> bool:
    """Test error scenarios"""
    logger.info("\n" + "="*60)
    logger.info("TEST: Error Scenarios")
    logger.info("="*60)
    
    all_passed = True
    
    # Scenario 1: Non-existent invoice
    logger.info("\n1. Non-existent invoice...")
    result = client.create_payment(99999, 100.00, 'card', 1, 'Invalid invoice test')
    if result['status_code'] == 404:
        data = result['data']
        if validate_error_response(data):
            logger.info(f"✅ Correctly returned 404")
            logger.info(f"   Detail: {data.get('detail')}")
        else:
            logger.warning(f"⚠️ Invalid error response format")
            all_passed = False
    else:
        logger.warning(f"⚠️ Expected 404, got {result['status_code']}")
        all_passed = False
    
    # Scenario 2: Zero amount
    logger.info("\n2. Zero amount payment...")
    result = client.create_payment(1, 0.00, 'card', 1, 'Zero amount test')
    if result['status_code'] in [400, 422]:
        logger.info(f"✅ Correctly rejected zero amount (HTTP {result['status_code']})")
    else:
        logger.warning(f"⚠️ Expected 400/422, got {result['status_code']}")
        all_passed = False
    
    # Scenario 3: Non-existent payment for confirmation
    logger.info("\n3. Confirm non-existent payment...")
    result = client.confirm_payment(99999, {})
    if result['status_code'] == 404:
        logger.info(f"✅ Correctly returned 404")
    else:
        logger.warning(f"⚠️ Expected 404, got {result['status_code']}")
        all_passed = False
    
    # Scenario 4: Non-existent payment for refund
    logger.info("\n4. Refund non-existent payment...")
    result = client.refund_payment(99999, 100, 'Test refund')
    if result['status_code'] == 404:
        logger.info(f"✅ Correctly returned 404")
    else:
        logger.warning(f"⚠️ Expected 404, got {result['status_code']}")
        all_passed = False
    
    return all_passed


# ==================== MAIN TEST RUNNER ====================

def run_all_tests():
    """Run all payment endpoint tests"""
    logger.info("\n" + "🚀"*30)
    logger.info("PAYMENT ENDPOINT TEST SUITE")
    logger.info("🚀"*30)
    
    client = PaymentTestClient()
    results = {
        'total': 0,
        'passed': 0,
        'failed': 0,
        'details': []
    }
    
    # ==================== STEP 1: Health Check ====================
    logger.info(f"\n📝 STEP {results['total'] + 1}: Health Check...")
    result = test_health_check(client)
    results['total'] += 1
    if result:
        results['passed'] += 1
        results['details'].append({'name': 'Health Check', 'status': 'PASSED'})
    else:
        results['failed'] += 1
        results['details'].append({'name': 'Health Check', 'status': 'FAILED'})
    
    # ==================== STEP 2: Create Payments ====================
    logger.info(f"\n📝 STEP {results['total'] + 1}: Create Payments...")
    created_ids = test_create_payment(client)
    results['total'] += 1
    if created_ids:
        results['passed'] += 1
        results['details'].append({'name': 'Create Payments', 'status': 'PASSED', 'created': len(created_ids)})
    else:
        results['failed'] += 1
        results['details'].append({'name': 'Create Payments', 'status': 'FAILED'})
    
    # ==================== STEP 3: Get Invoice Payments ====================
    logger.info(f"\n📝 STEP {results['total'] + 1}: Get Invoice Payments...")
    result = test_get_invoice_payments(client)
    results['total'] += 1
    if result:
        results['passed'] += 1
        results['details'].append({'name': 'Get Invoice Payments', 'status': 'PASSED'})
    else:
        results['failed'] += 1
        results['details'].append({'name': 'Get Invoice Payments', 'status': 'FAILED'})
    
    # ==================== STEP 4: Get Payment Details ====================
    if client.created_payment_ids:
        payment_id = client.created_payment_ids[0]
        logger.info(f"\n📝 STEP {results['total'] + 1}: Get Payment Details...")
        result = test_get_payment_details(client, payment_id)
        results['total'] += 1
        if result:
            results['passed'] += 1
            results['details'].append({'name': 'Get Payment Details', 'status': 'PASSED'})
        else:
            results['failed'] += 1
            results['details'].append({'name': 'Get Payment Details', 'status': 'FAILED'})
    else:
        logger.warning("⚠️ No payment IDs available for Get Payment Details test")
    
    # ==================== STEP 5: Confirm Payment ====================
    if client.created_payment_ids:
        payment_id = client.created_payment_ids[0]
        logger.info(f"\n📝 STEP {results['total'] + 1}: Confirm Payment...")
        result = test_confirm_payment(client, payment_id)
        results['total'] += 1
        if result:
            results['passed'] += 1
            results['details'].append({'name': 'Confirm Payment', 'status': 'PASSED'})
        else:
            results['failed'] += 1
            results['details'].append({'name': 'Confirm Payment', 'status': 'FAILED'})
    else:
        logger.warning("⚠️ No payment IDs available for Confirm Payment test")
    
    # ==================== STEP 6: Create Payment for Rejection ====================
    logger.info(f"\n📝 STEP {results['total'] + 1}: Create Payment for Rejection...")
    result = client.create_payment(8, 230.50, 'card', 1, 'Test payment for rejection')
    reject_payment_id = None
    if result['status_code'] == 200:
        reject_payment_id = result['data'].get('id')
        logger.info(f"✅ Created payment {reject_payment_id} for rejection")
        results['passed'] += 1
        results['details'].append({'name': 'Create Payment for Rejection', 'status': 'PASSED'})
    else:
        logger.warning("⚠️ Could not create payment for rejection test")
        results['failed'] += 1
        results['details'].append({'name': 'Create Payment for Rejection', 'status': 'FAILED'})
    results['total'] += 1
    
    # ==================== STEP 7: Reject Payment ====================
    if reject_payment_id:
        logger.info(f"\n📝 STEP {results['total'] + 1}: Reject Payment...")
        result = test_reject_payment(client, reject_payment_id)
        results['total'] += 1
        if result:
            results['passed'] += 1
            results['details'].append({'name': 'Reject Payment', 'status': 'PASSED'})
        else:
            results['failed'] += 1
            results['details'].append({'name': 'Reject Payment', 'status': 'FAILED'})
    else:
        logger.warning("⚠️ No payment ID available for Reject Payment test")
    
    # ==================== STEP 8: Daily Statistics ====================
    logger.info(f"\n📝 STEP {results['total'] + 1}: Daily Statistics...")
    result = test_daily_stats(client)
    results['total'] += 1
    if result:
        results['passed'] += 1
        results['details'].append({'name': 'Daily Statistics', 'status': 'PASSED'})
    else:
        results['failed'] += 1
        results['details'].append({'name': 'Daily Statistics', 'status': 'FAILED'})
    
    # ==================== STEP 9: Error Scenarios ====================
    logger.info(f"\n📝 STEP {results['total'] + 1}: Error Scenarios...")
    result = test_error_scenarios(client)
    results['total'] += 1
    if result:
        results['passed'] += 1
        results['details'].append({'name': 'Error Scenarios', 'status': 'PASSED'})
    else:
        results['failed'] += 1
        results['details'].append({'name': 'Error Scenarios', 'status': 'FAILED'})
    
    # ==================== SUMMARY ====================
    logger.info("\n" + "="*60)
    logger.info("TEST SUMMARY")
    logger.info("="*60)
    logger.info(f"Total tests: {results['total']}")
    logger.info(f"✅ Passed: {results['passed']}")
    logger.info(f"❌ Failed: {results['failed']}")
    
    # Detailed results
    logger.info("\nDetailed Results:")
    for detail in results['details']:
        status = "✅" if detail['status'] == 'PASSED' else "❌"
        extra = f" (created {detail.get('created', 0)} payments)" if detail.get('created') else ""
        logger.info(f"  {status} {detail['name']}{extra}")
    
    if results['failed'] == 0:
        logger.info("\n🎉 All tests passed!")
    else:
        logger.warning(f"\n⚠️ {results['failed']} tests failed")
    
    return results


# ==================== RUN TESTS ====================

if __name__ == "__main__":
    try:
        # Check if server is running
        import requests
        try:
            health_check = requests.get(f"{BASE_URL}/health")
            if health_check.status_code == 200:
                logger.info(f"✅ Server is running: {health_check.status_code}")
            else:
                logger.warning(f"⚠️ Server returned: {health_check.status_code}")
                logger.info("Continuing with tests anyway...")
        except requests.exceptions.ConnectionError:
            logger.warning("⚠️ Could not connect to server. Make sure it's running.")
            logger.info("Continuing with tests anyway...")
        
        # Run all tests
        results = run_all_tests()
        
        # Exit with appropriate code
        sys.exit(0 if results['failed'] == 0 else 1)
        
    except KeyboardInterrupt:
        logger.info("\n⚠️ Tests interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"\n❌ Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)