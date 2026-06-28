# repositories/payment_repository.py

from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import and_, or_, desc, func, between
from core.models import (
    Cart, Payment, Invoice, Wallet, MoneyTransaction, 
    AppUser, Plan
)
from core.exceptions.handler import DatabaseException, APIException
from core.messages import *
import logging

logger = logging.getLogger(__name__)

class MoneyTransactionRepository:
    
    """Repository for money transaction operations"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create_transaction(self, transaction_data: Dict[str, Any]) -> MoneyTransaction:
        """Create a new money transaction"""
        try:
            transaction = MoneyTransaction(**transaction_data)
            self.session.add(transaction)
            self.session.flush()
            return transaction
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to create transaction: {e}")
            raise DatabaseException(f"Transaction creation failed: {e}")
    
    def get_transaction_by_id(self, transaction_id: int) -> Optional[MoneyTransaction]:
        """Get transaction by ID"""
        try:
            return self.session.query(MoneyTransaction).options(
                joinedload(MoneyTransaction.money_transaction_wallet_source),
                joinedload(MoneyTransaction.money_transaction_wallet_destination),
                joinedload(MoneyTransaction.payment)
            ).filter(MoneyTransaction.id_money_transaction == transaction_id).first()
        except Exception as e:
            logger.error(f"Failed to get transaction {transaction_id}: {e}")
            return None
    
    def get_transactions_by_wallet(self, wallet_id: int, 
                                  status: Optional[str] = None,
                                  limit: int = 50) -> List[MoneyTransaction]:
        """Get transactions for a wallet"""
        try:
            query = self.session.query(MoneyTransaction).filter(
                or_(
                    MoneyTransaction.money_transaction_wallet_source_id == wallet_id,
                    MoneyTransaction.money_transaction_wallet_destination_id == wallet_id
                )
            )
            
            if status:
                query = query.filter(MoneyTransaction.money_transaction_status == status)
            
            return query.order_by(
                desc(MoneyTransaction.money_transaction_creation)
            ).limit(limit).all()
        except Exception as e:
            logger.error(f"Failed to get wallet transactions: {e}")
            return []
        
    def get_transactions_by_payment(self, payment_id: int, 
                                  status: Optional[str] = None,
                                  limit: int = 50) -> List[MoneyTransaction]:
        """Get transactions for a payment"""
        try:
            query = self.session.query(MoneyTransaction).filter(
                or_(
                    MoneyTransaction.money_transaction_for_payment == payment_id,
                )
            )
            
            if status:
                query = query.filter(MoneyTransaction.money_transaction_status == status)
            
            return query.order_by(
                desc(MoneyTransaction.money_transaction_creation)
            ).limit(limit).all()
        except Exception as e:
            logger.error(f"Failed to get wallet transactions: {e}")
            return []
    
    def update_transaction_status(self, transaction_id: int, 
                                 status: str) -> Optional[MoneyTransaction]:
        """Update transaction status"""
        try:
            transaction = self.session.query(MoneyTransaction).filter(
                MoneyTransaction.id_money_transaction == transaction_id
            ).first()
            
            if not transaction:
                return None
            
            transaction.money_transaction_status = status
            transaction.money_transaction_last_updated = datetime.now()
            
            self.session.flush()
            return transaction
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to update transaction {transaction_id}: {e}")
            return None

