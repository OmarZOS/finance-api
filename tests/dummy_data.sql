 -- ==================== INVOICE DUMMY DATA ====================

 INSERT INTO `gluttex`.`invoice` (
     `invoice_number`, 
     `invoice_total_amount`, 
     `invoice_status`, 
     `invoice_issue_date`, 
     `invoice_due_date`, 
     `invoice_notes`, 
     `invoice_created_at`, 
     `invoice_updated_at`, 
     `invoice_type`, 
     `invoice_tax_applied`
 ) VALUES
 -- Paid invoices
 (
     'INV-2024-001',
     1250.5000,
     'paid',
     '2024-01-15',
     '2024-02-14',
     'Monthly service subscription - January 2024',
     '2024-01-15 10:30:00',
     '2024-01-20 14:15:00',
     'invoice',
     1
 ),
 (
     'INV-2024-002',
     350.7500,
     'paid',
     '2024-01-20',
     '2024-02-19',
     'Consultation fee - Dr. Smith',
     '2024-01-20 09:00:00',
     '2024-01-25 16:45:00',
     'receipt',
     0
 ),
 (
     'INV-2024-003',
     2780.0000,
     'paid',
     '2024-02-01',
     '2024-03-02',
     'Medical supplies - Bulk order',
     '2024-02-01 11:20:00',
     '2024-02-05 10:30:00',
     'invoice',
     1
 ),

 -- Unpaid invoices
 (
     'INV-2024-004',
     567.8000,
     'unpaid',
     '2024-02-10',
     '2024-03-11',
     'Pharmacy order 5678',
     '2024-02-10 14:00:00',
     '2024-02-10 14:00:00',
     'receipt',
     0
 ),
 (
     'INV-2024-005',
     1890.2500,
     'unpaid',
     '2024-02-15',
     '2024-03-16',
     'Lab tests - Complete blood panel',
     '2024-02-15 08:30:00',
     '2024-02-15 08:30:00',
     'invoice',
     1
 ),

 -- Partially paid invoices
 (
     'INV-2024-006',
     430.0000,
     'partially_paid',
     '2024-01-25',
     '2024-02-24',
     'X-Ray and MRI services',
     '2024-01-25 13:45:00',
     '2024-02-01 09:15:00',
     'invoice',
     1
 ),
 (
     'INV-2024-007',
     1500.0000,
     'partially_paid',
     '2024-02-05',
     '2024-03-06',
     'Surgical procedure - Appendix removal',
     '2024-02-05 15:30:00',
     '2024-02-15 11:00:00',
     'invoice',
     1
 ),

 -- Overdue invoices
 (
     'INV-2024-008',
     230.5000,
     'overdue',
     '2024-01-01',
     '2024-01-31',
     'Consultation - Follow-up visit',
     '2024-01-01 10:00:00',
     '2024-01-01 10:00:00',
     'receipt',
     0
 ),
 (
     'INV-2024-009',
     945.0000,
     'overdue',
     '2024-01-10',
     '2024-02-09',
     'Dental cleaning and X-rays',
     '2024-01-10 11:15:00',
     '2024-01-10 11:15:00',
     'invoice',
     1
 ),

 -- Canceled invoices
 (
     'INV-2024-010',
     675.3000,
     'canceled',
     '2024-01-30',
     '2024-02-29',
     'Canceled order - Patient requested cancellation',
     '2024-01-30 09:45:00',
     '2024-02-01 08:00:00',
     'invoice',
     1
 ),
 (
     'INV-2024-011',
     1200.0000,
     'canceled',
     '2024-02-08',
     '2024-03-09',
     'Specialist consultation - Cancelled',
     '2024-02-08 16:20:00',
     '2024-02-10 12:00:00',
     'proforma',
     0
 ),

 -- Refunded invoices
 (
     'INV-2024-012',
     890.0000,
     'refunded',
     '2024-01-18',
     '2024-02-17',
     'Refund for duplicate payment',
     '2024-01-18 10:30:00',
     '2024-01-25 15:30:00',
     'receipt',
     0
 ),
 (
     'INV-2024-013',
     2560.7500,
     'refunded',
     '2024-02-12',
     '2024-03-13',
     'Refund - Cancelled surgery',
     '2024-02-12 09:00:00',
     '2024-02-20 14:45:00',
     'invoice',
     1
 ),

 -- Proforma invoices
 (
     'INV-PRO-2024-001',
     3000.0000,
     'unpaid',
     '2024-02-20',
     '2024-03-20',
     'Proforma for upcoming surgery',
     '2024-02-20 08:00:00',
     '2024-02-20 08:00:00',
     'proforma',
     1
 ),
 (
     'INV-PRO-2024-002',
     450.5000,
     'unpaid',
     '2024-02-22',
     '2024-03-22',
     'Proforma - Annual checkup package',
     '2024-02-22 13:30:00',
     '2024-02-22 13:30:00',
     'proforma',
     0
 ),

 -- More paid invoices with different dates
 (
     'INV-2024-014',
     750.0000,
     'paid',
     '2024-02-14',
     '2024-03-15',
     'Monthly subscription - February 2024',
     '2024-02-14 10:00:00',
     '2024-02-18 16:30:00',
     'invoice',
     1
 ),
 (
     'INV-2024-015',
     125.7500,
     'paid',
     '2024-02-16',
     '2024-03-17',
     'Prescription refill - Antibiotics',
     '2024-02-16 14:45:00',
     '2024-02-17 09:15:00',
     'receipt',
     0
 );

 -- ==================== VERIFY INSERT ====================
  SELECT COUNT(*) FROM `gluttex`.`invoice`;
 SELECT * FROM `gluttex`.`invoice` ORDER BY `invoice_created_at` ;


 -- ==================== WALLET DUMMY DATA ====================

 INSERT INTO `gluttex`.`wallet` (
     `wallet_type`, 
     `wallet_currency`, 
     `wallet_balance`, 
     `wallet_status`, 
     `wallet_version`
 ) VALUES
 -- User wallets
 (
     'user',
     'DZD',
     15250.50000000,
     'active',
     0
 ),
 (
     'user',
     'USD',
     500.00000000,
     'active',
     0
 ),
 (
     'user',
     'EUR',
     350.25000000,
     'active',
     0
 ),
 (
     'user',
     'DZD',
     0.00000000,
     'inactive',
     0
 ),
 (
     'user',
     'DZD',
     8750.00000000,
     'active',
     0
 ),
 (
     'user',
     'USD',
     1200.00000000,
     'pending_verification',
     0
 ),

 -- Provider wallets
 (
     'provider',
     'DZD',
     250000.00000000,
     'active',
     0
 ),
 (
     'provider',
     'DZD',
     180000.75000000,
     'active',
     0
 ),
 (
     'provider',
     'USD',
     25000.00000000,
     'active',
     0
 ),
 (
     'provider',
     'DZD',
     0.00000000,
     'suspended',
     0
 ),

 -- Organization wallets
 (
     'organization',
     'DZD',
     1000000.00000000,
     'active',
     0
 ),
 (
     'organization',
     'EUR',
     50000.00000000,
     'active',
     0
 ),
 (
     'organization',
     'USD',
     75000.50000000,
     'pending_verification',
     0
 ),

 -- System wallets
 (
     'system',
     'DZD',
     5000000.00000000,
     'active',
     0
 ),
 (
     'system',
     'USD',
     100000.00000000,
     'active',
     0
 ),

 -- Virtual wallets (for promotions, rewards, etc.)
 (
     'virtual',
     'DZD',
     10000.00000000,
     'active',
     0
 ),
 (
     'virtual',
     'DZD',
     5000.00000000,
     'inactive',
     0
 ),

 -- Business wallets
 (
     'business',
     'DZD',
     350000.00000000,
     'active',
     0
 ),
 (
     'business',
     'USD',
     15000.00000000,
     'active',
     0
 ),
 (
     'business',
     'EUR',
     12000.75000000,
     'pending_verification',
     0
 ),

 -- Additional user wallets
 (
     'user',
     'DZD',
     3200.00000000,
     'active',
     0
 ),
 (
     'user',
     'DZD',
     450.50000000,
     'active',
     0
 ),
 (
     'user',
     'USD',
     100.00000000,
     'active',
     0
 ),
 (
     'user',
     'EUR',
     50.00000000,
     'active',
     0
 );

 -- ==================== VERIFY INSERT ====================
 SELECT COUNT(*) FROM `gluttex`.`wallet`;
 SELECT * FROM `gluttex`.`wallet` ORDER BY `id_wallet` ;
