# constants/error_messages.py
"""Human-readable error messages mapped to error codes"""


# Map error codes to user-friendly messages
from core.exceptions.error_codes import ErrorCode


ERROR_MESSAGES = {
    # Generic
    ErrorCode.SUCCESS: "Operation completed successfully",
    ErrorCode.FAILED: "Operation failed",
    ErrorCode.TIMEDOUT: "Operation timed out",
    ErrorCode.UNKNOWN: "An unknown error occurred",
    
    # Authentication
    ErrorCode.AUTH_REQUIRED: "Authentication is required to access this resource",
    ErrorCode.AUTH_DECODE_FAILED: "Failed to decode authentication token",
    ErrorCode.AUTH_UNAUTHORIZED: "You are not authorized to perform this action",
    ErrorCode.INCORRECT_CREDENTIALS: "Invalid username or password",
    ErrorCode.USER_AUTH_CREATION_FAILED: "Failed to create user authentication",
    
    # Product
    ErrorCode.PRODUCT_ALREADY_EXISTS: "A product with this identifier already exists",
    ErrorCode.PRODUCT_CATEGORY_NOT_EXISTS: "The specified product category does not exist",
    ErrorCode.PRODUCT_NOT_EXISTS: "The requested product does not exist",
    ErrorCode.PRODUCT_QUANTITY_NOT_ENOUGH: "Insufficient product quantity available",
    ErrorCode.PRODUCT_QUANTITY_RESTORE_FAILED: "Failed to restore product quantity",
    ErrorCode.PRODUCT_SUPPLIER_NOT_EXISTS: "The product supplier does not exist",
    ErrorCode.PRODUCT_SUPPLIER_ALREADY_EXISTS: "This supplier is already associated with the product",
    ErrorCode.PRODUCT_FETCH_NOT_FOUND: "Unable to retrieve product information",
    ErrorCode.PRODUCT_INSERT_FAILED: "Failed to add product to database",
    ErrorCode.PRODUCT_UPDATE_FAILED: "Failed to update product information",
    ErrorCode.PRODUCT_DELETE_FAILED: "Failed to delete product",
    ErrorCode.PRODUCT_SEARCH_NOT_FOUND: "No products match your search criteria",
    ErrorCode.PRODUCT_IMAGE_NOT_FOUND: "Product image not found",
    
    # Recipe
    ErrorCode.RECIPE_ALREADY_EXISTS: "A recipe with this name already exists",
    ErrorCode.RECIPE_CATEGORY_NOT_EXISTS: "The specified recipe category does not exist",
    ErrorCode.RECIPE_NOT_EXISTS: "The requested recipe does not exist",
    ErrorCode.RECIPE_FETCH_NOT_FOUND: "Unable to retrieve recipe information",
    ErrorCode.RECIPE_INSERT_FAILED: "Failed to add recipe to database",
    ErrorCode.RECIPE_UPDATE_FAILED: "Failed to update recipe information",
    ErrorCode.RECIPE_DELETE_FAILED: "Failed to delete recipe",
    ErrorCode.RECIPE_SEARCH_NOT_FOUND: "No recipes match your search criteria",
    
    # Supplier
    ErrorCode.SUPPLIER_NOT_EXISTS: "The requested supplier does not exist",
    ErrorCode.SUPPLIER_TYPE_NOT_EXISTS: "The specified supplier type does not exist",
    ErrorCode.SUPPLIER_FETCH_NOT_FOUND: "Unable to retrieve supplier information",
    ErrorCode.SUPPLIER_INSERT_FAILED: "Failed to add supplier to database",
    ErrorCode.SUPPLIER_UPDATE_FAILED: "Failed to update supplier information",
    ErrorCode.SUPPLIER_DELETE_FAILED: "Failed to delete supplier",
    
    # Organisation
    ErrorCode.ORGANISATION_NOT_FOUND: "The requested organisation does not exist",
    ErrorCode.ORGANISATION_NAME_USED: "An organisation with this name already exists",
    ErrorCode.ORG_ALREADY_EXISTS: "This organisation already exists in the system",
    ErrorCode.ORG_INSERT_FAILED: "Failed to create organisation",
    ErrorCode.ORG_UPDATE_FAILED: "Failed to update organisation information",
    ErrorCode.ORG_DELETE_FAILED: "Failed to delete organisation",
    
    # User
    ErrorCode.APPUSER_ALREADY_EXISTS: "A user with this username already exists",
    ErrorCode.APPUSER_NOT_EXISTS: "The requested user does not exist",
    ErrorCode.APPUSERTYPE_NOT_EXISTS: "The specified user type does not exist",
    ErrorCode.USER_FETCH_NOT_FOUND: "Unable to retrieve user information",
    ErrorCode.USER_INSERT_FAILED: "Failed to create user account",
    ErrorCode.USER_UPDATE_FAILED: "Failed to update user information",
    ErrorCode.USER_DELETE_FAILED: "Failed to delete user account",
    ErrorCode.USER_NET_FAILED: "Network error while processing user request",
    
    # Person
    ErrorCode.PERSON_NOT_EXISTS: "The requested person record does not exist",
    ErrorCode.PERSON_INSERT_FAILED: "Failed to create person record",
    ErrorCode.PERSON_UPDATE_FAILED: "Failed to update person information",
    ErrorCode.PERSON_DELETE_FAILED: "Failed to delete person record",
    ErrorCode.PERSON_DETAIL_INSERT_FAILED: "Failed to add person details",
    ErrorCode.PERSON_DETAILS_NOT_FOUND: "Person details not found",
    ErrorCode.PERSON_FETCH_NOT_FOUND: "Unable to retrieve person information",
    
    # Location
    ErrorCode.LOCATION_NOT_FOUND: "The specified location does not exist",
    ErrorCode.LOCATION_UPDATE_FAILED: "Failed to update location information",
    ErrorCode.LOCATION_FETCH_NOT_FOUND: "Unable to retrieve location information",
    ErrorCode.LOCATION_INSERT_FAILED: "Failed to add location",
    ErrorCode.ADDRESS_NOT_FOUND: "The specified address does not exist",
    
    # Serology
    ErrorCode.SEROLOGY_ALREADY_EXISTS: "A serology record already exists for this patient and indicator",
    ErrorCode.SEROLOGY_INDICATOR_NOT_EXISTS: "The specified serology indicator does not exist",
    ErrorCode.SEROLOGY_NOT_EXISTS: "The requested serology record does not exist",
    ErrorCode.SEROLOGY_FETCH_NOT_FOUND: "Unable to retrieve serology records",
    ErrorCode.SEROLOGY_INSERT_FAILED: "Failed to add serology record",
    ErrorCode.SEROLOGY_UPDATE_FAILED: "Failed to update serology record",
    ErrorCode.SEROLOGY_DELETE_FAILED: "Failed to delete serology record",
    
    # Symptoms
    ErrorCode.SYMPTOM_FETCH_NOT_FOUND: "Unable to retrieve symptom information",
    ErrorCode.SYMPTOM_INSERT_FAILED: "Failed to record symptom occurrence",
    ErrorCode.SYMPTOM_UPDATE_FAILED: "Failed to update symptom record",
    ErrorCode.SYMPTOM_DELETE_FAILED: "Failed to delete symptom record",
    ErrorCode.SYMPTOM_NOT_EXISTS: "The specified symptom does not exist",
    ErrorCode.SYMPTOM_OCCURRENCE_NOT_EXISTS: "The symptom occurrence record does not exist",
    
    # Patient
    ErrorCode.PATIENT_NOT_EXISTS: "The requested patient record does not exist",
    ErrorCode.PATIENT_INSERT_FAILED: "Failed to create patient record",
    ErrorCode.PATIENT_UPDATE_FAILED: "Failed to update patient information",
    
    # Blood type
    ErrorCode.BLOOD_TYPE_NOT_EXISTS: "The specified blood type does not exist",
    
    # Ingredient
    ErrorCode.INGREDIENT_ALREADY_EXISTS: "This ingredient already exists in the system",
    ErrorCode.INGREDIENT_INSERT_FAILED: "Failed to add ingredient",
    ErrorCode.INGREDIENT_NOT_EXISTS: "The requested ingredient does not exist",
    ErrorCode.INGREDIENT_DELETE_FAILED: "Failed to delete ingredient",
    
    # Order
    ErrorCode.ORDER_FETCH_NOT_FOUND: "Unable to retrieve order information",
    ErrorCode.ORDER_INSERT_CONFLICT: "Order could not be placed due to conflicts",
    ErrorCode.ORDER_LIB_FAILED: "Order processing library error",
    ErrorCode.ORDER_UPDATE_FAILED: "Failed to update order",
    ErrorCode.ORDER_DELETE_FAILED: "Failed to delete order",
    ErrorCode.ORDER_NOT_EXISTS: "The requested order does not exist",
    ErrorCode.INVALID_ORDER_STATUS: "Invalid order status transition",
    ErrorCode.ORDER_ITEMS_DELETE_FAILED: "Failed to delete order items",
    ErrorCode.ORDER_ITEM_INSERT_FAILED: "Failed to add items to order",
    
    # Cart
    ErrorCode.CART_NOT_EXISTS: "The requested shopping cart does not exist",
    ErrorCode.CART_INSERT_FAILED: "Failed to create shopping cart",
    
    # Delivery
    ErrorCode.DELIVERY_NOT_EXISTS: "The requested delivery record does not exist",
    ErrorCode.DELIVERY_UPDATE_FAILED: "Failed to update delivery information",
    ErrorCode.DELIVERY_CANNOT_BE_UPDATED: "Delivery cannot be updated in its current status",
    ErrorCode.DELIVERY_BULK_UPDATE_FAILED: "Bulk delivery update operation failed",
    ErrorCode.DELIVERY_DELETE_FAILED: "Failed to delete delivery record",
    ErrorCode.DELIVERY_BULK_DELETE_FAILED: "Bulk delivery deletion failed",
    ErrorCode.DELIVERY_INSERT_FAILED: "Failed to create delivery record",
    ErrorCode.DELIVERY_VALIDATION_FAILED: "Delivery information validation failed",
    
    # Service
    ErrorCode.SERVICE_NOT_FOUND: "The requested service does not exist",
    ErrorCode.SERVICE_INSERT_CONFLICT: "Service could not be created due to conflicts",
    ErrorCode.SERVICE_CATEGORY_NOT_FOUND: "The service category does not exist",
    
    # Staff/Rules
    ErrorCode.RULE_ALREADY_EXISTS: "This staff assignment already exists",
    ErrorCode.RULE_NOT_EXISTS: "The staff assignment record does not exist",
    ErrorCode.RULE_INSERT_FAILED: "Failed to create staff assignment",
    ErrorCode.RULE_UPDATE_FAILED: "Failed to update staff assignment",
    ErrorCode.RULE_DELETE_FAILED: "Failed to delete staff assignment",
    ErrorCode.RULE_INVALID_STATUS: "Invalid staff assignment status",
    ErrorCode.INVITATION_ALREADY_PROCESSED: "This invitation has already been processed",
    
    # Notifications
    ErrorCode.NOTIFICATION_NOT_EXISTS: "The requested notification does not exist",
    ErrorCode.NOTIFICATION_ALREADY_EXISTS: "This notification already exists",
    ErrorCode.NOTIFICATION_INSERT_FAILED: "Failed to send notification",
    ErrorCode.NOTIFICATION_UPDATE_FAILED: "Failed to update notification",
    ErrorCode.NOTIFICATION_DELETE_FAILED: "Failed to delete notification",
    ErrorCode.NOTIFICATION_BULK_INSERT_FAILED: "Failed to send bulk notifications",
    
    # Images
    ErrorCode.IMAGE_INSERT_FAILED: "Failed to upload image",
    ErrorCode.IMAGE_UPDATE_FAILED: "Failed to update image",
    
    # Client
    ErrorCode.CLIENT_NOT_EXISTS: "The client record does not exist",
    
    # Health
    ErrorCode.HEALTH_FETCH_FAILED: "Unable to retrieve health records",
    ErrorCode.HEALTH_DELETE_FAILED: "Failed to delete health record",
    
    # Database
    ErrorCode.INTEGRITY_ERROR: "Database integrity constraint violated",
    ErrorCode.DATA_ERROR: "Data error occurred in database operation",
    ErrorCode.OPERATIONAL_ERROR: "Database connection or operational error",
    ErrorCode.PROGRAMMING_ERROR: "Database programming error",
    ErrorCode.DATABASE_ERROR: "Unspecified database error occurred",
    ErrorCode.INTERNAL_ERROR: "Internal system error",
    ErrorCode.INTERFACE_ERROR: "Database interface error",
    ErrorCode.STATEMENT_ERROR: "SQL statement error",
    ErrorCode.SQLALCHEMY_ERROR: "Database ORM error",
    
    # Network
    ErrorCode.NETWORK_TIMEOUT: "Network request timed out",
    
    # Internal server
    ErrorCode.INTERNAL_SERVER_ERROR: "Internal server error occurred",
    ErrorCode.HTTP_EXCEPTION: "HTTP protocol error",
    
    # Success
    ErrorCode.PUT_SUCCESS: "Resource updated successfully",
}


def get_error_message(error_code: ErrorCode, default: str = None) -> str:
    """Get human-readable error message for an error code"""
    return ERROR_MESSAGES.get(
        error_code, 
        default or f"Error: {error_code.value if hasattr(error_code, 'value') else error_code}"
    )