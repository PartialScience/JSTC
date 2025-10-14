"""
Items router for JSTC API

T@router.get("", response_model=ItemListResponse, summary="Get all items")
async def get_items(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(
        default=settings.pagination.default_page_size,
        ge=1, 
        le=settings.pagination.max_page_size,
        description=f"Maximum number of items to return (1-{settings.pagination.max_page_size})"
    )
):odule contains all item-related endpoints.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List
from datetime import datetime

from ..models.item import (
    Item,
    ItemCreate,
    ItemUpdate,
    ItemResponse,
    ItemListResponse
)
from ..models.common import SuccessResponse
from ..core.config import get_settings

# Get settings
settings = get_settings()

# Create router instance
router = APIRouter(
    prefix="/items",
    tags=["items"],
    responses={404: {"description": "Not found"}},
)

# In-memory storage (replace with database in production)
items_db: List[Item] = []
next_id = 1


@router.get("", response_model=ItemListResponse, summary="Get all items")
async def get_items(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of items to return")
):
    """
    Retrieve all items with pagination.
    
    - **skip**: Number of items to skip (for pagination)
    - **limit**: Maximum number of items to return (1-1000)
    """
    total = len(items_db)
    items = items_db[skip : skip + limit]
    
    return ItemListResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/{item_id}", response_model=ItemResponse, summary="Get item by ID")
async def get_item(item_id: int):
    """
    Get a specific item by its ID.
    
    - **item_id**: The ID of the item to retrieve
    """
    for item in items_db:
        if item.id == item_id:
            return item
    
    raise HTTPException(
        status_code=404,
        detail=f"Item with ID {item_id} not found"
    )


@router.post("", response_model=ItemResponse, status_code=201, summary="Create new item")
async def create_item(item: ItemCreate):
    """
    Create a new item.
    
    - **name**: Item name (required, 1-100 characters)
    - **description**: Item description (optional, max 500 characters)
    - **price**: Item price (required, must be positive)
    - **tax**: Tax amount (optional, must be non-negative)
    """
    global next_id
    
    now = datetime.now()
    new_item = Item(
        id=next_id,
        name=item.name,
        description=item.description,
        price=item.price,
        tax=item.tax,
        created_at=now,
        updated_at=now
    )
    
    items_db.append(new_item)
    next_id += 1
    
    return new_item


@router.put("/{item_id}", response_model=ItemResponse, summary="Update item")
async def update_item(item_id: int, item_update: ItemUpdate):
    """
    Update an existing item.
    
    - **item_id**: The ID of the item to update
    - **name**: New item name (optional, 1-100 characters)
    - **description**: New item description (optional, max 500 characters)
    - **price**: New item price (optional, must be positive)
    - **tax**: New tax amount (optional, must be non-negative)
    """
    for i, existing_item in enumerate(items_db):
        if existing_item.id == item_id:
            # Update only provided fields
            update_data = item_update.model_dump(exclude_unset=True)
            
            # Create updated item
            updated_item = existing_item.model_copy(
                update={
                    **update_data,
                    "updated_at": datetime.now()
                }
            )
            
            items_db[i] = updated_item
            return updated_item
    
    raise HTTPException(
        status_code=404,
        detail=f"Item with ID {item_id} not found"
    )


@router.delete("/{item_id}", response_model=SuccessResponse, summary="Delete item")
async def delete_item(item_id: int):
    """
    Delete an item by its ID.
    
    - **item_id**: The ID of the item to delete
    """
    for i, item in enumerate(items_db):
        if item.id == item_id:
            deleted_item = items_db.pop(i)
            return SuccessResponse(
                message=f"Item '{deleted_item.name}' (ID: {item_id}) deleted successfully"
            )
    
    raise HTTPException(
        status_code=404,
        detail=f"Item with ID {item_id} not found"
    )
