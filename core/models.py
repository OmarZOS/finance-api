from sqlalchemy import Column, DECIMAL, Date, DateTime, Enum, Float, ForeignKeyConstraint, Index, Integer, JSON, String, TIMESTAMP, Text, text
from sqlalchemy.dialects.mysql import TINYINT

from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()



class PlacedOrder(Base):
    __tablename__ = 'placed_order'
    __table_args__ = (
        ForeignKeyConstraint(['ordering_user_id'], ['app_user.id_app_user'], ondelete='RESTRICT', onupdate='RESTRICT', name='fk_placed_order_1'),
        ForeignKeyConstraint(['placed_order_invoice'], ['invoice.invoice_id'], name='fk_placed_order_3'),
        Index('fk_placed_order_1_idx', 'ordering_user_id'),
        Index('fk_placed_order_3_idx', 'placed_order_invoice')
    )

    id_placed_order = Column(Integer, primary_key=True)
    order_discount = Column(Float(asdecimal=True))
    total_price = Column(Float(asdecimal=True))
    ordering_user_id = Column(Integer)
    placed_order_state = Column(Enum('PENDING', 'PROCESSING', 'SHIPPED', 'DELIVERED', 'CANCELLED', 'REFUNDED'), server_default=text("'PENDING'"))
    placed_order_last_mod = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))
    placed_order_receipt_ref = Column(Integer)
    placed_order_creation = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    placed_order_invoice = Column(Integer)

    ordering_user = relationship('AppUser', back_populates='placed_order')
    invoice = relationship('Invoice', back_populates='placed_order')
    ordered_item = relationship('OrderedItem', back_populates='placed_order')


class Invoice(Base):
    __tablename__ = 'invoice'
    __table_args__ = (
        Index('idx_invoice_status', 'invoice_status'),
    )

    invoice_id = Column(Integer, primary_key=True)
    invoice_number = Column(String(100))
    invoice_total_amount = Column(DECIMAL(15, 4))
    invoice_status = Column(Enum('unpaid', 'paid', 'canceled', 'partially_paid', 'overdue', 'refunded'), server_default=text("'unpaid'"), comment='unpaid, paid, canceled')
    invoice_issue_date = Column(Date)
    invoice_due_date = Column(Date)
    invoice_notes = Column(Text)
    invoice_created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    invoice_updated_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))
    invoice_type = Column(Enum('receipt', 'invoice', 'proforma'), server_default=text("'receipt'"))
    invoice_tax_applied = Column(TINYINT)

    payment = relationship('Payment', back_populates='payment_invoice')
    placed_order = relationship('PlacedOrder', back_populates='invoice')
    additional_fee = relationship('AdditionalFee', back_populates='invoice')
    cart = relationship('Cart', back_populates='invoice')



class Plan(Base):
    __tablename__ = 'plan'

    id_plan = Column(Integer, primary_key=True)
    plan_name = Column(String(45))
    plan_price = Column(DECIMAL(10, 2))
    billing_cycle = Column(Enum('monthly', 'yearly'), server_default=text("'monthly'"))
    plan_type = Column(Enum('individual', 'organization'), server_default=text("'individual'"))
    plan_created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    plan_updated_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))

    app_user = relationship('AppUser', back_populates='plan')


class ProviderOrganisation(Base):
    __tablename__ = 'provider_organisation'
    __table_args__ = (
        ForeignKeyConstraint(['provider_organisation_naming'], ['naming_contribution.id_naming_contribution'], name='fk_provider_organisation_2'),
        ForeignKeyConstraint(['provider_organisation_wallet_id'], ['wallet.id_wallet'], name='fk_provider_organisation_1'),
        Index('fk_provider_organisation_1_idx', 'provider_organisation_wallet_id'),
        Index('fk_provider_organisation_2_idx', 'provider_organisation_naming')
    )

    idprovider_organisation = Column(Integer, primary_key=True)
    provider_organisation_naming = Column(Integer)
    provider_organisation_wallet_id = Column(Integer)
    provider_organisation_name = Column(String(255))
    provider_organisation_icon_url = Column(String(255))
    provider_organisation_desc = Column(String(255))

    provider_organisation_wallet = relationship('Wallet', back_populates='provider_organisation')
    product_provider = relationship('ProductProvider', back_populates='product_provider_org')
    management_rule = relationship('ManagementRule', back_populates='provider_organisation')
    service_contribution = relationship('ServiceContribution', back_populates='provider_organisation')


class DeliveryBroker(Base):
    __tablename__ = 'delivery_broker'
    __table_args__ = (
        ForeignKeyConstraint(['delivery_broker_wallet_id'], ['wallet.id_wallet'], name='fk_delivery_broker_1'),
        Index('fk_delivery_broker_1_idx', 'delivery_broker_wallet_id')
    )

    id_delivery_broker = Column(Integer, primary_key=True)
    delivery_broker_name = Column(String(255))
    delivery_broker_label = Column(String(255))
    delivery_broker_logo_url = Column(String(255))
    delivery_broker_image_url = Column(String(255))
    delivery_broker_wallet_id = Column(Integer)
    delivery_broker_price_matrix = Column(Text)

    delivery_broker_wallet = relationship('Wallet', back_populates='delivery_broker')



class LedgerEntry(Base):
    __tablename__ = 'ledger_entry'
    __table_args__ = (
        ForeignKeyConstraint(['money_transaction_id'], ['money_transaction.id_money_transaction'], name='fk_ledger_entry_money_transaction1'),
        ForeignKeyConstraint(['wallet_id'], ['wallet.id_wallet'], name='fk_ledger_entry_wallet1'),
        Index('fk_ledger_entry_money_transaction1_idx', 'money_transaction_id'),
        Index('fk_ledger_entry_wallet1_idx', 'wallet_id')
    )

    id_ledger_entry = Column(Integer, primary_key=True)
    wallet_id = Column(Integer, nullable=False)
    money_transaction_id = Column(Integer, nullable=False)
    ledger_entry_type = Column(Enum('CREDIT', 'DEBIT'))
    ledger_entry_amount = Column(DECIMAL(20, 8))

    money_transaction = relationship('MoneyTransaction', back_populates='ledger_entry')
    wallet = relationship('Wallet', back_populates='ledger_entry')



class Wallet(Base):
    __tablename__ = 'wallet'

    id_wallet = Column(Integer, primary_key=True)
    wallet_type = Column(Enum('user', 'provider', 'organization', 'system', 'virtual', 'business'), server_default=text("'user'"))
    wallet_currency = Column(Enum('DZD', 'USD', 'EUR'), server_default=text("'DZD'"))
    wallet_balance = Column(DECIMAL(20, 8))
    wallet_status = Column(Enum('active', 'inactive', 'suspended', 'closed', 'pending_verification'), server_default=text("'pending_verification'"))
    wallet_version = Column(Integer, server_default=text("'0'"))

    delivery_broker = relationship('DeliveryBroker', back_populates='delivery_broker_wallet')
    provider_organisation = relationship('ProviderOrganisation', back_populates='provider_organisation_wallet')
    money_transaction = relationship('MoneyTransaction', foreign_keys='[MoneyTransaction.money_transaction_wallet_destination_id]', back_populates='money_transaction_wallet_destination')
    money_transaction_ = relationship('MoneyTransaction', foreign_keys='[MoneyTransaction.money_transaction_wallet_source_id]', back_populates='money_transaction_wallet_source')
    ledger_entry = relationship('LedgerEntry', back_populates='wallet')
    app_user = relationship('AppUser', back_populates='app_user_wallet')
    product_provider = relationship('ProductProvider', back_populates='product_provider_wallet')



class Payment(Base):
    __tablename__ = 'payment'
    __table_args__ = (
        ForeignKeyConstraint(['payment_invoice_id'], ['invoice.invoice_id'], ondelete='RESTRICT', onupdate='CASCADE', name='payment_ibfk_1'),
        Index('idx_invoice', 'payment_invoice_id'),
        Index('idx_status', 'payment_status')
    )

    payment_id = Column(Integer, primary_key=True)
    payment_invoice_id = Column(Integer)
    payment_amount = Column(DECIMAL(15, 4))
    payment_method = Column(Enum('cash', 'card', 'bank_transfer', 'mobile_money', 'crypto', 'deposit', 'wallet', 'check'), server_default=text("'cash'"), comment='cash, card, bank, mobile')
    payment_status = Column(Enum('pending', 'processing', 'completed', 'partial', 'failed', 'cancelled'), server_default=text("'pending'"))
    payment_reference = Column(String(255), comment='Bank or transaction reference')
    payment_notes = Column(Text)
    payment_created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    payment_updated_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))
    payment_type = Column(Enum('deposit', 'payment', 'refund'))

    payment_invoice = relationship('Invoice', back_populates='payment')
    money_transaction = relationship('MoneyTransaction', back_populates='payment')


class MoneyTransaction(Base):
    __tablename__ = 'money_transaction'
    __table_args__ = (
        ForeignKeyConstraint(['money_transaction_for_payment'], ['payment.payment_id'], name='fk_money_transaction_3'),
        ForeignKeyConstraint(['money_transaction_wallet_destination_id'], ['wallet.id_wallet'], name='fk_money_transaction_2'),
        ForeignKeyConstraint(['money_transaction_wallet_source_id'], ['wallet.id_wallet'], name='fk_money_transaction_1'),
        Index('fk_money_transaction_1_idx', 'money_transaction_wallet_source_id'),
        Index('fk_money_transaction_2_idx', 'money_transaction_wallet_destination_id'),
        Index('fk_money_transaction_3_idx', 'money_transaction_for_payment')
    )

    id_money_transaction = Column(Integer, primary_key=True)
    money_transaction_document_url = Column(String(255))
    money_transaction_amount = Column(DECIMAL(20, 8), server_default=text("'0.00000000'"))
    money_transaction_reference = Column(String(255))
    money_transaction_creation = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    money_transaction_last_updated = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))
    money_transaction_wallet_source_id = Column(Integer)
    money_transaction_wallet_destination_id = Column(Integer)
    money_transaction_status = Column(Enum('pending', 'processing', 'completed', 'failed', 'cancelled', 'refunded', 'reversed'), server_default=text("'pending'"))
    money_transaction_for_payment = Column(Integer)

    payment = relationship('Payment', back_populates='money_transaction')
    money_transaction_wallet_destination = relationship('Wallet', foreign_keys=[money_transaction_wallet_destination_id], back_populates='money_transaction')
    money_transaction_wallet_source = relationship('Wallet', foreign_keys=[money_transaction_wallet_source_id], back_populates='money_transaction_')
    ledger_entry = relationship('LedgerEntry', back_populates='money_transaction')



class AppUser(Base):
    __tablename__ = 'app_user'
    __table_args__ = (
        ForeignKeyConstraint(['app_user_subscription_ref'], ['plan.id_plan'], name='fk_app_user_2'),
        ForeignKeyConstraint(['app_user_wallet_id'], ['wallet.id_wallet'], name='fk_app_user_4'),
        Index('fk_app_user_2_idx', 'app_user_subscription_ref'),
        Index('fk_app_user_4_idx', 'app_user_wallet_id')
    )

    id_app_user = Column(Integer, primary_key=True)
    app_user_name = Column(String(100))
    app_user_password = Column(String(256))
    app_user_person_id = Column(Integer)
    app_user_type = Column(Enum('admin', 'provider', 'customer', 'patient', 'guest'), server_default=text("'customer'"))
    app_user_preferences = Column(Text)
    app_user_image_url = Column(String(255))
    app_user_last_active = Column(TIMESTAMP)
    app_user_last_updated = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))
    app_user_creation = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    app_user_subscription_ref = Column(Integer)
    app_user_email = Column(String(255))
    app_user_wallet_id = Column(Integer)
    app_user_login_option = Column(Enum('google', 'gluttex'))

    plan = relationship('Plan', back_populates='app_user')
    app_user_wallet = relationship('Wallet', back_populates='app_user')
    placed_order = relationship('PlacedOrder', back_populates='ordering_user')
    product_provider = relationship('ProductProvider', back_populates='app_user')
    additional_fee = relationship('AdditionalFee', back_populates='additional_fee_user')
    cart = relationship('Cart', foreign_keys='[Cart.cart_client_user]', back_populates='app_user')
    cart_ = relationship('Cart', foreign_keys='[Cart.cart_selling_user]', back_populates='app_user_')
    product = relationship('Product', back_populates='app_user')
    service_contribution = relationship('ServiceContribution', back_populates='app_user')
    management_rule = relationship('ManagementRule', back_populates='app_user')


class ProductProvider(Base):
    __tablename__ = 'product_provider'
    __table_args__ = (
        ForeignKeyConstraint(['product_provider_details_id'], ['provider_details.idprovider_details_id'], ondelete='RESTRICT', onupdate='RESTRICT', name='fk_product_provider_3'),
        ForeignKeyConstraint(['product_provider_org_id'], ['provider_organisation.idprovider_organisation'], ondelete='RESTRICT', onupdate='RESTRICT', name='fk_product_provider_2'),
        ForeignKeyConstraint(['product_provider_owner'], ['app_user.id_app_user'], name='fk_product_provider_5'),
        ForeignKeyConstraint(['product_provider_type_id'], ['product_provider_type.id_product_provider_type'], ondelete='RESTRICT', onupdate='RESTRICT', name='fk_product_provider_1'),
        ForeignKeyConstraint(['product_provider_wallet_id'], ['wallet.id_wallet'], name='fk_product_provider_6'),
        Index('fk_product_provider_1_idx', 'product_provider_type_id'),
        Index('fk_product_provider_2_idx', 'product_provider_org_id'),
        Index('fk_product_provider_3_idx', 'product_provider_details_id'),
        Index('fk_product_provider_5_idx', 'product_provider_owner'),
        Index('fk_product_provider_6_idx', 'product_provider_wallet_id')
    )

    id_product_provider = Column(Integer, primary_key=True)
    product_provider_details_id = Column(Integer)
    product_provider_type_id = Column(Integer)
    product_provider_org_id = Column(Integer)
    product_provider_owner = Column(Integer)
    product_provider_wallet_id = Column(Integer)

    service_contribution = relationship('ServiceContribution', back_populates='product_provider')
    product_provider_org = relationship('ProviderOrganisation', back_populates='product_provider')
    app_user = relationship('AppUser', back_populates='product_provider')
    product_provider_wallet = relationship('Wallet', back_populates='product_provider')
    additional_fee = relationship('AdditionalFee', back_populates='additional_fee_on_provider')
    cart = relationship('Cart', back_populates='cart_product_provider')
    management_rule = relationship('ManagementRule', back_populates='product_provider')
    product = relationship('Product', back_populates='product_provider')
    provided_service = relationship('ProvidedService', back_populates='provided_service_product_provider')
    service_package = relationship('ServicePackage', back_populates='service_package_product_provider')




class AdditionalFee(Base):
    __tablename__ = 'additional_fee'
    __table_args__ = (
        ForeignKeyConstraint(['additional_fee_invoice'], ['invoice.invoice_id'], name='fk_additional_fee_3'),
        ForeignKeyConstraint(['additional_fee_on_provider_id'], ['product_provider.id_product_provider'], name='fk_additional_fee_2'),
        ForeignKeyConstraint(['additional_fee_user_id'], ['app_user.id_app_user'], name='fk_additional_fee_1'),
        Index('fk_additional_fee_1_idx', 'additional_fee_user_id'),
        Index('fk_additional_fee_2_idx', 'additional_fee_on_provider_id'),
        Index('fk_additional_fee_3_idx', 'additional_fee_invoice')
    )

    additional_fee_id = Column(Integer, primary_key=True)
    additional_fee_name = Column(String(255))
    additional_fee_amount = Column(DECIMAL(15, 4))
    additional_fee_description = Column(Text)
    additional_fee_created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    additional_fee_updated_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))
    additional_fee_document_url = Column(String(255))
    additional_fee_user_id = Column(Integer)
    additional_fee_on_provider_id = Column(Integer)
    additional_fee_invoice = Column(Integer)

    invoice = relationship('Invoice', back_populates='additional_fee')
    additional_fee_on_provider = relationship('ProductProvider', back_populates='additional_fee')
    additional_fee_user = relationship('AppUser', back_populates='additional_fee')


class Cart(Base):
    __tablename__ = 'cart'
    __table_args__ = (
        ForeignKeyConstraint(['cart_client_user'], ['app_user.id_app_user'], name='fk_cart_2'),
        ForeignKeyConstraint(['cart_invoice'], ['invoice.invoice_id'], name='fk_cart_5'),
        ForeignKeyConstraint(['cart_product_provider_id'], ['product_provider.id_product_provider'], ondelete='RESTRICT', onupdate='CASCADE', name='cart_ibfk_1'),
        ForeignKeyConstraint(['cart_selling_user'], ['app_user.id_app_user'], name='fk_cart_1'),
        Index('fk_cart_2', 'cart_client_user'),
        Index('fk_cart_5_idx', 'cart_invoice'),
        Index('idx_cart_provider', 'cart_product_provider_id'),
        Index('idx_cart_status', 'cart_status'),
        Index('idx_cart_user', 'cart_selling_user')
    )

    cart_id = Column(Integer, primary_key=True)
    cart_product_provider_id = Column(Integer, comment='Provider owning the cart')
    cart_selling_user = Column(Integer, comment='Customer / patient / client id')
    cart_status = Column(Enum('open', 'pending', 'completed', 'canceled', 'partial', 'checkout', 'abandoned'), server_default=text("'open'"), comment='open, pending, completed, canceled')
    cart_total_amount = Column(DECIMAL(15, 4), server_default=text("'0.0000'"))
    cart_notes = Column(Text)
    cart_created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    cart_updated_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))
    cart_person_ref = Column(Integer)
    cart_client_user = Column(Integer)
    cart_due_date = Column(Date)
    cart_invoice = Column(Integer)

    app_user = relationship('AppUser', foreign_keys=[cart_client_user], back_populates='cart')
    invoice = relationship('Invoice', back_populates='cart')
    cart_product_provider = relationship('ProductProvider', back_populates='cart')
    app_user_ = relationship('AppUser', foreign_keys=[cart_selling_user], back_populates='cart_')
    ordered_item = relationship('OrderedItem', back_populates='cart')
    ordered_service = relationship('OrderedService', back_populates='ordered_service_cart')



class ManagementRule(Base):
    __tablename__ = 'management_rule'
    __table_args__ = (
        ForeignKeyConstraint(['rule_ref_org'], ['provider_organisation.idprovider_organisation'], ondelete='RESTRICT', onupdate='RESTRICT', name='fk_management_rule_1'),
        ForeignKeyConstraint(['rule_ref_provider'], ['product_provider.id_product_provider'], name='fk_management_rule_2'),
        ForeignKeyConstraint(['rule_ref_user'], ['app_user.id_app_user'], ondelete='RESTRICT', onupdate='RESTRICT', name='fk_management_rule_3'),
        Index('fk_management_rule_1_idx', 'rule_ref_org'),
        Index('fk_management_rule_2_idx', 'rule_ref_provider'),
        Index('fk_management_rule_3_idx', 'rule_ref_user')
    )

    id_management_rule = Column(Integer, primary_key=True)
    rule_ref_org = Column(Integer)
    rule_ref_provider = Column(Integer)
    rule_ref_user = Column(Integer)
    management_rule_code = Column(Integer)
    management_rule_status = Column(Enum('PENDING', 'REJECTED', 'SUSPENDED', 'OBSOLETE', 'ACTIVE'), server_default=text("'PENDING'"))
    management_rule_expiry = Column(DateTime)

    provider_organisation = relationship('ProviderOrganisation', back_populates='management_rule')
    product_provider = relationship('ProductProvider', back_populates='management_rule')
    app_user = relationship('AppUser', back_populates='management_rule')



class Product(Base):
    __tablename__ = 'product'
    __table_args__ = (
        ForeignKeyConstraint(['product_owner'], ['app_user.id_app_user'], ondelete='RESTRICT', onupdate='RESTRICT', name='fk_product_3'),
        ForeignKeyConstraint(['product_provider_id'], ['product_provider.id_product_provider'], ondelete='RESTRICT', onupdate='RESTRICT', name='fk_product_1'),
        Index('fk_product_1_idx', 'product_provider_id'),
        Index('fk_product_3_idx', 'product_owner'),
    )

    id_product = Column(Integer, primary_key=True)
    product_name = Column(String(45))
    product_brand = Column(String(45))
    product_provider_id = Column(Integer)
    product_category_id = Column(Integer)
    product_barcode = Column(String(45))
    last_updated = Column(DateTime, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))
    created = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    product_description = Column(String(300))
    product_price = Column(Float(asdecimal=True))
    product_quantity = Column(Integer)
    product_quantifier = Column(String(45))
    product_owner = Column(Integer)
    product_origin_id = Column(Integer)
    product_visibility = Column(Enum('VISIBLE', 'HIDDEN'), server_default=text("'VISIBLE'"))

    app_user = relationship('AppUser', back_populates='product')
    product_provider = relationship('ProductProvider', back_populates='product')
    ordered_item = relationship('OrderedItem', back_populates='ordered_product')
    service_resource_requirement = relationship('ServiceResourceRequirement', back_populates='product')


class ProvidedService(Base):
    __tablename__ = 'provided_service'
    __table_args__ = (
        ForeignKeyConstraint(['provided_service_product_provider_id'], ['product_provider.id_product_provider'], ondelete='RESTRICT', onupdate='CASCADE', name='provided_service_ibfk_2'),
        Index('idx_provided_service_active', 'provided_service_is_active', 'provided_service_deleted_at'),
        Index('idx_provided_service_created_at', 'provided_service_created_at'),
        Index('idx_provided_service_name', 'provided_service_name'),
        Index('idx_provided_service_price_range', 'provided_service_base_price', 'provided_service_final_price'),
        Index('idx_provided_service_provider', 'provided_service_product_provider_id')
    )

    provided_service_id = Column(Integer, primary_key=True)
    provided_service_name = Column(String(255))
    provided_service_description = Column(Text)
    provided_service_category_id = Column(Integer)
    provided_service_product_provider_id = Column(Integer, comment='References i_product_provider.id_product_provider')
    provided_service_base_price = Column(DECIMAL(15, 4))
    provided_service_final_price = Column(DECIMAL(15, 4))
    provided_service_actual_duration = Column(DECIMAL(10, 2))
    provided_service_is_active = Column(TINYINT(1), server_default=text("'1'"))
    provided_service_pricing_config = Column(JSON)
    provided_service_created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    provided_service_updated_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))
    provided_service_deleted_at = Column(TIMESTAMP)

    provided_service_product_provider = relationship('ProductProvider', back_populates='provided_service')
    ordered_service = relationship('OrderedService', back_populates='ordered_service_service')
    service_contribution = relationship('ServiceContribution', back_populates='provided_service')
    service_package_item = relationship('ServicePackageItem', back_populates='service_package_item_service')
    service_resource_requirement = relationship('ServiceResourceRequirement', back_populates='service_resource_requirement_service')
    service_staff_requirement = relationship('ServiceStaffRequirement', back_populates='service_staff_requirement_service')




class ServicePackage(Base):
    __tablename__ = 'service_package'
    __table_args__ = (
        ForeignKeyConstraint(['service_package_product_provider_id'], ['product_provider.id_product_provider'], ondelete='RESTRICT', onupdate='CASCADE', name='service_package_ibfk_1'),
        Index('idx_service_package_active', 'service_package_is_active'),
        Index('idx_service_package_provider', 'service_package_product_provider_id'),
        Index('idx_service_package_validity', 'service_package_valid_from', 'service_package_valid_to')
    )

    service_package_id = Column(Integer, primary_key=True)
    service_package_name = Column(String(255))
    service_package_description = Column(Text)
    service_package_product_provider_id = Column(Integer)
    service_package_price = Column(DECIMAL(15, 4))
    service_package_discount_percentage = Column(DECIMAL(5, 2))
    service_package_is_active = Column(TINYINT(1), server_default=text("'1'"))
    service_package_valid_from = Column(Date)
    service_package_valid_to = Column(Date)
    service_package_created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    service_package_updated_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))

    service_package_product_provider = relationship('ProductProvider', back_populates='service_package')
    service_package_item = relationship('ServicePackageItem', back_populates='service_package_item_package')



class OrderedItem(Base):
    __tablename__ = 'ordered_item'
    __table_args__ = (
        ForeignKeyConstraint(['order_ref'], ['placed_order.id_placed_order'], name='fk_ordered_item_3'),
        ForeignKeyConstraint(['ordered_item_cart_ref'], ['cart.cart_id'], name='fk_ordered_item_2'),
        ForeignKeyConstraint(['ordered_product_id'], ['product.id_product'], ondelete='RESTRICT', onupdate='RESTRICT', name='fk_ordered_item_1'),
        Index('fk_ordered_item_1_idx', 'ordered_product_id'),
        Index('fk_ordered_item_2_idx', 'ordered_item_cart_ref'),
        Index('fk_ordered_item_3_idx', 'order_ref')
    )

    id_ordered_item = Column(Integer, primary_key=True)
    ordered_product_id = Column(Integer)
    ordered_quantity = Column(Integer)
    applied_vat = Column(Float(asdecimal=True))
    order_ref = Column(Integer)
    unit_price = Column(Float(asdecimal=True))
    product_discount = Column(Float(asdecimal=True))
    ordered_item_cart_ref = Column(Integer)
    ordered_item_delivery_status = Column(Enum('pending', 'processing', 'shipped', 'delivered', 'cancelled', 'returned', 'partial'), server_default=text("'pending'"))
    ordered_item_delivery_fee = Column(Float(asdecimal=True), server_default=text("'0'"))

    placed_order = relationship('PlacedOrder', back_populates='ordered_item')
    cart = relationship('Cart', back_populates='ordered_item')
    ordered_product = relationship('Product', back_populates='ordered_item')


class OrderedService(Base):
    __tablename__ = 'ordered_service'
    __table_args__ = (
        ForeignKeyConstraint(['ordered_service_cart_id'], ['cart.cart_id'], ondelete='CASCADE', onupdate='CASCADE', name='ordered_service_ibfk_1'),
        ForeignKeyConstraint(['ordered_service_service_id'], ['provided_service.provided_service_id'], ondelete='RESTRICT', onupdate='CASCADE', name='ordered_service_ibfk_2'),
        Index('idx_cart', 'ordered_service_cart_id'),
        Index('idx_service', 'ordered_service_service_id')
    )

    ordered_service_id = Column(Integer, primary_key=True)
    ordered_service_cart_id = Column(Integer)
    ordered_service_service_id = Column(Integer, comment='References provided_service')
    ordered_service_quantity = Column(Integer, server_default=text("'1'"))
    ordered_service_unit_price = Column(DECIMAL(15, 4))
    ordered_service_total_price = Column(DECIMAL(15, 4))
    ordered_service_notes = Column(Text)
    ordered_service_created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    ordered_service_updated_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))
    ordered_service_scheduled_at = Column(TIMESTAMP)
    ordered_service_delivery_fee = Column(Float(asdecimal=True), server_default=text("'0'"))
    ordered_service_delivery_status = Column(Enum('pending', 'processing', 'scheduled', 'in_progress', 'completed', 'cancelled', 'no_show'), server_default=text("'pending'"))

    ordered_service_cart = relationship('Cart', back_populates='ordered_service')
    ordered_service_service = relationship('ProvidedService', back_populates='ordered_service')




class ServiceContribution(Base):
    __tablename__ = 'service_contribution'
    __table_args__ = (
        ForeignKeyConstraint(['service_contribution_org_ref'], ['provider_organisation.idprovider_organisation'], name='fk_service_contribution_2'),
        ForeignKeyConstraint(['service_contribution_provider_ref'], ['product_provider.id_product_provider'], name='fk_service_contribution_6'),
        ForeignKeyConstraint(['service_contribution_user_ref'], ['app_user.id_app_user'], name='fk_service_contribution_3'),
        ForeignKeyConstraint(['service_ref'], ['provided_service.provided_service_id'], name='fk_service_contribution_5'),
        Index('fk_service_contribution_2_idx', 'service_contribution_org_ref'),
        Index('fk_service_contribution_3_idx', 'service_contribution_user_ref'),
        Index('fk_service_contribution_5_idx', 'service_ref'),
        Index('fk_service_contribution_6_idx', 'service_contribution_provider_ref')
    )

    id_service_contribution = Column(Integer, primary_key=True)
    service_contribution_duration = Column(String(45))
    service_contribution_price = Column(Float)
    service_contribution_currency = Column(String(45))
    service_contribution_org_ref = Column(Integer)
    service_contribution_user_ref = Column(Integer)
    service_contribution_person_ref = Column(Integer)
    service_ref = Column(Integer)
    service_contribution_start = Column(TIMESTAMP)
    service_contribution_provider_ref = Column(Integer)

    provider_organisation = relationship('ProviderOrganisation', back_populates='service_contribution')
    product_provider = relationship('ProductProvider', back_populates='service_contribution')
    app_user = relationship('AppUser', back_populates='service_contribution')
    provided_service = relationship('ProvidedService', back_populates='service_contribution')


class ServicePackageItem(Base):
    __tablename__ = 'service_package_item'
    __table_args__ = (
        ForeignKeyConstraint(['service_package_item_package_id'], ['service_package.service_package_id'], ondelete='CASCADE', onupdate='CASCADE', name='service_package_item_ibfk_1'),
        ForeignKeyConstraint(['service_package_item_service_id'], ['provided_service.provided_service_id'], ondelete='CASCADE', onupdate='CASCADE', name='service_package_item_ibfk_2'),
        Index('idx_service_package_item_service', 'service_package_item_service_id'),
        Index('uk_package_service', 'service_package_item_package_id', 'service_package_item_service_id', unique=True)
    )

    service_package_item_id = Column(Integer, primary_key=True)
    service_package_item_package_id = Column(Integer)
    service_package_item_service_id = Column(Integer)
    service_package_item_sequence_order = Column(Integer, server_default=text("'1'"))
    service_package_item_quantity = Column(Integer, server_default=text("'1'"))
    service_package_item_notes = Column(Text)

    service_package_item_package = relationship('ServicePackage', back_populates='service_package_item')
    service_package_item_service = relationship('ProvidedService', back_populates='service_package_item')


class ServiceResourceRequirement(Base):
    __tablename__ = 'service_resource_requirement'
    __table_args__ = (
        ForeignKeyConstraint(['service_resource_requirement_product_ref'], ['product.id_product'], name='fk_service_resource_requirement_1'),
        ForeignKeyConstraint(['service_resource_requirement_service_id'], ['provided_service.provided_service_id'], ondelete='CASCADE', onupdate='CASCADE', name='service_resource_requirement_ibfk_1'),
        Index('fk_service_resource_requirement_1_idx', 'service_resource_requirement_product_ref'),
        Index('idx_resource_requirement_name', 'service_resource_requirement_name'),
        Index('idx_resource_requirement_service', 'service_resource_requirement_service_id'),
        Index('idx_resource_requirement_type', 'service_resource_requirement_type')
    )

    service_resource_requirement_id = Column(Integer, primary_key=True)
    service_resource_requirement_service_id = Column(Integer)
    service_resource_requirement_name = Column(String(255))
    service_resource_requirement_type = Column(String(100))
    service_resource_requirement_quantity = Column(Integer, server_default=text("'1'"))
    service_resource_requirement_cost_per_unit = Column(DECIMAL(15, 4))
    service_resource_requirement_is_consumable = Column(TINYINT(1), server_default=text("'0'"))
    service_resource_requirement_notes = Column(Text)
    service_resource_requirement_created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    service_resource_requirement_updated_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))
    service_resource_requirement_product_ref = Column(Integer)

    product = relationship('Product', back_populates='service_resource_requirement')
    service_resource_requirement_service = relationship('ProvidedService', back_populates='service_resource_requirement')


class ServiceStaffRequirement(Base):
    __tablename__ = 'service_staff_requirement'
    __table_args__ = (
        ForeignKeyConstraint(['service_staff_requirement_service_id'], ['provided_service.provided_service_id'], ondelete='CASCADE', onupdate='CASCADE', name='service_staff_requirement_ibfk_1'),
        Index('idx_service_staff_requirement_service', 'service_staff_requirement_service_id')
    )

    service_staff_requirement_id = Column(Integer, primary_key=True)
    service_staff_requirement_service_id = Column(Integer)
    service_staff_requirement_role = Column(Integer)
    service_staff_requirement_min_count = Column(Integer, server_default=text("'1'"))
    service_staff_requirement_max_count = Column(Integer)
    service_staff_requirement_hourly_rate = Column(DECIMAL(15, 4))
    service_staff_requirement_allocated_hours = Column(DECIMAL(5, 2))
    service_staff_requirement_notes = Column(Text)
    service_staff_requirement_created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    service_staff_requirement_updated_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))

    service_staff_requirement_service = relationship('ProvidedService', back_populates='service_staff_requirement')
