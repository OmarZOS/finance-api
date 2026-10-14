# lib/models/finance_models.py
#
# Finance-only slice of the schema. Columns and tables mirror the full
# schema in `persistent_models.py`. Relationships to classes that are not
# part of the finance slice have been removed so this file can be imported
# standalone without pulling in the rest of the model tree.
#
# Changelog (this revision):
#   * Invoice rewritten for the current schema: `invoice_reference` +
#     `subtotal_amount` / `tax_amount` / `discount_amount` /
#     `additional_amount` / `grand_total` replace the old
#     `invoice_reference` / `grand_total` / `invoice_tax_applied`.
#   * Plan widened to include `semestrial` and `lifetime` billing cycles
#     and the `plan_naming_id` FK.
#   * ProviderOrganisation: added `user_id`, `verified_organisation`.
#   * DeliveryBroker: added `verified_delivery_broker`.
#   * AppUser: restored `app_user_person_id`, `app_user_subscription_id`,
#     `verified_app_user`.
#   * ProductProvider: restored details/location FKs.
#   * Cart: added `client_person_id`, `subtotal`, `taxable_amount`,
#     `discount_amount`.
#   * Product / ProvidedService: added `vat_rate`.
#   * ServicePackageItem, ServiceResourceRequirement,
#     ServiceStaffRequirement: fields renamed to canonical short names.
#   * Removed every relationship whose target class isn't declared here.

from sqlalchemy import (
    BigInteger,
    Column,
    DECIMAL,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKeyConstraint,
    Index,
    Integer,
    JSON,
    String,
    TIMESTAMP,
    Text,
    text,
)
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


# ============================================================================
# PLACED ORDER
# ============================================================================

class PlacedOrder(Base):
    __tablename__ = 'placed_order'
    __table_args__ = (
        ForeignKeyConstraint(
            ['discount_id'], ['discount.id_discount'], name='fk_placed_order_4'
        ),
        ForeignKeyConstraint(
            ['invoice_id'], ['invoice.invoice_id'], name='fk_placed_order_3'
        ),
        ForeignKeyConstraint(
            ['ordering_user_id'], ['app_user.id_app_user'],
            ondelete='RESTRICT', onupdate='RESTRICT', name='fk_placed_order_1',
        ),
        Index('fk_placed_order_1_idx', 'ordering_user_id'),
        Index('fk_placed_order_3_idx', 'invoice_id'),
        Index('fk_placed_order_4_idx', 'discount_id'),
    )

    id_placed_order = Column(Integer, primary_key=True)
    order_location_id = Column(Integer)
    ordering_user_id = Column(Integer)
    discount_amount = Column(DECIMAL(12, 2))
    subtotal = Column(DECIMAL(12, 2))
    order_state = Column(
        Enum('PENDING', 'PROCESSING', 'SHIPPED', 'DELIVERED', 'CANCELLED', 'REFUNDED'),
        server_default=text("'PENDING'"),
    )
    created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    updated_at = Column(
        TIMESTAMP,
        server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'),
    )
    invoice_id = Column(Integer)
    discount_id = Column(Integer)

    discount = relationship('Discount', back_populates='placed_order')
    invoice = relationship('Invoice', back_populates='placed_order')
    ordering_user = relationship('AppUser', back_populates='placed_order')
    ordered_item = relationship('OrderedItem', back_populates='order')


# ============================================================================
# INVOICE
# ============================================================================

class Invoice(Base):
    __tablename__ = 'invoice'
    __table_args__ = (
        Index('idx_invoice_status', 'invoice_status'),
    )

    invoice_id = Column(Integer, primary_key=True)
    invoice_reference = Column(String(100))
    invoice_status = Column(
        Enum('unpaid', 'paid', 'canceled', 'partially_paid', 'overdue', 'refunded'),
        server_default=text("'unpaid'"),
        comment='unpaid, paid, canceled',
    )
    invoice_issue_date = Column(Date)
    invoice_due_date = Column(Date)
    invoice_notes = Column(Text)
    created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    updated_at = Column(
        TIMESTAMP,
        server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'),
    )
    invoice_type = Column(
        Enum('receipt', 'invoice', 'proforma'),
        server_default=text("'receipt'"),
    )
    tax_amount = Column(DECIMAL(12, 2))
    grand_total = Column(DECIMAL(12, 2))
    discount_amount = Column(DECIMAL(12, 2))
    additional_amount = Column(DECIMAL(12, 2))
    subtotal_amount = Column(DECIMAL(12, 2))

    payment = relationship('Payment', back_populates='payment_invoice')
    placed_order = relationship('PlacedOrder', back_populates='invoice')
    additional_fee = relationship('AdditionalFee', back_populates='invoice')
    cart = relationship('Cart', back_populates='invoice')


# ============================================================================
# PLAN
# ============================================================================

class Plan(Base):
    __tablename__ = 'plan'

    id_plan = Column(Integer, primary_key=True)
    plan_name = Column(String(45))
    plan_price = Column(DECIMAL(10, 2))
    billing_cycle = Column(
        Enum('monthly', 'semestrial', 'yearly', 'lifetime'),
        server_default=text("'monthly'"),
    )
    plan_type = Column(
        Enum('individual', 'organization'),
        server_default=text("'individual'"),
    )
    plan_created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    plan_updated_at = Column(
        TIMESTAMP,
        server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'),
    )
    plan_naming_id = Column(Integer)

    subscription = relationship('Subscription', back_populates='subscription_plan')


# ============================================================================
# PROVIDER ORGANISATION
# ============================================================================

class ProviderOrganisation(Base):
    __tablename__ = 'provider_organisation'
    __table_args__ = (
        ForeignKeyConstraint(
            ['provider_organisation_wallet_id'], ['wallet.id_wallet'],
            name='fk_provider_organisation_1',
        ),
        ForeignKeyConstraint(
            ['user_id'], ['app_user.id_app_user'],
            name='fk_provider_organisation_app_user1',
        ),
        Index('fk_provider_organisation_1_idx', 'provider_organisation_wallet_id'),
        Index('fk_provider_organisation_app_user1_idx', 'user_id'),
    )

    id_provider_organisation = Column(Integer, primary_key=True)
    naming_id = Column(Integer)
    provider_organisation_wallet_id = Column(Integer)
    provider_organisation_name = Column(String(255))
    provider_organisation_icon_url = Column(String(255))
    provider_organisation_description = Column(String(255))
    user_id = Column(Integer)
    verified_organisation = Column(TINYINT)

    provider_organisation_wallet = relationship(
        'Wallet', back_populates='provider_organisation'
    )
    user = relationship('AppUser', back_populates='provider_organisation')
    product_provider = relationship(
        'ProductProvider', back_populates='product_provider_org'
    )


# ============================================================================
# DELIVERY BROKER
# ============================================================================

class DeliveryBroker(Base):
    __tablename__ = 'delivery_broker'
    __table_args__ = (
        ForeignKeyConstraint(
            ['delivery_broker_wallet_id'], ['wallet.id_wallet'],
            name='fk_delivery_broker_1',
        ),
        Index('fk_delivery_broker_1_idx', 'delivery_broker_wallet_id'),
    )

    id_delivery_broker = Column(Integer, primary_key=True)
    delivery_broker_name = Column(String(255))
    delivery_broker_label = Column(String(255))
    delivery_broker_logo_url = Column(String(255))
    delivery_broker_image_url = Column(String(255))
    delivery_broker_wallet_id = Column(Integer)
    delivery_broker_price_matrix = Column(Text)
    verified_delivery_broker = Column(TINYINT)

    delivery_broker_wallet = relationship('Wallet', back_populates='delivery_broker')


# ============================================================================
# LEDGER ENTRY
# ============================================================================

class LedgerEntry(Base):
    __tablename__ = 'ledger_entry'
    __table_args__ = (
        ForeignKeyConstraint(
            ['money_transaction_id'], ['money_transaction.id_money_transaction'],
            name='fk_ledger_entry_money_transaction1',
        ),
        ForeignKeyConstraint(
            ['wallet_id'], ['wallet.id_wallet'],
            name='fk_ledger_entry_wallet1',
        ),
        Index('fk_ledger_entry_money_transaction1_idx', 'money_transaction_id'),
        Index('fk_ledger_entry_wallet1_idx', 'wallet_id'),
    )

    id_ledger_entry = Column(Integer, primary_key=True)
    wallet_id = Column(Integer, nullable=False)
    money_transaction_id = Column(Integer, nullable=False)
    ledger_entry_type = Column(Enum('CREDIT', 'DEBIT'))
    ledger_entry_amount = Column(DECIMAL(20, 8))

    money_transaction = relationship(
        'MoneyTransaction', back_populates='ledger_entry'
    )
    wallet = relationship('Wallet', back_populates='ledger_entry')


# ============================================================================
# WALLET
# ============================================================================

class Wallet(Base):
    __tablename__ = 'wallet'

    id_wallet = Column(Integer, primary_key=True)
    wallet_type = Column(
        Enum('user', 'provider', 'organization', 'system', 'virtual', 'business'),
        server_default=text("'user'"),
    )
    wallet_currency = Column(
        Enum('DZD', 'USD', 'EUR'), server_default=text("'DZD'")
    )
    wallet_balance = Column(DECIMAL(20, 8))
    wallet_status = Column(
        Enum('active', 'inactive', 'suspended', 'closed', 'pending_verification'),
        server_default=text("'pending_verification'"),
    )
    wallet_version = Column(Integer, server_default=text("'0'"))

    delivery_broker = relationship(
        'DeliveryBroker', back_populates='delivery_broker_wallet'
    )
    provider_organisation = relationship(
        'ProviderOrganisation', back_populates='provider_organisation_wallet'
    )
    money_transaction = relationship(
        'MoneyTransaction',
        foreign_keys='[MoneyTransaction.money_transaction_wallet_destination_id]',
        back_populates='money_transaction_wallet_destination',
    )
    money_transaction_ = relationship(
        'MoneyTransaction',
        foreign_keys='[MoneyTransaction.money_transaction_wallet_source_id]',
        back_populates='money_transaction_wallet_source',
    )
    ledger_entry = relationship('LedgerEntry', back_populates='wallet')
    app_user = relationship('AppUser', back_populates='app_user_wallet')
    product_provider = relationship(
        'ProductProvider', back_populates='product_provider_wallet'
    )


# ============================================================================
# PAYMENT
# ============================================================================

class Payment(Base):
    __tablename__ = 'payment'
    __table_args__ = (
        ForeignKeyConstraint(
            ['payment_invoice_id'], ['invoice.invoice_id'],
            ondelete='RESTRICT', onupdate='CASCADE', name='payment_ibfk_1',
        ),
        Index('idx_invoice', 'payment_invoice_id'),
        Index('idx_status', 'payment_status'),
    )

    payment_id = Column(Integer, primary_key=True)
    payment_invoice_id = Column(Integer)
    payment_amount = Column(DECIMAL(15, 4))
    payment_method = Column(
        Enum(
            'cash', 'card', 'bank_transfer', 'mobile_money',
            'crypto', 'deposit', 'wallet', 'check',
        ),
        server_default=text("'cash'"),
        comment='cash, card, bank, mobile',
    )
    payment_status = Column(
        Enum('pending', 'processing', 'completed', 'partial', 'failed', 'cancelled'),
        server_default=text("'pending'"),
    )
    payment_reference = Column(String(255), comment='Bank or transaction reference')
    payment_notes = Column(Text)
    payment_created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    payment_updated_at = Column(
        TIMESTAMP,
        server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'),
    )
    payment_type = Column(Enum('deposit', 'payment', 'refund'))

    subscription = relationship('Subscription', back_populates='subscription_payment')
    payment_invoice = relationship('Invoice', back_populates='payment')
    money_transaction = relationship('MoneyTransaction', back_populates='payment')


# ============================================================================
# MONEY TRANSACTION
# ============================================================================

class MoneyTransaction(Base):
    __tablename__ = 'money_transaction'
    __table_args__ = (
        ForeignKeyConstraint(
            ['money_transaction_for_payment'], ['payment.payment_id'],
            name='fk_money_transaction_3',
        ),
        ForeignKeyConstraint(
            ['money_transaction_wallet_destination_id'], ['wallet.id_wallet'],
            name='fk_money_transaction_2',
        ),
        ForeignKeyConstraint(
            ['money_transaction_wallet_source_id'], ['wallet.id_wallet'],
            name='fk_money_transaction_1',
        ),
        Index('fk_money_transaction_1_idx', 'money_transaction_wallet_source_id'),
        Index('fk_money_transaction_2_idx', 'money_transaction_wallet_destination_id'),
        Index('fk_money_transaction_3_idx', 'money_transaction_for_payment'),
    )

    id_money_transaction = Column(Integer, primary_key=True)
    money_transaction_document_url = Column(String(255))
    money_transaction_amount = Column(
        DECIMAL(20, 8), server_default=text("'0.00000000'")
    )
    money_transaction_reference = Column(String(255))
    money_transaction_creation = Column(
        TIMESTAMP, server_default=text('CURRENT_TIMESTAMP')
    )
    money_transaction_last_updated = Column(
        TIMESTAMP,
        server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'),
    )
    money_transaction_wallet_source_id = Column(Integer)
    money_transaction_wallet_destination_id = Column(Integer)
    money_transaction_status = Column(
        Enum('pending', 'processing', 'completed', 'failed', 'cancelled', 'refunded', 'reversed'),
        server_default=text("'pending'"),
    )
    money_transaction_for_payment = Column(Integer)

    payment = relationship('Payment', back_populates='money_transaction')
    money_transaction_wallet_destination = relationship(
        'Wallet',
        foreign_keys=[money_transaction_wallet_destination_id],
        back_populates='money_transaction',
    )
    money_transaction_wallet_source = relationship(
        'Wallet',
        foreign_keys=[money_transaction_wallet_source_id],
        back_populates='money_transaction_',
    )
    ledger_entry = relationship('LedgerEntry', back_populates='money_transaction')


# ============================================================================
# SUBSCRIPTION
# ============================================================================

class Subscription(Base):
    __tablename__ = 'subscription'
    __table_args__ = (
        ForeignKeyConstraint(
            ['subscription_payment_id'], ['payment.payment_id'],
            name='fk_subscription_2',
        ),
        ForeignKeyConstraint(
            ['subscription_plan_id'], ['plan.id_plan'], name='fk_subscription_1'
        ),
        Index('fk_subscription_1_idx', 'subscription_plan_id'),
        Index('fk_subscription_2_idx', 'subscription_payment_id'),
    )

    id_subscription = Column(Integer, primary_key=True)
    subscription_plan_id = Column(Integer)
    subscription_payment_id = Column(Integer)
    subscription_created_at = Column(
        TIMESTAMP, server_default=text('CURRENT_TIMESTAMP')
    )
    subscription_updated_at = Column(
        TIMESTAMP,
        server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'),
    )
    subscription_expiry = Column(TIMESTAMP)
    subscription_quota = Column(Integer, server_default=text("'0'"))
    current_period_start = Column(Date)
    current_period_end = Column(Date)

    app_user = relationship('AppUser', back_populates='app_user_subscription')
    subscription_payment = relationship('Payment', back_populates='subscription')
    subscription_plan = relationship('Plan', back_populates='subscription')
    subscription_usage = relationship(
        'SubscriptionUsage', back_populates='subscription'
    )


# ============================================================================
# SUBSCRIPTION USAGE
# ============================================================================

class SubscriptionUsage(Base):
    __tablename__ = 'subscription_usage'
    __table_args__ = (
        ForeignKeyConstraint(
            ['subscription_id'], ['subscription.id_subscription'],
            name='fk_subscription_usage_1',
        ),
        Index('fk_subscription_usage_1_idx', 'subscription_id'),
    )

    id_subscription_usage = Column(Integer, primary_key=True)
    subscription_id = Column(Integer)
    period_start = Column(Date)
    period_end = Column(Date)
    ai_credits_used = Column(Integer)
    ai_product_searches = Column(Integer)
    ai_auto_fills = Column(Integer)
    products_created = Column(Integer)
    created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    updated_at = Column(
        TIMESTAMP,
        server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'),
    )

    subscription = relationship('Subscription', back_populates='subscription_usage')


# ============================================================================
# APP USER
# ============================================================================

class AppUser(Base):
    __tablename__ = 'app_user'
    __table_args__ = (
        ForeignKeyConstraint(
            ['app_user_subscription_id'], ['subscription.id_subscription'],
            ondelete='RESTRICT', onupdate='RESTRICT', name='fk_app_user_2',
        ),
        ForeignKeyConstraint(
            ['app_user_wallet_id'], ['wallet.id_wallet'], name='fk_app_user_4'
        ),
        Index('fk_app_user_2_idx', 'app_user_subscription_id'),
        Index('fk_app_user_4_idx', 'app_user_wallet_id'),
    )

    id_app_user = Column(Integer, primary_key=True)
    app_user_name = Column(String(100))
    app_user_password = Column(String(256))
    app_user_person_id = Column(Integer)
    app_user_type = Column(
        Enum('admin', 'provider', 'customer', 'patient', 'guest'),
        server_default=text("'customer'"),
    )
    app_user_preferences = Column(Text)
    app_user_image_url = Column(String(255))
    app_user_last_active = Column(TIMESTAMP)
    app_user_last_updated = Column(
        TIMESTAMP,
        server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'),
    )
    app_user_creation = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    app_user_subscription_id = Column(Integer)
    app_user_email = Column(String(255))
    app_user_wallet_id = Column(Integer)
    app_user_login_option = Column(Enum('google', 'verdelia'))
    verified_app_user = Column(TINYINT)

    app_user_subscription = relationship('Subscription', back_populates='app_user')
    app_user_wallet = relationship('Wallet', back_populates='app_user')
    placed_order = relationship('PlacedOrder', back_populates='ordering_user')
    product_provider = relationship(
        'ProductProvider', back_populates='product_provider_user'
    )
    additional_fee = relationship('AdditionalFee', back_populates='user')
    cart = relationship(
        'Cart', foreign_keys='[Cart.client_user_id]', back_populates='client_user'
    )
    cart_ = relationship(
        'Cart', foreign_keys='[Cart.selling_user_id]', back_populates='selling_user'
    )
    provider_organisation = relationship(
        'ProviderOrganisation', back_populates='user'
    )
    product = relationship('Product', back_populates='user')


# ============================================================================
# PRODUCT PROVIDER
# ============================================================================

class ProductProvider(Base):
    __tablename__ = 'product_provider'
    __table_args__ = (
        ForeignKeyConstraint(
            ['product_provider_details_id'], ['provider_details.idprovider_details_id'],
            ondelete='RESTRICT', onupdate='RESTRICT', name='fk_product_provider_3',
        ),
        ForeignKeyConstraint(
            ['product_provider_org_id'], ['provider_organisation.id_provider_organisation'],
            ondelete='RESTRICT', onupdate='RESTRICT', name='fk_product_provider_2',
        ),
        ForeignKeyConstraint(
            ['product_provider_type_id'], ['product_provider_type.id_product_provider_type'],
            ondelete='RESTRICT', onupdate='RESTRICT', name='fk_product_provider_1',
        ),
        ForeignKeyConstraint(
            ['product_provider_user_id'], ['app_user.id_app_user'],
            name='fk_product_provider_5',
        ),
        ForeignKeyConstraint(
            ['product_provider_wallet_id'], ['wallet.id_wallet'],
            name='fk_product_provider_6',
        ),
        Index('fk_product_provider_1_idx', 'product_provider_type_id'),
        Index('fk_product_provider_2_idx', 'product_provider_org_id'),
        Index('fk_product_provider_3_idx', 'product_provider_details_id'),
        Index('fk_product_provider_5_idx', 'product_provider_user_id'),
        Index('fk_product_provider_6_idx', 'product_provider_wallet_id'),
    )

    id_product_provider = Column(Integer, primary_key=True)
    product_provider_details_id = Column(Integer)
    product_provider_type_id = Column(Integer)
    product_provider_location_id = Column(Integer)
    product_provider_org_id = Column(Integer)
    product_provider_user_id = Column(Integer)
    product_provider_wallet_id = Column(Integer)
    verified_provider = Column(TINYINT)

    product_provider_org = relationship(
        'ProviderOrganisation', back_populates='product_provider'
    )
    product_provider_user = relationship(
        'AppUser', back_populates='product_provider'
    )
    product_provider_wallet = relationship(
        'Wallet', back_populates='product_provider'
    )
    additional_fee = relationship('AdditionalFee', back_populates='provider')
    cart = relationship('Cart', back_populates='provider')
    product = relationship('Product', back_populates='provider')
    provided_service = relationship('ProvidedService', back_populates='provider')


# ============================================================================
# ADDITIONAL FEE
# ============================================================================

class AdditionalFee(Base):
    __tablename__ = 'additional_fee'
    __table_args__ = (
        ForeignKeyConstraint(
            ['invoice_id'], ['invoice.invoice_id'], name='fk_additional_fee_3'
        ),
        ForeignKeyConstraint(
            ['provider_id'], ['product_provider.id_product_provider'],
            name='fk_additional_fee_2',
        ),
        ForeignKeyConstraint(
            ['user_id'], ['app_user.id_app_user'], name='fk_additional_fee_1'
        ),
        Index('fk_additional_fee_1_idx', 'user_id'),
        Index('fk_additional_fee_2_idx', 'provider_id'),
        Index('fk_additional_fee_3_idx', 'invoice_id'),
    )

    id_additional_fee = Column(Integer, primary_key=True)
    name = Column(String(255))
    amount = Column(DECIMAL(15, 2))
    description = Column(Text)
    created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    updated_at = Column(
        TIMESTAMP,
        server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'),
    )
    document_url = Column(String(255))
    user_id = Column(Integer)
    provider_id = Column(Integer)
    invoice_id = Column(Integer)

    invoice = relationship('Invoice', back_populates='additional_fee')
    provider = relationship('ProductProvider', back_populates='additional_fee')
    user = relationship('AppUser', back_populates='additional_fee')


# ============================================================================
# CART
# ============================================================================

class Cart(Base):
    __tablename__ = 'cart'
    __table_args__ = (
        ForeignKeyConstraint(
            ['client_user_id'], ['app_user.id_app_user'], name='fk_cart_2'
        ),
        ForeignKeyConstraint(
            ['discount_id'], ['discount.id_discount'], name='fk_cart_4'
        ),
        ForeignKeyConstraint(
            ['invoice_id'], ['invoice.invoice_id'], name='fk_cart_5'
        ),
        ForeignKeyConstraint(
            ['provider_id'], ['product_provider.id_product_provider'],
            ondelete='RESTRICT', onupdate='CASCADE', name='cart_ibfk_1',
        ),
        ForeignKeyConstraint(
            ['selling_user_id'], ['app_user.id_app_user'], name='fk_cart_1'
        ),
        Index('fk_cart_2', 'client_user_id'),
        Index('fk_cart_4_idx', 'discount_id'),
        Index('fk_cart_5_idx', 'invoice_id'),
        Index('idx_cart_provider', 'provider_id'),
        Index('idx_cart_status', 'cart_status'),
        Index('idx_cart_user', 'selling_user_id'),
    )

    cart_id = Column(Integer, primary_key=True)
    provider_id = Column(Integer, comment='Provider owning the cart')
    cart_status = Column(
        Enum('open', 'pending', 'completed', 'canceled', 'partial', 'checkout', 'abandoned'),
        server_default=text("'open'"),
        comment='open, pending, completed, canceled',
    )
    notes = Column(Text)
    created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    updated_at = Column(
        TIMESTAMP,
        server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'),
    )
    cart_due_date = Column(Date)
    selling_user_id = Column(Integer, comment='Customer / patient / client id')
    client_user_id = Column(Integer)
    client_person_id = Column(Integer)
    invoice_id = Column(Integer)
    discount_id = Column(Integer)
    subtotal = Column(DECIMAL(15, 2))
    taxable_amount = Column(DECIMAL(15, 2))
    discount_amount = Column(DECIMAL(15, 2))

    client_user = relationship(
        'AppUser', foreign_keys=[client_user_id], back_populates='cart'
    )
    discount = relationship('Discount', back_populates='cart')
    invoice = relationship('Invoice', back_populates='cart')
    provider = relationship('ProductProvider', back_populates='cart')
    selling_user = relationship(
        'AppUser', foreign_keys=[selling_user_id], back_populates='cart_'
    )
    ordered_item = relationship('OrderedItem', back_populates='cart')
    ordered_service = relationship('OrderedService', back_populates='cart')


# ============================================================================
# DISCOUNT
# ============================================================================

class Discount(Base):
    __tablename__ = 'discount'
    __table_args__ = (
        ForeignKeyConstraint(
            ['discount_user_id'], ['app_user.id_app_user'], name='fk_discount_1'
        ),
        Index('fk_discount_1_idx', 'discount_user_id'),
    )

    id_discount = Column(Integer, primary_key=True)
    discount_type = Column(
        Enum('percentage', 'fixed'), server_default=text("'fixed'")
    )
    discount_value = Column(
        DECIMAL(20, 2), server_default=text("'0.00'")
    )
    discount_code = Column(String(45))
    discount_state = Column(
        Enum('AVAILABLE', 'USED', 'OBSOLETE'),
        server_default=text("'AVAILABLE'"),
    )
    created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    updated_at = Column(
        TIMESTAMP,
        server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'),
    )
    discount_user_id = Column(Integer)

    placed_order = relationship('PlacedOrder', back_populates='discount')
    cart = relationship('Cart', back_populates='discount')
    ordered_item = relationship('OrderedItem', back_populates='discount')
    ordered_service = relationship('OrderedService', back_populates='discount')


# ============================================================================
# PRODUCT
# ============================================================================

class Product(Base):
    __tablename__ = 'product'
    __table_args__ = (
        ForeignKeyConstraint(
            ['provider_id'], ['product_provider.id_product_provider'],
            ondelete='RESTRICT', onupdate='RESTRICT', name='fk_product_1',
        ),
        ForeignKeyConstraint(
            ['user_id'], ['app_user.id_app_user'],
            ondelete='RESTRICT', onupdate='RESTRICT', name='fk_product_3',
        ),
        Index('fk_product_1_idx', 'provider_id'),
        Index('fk_product_3_idx', 'user_id'),
    )

    id_product = Column(Integer, primary_key=True)
    generic_name = Column(String(45))
    brand = Column(String(45))
    provider_id = Column(Integer)
    category_id = Column(Integer)
    barcode = Column(String(45))
    last_updated = Column(
        DateTime, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')
    )
    created = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    product_description = Column(String(300))
    unit_price = Column(DECIMAL(12, 2), server_default=text("'0.00'"))
    base_price = Column(DECIMAL(12, 2), server_default=text("'0.00'"))
    available_quantity = Column(BigInteger, server_default=text("'0'"))
    reserved_quantity = Column(Integer, server_default=text("'0'"))
    quantifier = Column(String(45))
    user_id = Column(Integer)
    origin_id = Column(Integer)
    visibility = Column(
        Enum('VISIBLE', 'HIDDEN', 'DELETED'), server_default=text("'VISIBLE'")
    )
    vat_rate = Column(DECIMAL(5, 2), server_default=text("'0.00'"))

    provider = relationship('ProductProvider', back_populates='product')
    user = relationship('AppUser', back_populates='product')
    ordered_item = relationship('OrderedItem', back_populates='product')
    service_resource_requirement = relationship(
        'ServiceResourceRequirement', back_populates='product'
    )
    product_consumption = relationship(
        'ProductConsumption', back_populates='consumed_product'
    )


# ============================================================================
# PROVIDED SERVICE
# ============================================================================

class ProvidedService(Base):
    __tablename__ = 'provided_service'
    __table_args__ = (
        ForeignKeyConstraint(
            ['provider_id'], ['product_provider.id_product_provider'],
            ondelete='RESTRICT', onupdate='CASCADE', name='provided_service_ibfk_2',
        ),
        Index('idx_provided_service_active', 'provided_service_is_active', 'deleted_at'),
        Index('idx_provided_service_created_at', 'created_at'),
        Index('idx_provided_service_name', 'provided_service_name'),
        Index('idx_provided_service_price_range', 'base_price', 'unit_price'),
        Index('idx_provided_service_provider', 'provider_id'),
    )

    idprovided_service = Column(Integer, primary_key=True)
    provided_service_name = Column(String(255))
    provided_service_description = Column(Text)
    category_id = Column(Integer)
    provider_id = Column(
        Integer,
        comment='References i_product_provider.id_product_provider',
    )
    base_price = Column(DECIMAL(12, 2))
    unit_price = Column(DECIMAL(12, 2))
    provided_service_actual_duration = Column(DECIMAL(10, 2))
    provided_service_is_active = Column(TINYINT(1), server_default=text("'1'"))
    provided_service_pricing_config = Column(JSON)
    created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    updated_at = Column(
        TIMESTAMP,
        server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'),
    )
    deleted_at = Column(TIMESTAMP)
    vat_rate = Column(DECIMAL(5, 2), server_default=text("'0.00'"))

    provider = relationship('ProductProvider', back_populates='provided_service')
    ordered_service = relationship('OrderedService', back_populates='service')
    service_resource_requirement = relationship(
        'ServiceResourceRequirement', back_populates='service'
    )
    service_staff_requirement = relationship(
        'ServiceStaffRequirement',
        back_populates='service_staff_requirement_service',
    )


# ============================================================================
# ORDERED ITEM
# ============================================================================

class OrderedItem(Base):
    __tablename__ = 'ordered_item'
    __table_args__ = (
        ForeignKeyConstraint(
            ['cart_id'], ['cart.cart_id'], name='fk_ordered_item_2'
        ),
        ForeignKeyConstraint(
            ['discount_id'], ['discount.id_discount'], name='fk_ordered_item_4'
        ),
        ForeignKeyConstraint(
            ['order_id'], ['placed_order.id_placed_order'],
            ondelete='RESTRICT', onupdate='RESTRICT', name='fk_ordered_item_3',
        ),
        ForeignKeyConstraint(
            ['product_id'], ['product.id_product'],
            ondelete='RESTRICT', onupdate='RESTRICT', name='fk_ordered_item_1',
        ),
        Index('fk_ordered_item_1_idx', 'product_id'),
        Index('fk_ordered_item_2_idx', 'cart_id'),
        Index('fk_ordered_item_3_idx', 'order_id'),
        Index('fk_ordered_item_4_idx', 'discount_id'),
    )

    id_ordered_item = Column(Integer, primary_key=True)
    ordered_quantity = Column(Integer, server_default=text("'0'"))
    reserved_quantity = Column(Integer, server_default=text("'0'"))
    vat_rate = Column(DECIMAL(5, 2))
    unit_price = Column(DECIMAL(12, 2))
    vat_amount = Column(DECIMAL(12, 2))
    discount_amount = Column(DECIMAL(12, 2))
    delivery_status = Column(
        Enum('pending', 'processing', 'shipped', 'delivered', 'cancelled', 'returned', 'partial'),
        server_default=text("'pending'"),
    )
    delivery_fee = Column(DECIMAL(12, 2), server_default=text("'0.00'"))
    updated_at = Column(
        TIMESTAMP,
        server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'),
    )
    created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    discount_id = Column(Integer)
    cart_id = Column(Integer)
    product_id = Column(Integer)
    order_id = Column(Integer)
    taxable_amount = Column(DECIMAL(12, 2))
    subtotal = Column(DECIMAL(12, 2))

    cart = relationship('Cart', back_populates='ordered_item')
    discount = relationship('Discount', back_populates='ordered_item')
    order = relationship('PlacedOrder', back_populates='ordered_item')
    product = relationship('Product', back_populates='ordered_item')


# ============================================================================
# ORDERED SERVICE
# ============================================================================

class OrderedService(Base):
    __tablename__ = 'ordered_service'
    __table_args__ = (
        ForeignKeyConstraint(
            ['cart_id'], ['cart.cart_id'],
            ondelete='CASCADE', onupdate='CASCADE', name='ordered_service_ibfk_1',
        ),
        ForeignKeyConstraint(
            ['discount_id'], ['discount.id_discount'], name='fk_ordered_service_1'
        ),
        ForeignKeyConstraint(
            ['service_id'], ['provided_service.idprovided_service'],
            ondelete='RESTRICT', onupdate='CASCADE', name='ordered_service_ibfk_2',
        ),
        Index('fk_ordered_service_1_idx', 'discount_id'),
        Index('idx_cart', 'cart_id'),
        Index('idx_service', 'service_id'),
    )

    ordered_service_id = Column(Integer, primary_key=True)
    ordered_service_notes = Column(Text)
    created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    updated_at = Column(
        TIMESTAMP,
        server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'),
    )
    scheduled_at = Column(TIMESTAMP)
    ordered_service_quantity = Column(Integer, server_default=text("'1'"))
    ordered_service_delivery_status = Column(
        Enum('pending', 'processing', 'scheduled', 'in_progress', 'completed', 'cancelled', 'no_show'),
        server_default=text("'pending'"),
    )
    discount_id = Column(Integer)
    cart_id = Column(Integer)
    service_id = Column(Integer, comment='References provided_service')
    vat_rate = Column(DECIMAL(5, 2), server_default=text("'0.00'"))
    discount_amount = Column(DECIMAL(12, 2))
    ordered_service_delivery_fee = Column(
        DECIMAL(12, 2), server_default=text("'0.00'")
    )
    unit_price = Column(DECIMAL(12, 2))
    subtotal = Column(DECIMAL(12, 2))
    taxable_amount = Column(DECIMAL(12, 2))

    cart = relationship('Cart', back_populates='ordered_service')
    discount = relationship('Discount', back_populates='ordered_service')
    service = relationship('ProvidedService', back_populates='ordered_service')
    product_consumption = relationship(
        'ProductConsumption', back_populates='consuming_service'
    )


# ============================================================================
# SERVICE RESOURCE REQUIREMENT
# ============================================================================

class ServiceResourceRequirement(Base):
    __tablename__ = 'service_resource_requirement'
    __table_args__ = (
        ForeignKeyConstraint(
            ['product_id'], ['product.id_product'],
            name='fk_service_resource_requirement_1',
        ),
        ForeignKeyConstraint(
            ['service_id'], ['provided_service.idprovided_service'],
            ondelete='CASCADE', onupdate='CASCADE',
            name='service_resource_requirement_ibfk_1',
        ),
        Index('fk_service_resource_requirement_1_idx', 'product_id'),
        Index('idx_resource_requirement_name', 'service_resource_requirement_name'),
        Index('idx_resource_requirement_service', 'service_id'),
        Index('idx_resource_requirement_type', 'service_resource_requirement_type'),
    )

    id_service_resource_requirement = Column(Integer, primary_key=True)
    service_id = Column(Integer)
    service_resource_requirement_name = Column(String(255))
    service_resource_requirement_type = Column(String(100))
    service_resource_requirement_quantity = Column(
        Integer, server_default=text("'1'")
    )
    service_resource_requirement_is_consumable = Column(
        TINYINT(1), server_default=text("'0'")
    )
    service_resource_requirement_notes = Column(Text)
    created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    unit_price = Column(DECIMAL(12, 2))
    updated_at = Column(
        TIMESTAMP,
        server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'),
    )
    product_id = Column(Integer)

    product = relationship('Product', back_populates='service_resource_requirement')
    service = relationship('ProvidedService', back_populates='service_resource_requirement')
    product_consumption = relationship(
        'ProductConsumption', back_populates='requirement'
    )


# ============================================================================
# SERVICE STAFF REQUIREMENT
# ============================================================================

class ServiceStaffRequirement(Base):
    __tablename__ = 'service_staff_requirement'
    __table_args__ = (
        ForeignKeyConstraint(
            ['service_staff_requirement_service_id'],
            ['provided_service.idprovided_service'],
            ondelete='CASCADE', onupdate='CASCADE',
            name='service_staff_requirement_ibfk_1',
        ),
        Index(
            'idx_service_staff_requirement_service',
            'service_staff_requirement_service_id',
        ),
    )

    id_service_staff_requirement = Column(Integer, primary_key=True)
    service_staff_requirement_service_id = Column(Integer)
    service_staff_requirement_role_id = Column(Integer)
    service_staff_requirement_min_count = Column(
        Integer, server_default=text("'1'")
    )
    service_staff_requirement_max_count = Column(Integer)
    service_staff_requirement_hourly_rate = Column(DECIMAL(15, 4))
    service_staff_requirement_allocated_hours = Column(DECIMAL(5, 2))
    service_staff_requirement_notes = Column(Text)
    service_staff_requirement_created_at = Column(
        TIMESTAMP, server_default=text('CURRENT_TIMESTAMP')
    )
    service_staff_requirement_updated_at = Column(
        TIMESTAMP,
        server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'),
    )

    service_staff_requirement_service = relationship(
        'ProvidedService', back_populates='service_staff_requirement'
    )


# ============================================================================
# PRODUCT CONSUMPTION
# ============================================================================

class ProductConsumption(Base):
    __tablename__ = 'product_consumption'
    __table_args__ = (
        ForeignKeyConstraint(
            ['consumed_product_id'], ['product.id_product'],
            name='fk_product_consumption_product1',
        ),
        ForeignKeyConstraint(
            ['consuming_service_id'], ['ordered_service.ordered_service_id'],
            name='fk_product_consumption_ordered_service1',
        ),
        ForeignKeyConstraint(
            ['requirement_id'], ['service_resource_requirement.id_service_resource_requirement'],
            name='fk_product_consumption_service_resource_requirement1',
        ),
        Index('fk_product_consumption_ordered_service1_idx', 'consuming_service_id'),
        Index('fk_product_consumption_product1_idx', 'consumed_product_id'),
        Index(
            'fk_product_consumption_service_resource_requirement1_idx',
            'requirement_id',
        ),
    )

    id_product_consumption = Column(Integer, primary_key=True)
    requirement_id = Column(Integer)
    consuming_service_id = Column(Integer)
    consumed_product_id = Column(Integer)
    product_reserved_quantity = Column(Integer)

    consumed_product = relationship(
        'Product', back_populates='product_consumption'
    )
    consuming_service = relationship(
        'OrderedService', back_populates='product_consumption'
    )
    requirement = relationship(
        'ServiceResourceRequirement', back_populates='product_consumption'
    )