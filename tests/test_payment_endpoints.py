# tests/test_payment_endpoints.py

import requests
import json
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import logging
from pprint import pprint

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== CONFIGURATION ====================

BASE_URL = "http://localhost:9098"  # Your server URL
API_PREFIX = "/payments"  # Correct prefix from OpenAPI schema

# Test data based on your dummy data
TEST_INVOICE_IDS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17]
TEST_USER_IDS = [1, 2, 3, 5, 21, 22]  # User wallet IDs
TEST_PROVIDER_IDS = [7, 8, 9]  # Provider wallet IDs

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
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """Make HTTP request and return JSON response"""
        url = f"{self.base_url}{self.api_prefix}{endpoint}"
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(url)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=data)
            elif method.upper() == 'PUT':
                response = self.session.put(url, json=data)
            elif method.upper() == 'DELETE':
                response = self.session.delete(url)
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
    
    def create_payment(self, invoice_id: int, amount: float, payment_method: str, 
                      user_id: int, notes: Optional[str] = None, 
                      payment_type: str = 'payment') -> Dict:
        """Test create payment endpoint - POST /payments/payment"""
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
        
        return self._make_request('POST', '/payment', data)
    
    def confirm_payment(self, payment_id: int, transaction_details: Optional[Dict] = None) -> Dict:
        """Test confirm payment endpoint - POST /payments/confirm/{payment_id}"""
        data = {
            'transaction_details': transaction_details or {}
        }
        return self._make_request('POST', f'/confirm/{payment_id}', data)
    
    def reject_payment(self, payment_id: int, reason: str) -> Dict:
        """Test reject payment endpoint - POST /payments/reject/{payment_id}"""
        data = {'reason': reason}
        return self._make_request('POST', f'/reject/{payment_id}', data)
    
    def refund_payment(self, payment_id: int, amount: float, reason: str) -> Dict:
        """Test refund payment endpoint - POST /payments/refund/{payment_id}"""
        data = {
            'amount': amount,
            'reason': reason
        }
        return self._make_request('POST', f'/refund/{payment_id}', data)
    
    def get_invoice_payments(self, invoice_id: int) -> Dict:
        """Test get invoice payments endpoint - GET /payments/invoice/{invoice_id}"""
        return self._make_request('GET', f'/invoice/{invoice_id}')
    
    def get_payment(self, payment_id: int) -> Dict:
        """Test get payment endpoint - GET /payments/{payment_id}"""
        return self._make_request('GET', f'/{payment_id}')
    
    def get_daily_stats(self, date: Optional[str] = None) -> Dict:
        """Test daily stats endpoint - GET /payments/stats/daily"""
        endpoint = '/stats/daily'
        if date:
            endpoint += f'?date={date}'
        return self._make_request('GET', endpoint)


# ==================== TEST FUNCTIONS ====================

def test_create_payments(client: PaymentTestClient):
    """Test creating payments for different invoices"""
    logger.info("\n" + "="*60)
    logger.info("TEST: Create Payments")
    logger.info("="*60)
    
    test_cases = [
        # (invoice_id, amount, payment_method, user_id, notes, payment_type)
        (1, 1250.50, 'card', 1, 'Full payment for invoice 1', 'payment'),
        (2, 350.75, 'cash', 2, 'Payment for consultation', 'payment'),
        (4, 567.80, 'bank_transfer', 5, 'Pharmacy order payment', 'payment'),
        (5, 1000.00, 'card', 21, 'Partial payment for lab tests', 'payment'),
        (6, 430.00, 'cash', 22, 'X-Ray services payment', 'payment'),
        (7, 500.00, 'card', 1, 'Partial payment for surgery', 'payment'),
        (8, 230.50, 'bank_transfer', 2, 'Follow-up visit payment', 'payment'),
    ]
    
    results = []
    
    for invoice_id, amount, method, user_id, notes, payment_type in test_cases:
        logger.info(f"\nCreating payment for invoice {invoice_id}...")
        result = client.create_payment(
            invoice_id=invoice_id,
            amount=amount,
            payment_method=method,
            user_id=user_id,
            notes=notes,
            payment_type=payment_type
        )
        
        results.append({
            'invoice_id': invoice_id,
            'status': result['status_code'],
            'data': result['data']
        })
        
        if result['status_code'] == 200:
            logger.info(f"✅ Payment created: ID={result['data'].get('payment_id')}")
            logger.info(f"   Status: {result['data'].get('status')}")
            logger.info(f"   Reference: {result['data'].get('reference')}")
        else:
            logger.error(f"❌ Failed to create payment: {result.get('error', 'Unknown error')}")
            if result.get('data'):
                logger.error(f"   Response: {result['data']}")
    
    return results


def test_confirm_payments(client: PaymentTestClient, payment_ids: list):
    """Test confirming pending payments"""
    logger.info("\n" + "="*60)
    logger.info("TEST: Confirm Payments")
    logger.info("="*60)
    
    results = []
    
    for payment_id in payment_ids:
        logger.info(f"\nConfirming payment {payment_id}...")
        
        transaction_details = {
            'reference': f'REF-{payment_id}-{datetime.now().strftime("%Y%m%d%H%M%S")}',
            'bank_reference': f'BANK-{payment_id}',
            'notes': f'Payment {payment_id} confirmed successfully'
        }
        
        result = client.confirm_payment(
            payment_id=payment_id,
            transaction_details=transaction_details
        )
        
        results.append({
            'payment_id': payment_id,
            'status': result['status_code'],
            'data': result['data']
        })
        
        if result['status_code'] == 200:
            logger.info(f"✅ Payment {payment_id} confirmed")
            logger.info(f"   New status: {result['data'].get('status')}")
            logger.info(f"   Transactions: {len(result['data'].get('transactions', []))}")
        else:
            logger.error(f"❌ Failed to confirm payment: {result.get('error', 'Unknown error')}")
    
    return results


def test_reject_payments(client: PaymentTestClient, payment_ids: list):
    """Test rejecting pending payments"""
    logger.info("\n" + "="*60)
    logger.info("TEST: Reject Payments")
    logger.info("="*60)
    
    results = []
    
    for payment_id in payment_ids:
        logger.info(f"\nRejecting payment {payment_id}...")
        
        result = client.reject_payment(
            payment_id=payment_id,
            reason=f'Payment rejected - Insufficient funds - {datetime.now().strftime("%Y-%m-%d %H:%M")}'
        )
        
        results.append({
            'payment_id': payment_id,
            'status': result['status_code'],
            'data': result['data']
        })
        
        if result['status_code'] == 200:
            logger.info(f"✅ Payment {payment_id} rejected")
            logger.info(f"   New status: {result['data'].get('status')}")
            logger.info(f"   Reason: {result['data'].get('reason')}")
        else:
            logger.error(f"❌ Failed to reject payment: {result.get('error', 'Unknown error')}")
    
    return results


def test_get_invoice_payments(client: PaymentTestClient):
    """Test getting payments for an invoice"""
    logger.info("\n" + "="*60)
    logger.info("TEST: Get Invoice Payments")
    logger.info("="*60)
    
    test_invoice_ids = [1, 2, 4, 5, 6, 8, 12]
    results = []
    
    for invoice_id in test_invoice_ids:
        logger.info(f"\nGetting payments for invoice {invoice_id}...")
        result = client.get_invoice_payments(invoice_id)
        
        results.append({
            'invoice_id': invoice_id,
            'status': result['status_code'],
            'data': result['data']
        })
        
        if result['status_code'] == 200:
            data = result['data']
            logger.info(f"✅ Invoice {invoice_id}:")
            logger.info(f"   Invoice Status: {data.get('invoice_status')}")
            logger.info(f"   Total Amount: {data.get('total_amount')}")
            
            summary = data.get('summary', {})
            if summary:
                logger.info(f"   Summary: {summary}")
            
            payments = data.get('payments', [])
            if payments:
                logger.info(f"   Payments: {len(payments)}")
                for payment in payments[:3]:
                    logger.info(f"     - ID: {payment.get('payment_id')}, Amount: {payment.get('amount')}, Status: {payment.get('status')}")
        else:
            logger.error(f"❌ Failed to get invoice payments: {result.get('error', 'Unknown error')}")
    
    return results


def test_get_payment_details(client: PaymentTestClient, payment_ids: list):
    """Test getting individual payment details"""
    logger.info("\n" + "="*60)
    logger.info("TEST: Get Payment Details")
    logger.info("="*60)
    
    results = []
    
    for payment_id in payment_ids:
        logger.info(f"\nGetting details for payment {payment_id}...")
        result = client.get_payment(payment_id)
        
        results.append({
            'payment_id': payment_id,
            'status': result['status_code'],
            'data': result['data']
        })
        
        if result['status_code'] == 200:
            data = result['data']
            logger.info(f"✅ Payment {payment_id}:")
            logger.info(f"   Invoice: {data.get('invoice_id')}")
            logger.info(f"   Amount: {data.get('amount')}")
            logger.info(f"   Status: {data.get('status')}")
            logger.info(f"   Method: {data.get('payment_method')}")
            logger.info(f"   Reference: {data.get('reference')}")
            
            transactions = data.get('transactions', [])
            if transactions:
                logger.info(f"   Transactions: {len(transactions)}")
                for tx in transactions[:2]:
                    logger.info(f"     - {tx.get('reference')}: {tx.get('amount')} ({tx.get('status')})")
        else:
            logger.error(f"❌ Failed to get payment details: {result.get('error', 'Unknown error')}")
    
    return results


def test_refund_payments(client: PaymentTestClient, payment_ids: list):
    """Test refunding payments"""
    logger.info("\n" + "="*60)
    logger.info("TEST: Refund Payments")
    logger.info("="*60)
    
    results = []
    
    for payment_id in payment_ids:
        logger.info(f"\nRefunding payment {payment_id}...")
        
        # Get payment details first to know the amount
        payment_info = client.get_payment(payment_id)
        amount = payment_info.get('data', {}).get('amount', 100)
        
        result = client.refund_payment(
            payment_id=payment_id,
            amount=amount,
            reason=f'Refund requested by customer - {datetime.now().strftime("%Y-%m-%d %H:%M")}'
        )
        
        results.append({
            'payment_id': payment_id,
            'status': result['status_code'],
            'data': result['data']
        })
        
        if result['status_code'] == 200:
            logger.info(f"✅ Payment {payment_id} refunded")
            logger.info(f"   New status: {result['data'].get('status')}")
            logger.info(f"   Refund amount: {result['data'].get('amount')}")
        else:
            logger.error(f"❌ Failed to refund payment: {result.get('error', 'Unknown error')}")
    
    return results


def test_daily_stats(client: PaymentTestClient):
    """Test daily payment statistics"""
    logger.info("\n" + "="*60)
    logger.info("TEST: Daily Payment Statistics")
    logger.info("="*60)
    
    # Test with different dates from your dummy data
    test_dates = [
        None,  # Today
        '2024-01-15',
        '2024-01-20',
        '2024-02-01',
        '2024-02-14',
        '2024-02-15',
        '2024-02-16',
    ]
    
    results = []
    
    for date in test_dates:
        logger.info(f"\nGetting stats for date: {date or 'today'}")
        result = client.get_daily_stats(date)
        
        results.append({
            'date': date,
            'status': result['status_code'],
            'data': result['data']
        })
        
        if result['status_code'] == 200:
            data = result['data']
            logger.info(f"✅ Stats for {date or 'today'}:")
            for key, value in data.items():
                if isinstance(value, dict):
                    logger.info(f"   {key}:")
                    for sub_key, sub_value in value.items():
                        logger.info(f"     - {sub_key}: {sub_value}")
                else:
                    logger.info(f"   {key}: {value}")
        else:
            logger.error(f"❌ Failed to get stats: {result.get('error', 'Unknown error')}")
    
    return results


# ==================== MAIN TEST RUNNER ====================

def run_all_tests():
    """Run all payment endpoint tests"""
    logger.info("\n" + "🚀"*30)
    logger.info("PAYMENT ENDPOINT TEST SUITE")
    logger.info("🚀"*30)
    
    client = PaymentTestClient()
    
    # Track created payment IDs for later tests
    created_payment_ids = []
    
    # 1. Create Payments
    logger.info("\n📝 STEP 1: Creating payments...")
    create_results = test_create_payments(client)
    
    # Extract payment IDs from successful creations
    for result in create_results:
        if result['status'] == 200 and result['data'].get('payment_id'):
            created_payment_ids.append(result['data']['payment_id'])
    
    logger.info(f"\n✅ Created {len(created_payment_ids)} payments")
    
    # 2. Get Invoice Payments
    logger.info("\n📝 STEP 2: Getting invoice payments...")
    test_get_invoice_payments(client)
    
    # 3. Get Payment Details
    if created_payment_ids:
        logger.info("\n📝 STEP 3: Getting payment details...")
        test_payment_ids = created_payment_ids[:3]
        test_get_payment_details(client, test_payment_ids)
    
    # 4. Confirm Payments
    if created_payment_ids:
        logger.info("\n📝 STEP 4: Confirming payments...")
        confirm_ids = created_payment_ids[:3]
        test_confirm_payments(client, confirm_ids)
    
    # 5. Test Rejections
    logger.info("\n📝 STEP 5: Testing payment rejections...")
    reject_result = client.create_payment(
        invoice_id=8,
        amount=230.50,
        payment_method='card',
        user_id=1,
        notes='Test payment for rejection'
    )
    
    if reject_result['status_code'] == 200 and reject_result['data'].get('payment_id'):
        rejection_id = reject_result['data']['payment_id']
        test_reject_payments(client, [rejection_id])
    
    # 6. Test Refunds
    if created_payment_ids:
        logger.info("\n📝 STEP 6: Testing payment refunds...")
        if len(created_payment_ids) >= 2:
            refund_payment_id = created_payment_ids[1]
            
            # Confirm it first
            confirm_result = client.confirm_payment(
                refund_payment_id,
                {'reference': f'REF-{refund_payment_id}', 'notes': 'For testing refund'}
            )
            
            if confirm_result['status_code'] == 200:
                # Now refund it
                test_refund_payments(client, [refund_payment_id])
    
    # 7. Daily Stats
    logger.info("\n📝 STEP 7: Getting daily statistics...")
    test_daily_stats(client)
    
    # 8. Summary
    logger.info("\n" + "="*60)
    logger.info("TEST SUMMARY")
    logger.info("="*60)
    logger.info(f"Total payments created: {len(created_payment_ids)}")
    logger.info("All tests completed!")
    
    return {
        'created_payment_ids': created_payment_ids,
        'create_results': create_results
    }


def test_specific_scenarios():
    """Test specific payment scenarios"""
    logger.info("\n" + "="*60)
    logger.info("SPECIFIC SCENARIO TESTS")
    logger.info("="*60)
    
    client = PaymentTestClient()
    
    # Scenario 1: Overpayment (amount > invoice total)
    logger.info("\n📝 Scenario 1: Overpayment")
    result = client.create_payment(
        invoice_id=2,  # Invoice total is 350.75
        amount=500.00,
        payment_method='card',
        user_id=1,
        notes='Overpayment test'
    )
    logger.info(f"Overpayment result: {result['status_code']}")
    if result['status_code'] == 200:
        logger.info(f"  Payment ID: {result['data'].get('payment_id')}")
        logger.info(f"  Status: {result['data'].get('status')}")
    
    # Scenario 2: Partial payment
    logger.info("\n📝 Scenario 2: Partial payment")
    result = client.create_payment(
        invoice_id=5,  # Invoice total: 1890.25
        amount=500.00,
        payment_method='cash',
        user_id=21,
        notes='Partial payment test'
    )
    logger.info(f"Partial payment result: {result['status_code']}")
    if result['status_code'] == 200:
        logger.info(f"  Payment ID: {result['data'].get('payment_id')}")
        logger.info(f"  Status: {result['data'].get('status')}")
    
    # Scenario 3: Payment for non-existent invoice
    logger.info("\n📝 Scenario 3: Non-existent invoice")
    result = client.create_payment(
        invoice_id=99999,
        amount=100.00,
        payment_method='card',
        user_id=1,
        notes='Invalid invoice test'
    )
    logger.info(f"Invalid invoice result: {result['status_code']}")
    if result['status_code'] >= 400:
        logger.info(f"  Error: {result['data'].get('detail', result.get('error', 'Unknown error'))}")
    
    # Scenario 4: Zero amount payment
    logger.info("\n📝 Scenario 4: Zero amount payment")
    result = client.create_payment(
        invoice_id=1,
        amount=0.00,
        payment_method='card',
        user_id=1,
        notes='Zero amount test'
    )
    logger.info(f"Zero amount result: {result['status_code']}")
    if result['status_code'] >= 400:
        logger.info(f"  Error: {result['data'].get('detail', result.get('error', 'Unknown error'))}")
    
    # Scenario 5: Confirm non-existent payment
    logger.info("\n📝 Scenario 5: Confirm non-existent payment")
    result = client.confirm_payment(99999, {})
    logger.info(f"Invalid confirm result: {result['status_code']}")
    
    # Scenario 6: Refund non-existent payment
    logger.info("\n📝 Scenario 6: Refund non-existent payment")
    result = client.refund_payment(99999, 100, 'Test refund')
    logger.info(f"Invalid refund result: {result['status_code']}")


# ==================== RUN TESTS ====================

if __name__ == "__main__":
    try:
        # Check if server is running
        import requests
        try:
            health_check = requests.get(f"{BASE_URL}/health")
            logger.info(f"✅ Server is running: {health_check.status_code}")
        except:
            logger.warning("⚠️ Server health check failed. Make sure the server is running.")
            logger.info("Continuing with tests anyway...")
        
        # Run all tests
        results = run_all_tests()
        
        # Run specific scenarios
        test_specific_scenarios()
        
        logger.info("\n✅ All tests completed successfully!")
        
    except KeyboardInterrupt:
        logger.info("\n⚠️ Tests interrupted by user")
    except Exception as e:
        logger.error(f"\n❌ Test execution failed: {e}")
        import traceback
        traceback.print_exc()