from fastapi import APIRouter, Depends, HTTPException, Query
from pymongo.database import Database
from app.mongo_database import get_db
from app.schemas.mistake_schema import MistakeCreate, MistakeUpdate, Mistake
from app.crud import mistake_crud
from typing import List

router = APIRouter(tags=["mistakes"])

@router.post("/", response_model=Mistake)
async def create_mistake(mistake: MistakeCreate, db: Database = Depends(get_db)):
    """Create a new custom mistake type"""
    try:
        mistake_data = mistake.model_dump()
        result = mistake_crud.create_mistake(db, mistake_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/user/{user_id}", response_model=List[Mistake])
async def get_user_mistakes(user_id: str, db: Database = Depends(get_db)):
    """Get all mistakes for a user with occurrence counts"""
    try:
        mistakes = mistake_crud.get_mistakes(db, user_id)
        return mistakes
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/{user_id}")
async def get_mistake_analytics(
    user_id: str,
    time_filter: str = Query("all", regex="^(all|month)$"),
    db: Database = Depends(get_db)
):
    """Get analytics data for mistakes page"""
    try:
        analytics = mistake_crud.get_mistake_analytics(db, user_id, time_filter)
        return analytics
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/frequency/{user_id}")
async def get_frequency_heatmap(
    user_id: str,
    days: int = Query(35, ge=1, le=365),
    db: Database = Depends(get_db)
):
    """Get frequency heatmap data"""
    try:
        heatmap_data = mistake_crud.get_frequency_heatmap_data(db, user_id, days)
        return {"data": heatmap_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{mistake_id}", response_model=Mistake)
async def get_mistake(mistake_id: str, db: Database = Depends(get_db)):
    """Get a single mistake by ID"""
    mistake = mistake_crud.get_mistake_by_id(db, mistake_id)
    if not mistake:
        raise HTTPException(status_code=404, detail="Mistake not found")
    return mistake

@router.put("/{mistake_id}", response_model=Mistake)
async def update_mistake(
    mistake_id: str,
    mistake_update: MistakeUpdate,
    db: Database = Depends(get_db)
):
    """Update a mistake"""
    update_data = mistake_update.model_dump(exclude_unset=True)
    result = mistake_crud.update_mistake(db, mistake_id, update_data)
    if not result:
        raise HTTPException(status_code=404, detail="Mistake not found")
    return result

@router.delete("/{mistake_id}")
async def delete_mistake(mistake_id: str, db: Database = Depends(get_db)):
    """Delete a mistake"""
    success = mistake_crud.delete_mistake(db, mistake_id)
    if not success:
        raise HTTPException(status_code=404, detail="Mistake not found")
    return {"message": "Mistake deleted successfully"}
