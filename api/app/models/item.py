"""
Item models for JSTC API

This module contains all Pydantic models related to items.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ItemBase(BaseModel):
    """Base item model with common fields"""
    name: str = Field(..., min_length=1, max_length=100, description="The name of the item")
    description: Optional[str] = Field(None, max_length=500, description="Optional description of the item")
    price: float = Field(..., gt=0, description="The price of the item (must be positive)")
    tax: Optional[float] = Field(None, ge=0, description="Tax amount (must be non-negative)")


class ItemCreate(ItemBase):
    """Model for creating a new item"""
    pass


class ItemUpdate(BaseModel):
    """Model for updating an existing item (all fields optional)"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    price: Optional[float] = Field(None, gt=0)
    tax: Optional[float] = Field(None, ge=0)


class Item(ItemBase):
    """Full item model with all fields including ID and metadata"""
    id: int = Field(..., description="Unique identifier for the item")
    created_at: Optional[datetime] = Field(None, description="When the item was created")
    updated_at: Optional[datetime] = Field(None, description="When the item was last updated")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "Laptop",
                "description": "Gaming laptop with high-end specs",
                "price": 999.99,
                "tax": 99.99,
                "created_at": "2025-10-14T10:30:00Z",
                "updated_at": "2025-10-14T10:30:00Z"
            }
        }


class ItemResponse(Item):
    """Response model for item operations"""
    pass


class ItemListResponse(BaseModel):
    """Response model for listing items with pagination info"""
    items: list[Item] = Field(..., description="List of items")
    total: int = Field(..., description="Total number of items")
    skip: int = Field(..., description="Number of items skipped")
    limit: int = Field(..., description="Maximum number of items returned")
    
    class Config:
        json_schema_extra = {
            "example": {
                "items": [
                    {
                        "id": 1,
                        "name": "Laptop",
                        "description": "Gaming laptop",
                        "price": 999.99,
                        "tax": 99.99,
                        "created_at": "2025-10-14T10:30:00Z",
                        "updated_at": "2025-10-14T10:30:00Z"
                    }
                ],
                "total": 1,
                "skip": 0,
                "limit": 100
            }
        }
