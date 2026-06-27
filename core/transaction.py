# storage/transaction.py

"""
Transaction management utilities for database operations.
Provides decorators and context managers for atomic transactions.
"""

import logging
from functools import wraps
from typing import Optional, TypeVar, Callable, Any, Union, List
from contextlib import contextmanager
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from core.database import get_engine, session_scope
from core.exceptions.handler import APIException
from core.exceptions.error_codes import ErrorCode
from core.exceptions.http_status import (
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_417_EXPECTATION_FAILED,
    HTTP_500_INTERNAL_SERVER_ERROR
)

logger = logging.getLogger(__name__)

# Type variable for the return type of decorated functions
T = TypeVar('T')


class TransactionError(Exception):
    """Base exception for transaction-related errors"""
    pass


class TransactionManager:
    """
    Transaction manager for database operations.
    Supports nested transactions, savepoints, and automatic retry.
    """
    
    def __init__(self, retry_count: int = 3, retry_delay: float = 0.1):
        """
        Initialize transaction manager.
        
        Args:
            retry_count: Number of retry attempts on deadlock/serialization errors
            retry_delay: Delay between retries in seconds
        """
        self.retry_count = retry_count
        self.retry_delay = retry_delay
    
    @contextmanager
    def begin(self, session: Optional[Session] = None):
        """
        Context manager for transaction boundaries.
        
        Usage:
            with transaction_manager.begin(session) as tx:
                # Do work
                tx.add(record)
                tx.commit()
        
        Args:
            session: Optional existing session. If not provided, creates a new one.
        """
        if session:
            # Use existing session
            try:
                yield session
            except Exception as e:
                session.rollback()
                raise
        else:
            # Create new session
            with session_scope() as new_session:
                try:
                    yield new_session
                except Exception as e:
                    new_session.rollback()
                    raise
    
    def transactional(self, func: Callable[..., T]) -> Callable[..., T]:
        """
        Decorator that wraps a function in a transaction.
        
        Usage:
            @transaction_manager.transactional
            def create_order(data):
                # Multiple database operations
                # All commit or all rollback
                return result
        
        Args:
            func: Function to decorate
        
        Returns:
            Wrapped function with transaction support
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Check if session is passed as argument
            session = kwargs.get('session') or self._extract_session(args)
            
            if session:
                # Use existing session
                return self._execute_in_transaction(func, session, *args, **kwargs)
            else:
                # Create new session
                with session_scope() as new_session:
                    # Add session to kwargs if not present
                    if 'session' not in kwargs:
                        kwargs['session'] = new_session
                    return self._execute_in_transaction(func, new_session, *args, **kwargs)
        
        return wrapper
    
    def _extract_session(self, args: tuple) -> Optional[Session]:
        """Extract session from function arguments"""
        for arg in args:
            if isinstance(arg, Session):
                return arg
        return None
    
    def _execute_in_transaction(self, func, session, *args, **kwargs):
        """Execute function with retry logic"""
        last_error = None
        
        for attempt in range(self.retry_count):
            try:
                result = func(*args, **kwargs)
                # If function doesn't commit, do it here
                if not kwargs.get('_manual_commit', False):
                    session.commit()
                return result
                
            except SQLAlchemyError as e:
                session.rollback()
                logger.warning(f"Transaction attempt {attempt + 1} failed: {e}")
                last_error = e
                
                # Check if retryable error
                if not self._is_retryable_error(e):
                    raise
                
                if attempt < self.retry_count - 1:
                    import time
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                else:
                    raise
                    
            except Exception as e:
                session.rollback()
                raise
        
        if last_error:
            raise last_error
    
    def _is_retryable_error(self, error: Exception) -> bool:
        """Check if error is retryable (deadlock, serialization, etc.)"""
        error_msg = str(error).lower()
        retryable_patterns = [
            'deadlock',
            'serialization',
            'lock wait timeout',
            'connection reset',
            'connection timed out'
        ]
        return any(pattern in error_msg for pattern in retryable_patterns)


# Singleton transaction manager
_default_transaction_manager = TransactionManager()


# ==================== Convenience Functions ====================

def transactional(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator for atomic transactions.
    
    Usage:
        @transactional
        def my_function(data):
            # All operations are atomic
            return result
    """
    return _default_transaction_manager.transactional(func)


@contextmanager
def transaction(session: Optional[Session] = None):
    """
    Context manager for transactions.
    
    Usage:
        with transaction() as tx:
            tx.add(record)
            # Auto-commit on success, auto-rollback on error
    """
    with _default_transaction_manager.begin(session) as tx:
        yield tx


def atomic(operation: Callable[..., T], *args, **kwargs) -> T:
    """
    Execute a function atomically.
    
    Usage:
        result = atomic(create_user, username="john", email="john@example.com")
    """
    @transactional
    def wrapped():
        return operation(*args, **kwargs)
    return wrapped()


# ==================== Advanced Transaction Decorators ====================

class AtomicTransaction:
    """
    Class-based transaction decorator with more control.
    
    Usage:
        @AtomicTransaction(retry_count=5, retry_delay=0.5)
        def process_payment(invoice_id, amount):
            # Atomic operations
            return result
    """
    
    def __init__(self, retry_count: int = 3, retry_delay: float = 0.1, 
                 isolation_level: Optional[str] = None):
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        self.isolation_level = isolation_level
        self._manager = TransactionManager(retry_count, retry_delay)
    
    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Set isolation level if specified
            if self.isolation_level:
                kwargs['_isolation_level'] = self.isolation_level
            
            return self._manager.transactional(func)(*args, **kwargs)
        
        return wrapper


class NestedTransaction:
    """
    Support for nested transactions using savepoints.
    
    Usage:
        @transactional
        def outer_function(session):
            # Outer transaction
            with nested_transaction(session) as savepoint:
                # Inner transaction that can be rolled back independently
                pass
    """
    
    def __init__(self, session: Session):
        self.session = session
        self.savepoint_name = None
    
    @contextmanager
    def begin(self):
        """Begin a nested transaction (savepoint)"""
        try:
            self.savepoint_name = f"sp_{id(self)}"
            self.session.begin_nested()
            yield self.session
            # If we get here, commit the savepoint
            # The session.commit() will handle it
        except Exception as e:
            # Rollback to savepoint on error
            self.session.rollback()
            raise


def nested_transaction(session: Session):
    """
    Create a nested transaction (savepoint).
    
    Usage:
        with nested_transaction(session) as savepoint:
            # Operations that can be rolled back independently
            session.add(record)
            # If exception occurs, only this part is rolled back
    """
    return NestedTransaction(session).begin()


# ==================== Batch Transaction ====================

class BatchTransaction:
    """
    Batch transaction with chunked commits.
    
    Usage:
        with BatchTransaction(session, chunk_size=100) as batch:
            for record in records:
                batch.add(record)
                # Auto-commits every 100 records
    """
    
    def __init__(self, session: Session, chunk_size: int = 100):
        self.session = session
        self.chunk_size = chunk_size
        self.counter = 0
        self.items = []
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            # Commit remaining items
            self.flush()
            self.session.commit()
        else:
            self.session.rollback()
    
    def add(self, item: Any):
        """Add an item to the batch"""
        self.session.add(item)
        self.counter += 1
        
        if self.counter >= self.chunk_size:
            self.flush()
            self.counter = 0
    
    def add_all(self, items: List[Any]):
        """Add multiple items to the batch"""
        for item in items:
            self.add(item)
    
    def flush(self):
        """Flush pending items to the database"""
        if self.counter > 0:
            self.session.flush()
            self.counter = 0


# ==================== Repository Base with Transaction Support ====================

class TransactionalRepository:
    """
    Base repository with transaction support.
    """
    
    def __init__(self, session: Optional[Session] = None):
        self._session = session
        self._transaction_manager = TransactionManager()
    
    @property
    def session(self) -> Session:
        """Get session, creating one if needed"""
        if self._session is None:
            engine = get_engine()
            SessionLocal = sessionmaker(bind=engine)
            self._session = SessionLocal()
        return self._session
    
    @contextmanager
    def begin(self):
        """Begin a transaction"""
        with self._transaction_manager.begin(self.session) as tx:
            yield tx
    
    def transactional(self, func):
        """Decorator for transactional methods"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            if 'session' not in kwargs:
                kwargs['session'] = self.session
            return self._transaction_manager.transactional(func)(*args, **kwargs)
        return wrapper
    
    def commit(self):
        """Commit current transaction"""
        if self._session:
            self._session.commit()
    
    def rollback(self):
        """Rollback current transaction"""
        if self._session:
            self._session.rollback()
    
    def close(self):
        """Close session"""
        if self._session:
            self._session.close()
            self._session = None


# ==================== Example Usage ====================

class ExampleRepository(TransactionalRepository):
    """Example repository using transactional base"""
    
    @transactional
    def create_with_transaction(self, data):
        """Method with automatic transaction"""
        # Multiple database operations
        record1 = self.session.add(data)  # This will auto-commit on success
        return record1
    
    def create_with_manual_transaction(self, data):
        """Method with manual transaction control"""
        with self.begin():
            record = self.session.add(data)
            # Additional operations
            return record
    
    def create_batch(self, records):
        """Batch insert with chunked transactions"""
        with BatchTransaction(self.session, chunk_size=50) as batch:
            batch.add_all(records)
        return len(records)


# ==================== Convenience Functions ====================

def transaction_wrapper(func: Callable[..., T]) -> Callable[..., T]:
    """
    Alternative decorator syntax for transactions.
    
    Usage:
        @transaction_wrapper
        def my_function():
            pass
    """
    return transactional(func)


def run_in_transaction(func: Callable[..., T], *args, **kwargs) -> T:
    """
    Run a function in a transaction with retry support.
    
    Usage:
        result = run_in_transaction(process_payment, invoice_id=123, amount=100)
    """
    @transactional
    def wrapper():
        return func(*args, **kwargs)
    return wrapper()


# ==================== Error Handling Decorators ====================

def handle_db_errors(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator to handle database errors uniformly.
    
    Usage:
        @handle_db_errors
        @transactional
        def my_function():
            pass
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except SQLAlchemyError as e:
            error_msg = str(e).lower()
            
            if "integrity" in error_msg or "duplicate" in error_msg:
                raise APIException(
                    status_code=HTTP_417_EXPECTATION_FAILED,
                    error_code=ErrorCode.INTEGRITY_ERROR,
                    message="Database integrity constraint violated",
                    details={"error": str(e)}
                )
            elif "not found" in error_msg:
                raise APIException(
                    status_code=HTTP_404_NOT_FOUND,
                    error_code=ErrorCode.DATA_ERROR,
                    message="Record not found",
                    details={"error": str(e)}
                )
            else:
                raise APIException(
                    status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                    error_code=ErrorCode.DATABASE_ERROR,
                    message="Database operation failed",
                    details={"error": str(e)}
                )
        except APIException:
            raise
        except Exception as e:
            raise APIException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                error_code=ErrorCode.DATABASE_ERROR,
                message=f"Operation failed: {str(e)}",
                details={"error": str(e)}
            )
    
    return wrapper