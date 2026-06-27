# core/database.py

"""
Database engine and session management.
This module is the single source of truth for database connections.
"""

import logging
from contextlib import contextmanager
from typing import Optional
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from constants import DB_URI
from core.exceptions.handler import APIException
from core.exceptions.error_codes import ErrorCode
from core.exceptions.http_status import (
    HTTP_500_INTERNAL_SERVER_ERROR
)

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Singleton manager for database engine with connection pooling.
    """
    _instance = None
    _engine = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_engine(self, uri: str = None, force_reconnect: bool = False):
        """Get or create database engine"""
        if force_reconnect and self._engine:
            self._engine.dispose()
            self._engine = None
        
        if self._engine is None:
            uri = uri or DB_URI
            self._engine = self._create_engine(uri)
            logger.info("Database engine initialized successfully")
        
        return self._engine
    
    def _create_engine(self, uri: str):
        """Create engine with connection pooling"""
        try:
            engine = create_engine(
                uri,
                poolclass=QueuePool,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                pool_recycle=3600,
                echo=False
            )
            
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                conn.commit()
            
            return engine
        except Exception as e:
            logger.error(f"Failed to create database engine: {e}")
            raise RuntimeError(f"Database connection failed: {e}")
    
    def is_healthy(self) -> bool:
        """Check if database connection is healthy"""
        if self._engine is None:
            return False
        try:
            with self._engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                conn.commit()
            return True
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False
    
    def reset(self):
        """Reset the engine (useful for testing)"""
        if self._engine:
            self._engine.dispose()
        self._engine = None


# Global instance
_db_manager = DatabaseManager()


def get_engine(uri: str = None, force_reconnect: bool = False):
    """Convenience function to get database engine"""
    return _db_manager.get_engine(uri, force_reconnect)


@contextmanager
def session_scope() -> Session:
    """Context manager for database sessions"""
    engine = get_engine()
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Session error: {e}")
        raise
    finally:
        session.close()


def health_check() -> dict:
    """Check database health"""
    return {
        "status": "healthy" if _db_manager.is_healthy() else "unhealthy",
        "engine_initialized": _db_manager._engine is not None
    }


def reset_engine():
    """Reset the database engine (mainly for testing)"""
    _db_manager.reset()