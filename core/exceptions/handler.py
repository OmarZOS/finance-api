# core/exceptions.py
"""
Custom exception classes for the API.
Provides a hierarchy of exceptions with proper error codes and messages.
"""

from typing import Optional, Dict, Any, List
from enum import Enum


from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import SQLAlchemyError

from core.exceptions.error_codes import ErrorCode
from core.exceptions.error_messages import get_error_message
import logging

from core.exceptions.error_responses import create_error_response, create_validation_error_response
from core.messages import *

logger = logging.getLogger(__name__)


def setup_exception_handlers_with_config(app: FastAPI, debug: bool = False):
    """Configure all global exception handlers"""
    
    @app.exception_handler(APIException)
    async def api_exception_handler(request: Request, exc: APIException):
        """Handle custom API exceptions"""
        logger.warning(f"API Exception: {exc.error_code} - {exc.message}")
        
        return create_error_response(
            status_code=exc.status_code,
            error_code=exc.error_code.value if hasattr(exc.error_code, 'value') else str(exc.error_code),
            message=exc.message,
            request=request,
            details=exc.details,
            headers=exc.headers
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle request validation errors (422)"""
        logger.warning(f"Validation error: {exc.errors()}")
        
        errors = []
        for error in exc.errors():
            errors.append({
                "loc": error.get("loc", []),
                "msg": error.get("msg", ""),
                "type": error.get("type", "")
            })
        
        return create_validation_error_response(request, errors)
    
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """Handle HTTP exceptions"""
        return create_error_response(
            status_code=exc.status_code,
            error_code="HTTP_ERROR",
            message=str(exc.detail),
            request=request
        )
    
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Global catch-all for any unhandled exceptions"""
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        
        error_message = str(exc) if debug else "An unexpected error occurred"
        
        return create_error_response(
            status_code=500,
            error_code="INTERNAL_SERVER_ERROR",
            message=error_message,
            request=request
        )


# ==================== Base Exception ====================

class APIException(Exception):
    """Base exception for all API errors"""
    
    def __init__(
        self,
        status_code: int,
        error_code: ErrorCode,
        message: str = None,
        details: dict = None,
        headers: dict = None
    ):
        self.status_code = status_code
        self.error_code = error_code
        # Use provided message or get from error code mapping
        self.message = message or get_error_message(error_code)
        self.details = details or {}
        self.headers = headers or {}
        super().__init__(self.message)
    
    def to_dict(self) -> dict:
        """Convert exception to dictionary for JSON response"""
        return {
            "success": False,
            "status_code": self.status_code,
            "code": self.error_code.value if hasattr(self.error_code, 'value') else str(self.error_code),
            "message": self.message,
            "details": self.details
        }


# ==================== HTTP Exception Classes ====================

class BadRequestException(APIException):
    """400 Bad Request"""
    
    def __init__(self, message: str = "Bad request", details: dict = None):
        super().__init__(
            status_code=HTTP_400_BAD_REQUEST,
            error_code=ErrorCode.FAILED,
            message=message,
            details=details
        )


class UnauthorizedException(APIException):
    """401 Unauthorized"""
    
    def __init__(self, message: str = "Authentication required", details: dict = None):
        super().__init__(
            status_code=HTTP_401_UNAUTHORIZED,
            error_code=ErrorCode.AUTH_REQUIRED,
            message=message,
            details=details
        )


class ForbiddenException(APIException):
    """403 Forbidden"""
    
    def __init__(self, message: str = "Insufficient permissions", details: dict = None):
        super().__init__(
            status_code=HTTP_403_FORBIDDEN,
            error_code=ErrorCode.AUTH_UNAUTHORIZED,
            message=message,
            details=details
        )


class NotFoundException(APIException):
    """404 Not Found"""
    
    def __init__(self, resource: str = "Resource", identifier: str = None, details: dict = None):
        message = f"{resource} not found"
        if identifier:
            message += f": {identifier}"
        
        super().__init__(
            status_code=HTTP_404_NOT_FOUND,
            error_code=ErrorCode.DATA_ERROR,
            message=message,
            details=details or {"resource": resource, "identifier": identifier}
        )


class ConflictException(APIException):
    """409 Conflict"""
    
    def __init__(self, message: str = "Resource conflict", details: dict = None):
        super().__init__(
            status_code=HTTP_409_CONFLICT,
            error_code=ErrorCode.FAILED,
            message=message,
            details=details
        )


class GoneException(APIException):
    """410 Gone"""
    
    def __init__(self, message: str = "Resource no longer available", details: dict = None):
        super().__init__(
            status_code=HTTP_410_GONE,
            error_code=ErrorCode.FAILED,
            message=message,
            details=details
        )


class ValidationException(APIException):
    """422 Unprocessable Entity - for validation errors"""
    
    def __init__(self, message: str = "Validation error", details: dict = None):
        super().__init__(
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
            error_code=ErrorCode.FAILED,
            message=message,
            details=details
        )


class TooManyRequestsException(APIException):
    """429 Too Many Requests"""
    
    def __init__(self, message: str = "Rate limit exceeded", details: dict = None):
        super().__init__(
            status_code=HTTP_429_TOO_MANY_REQUESTS,
            error_code=ErrorCode.TIMEDOUT,
            message=message,
            details=details
        )


# ==================== Resource-Specific Exceptions ====================

# Product Exceptions
class ProductNotFoundException(APIException):
    def __init__(self, product_id: int = None, product_name: str = None):
        details = {}
        if product_id:
            details["product_id"] = product_id
        if product_name:
            details["product_name"] = product_name
        
        message = "Product not found"
        if product_id:
            message = f"Product with ID '{product_id}' not found"
        elif product_name:
            message = f"Product '{product_name}' not found"
        
        super().__init__(
            status_code=HTTP_404_NOT_FOUND,
            error_code=ErrorCode.PRODUCT_NOT_EXISTS,
            message=message,
            details=details
        )


class ProductAlreadyExistsException(APIException):
    def __init__(self, product_name: str = None, barcode: str = None):
        details = {}
        if product_name:
            details["product_name"] = product_name
        if barcode:
            details["barcode"] = barcode
        
        message = "Product already exists"
        if product_name:
            message = f"Product '{product_name}' already exists"
        elif barcode:
            message = f"Product with barcode '{barcode}' already exists"
        
        super().__init__(
            status_code=HTTP_409_CONFLICT,
            error_code=ErrorCode.PRODUCT_ALREADY_EXISTS,
            message=message,
            details=details
        )


class ProductCategoryNotFoundException(APIException):
    def __init__(self, category_id: int = None, category_name: str = None):
        details = {}
        if category_id:
            details["category_id"] = category_id
        if category_name:
            details["category_name"] = category_name
        
        message = "Product category not found"
        if category_id:
            message = f"Product category with ID '{category_id}' not found"
        
        super().__init__(
            status_code=HTTP_404_NOT_FOUND,
            error_code=ErrorCode.PRODUCT_CATEGORY_NOT_EXISTS,
            message=message,
            details=details
        )


class InsufficientStockException(APIException):
    def __init__(self, product_name: str, requested: int, available: int):
        super().__init__(
            status_code=HTTP_409_CONFLICT,
            error_code=ErrorCode.PRODUCT_QUANTITY_NOT_ENOUGH,
            message=f"Insufficient stock for '{product_name}'. Requested: {requested}, Available: {available}",
            details={
                "product": product_name,
                "requested_quantity": requested,
                "available_quantity": available
            }
        )


# User Exceptions
class UserNotFoundException(APIException):
    def __init__(self, user_id: int = None, username: str = None, user_email: str = None):
        details = {}
        if user_id:
            details["user_id"] = user_id
        if username:
            details["username"] = username
        if user_email:
            details["user_email"] = username
        
        message = "User not found"
        if user_id:
            message = f"User with ID '{user_id}' not found"
        elif username:
            message = f"User '{username}' not found"
        elif user_email:
            message = f"Email '{user_email}' not found"
        
        super().__init__(
            status_code=HTTP_404_NOT_FOUND,
            error_code=ErrorCode.APPUSER_NOT_EXISTS,
            message=message,
            details=details
        )


class UserAlreadyExistsException(APIException):
    def __init__(self, username: str = None, email: str = None):
        details = {}
        if username:
            details["username"] = username
        if email:
            details["email"] = email
        
        message = "User already exists"
        if username:
            message = f"User '{username}' already exists"
        elif email:
            message = f"User with email '{email}' already exists"
        
        super().__init__(
            status_code=HTTP_409_CONFLICT,
            error_code=ErrorCode.APPUSER_ALREADY_EXISTS,
            message=message,
            details=details
        )


class UserTypeNotFoundException(APIException):
    def __init__(self, user_type_id: int = None):
        details = {"user_type_id": user_type_id} if user_type_id else None
        super().__init__(
            status_code=HTTP_404_NOT_FOUND,
            error_code=ErrorCode.APPUSERTYPE_NOT_EXISTS,
            message=f"User type with ID '{user_type_id}' not found" if user_type_id else "User type not found",
            details=details
        )


# Recipe Exceptions
class RecipeNotFoundException(APIException):
    def __init__(self, recipe_id: int = None, recipe_name: str = None):
        details = {}
        if recipe_id:
            details["recipe_id"] = recipe_id
        if recipe_name:
            details["recipe_name"] = recipe_name
        
        message = "Recipe not found"
        if recipe_id:
            message = f"Recipe with ID '{recipe_id}' not found"
        elif recipe_name:
            message = f"Recipe '{recipe_name}' not found"
        
        super().__init__(
            status_code=HTTP_404_NOT_FOUND,
            error_code=ErrorCode.RECIPE_NOT_EXISTS,
            message=message,
            details=details
        )


class RecipeAlreadyExistsException(APIException):
    def __init__(self, recipe_name: str):
        super().__init__(
            status_code=HTTP_409_CONFLICT,
            error_code=ErrorCode.RECIPE_ALREADY_EXISTS,
            message=f"Recipe '{recipe_name}' already exists",
            details={"recipe_name": recipe_name}
        )


# Supplier Exceptions
class SupplierNotFoundException(APIException):
    def __init__(self, supplier_id: int = None, supplier_name: str = None):
        details = {}
        if supplier_id:
            details["supplier_id"] = supplier_id
        if supplier_name:
            details["supplier_name"] = supplier_name
        
        message = "Supplier not found"
        if supplier_id:
            message = f"Supplier with ID '{supplier_id}' not found"
        elif supplier_name:
            message = f"Supplier '{supplier_name}' not found"
        
        super().__init__(
            status_code=HTTP_404_NOT_FOUND,
            error_code=ErrorCode.SUPPLIER_NOT_EXISTS,
            message=message,
            details=details
        )


# Organisation Exceptions
class OrganisationNotFoundException(APIException):
    def __init__(self, org_id: int = None, org_name: str = None):
        details = {}
        if org_id:
            details["organisation_id"] = org_id
        if org_name:
            details["organisation_name"] = org_name
        
        message = "Organisation not found"
        if org_id:
            message = f"Organisation with ID '{org_id}' not found"
        elif org_name:
            message = f"Organisation '{org_name}' not found"
        
        super().__init__(
            status_code=HTTP_404_NOT_FOUND,
            error_code=ErrorCode.ORGANISATION_NOT_FOUND,
            message=message,
            details=details
        )


class OrganisationNameAlreadyUsedException(APIException):
    def __init__(self, org_name: str):
        super().__init__(
            status_code=HTTP_409_CONFLICT,
            error_code=ErrorCode.ORGANISATION_NAME_USED,
            message=f"Organisation name '{org_name}' is already in use",
            details={"organisation_name": org_name}
        )


# Order Exceptions
class OrderNotFoundException(APIException):
    def __init__(self, order_id: int = None):
        details = {"order_id": order_id} if order_id else None
        super().__init__(
            status_code=HTTP_404_NOT_FOUND,
            error_code=ErrorCode.ORDER_NOT_EXISTS,
            message=f"Order with ID '{order_id}' not found" if order_id else "Order not found",
            details=details
        )


class InvalidOrderStatusException(APIException):
    def __init__(self, current_status: str, requested_status: str):
        super().__init__(
            status_code=HTTP_400_BAD_REQUEST,
            error_code=ErrorCode.INVALID_ORDER_STATUS,
            message=f"Cannot change order status from '{current_status}' to '{requested_status}'",
            details={
                "current_status": current_status,
                "requested_status": requested_status
            }
        )


# Cart Exceptions
class CartNotFoundException(APIException):
    def __init__(self, cart_id: int = None):
        details = {"cart_id": cart_id} if cart_id else None
        super().__init__(
            status_code=HTTP_404_NOT_FOUND,
            error_code=ErrorCode.CART_NOT_EXISTS,
            message=f"Shopping cart with ID '{cart_id}' not found" if cart_id else "Shopping cart not found",
            details=details
        )


# Delivery Exceptions
class DeliveryNotFoundException(APIException):
    def __init__(self, delivery_id: int = None):
        details = {"delivery_id": delivery_id} if delivery_id else None
        super().__init__(
            status_code=HTTP_404_NOT_FOUND,
            error_code=ErrorCode.DELIVERY_NOT_EXISTS,
            message=f"Delivery with ID '{delivery_id}' not found" if delivery_id else "Delivery not found",
            details=details
        )


class DeliveryCannotBeUpdatedException(APIException):
    def __init__(self, delivery_id: int, current_status: str):
        super().__init__(
            status_code=HTTP_400_BAD_REQUEST,
            error_code=ErrorCode.DELIVERY_CANNOT_BE_UPDATED,
            message=f"Delivery {delivery_id} cannot be updated in current status: {current_status}",
            details={
                "delivery_id": delivery_id,
                "current_status": current_status
            }
        )


# Staff/Rule Exceptions
class RuleNotFoundException(APIException):
    def __init__(self, rule_id: int = None):
        details = {"rule_id": rule_id} if rule_id else None
        super().__init__(
            status_code=HTTP_404_NOT_FOUND,
            error_code=ErrorCode.RULE_NOT_EXISTS,
            message=f"Staff assignment with ID '{rule_id}' not found" if rule_id else "Staff assignment not found",
            details=details
        )


class RuleAlreadyExistsException(APIException):
    def __init__(self, user_id: int, provider_id: int):
        super().__init__(
            status_code=HTTP_409_CONFLICT,
            error_code=ErrorCode.RULE_ALREADY_EXISTS,
            message=f"Staff assignment already exists for user {user_id} at provider {provider_id}",
            details={
                "user_id": user_id,
                "provider_id": provider_id
            }
        )


# Notification Exceptions
class NotificationNotFoundException(APIException):
    def __init__(self, notification_id: int = None):
        details = {"notification_id": notification_id} if notification_id else None
        super().__init__(
            status_code=HTTP_404_NOT_FOUND,
            error_code=ErrorCode.NOTIFICATION_NOT_EXISTS,
            message=f"Notification with ID '{notification_id}' not found" if notification_id else "Notification not found",
            details=details
        )


# Serology Exceptions
class SerologyNotFoundException(APIException):
    def __init__(self, serology_id: int = None, patient_id: int = None):
        details = {}
        if serology_id:
            details["serology_id"] = serology_id
        if patient_id:
            details["patient_id"] = patient_id
        
        message = "Serology record not found"
        if serology_id:
            message = f"Serology record with ID '{serology_id}' not found"
        elif patient_id:
            message = f"Serology records for patient '{patient_id}' not found"
        
        super().__init__(
            status_code=HTTP_404_NOT_FOUND,
            error_code=ErrorCode.SEROLOGY_NOT_EXISTS,
            message=message,
            details=details
        )


class SerologyIndicatorNotFoundException(APIException):
    def __init__(self, indicator_id: int = None):
        details = {"indicator_id": indicator_id} if indicator_id else None
        super().__init__(
            status_code=HTTP_404_NOT_FOUND,
            error_code=ErrorCode.SEROLOGY_INDICATOR_NOT_EXISTS,
            message=f"Serology indicator with ID '{indicator_id}' not found" if indicator_id else "Serology indicator not found",
            details=details
        )


# person exceptions



# Location Exceptions
class LocationNotFoundException(APIException):
    def __init__(self, location_id: int = None):
        details = {"location_id": location_id} if location_id else None
        super().__init__(
            status_code=HTTP_404_NOT_FOUND,
            error_code=ErrorCode.LOCATION_NOT_FOUND,
            message=f"Location with ID '{location_id}' not found" if location_id else "Location not found",
            details=details
        )


# Ingredient Exceptions
class IngredientNotFoundException(APIException):
    def __init__(self, ingredient_id: int = None, ingredient_name: str = None):
        details = {}
        if ingredient_id:
            details["ingredient_id"] = ingredient_id
        if ingredient_name:
            details["ingredient_name"] = ingredient_name
        
        message = "Ingredient not found"
        if ingredient_id:
            message = f"Ingredient with ID '{ingredient_id}' not found"
        elif ingredient_name:
            message = f"Ingredient '{ingredient_name}' not found"
        
        super().__init__(
            status_code=HTTP_404_NOT_FOUND,
            error_code=ErrorCode.INGREDIENT_NOT_EXISTS,
            message=message,
            details=details
        )


class IngredientAlreadyExistsException(APIException):
    def __init__(self, ingredient_name: str):
        super().__init__(
            status_code=HTTP_409_CONFLICT,
            error_code=ErrorCode.INGREDIENT_ALREADY_EXISTS,
            message=f"Ingredient '{ingredient_name}' already exists",
            details={"ingredient_name": ingredient_name}
        )


# ==================== Database Exceptions ====================

class DatabaseException(APIException):
    """Base exception for all database-related errors"""
    
    def __init__(
        self,
        message: str = "Database operation failed",
        details: Optional[Dict] = None,
        status_code: int = HTTP_500_INTERNAL_SERVER_ERROR
    ):
        super().__init__(
            status_code=status_code,
            error_code=ErrorCode.DATABASE_ERROR,
            message=message,
            details=details
        )


class DatabaseConnectionException(DatabaseException):
    """Exception for database connection failures"""
    
    def __init__(
        self,
        error: Optional[str] = None,
        db_uri: Optional[str] = None,
        details: Optional[Dict] = None
    ):
        message = "Failed to connect to database"
        error_details = details or {}
        
        if error:
            error_details["error"] = error
        if db_uri:
            # Mask sensitive info
            masked_uri = db_uri.split('@')[-1] if '@' in db_uri else 'unknown'
            error_details["db_uri"] = masked_uri
        
        super().__init__(
            message=message,
            details=error_details,
            status_code=HTTP_511_NETWORK_AUTHENTICATION_REQUIRED
        )


class DatabaseTimeoutException(DatabaseException):
    """Exception for database timeout errors"""
    
    def __init__(
        self,
        operation: str = "query",
        timeout_seconds: int = 30,
        details: Optional[Dict] = None
    ):
        message = f"Database {operation} timed out after {timeout_seconds} seconds"
        error_details = details or {}
        error_details.update({
            "operation": operation,
            "timeout_seconds": timeout_seconds
        })
        
        super().__init__(
            message=message,
            details=error_details,
            status_code=HTTP_504_GATEWAY_TIMEOUT
        )


class DatabaseIntegrityException(DatabaseException):
    """Exception for integrity constraint violations"""
    
    def __init__(
        self,
        message: str = "Database integrity constraint violated",
        constraint_name: Optional[str] = None,
        record_type: Optional[str] = None,
        details: Optional[Dict] = None
    ):
        error_details = details or {}
        
        if constraint_name:
            error_details["constraint"] = constraint_name
        if record_type:
            error_details["record_type"] = record_type
        
        super().__init__(
            message=message,
            details=error_details,
            status_code=HTTP_409_CONFLICT
        )


class DuplicateRecordException(DatabaseIntegrityException):
    """Exception for duplicate record insertion"""
    
    def __init__(
        self,
        record_type: str,
        unique_field: str,
        unique_value: Any,
        details: Optional[Dict] = None
    ):
        message = f"{record_type} with {unique_field} '{unique_value}' already exists"
        error_details = details or {}
        error_details.update({
            "record_type": record_type,
            "unique_field": unique_field,
            "unique_value": unique_value
        })
        
        super().__init__(
            message=message,
            constraint_name=f"unique_{unique_field}",
            record_type=record_type,
            details=error_details
        )


class RecordNotFoundException(DatabaseException):
    """Exception when a record is not found"""
    
    def __init__(
        self,
        record_type: str,
        record_id: Optional[Any] = None,
        message: Optional[str] = None,
        details: Optional[Dict] = None
    ):
        if message is None:
            if record_id is not None:
                message = f"{record_type} with ID '{record_id}' not found"
            else:
                message = f"{record_type} not found"
        
        error_details = details or {}
        error_details["record_type"] = record_type
        if record_id is not None:
            error_details["record_id"] = record_id
        
        super().__init__(
            message=message,
            details=error_details,
            status_code=HTTP_404_NOT_FOUND
        )


class DatabaseQueryException(DatabaseException):
    """Exception for malformed or invalid database queries"""
    
    def __init__(
        self,
        message: str = "Invalid database query",
        query_type: Optional[str] = None,
        details: Optional[Dict] = None
    ):
        error_details = details or {}
        if query_type:
            error_details["query_type"] = query_type
        
        super().__init__(
            message=message,
            details=error_details,
            status_code=HTTP_400_BAD_REQUEST
        )


class DatabaseTransactionException(DatabaseException):
    """Exception for transaction-related errors"""
    
    def __init__(
        self,
        operation: str = "transaction",
        message: Optional[str] = None,
        details: Optional[Dict] = None
    ):
        if message is None:
            message = f"Database {operation} failed"
        
        error_details = details or {}
        error_details["operation"] = operation
        
        super().__init__(
            message=message,
            details=error_details,
            status_code=HTTP_500_INTERNAL_SERVER_ERROR
        )


class DatabaseUnavailableException(DatabaseException):
    """Exception when database is unavailable"""
    
    def __init__(
        self,
        reason: str = "Database service unavailable",
        details: Optional[Dict] = None
    ):
        super().__init__(
            message=reason,
            details=details,
            status_code=HTTP_503_SERVICE_UNAVAILABLE
        )


class BatchOperationException(DatabaseException):
    """Exception for batch operation failures"""
    
    def __init__(
        self,
        operation: str,
        record_count: int,
        failed_count: int,
        errors: Optional[List] = None,
        details: Optional[Dict] = None
    ):
        message = f"Batch {operation} failed for {failed_count} of {record_count} records"
        error_details = details or {}
        error_details.update({
            "operation": operation,
            "total_records": record_count,
            "failed_records": failed_count,
            "success_rate": f"{(record_count - failed_count) / record_count * 100:.1f}%"
        })
        
        if errors:
            error_details["errors"] = errors
        
        super().__init__(
            message=message,
            details=error_details,
            status_code=HTTP_500_INTERNAL_SERVER_ERROR
        )


# ==================== Authentication Exceptions ====================

class AuthenticationException(APIException):
    """Base exception for authentication errors"""
    
    def __init__(
        self,
        message: str = "Authentication failed",
        error_code: ErrorCode = ErrorCode.AUTH_REQUIRED,
        details: Optional[Dict] = None
    ):
        super().__init__(
            status_code=HTTP_401_UNAUTHORIZED,
            error_code=error_code,
            message=message,
            details=details
        )


class InvalidCredentialsException(AuthenticationException):
    """Exception for invalid username/password"""
    
    def __init__(self, details: Optional[Dict] = None):
        super().__init__(
            message="Invalid username or password",
            error_code=ErrorCode.INCORRECT_CREDENTIALS,
            details=details
        )


class TokenExpiredException(AuthenticationException):
    """Exception for expired tokens"""
    
    def __init__(self, details: Optional[Dict] = None):
        super().__init__(
            message="Authentication token has expired",
            error_code=ErrorCode.AUTH_DECODE_FAILED,
            details=details
        )


class TokenInvalidException(AuthenticationException):
    """Exception for invalid tokens"""
    
    def __init__(self, details: Optional[Dict] = None):
        super().__init__(
            message="Invalid authentication token",
            error_code=ErrorCode.AUTH_DECODE_FAILED,
            details=details
        )


# ==================== Business Logic Exceptions ====================

class BusinessRuleViolationException(APIException):
    """Exception for business rule violations"""
    
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            status_code=HTTP_400_BAD_REQUEST,
            error_code=ErrorCode.FAILED,
            message=message,
            details=details
        )


class PaymentFailedException(APIException):
    """Exception for payment processing failures"""
    
    def __init__(self, message: str = "Payment processing failed", details: Optional[Dict] = None):
        super().__init__(
            status_code=HTTP_400_BAD_REQUEST,
            error_code=ErrorCode.FAILED,
            message=message,
            details=details
        )


class ServiceNotFoundException(APIException):
    """Exception for service not found"""
    
    def __init__(self, service_id: int = None, service_name: str = None):
        details = {}
        if service_id:
            details["service_id"] = service_id
        if service_name:
            details["service_name"] = service_name
        
        message = "Service not found"
        if service_id:
            message = f"Service with ID '{service_id}' not found"
        elif service_name:
            message = f"Service '{service_name}' not found"
        
        super().__init__(
            status_code=HTTP_404_NOT_FOUND,
            error_code=ErrorCode.SERVICE_NOT_FOUND,
            message=message,
            details=details
        )


# ==================== Authentication Exceptions (add this) ====================

class OAuthException(APIException):
    """Exception for OAuth authentication errors"""
    
    def __init__(
        self, 
        error: str, 
        provider: str = None,
        details: dict = None
    ):
        error_details = details or {}
        error_details["oauth_error"] = str(error)
        
        if provider:
            error_details["oauth_provider"] = provider
        
        message = f"OAuth authentication failed"
        if provider:
            message = f"OAuth authentication failed for provider '{provider}'"
        
        super().__init__(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.INTERFACE_ERROR,
            message=message,
            details=error_details
        )


class OAuthProviderNotSupportedException(APIException):
    """Exception for unsupported OAuth providers"""
    
    def __init__(self, provider: str, supported_providers: list = None):
        details = {
            "requested_provider": provider,
            "supported_providers": supported_providers or ["google", "facebook", "github"]
        }
        
        super().__init__(
            status_code=HTTP_400_BAD_REQUEST,
            error_code=ErrorCode.AUTH_REQUIRED,
            message=f"OAuth provider '{provider}' is not supported",
            details=details
        )


class OAuthCallbackException(APIException):
    """Exception for OAuth callback errors"""
    
    def __init__(self, error: str, provider: str = None, state_mismatch: bool = False):
        details = {
            "callback_error": str(error),
            "state_mismatch": state_mismatch
        }
        
        if provider:
            details["oauth_provider"] = provider
        
        message = "OAuth callback processing failed"
        if state_mismatch:
            message = "OAuth state validation failed - possible CSRF attack"
        
        super().__init__(
            status_code=HTTP_400_BAD_REQUEST,
            error_code=ErrorCode.AUTH_DECODE_FAILED,
            message=message,
            details=details
        )


class OAuthTokenExchangeException(APIException):
    """Exception for OAuth token exchange failures"""
    
    def __init__(self, error: str, provider: str = None, auth_code_error: bool = False):
        details = {
            "token_exchange_error": str(error),
            "auth_code_error": auth_code_error
        }
        
        if provider:
            details["oauth_provider"] = provider
        
        message = "Failed to exchange OAuth authorization code for access token"
        
        super().__init__(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.INTERFACE_ERROR,
            message=message,
            details=details
        )


class OAuthUserInfoException(APIException):
    """Exception for OAuth user info retrieval failures"""
    
    def __init__(self, error: str, provider: str = None):
        details = {
            "user_info_error": str(error)
        }
        
        if provider:
            details["oauth_provider"] = provider
        
        message = f"Failed to retrieve user information from OAuth provider"
        if provider:
            message = f"Failed to retrieve user information from '{provider}'"
        
        super().__init__(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.INTERFACE_ERROR,
            message=message,
            details=details
        )

# Add to core/exceptions.py in the Authentication Exceptions section

# ==================== Auth Client Exceptions ====================

class AuthClientException(APIException):
    """Base exception for authentication client errors"""
    
    def __init__(
        self,
        message: str = "Authentication service error",
        error_code: ErrorCode = ErrorCode.INTERFACE_ERROR,
        status_code: int = HTTP_502_BAD_GATEWAY,
        details: dict = None
    ):
        super().__init__(
            status_code=status_code,
            error_code=error_code,
            message=message,
            details=details
        )


class AuthServiceUnavailableException(AuthClientException):
    """Exception when authentication service is unavailable"""
    
    def __init__(self, service: str = "authentication", error: str = None):
        details = {"service": service, "unavailable": True}
        if error:
            details["error"] = error
        
        super().__init__(
            message=f"{service.capitalize()} service is unavailable",
            error_code=ErrorCode.INTERFACE_ERROR,
            status_code=HTTP_502_BAD_GATEWAY,
            details=details
        )


class AuthRegistrationException(APIException):
    """Exception raised when user registration fails."""
    
    def __init__(
        self,
        error: str,
        username: str = None,
        details: dict = None
    ):
        # Extract error_code from details if present
        error_code = ErrorCode.USER_AUTH_CREATION_FAILED
        status_code = HTTP_400_BAD_REQUEST
        
        if details:
            if "error_code" in details:
                error_code = details["error_code"]
            elif "code" in details:
                error_code = details["code"]
            
            if "status_code" in details:
                status_code = details["status_code"]
        
        # If the error_code is USERNAME_ALREADY_REGISTERED, use 409
        if error_code == "USERNAME_ALREADY_REGISTERED":
            status_code = HTTP_409_CONFLICT
        
        super().__init__(
            status_code=status_code,
            error_code=error_code,
            message=error,
            details=details or {}
        )
        self.username = username




class AuthLoginException(AuthClientException):
    """Exception for login failures"""
    
    def __init__(self, error: str, username: str = None, details: dict = None):
        error_details = details or {}
        error_details["login_error"] = error
        
        if username:
            error_details["username"] = username
        
        super().__init__(
            message="Authentication failed",
            error_code=ErrorCode.INCORRECT_CREDENTIALS,
            status_code=HTTP_401_UNAUTHORIZED,
            details=error_details
        )


class AuthPasswordChangeException(AuthClientException):
    """Exception for password change failures"""
    
    def __init__(self, error: str, user_id: int = None, username: str = None, details: dict = None):
        error_details = details or {}
        error_details["password_change_error"] = error
        
        if user_id:
            error_details["user_id"] = user_id
        if username:
            error_details["username"] = username
        
        super().__init__(
            message="Failed to change password",
            error_code=ErrorCode.USER_UPDATE_FAILED,
            status_code=HTTP_502_BAD_GATEWAY,
            details=error_details
        )


class AuthUserDeletionException(AuthClientException):
    """Exception for user deletion failures"""
    
    def __init__(self, error: str, user_id: int = None, username: str = None, details: dict = None):
        error_details = details or {}
        error_details["deletion_error"] = error
        
        if user_id:
            error_details["user_id"] = user_id
        if username:
            error_details["username"] = username
        
        super().__init__(
            message="Failed to delete user from authentication service",
            error_code=ErrorCode.USER_DELETE_FAILED,
            status_code=HTTP_502_BAD_GATEWAY,
            details=error_details
        )


class AuthTokenExpiredException(AuthClientException):
    """Exception for expired authentication tokens"""
    
    def __init__(self, token: str = None, details: dict = None):
        error_details = details or {}
        if token:
            error_details["token_preview"] = token[:10] + "..." if len(token) > 10 else token
        
        super().__init__(
            message="Authentication token has expired",
            error_code=ErrorCode.AUTH_DECODE_FAILED,
            status_code=HTTP_401_UNAUTHORIZED,
            details=error_details
        )


class AuthTokenInvalidException(AuthClientException):
    """Exception for invalid authentication tokens"""
    
    def __init__(self, error: str = None, details: dict = None):
        error_details = details or {}
        if error:
            error_details["error"] = error
        
        super().__init__(
            message="Invalid authentication token",
            error_code=ErrorCode.AUTH_DECODE_FAILED,
            status_code=HTTP_401_UNAUTHORIZED,
            details=error_details
        )


class AuthNetworkException(AuthClientException):
    """Exception for network-related errors when calling auth service"""
    
    def __init__(self, error: str, endpoint: str = None, details: dict = None):
        error_details = details or {}
        error_details["network_error"] = error
        
        if endpoint:
            error_details["endpoint"] = endpoint
        
        super().__init__(
            message="Network error when communicating with authentication service",
            error_code=ErrorCode.USER_NET_FAILED,
            status_code=HTTP_502_BAD_GATEWAY,
            details=error_details
        )


# ==================== Utility Functions ====================

def get_exception_handler(exception_class):
    """Decorator to register exception handlers with FastAPI"""
    def decorator(func):
        return func
    return decorator



class LocationException(APIException):
    """Base exception for location-related errors"""
    
    def __init__(
        self,
        message: str = "Location service error",
        error_code: ErrorCode = ErrorCode.LOCATION_NOT_EXISTS,
        status_code: int = HTTP_400_BAD_REQUEST,
        details: Dict[str, Any] = None
    ):
        super().__init__(
            status_code=status_code,
            error_code=error_code,
            message=message,
            details=details or {}
        )


class LocationDeleteFailedException(LocationException):
    """
    Exception when location deletion fails.
    
    This can happen when:
    - Location has references (e.g., used by deliveries, providers, etc.)
    - Database constraint violations
    - Location doesn't exist
    - Force delete is required but not provided
    """
    
    def __init__(
        self,
        location_id: str = None,
        error: str = None,
        has_references: bool = False,
        reference_count: int = 0,
        reference_tables: List[str] = None,
        force_delete_required: bool = False,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        if location_id:
            error_details["location_id"] = location_id
        if error:
            error_details["delete_error"] = error
        if has_references:
            error_details["has_references"] = has_references
        if reference_count:
            error_details["reference_count"] = reference_count
        if reference_tables:
            error_details["reference_tables"] = reference_tables
        if force_delete_required:
            error_details["force_delete_required"] = force_delete_required
        
        message = "Failed to delete location"
        if location_id:
            message = f"Failed to delete location with ID '{location_id}'"
        
        # Add specific reason if known
        if has_references:
            ref_msg = f"Location has {reference_count} reference(s)"
            if reference_tables:
                ref_msg += f" in tables: {', '.join(reference_tables)}"
            message += f" - {ref_msg}. Use force_delete=true to delete anyway."
        elif force_delete_required:
            message += " - This location has dependencies. Use force_delete=true to delete."
        elif error:
            message += f" - {error}"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.LOCATION_DELETE_FAILED,
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            details=error_details
        )


