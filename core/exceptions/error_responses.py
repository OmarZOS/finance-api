# core/error_responses.py
from typing import Dict, Any, Optional
from fastapi import Request
from fastapi.responses import JSONResponse
from datetime import datetime, timezone
import uuid


class ErrorResponse:
    """Builder for standardized error responses"""
    
    def __init__(self, request: Optional[Request] = None):
        self.request = request
        self.data = {
            "success": False,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": str(uuid.uuid4())
        }
        
        if request:
            self.data["path"] = request.url.path
            # Try to get request ID from headers if present
            if request_id := request.headers.get("X-Request-ID"):
                self.data["request_id"] = request_id
    
    def build(self) -> Dict[str, Any]:
        """Return the error response dictionary"""
        return self.data
    
    def to_response(self, status_code: int, headers: Optional[Dict] = None) -> JSONResponse:
        """Convert to FastAPI JSONResponse"""
        return JSONResponse(
            status_code=status_code,
            content=self.data,
            headers=headers
        )
    
    def with_code(self, code: str):
        """Add error code"""
        self.data["code"] = code
        return self
    
    def with_message(self, message: str):
        """Add error message"""
        self.data["message"] = message
        return self
    
    def with_details(self, details: Dict[str, Any]):
        """Add error details"""
        self.data["details"] = details
        return self
    
    def with_status_code(self, status_code: int):
        """Add HTTP status code"""
        self.data["status_code"] = status_code
        return self
    
    def with_validation_errors(self, errors: list):
        """Add validation errors (for 422 responses)"""
        self.data["code"] = "VALIDATION_ERROR"
        self.data["message"] = "Request validation failed"
        self.data["details"] = {"errors": errors}
        return self


def create_error_response(
    status_code: int,
    error_code: str,
    message: str,
    request: Optional[Request] = None,
    details: Optional[Dict] = None,
    headers: Optional[Dict] = None
) -> JSONResponse:
    """Factory function to create a JSON error response"""
    builder = ErrorResponse(request)
    response = (
        builder
        .with_status_code(status_code)
        .with_code(error_code)
        .with_message(message)
    )
    
    if details:
        response.with_details(details)
    
    return response.to_response(status_code, headers)


def create_validation_error_response(
    request: Request,
    errors: list,
    headers: Optional[Dict] = None
) -> JSONResponse:
    """Create a 422 validation error response"""
    builder = ErrorResponse(request)
    response = (
        builder
        .with_status_code(422)
        .with_validation_errors(errors)
    )
    return response.to_response(422, headers)