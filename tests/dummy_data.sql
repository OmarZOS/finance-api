-- ============================================================================
-- Invoice + Wallet dummy data
--
-- Idempotent: safe to re-run. Every INSERT uses a natural key
-- (invoice_reference for invoices, a composite of type/currency/balance
-- for wallets) so a second execution updates rather than duplicates.
--
-- Cleanup: the DELETE at the top is commented out. Uncomment if you
-- want a hard reset before inserting.
-- ============================================================================

USE `verdelia`;

SET @OLD_FOREIGN_KEY_CHECKS = @@FOREIGN_KEY_CHECKS;
SET FOREIGN_KEY_CHECKS = 0;

-- ---------------------------------------------------------------------------
-- Optional hard reset. Uncomment to wipe and re-seed.
-- ---------------------------------------------------------------------------
-- DELETE FROM `invoice` WHERE `invoice_reference` LIKE 'DUMMY-%';
-- DELETE FROM `wallet`  WHERE `wallet_type` IN ('user','provider','organization','system','virtual','business')
--   AND `wallet_version` = 0 AND `wallet_balance` IN (
--     15250.50000000, 500.00000000, 350.25000000, 0.00000000, 8750.00000000,
--     1200.00000000, 250000.00000000, 180000.75000000, 25000.00000000,
--     1000000.00000000, 50000.00000000, 75000.50000000, 5000000.00000000,
--     100000.00000000, 10000.00000000, 5000.00000000, 350000.00000000,
--     15000.00000000, 12000.75000000, 3200.00000000, 450.50000000,
--     100.00000000, 50.00000000
--   );

-- ============================================================================
-- INVOICES
-- ============================================================================

INSERT INTO `invoice` (
    `invoice_reference`,
    `invoice_status`,
    `invoice_type`,
    `invoice_issue_date`,
    `invoice_due_date`,
    `invoice_notes`,
    `subtotal_amount`,
    `discount_amount`,
    `tax_amount`,
    `additional_amount`,
    `grand_total`,
    `created_at`,
    `updated_at`
) VALUES
-- ── Paid ─────────────────────────────────────────────────────────────
('DUMMY-INV-001', 'paid',    'invoice', '2024-01-15', '2024-02-14',
 'Monthly service subscription - January 2024',
 1000.00, 0.00, 190.00, 60.50, 1250.50,
 '2024-01-15 10:30:00', '2024-01-20 14:15:00'),

('DUMMY-INV-002', 'paid',    'receipt', '2024-01-20', '2024-02-19',
 'Consultation fee - Dr. Smith',
 350.75, 0.00, 0.00, 0.00, 350.75,
 '2024-01-20 09:00:00', '2024-01-25 16:45:00'),

('DUMMY-INV-003', 'paid',    'invoice', '2024-02-01', '2024-03-02',
 'Medical supplies - Bulk order',
 2340.00, 0.00, 440.00, 0.00, 2780.00,
 '2024-02-01 11:20:00', '2024-02-05 10:30:00'),

-- ── Unpaid ───────────────────────────────────────────────────────────
('DUMMY-INV-004', 'unpaid',  'receipt', '2024-02-10', '2024-03-11',
 'Pharmacy order 5678',
 567.80, 0.00, 0.00, 0.00, 567.80,
 '2024-02-10 14:00:00', '2024-02-10 14:00:00'),

('DUMMY-INV-005', 'unpaid',  'invoice', '2024-02-15', '2024-03-16',
 'Lab tests - Complete blood panel',
 1588.45, 0.00, 301.80, 0.00, 1890.25,
 '2024-02-15 08:30:00', '2024-02-15 08:30:00'),

-- ── Partially paid ───────────────────────────────────────────────────
('DUMMY-INV-006', 'partially_paid', 'invoice', '2024-01-25', '2024-02-24',
 'X-Ray and MRI services',
 361.34, 0.00, 68.66, 0.00, 430.00,
 '2024-01-25 13:45:00', '2024-02-01 09:15:00'),

('DUMMY-INV-007', 'partially_paid', 'invoice', '2024-02-05', '2024-03-06',
 'Surgical procedure - Appendix removal',
 1260.50, 0.00, 239.50, 0.00, 1500.00,
 '2024-02-05 15:30:00', '2024-02-15 11:00:00'),

-- ── Overdue ──────────────────────────────────────────────────────────
('DUMMY-INV-008', 'overdue', 'receipt', '2024-01-01', '2024-01-31',
 'Consultation - Follow-up visit',
 230.50, 0.00, 0.00, 0.00, 230.50,
 '2024-01-01 10:00:00', '2024-01-01 10:00:00'),

('DUMMY-INV-009', 'overdue', 'invoice', '2024-01-10', '2024-02-09',
 'Dental cleaning and X-rays',
 794.12, 0.00, 150.88, 0.00, 945.00,
 '2024-01-10 11:15:00', '2024-01-10 11:15:00'),

-- ── Canceled ─────────────────────────────────────────────────────────
('DUMMY-INV-010', 'canceled', 'invoice', '2024-01-30', '2024-02-29',
 'Canceled order - Patient requested cancellation',
 567.48, 0.00, 107.82, 0.00, 675.30,
 '2024-01-30 09:45:00', '2024-02-01 08:00:00'),

('DUMMY-INV-011', 'canceled', 'proforma', '2024-02-08', '2024-03-09',
 'Specialist consultation - Cancelled',
 1200.00, 0.00, 0.00, 0.00, 1200.00,
 '2024-02-08 16:20:00', '2024-02-10 12:00:00'),

-- ── Refunded ─────────────────────────────────────────────────────────
('DUMMY-INV-012', 'refunded', 'receipt', '2024-01-18', '2024-02-17',
 'Refund for duplicate payment',
 890.00, 0.00, 0.00, 0.00, 890.00,
 '2024-01-18 10:30:00', '2024-01-25 15:30:00'),

('DUMMY-INV-013', 'refunded', 'invoice', '2024-02-12', '2024-03-13',
 'Refund - Cancelled surgery',
 2151.89, 0.00, 408.86, 0.00, 2560.75,
 '2024-02-12 09:00:00', '2024-02-20 14:45:00'),

-- ── Proforma ─────────────────────────────────────────────────────────
('DUMMY-INV-PRO-001', 'unpaid', 'proforma', '2024-02-20', '2024-03-20',
 'Proforma for upcoming surgery',
 2521.01, 0.00, 478.99, 0.00, 3000.00,
 '2024-02-20 08:00:00', '2024-02-20 08:00:00'),

('DUMMY-INV-PRO-002', 'unpaid', 'proforma', '2024-02-22', '2024-03-22',
 'Proforma - Annual checkup package',
 450.50, 0.00, 0.00, 0.00, 450.50,
 '2024-02-22 13:30:00', '2024-02-22 13:30:00'),

-- ── More paid, later dates ───────────────────────────────────────────
('DUMMY-INV-014', 'paid', 'invoice', '2024-02-14', '2024-03-15',
 'Monthly subscription - February 2024',
 630.25, 0.00, 119.75, 0.00, 750.00,
 '2024-02-14 10:00:00', '2024-02-18 16:30:00'),

('DUMMY-INV-015', 'paid', 'receipt', '2024-02-16', '2024-03-17',
 'Prescription refill - Antibiotics',
 125.75, 0.00, 0.00, 0.00, 125.75,
 '2024-02-16 14:45:00', '2024-02-17 09:15:00')

AS new
ON DUPLICATE KEY UPDATE
    `invoice_status`     = new.`invoice_status`,
    `invoice_type`       = new.`invoice_type`,
    `invoice_issue_date` = new.`invoice_issue_date`,
    `invoice_due_date`   = new.`invoice_due_date`,
    `invoice_notes`      = new.`invoice_notes`,
    `subtotal_amount`    = new.`subtotal_amount`,
    `discount_amount`    = new.`discount_amount`,
    `tax_amount`         = new.`tax_amount`,
    `additional_amount`  = new.`additional_amount`,
    `grand_total`        = new.`grand_total`,
    `updated_at`         = new.`updated_at`;

-- ============================================================================
-- WALLETS
-- ============================================================================

INSERT INTO `wallet` (
    `wallet_type`,
    `wallet_currency`,
    `wallet_balance`,
    `wallet_status`,
    `wallet_version`
) VALUES
-- User wallets
('user',         'DZD',   15250.50000000, 'active',               0),
('user',         'USD',     500.00000000, 'active',               0),
('user',         'EUR',     350.25000000, 'active',               0),
('user',         'DZD',       0.00000000, 'inactive',             0),
('user',         'DZD',    8750.00000000, 'active',               0),
('user',         'USD',    1200.00000000, 'pending_verification', 0),

-- Provider wallets
('provider',     'DZD',  250000.00000000, 'active',               0),
('provider',     'DZD',  180000.75000000, 'active',               0),
('provider',     'USD',   25000.00000000, 'active',               0),
('provider',     'DZD',       0.00000000, 'suspended',            0),

-- Organization wallets
('organization', 'DZD', 1000000.00000000, 'active',               0),
('organization', 'EUR',   50000.00000000, 'active',               0),
('organization', 'USD',   75000.50000000, 'pending_verification', 0),

-- System wallets
('system',       'DZD', 5000000.00000000, 'active',               0),
('system',       'USD',  100000.00000000, 'active',               0),

-- Virtual wallets
('virtual',      'DZD',   10000.00000000, 'active',               0),
('virtual',      'DZD',    5000.00000000, 'inactive',             0),

-- Business wallets
('business',     'DZD',  350000.00000000, 'active',               0),
('business',     'USD',   15000.00000000, 'active',               0),
('business',     'EUR',   12000.75000000, 'pending_verification', 0),

-- Additional user wallets
('user',         'DZD',    3200.00000000, 'active',               0),
('user',         'DZD',     450.50000000, 'active',               0),
('user',         'USD',     100.00000000, 'active',               0),
('user',         'EUR',      50.00000000, 'active',               0);

-- ============================================================================
-- VERIFY
-- ============================================================================

SELECT 'invoices' AS entity, COUNT(*) AS rows_inserted
FROM `invoice`
WHERE `invoice_reference` LIKE 'DUMMY-%'

UNION ALL

SELECT 'wallets' AS entity, COUNT(*) AS rows_inserted
FROM `wallet`
WHERE `wallet_status` IN ('active', 'inactive', 'pending_verification', 'suspended');

SET FOREIGN_KEY_CHECKS = @OLD_FOREIGN_KEY_CHECKS;