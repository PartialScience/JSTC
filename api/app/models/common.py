"""
Common response models for JSTC API
"""

from pydantic import BaseModel, Field
from typing import Optional, Any


class SuccessResponse(BaseModel):
    """Standard success response model"""
    success: bool = Field(True, description="Indicates if the operation was successful")
    message: str = Field(..., description="Success message")
    data: Optional[Any] = Field(None, description="Optional response data")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Operation completed successfully",
                "data": None
            }
        }


class ErrorResponse(BaseModel):
    """Standard error response model"""
    success: bool = Field(False, description="Indicates that the operation failed")
    error: str = Field(..., description="Error type or code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Any] = Field(None, description="Additional error details")

    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error": "NOT_FOUND",
                "message": "The requested resource was not found",
                "details": None
            }
        }


class HealthResponse(BaseModel):
    """Health check response model"""
    status: str = Field(..., description="Service health status")
    timestamp: str = Field(..., description="Current timestamp")
    version: str = Field(..., description="API version")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2025-10-14T10:30:00Z",
                "version": "1.0.0"
            }
        }
