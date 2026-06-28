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




class WalletRepository:
    """Repository for wallet operations"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def get_wallet_by_id(self, wallet_id: int) -> Optional[Wallet]:
        """Get wallet by ID"""
        try:
            return self.session.query(Wallet).filter(
                Wallet.id_wallet == wallet_id
            ).first()
        except Exception as e:
            logger.error(f"Failed to get wallet {wallet_id}: {e}")
            return None
    
    def get_wallet_by_user(self, user_id: int) -> Optional[Wallet]:
        """Get wallet for a user"""
        try:
            return self.session.query(Wallet).join(
                AppUser, AppUser.app_user_wallet_id == Wallet.id_wallet
            ).filter(AppUser.id_app_user == user_id).first()
        except Exception as e:
            logger.error(f"Failed to get wallet for user {user_id}: {e}")
            return None
    
    def update_wallet_balance(self, wallet_id: int, amount: float, 
                             operation: str = 'add') -> Optional[Wallet]:
        """Update wallet balance (add or subtract)"""
        try:
            wallet = self.session.query(Wallet).filter(
                Wallet.id_wallet == wallet_id
            ).first()
            
            if not wallet:
                return None
            
            current_balance = wallet.wallet_balance or 0.0
            if operation == 'add':
                wallet.wallet_balance = current_balance + amount
            elif operation == 'subtract':
                if current_balance < amount:
                    raise ValueError("Insufficient balance")
                wallet.wallet_balance = current_balance - amount
            else:
                raise ValueError(f"Invalid operation: {operation}")
            
            self.session.flush()
            return wallet
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to update wallet {wallet_id}: {e}")
            raise
    
    def create_wallet(self, wallet_data: Dict[str, Any]) -> Wallet:
        """Create a new wallet"""
        try:
            wallet = Wallet(**wallet_data)
            self.session.add(wallet)
            self.session.flush()
            return wallet
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to create wallet: {e}")
            raise DatabaseException(f"Wallet creation failed: {e}")
    
    def get_wallet_transactions(self, wallet_id: int, limit: int = 50) -> List[MoneyTransaction]:
        """Get wallet transactions"""
        try:
            return self.session.query(MoneyTransaction).filter(
                or_(
                    MoneyTransaction.money_transaction_wallet_source_id == wallet_id,
                    MoneyTransaction.money_transaction_wallet_destination_id == wallet_id
                )
            ).order_by(desc(MoneyTransaction.money_transaction_creation)).limit(limit).all()
        except Exception as e:
            logger.error(f"Failed to get wallet transactions: {e}")
            return []
