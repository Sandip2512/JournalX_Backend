from fastapi import APIRouter, Depends, HTTPException, Query
from pymongo.database import Database
from typing import Optional, List
from datetime import datetime
import logging

from app.mongo_database import get_db
from app.schemas.calendar_event_schema import (
    EconomicEventResponse,
    EventFilterParams,
    EventNoteCreate,
    EventNoteResponse,
    EventReminderCreate,
    EventReminderResponse,
    EventTradeLinkCreate,
    EventTradeLinkResponse,
    EventMarkRequest
)
from app.services.economic_calendar_service import economic_calendar_service
from app.crud import calendar_crud
from app.crud.user_crud import get_user_by_id

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/events")
async def get_calendar_events(
    user_id: str = Query(..., description="User ID"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    currencies: Optional[str] = Query(None, description="Comma-separated currency codes"),
    impacts: Optional[str] = Query(None, description="Comma-separated impact levels"),
    high_impact_only: bool = Query(False, description="Show only high impact events"),
    search: Optional[str] = Query(None, description="Search in event names"),
    status: Optional[str] = Query(None, description="Event status: upcoming or released"),
    timezone_offset: float = Query(0, description="Timezone offset in hours from UTC"),
    db: Database = Depends(get_db)
):
    """
    Get economic calendar events with filters
    
    Returns:
        List of economic events
    """
    try:
        # Parse dates
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None
        
        # Parse currencies
        currency_list = currencies.split(",") if currencies else None
        
        # Parse impacts
        impact_list = impacts.split(",") if impacts else None
        
        # Enforce Subscription Tier Restrictions
        user = get_user_by_id(db, user_id)
        sub_tier = str(user.get("subscription_tier", "free")).lower() if user else "free"
        
        if sub_tier == "free":
            # Free tier: Today only, USD only, High/Medium impact only
            now = datetime.utcnow()
            # Since internal storage is UTC, we use UTC for "Today" as well, 
            # though user might want local "Today". 
            # For simplicity and strictly enforcing limits:
            start_dt = datetime.combine(now.date(), datetime.min.time())
            end_dt = datetime.combine(now.date(), datetime.max.time())
            currency_list = ["USD"]
            if not high_impact_only:
                impact_list = ["high", "medium"]
            else:
                impact_list = ["high"]
            search = None # Disable search for free tier or keep it restricted
            status = status # Allow status filter? Yes.

        # Get events
        events = economic_calendar_service.get_events_with_filters(
            db=db,
            user_id=user_id,
            start_date=start_dt,
            end_date=end_dt,
            currencies=currency_list,
            impacts=impact_list,
            high_impact_only=high_impact_only if sub_tier != "free" else False,
            search_query=search,
            status=status
        )
        
        # Convert to user timezone if needed
        if timezone_offset != 0:
            events = [
                economic_calendar_service.convert_to_user_timezone(event, timezone_offset)
                for event in events
            ]
        
        return {
            "success": True,
            "count": len(events),
            "events": events
        }
        
    except Exception as e:
        logger.error(f"Error fetching calendar events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/events/{event_id}/mark")
async def mark_event_important(
    event_id: str,
    user_id: str = Query(..., description="User ID"),
    request: EventMarkRequest = None,
    db: Database = Depends(get_db)
):
    """
    Mark or unmark an event as important
    
    Returns:
        Success status
    """
    try:
        result = calendar_crud.mark_event_important(
            db=db,
            user_id=user_id,
            event_id=event_id,
            is_marked=request.is_marked
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error marking event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/events/{event_id}/notes")
async def add_event_note(
    event_id: str,
    user_id: str = Query(..., description="User ID"),
    note: EventNoteCreate = None,
    db: Database = Depends(get_db)
):
    """
    Add or update a note for an event
    
    Returns:
        Note document
    """
    try:
        result = calendar_crud.add_event_note(
            db=db,
            user_id=user_id,
            event_id=event_id,
            note_text=note.note_text
        )
        
        return {
            "success": True,
            "note": result
        }
        
    except Exception as e:
        logger.error(f"Error adding note: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/events/{event_id}/notes")
async def get_event_notes(
    event_id: str,
    user_id: str = Query(..., description="User ID"),
    db: Database = Depends(get_db)
):
    """
    Get all notes for an event
    
    Returns:
        List of notes
    """
    try:
        notes = calendar_crud.get_event_notes(
            db=db,
            user_id=user_id,
            event_id=event_id
        )
        
        return {
            "success": True,
            "count": len(notes),
            "notes": notes
        }
        
    except Exception as e:
        logger.error(f"Error getting notes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/events/{event_id}/link-trade")
async def link_event_to_trade(
    event_id: str,
    user_id: str = Query(..., description="User ID"),
    link: EventTradeLinkCreate = None,
    db: Database = Depends(get_db)
):
    """
    Link an event to a trade
    
    Returns:
        Link document
    """
    try:
        result = calendar_crud.link_event_to_trade(
            db=db,
            user_id=user_id,
            event_id=event_id,
            trade_id=link.trade_id
        )
        
        return {
            "success": True,
            "link": result
        }
        
    except Exception as e:
        logger.error(f"Error linking event to trade: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/events/{event_id}/linked-trades")
async def get_linked_trades(
    event_id: str,
    user_id: str = Query(..., description="User ID"),
    db: Database = Depends(get_db)
):
    """
    Get all trades linked to an event
    
    Returns:
        List of trades
    """
    try:
        trades = calendar_crud.get_linked_trades(
            db=db,
            user_id=user_id,
            event_id=event_id
        )
        
        return {
            "success": True,
            "count": len(trades),
            "trades": trades
        }
        
    except Exception as e:
        logger.error(f"Error getting linked trades: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reminders")
async def create_reminder(
    user_id: str = Query(..., description="User ID"),
    reminder: EventReminderCreate = None,
    db: Database = Depends(get_db)
):
    """
    Create a reminder for an event
    
    Returns:
        Reminder document
    """
    try:
        result = calendar_crud.create_reminder(
            db=db,
            user_id=user_id,
            event_id=reminder.event_id,
            minutes_before=reminder.minutes_before
        )
        
        return {
            "success": True,
            "reminder": result
        }
        
    except Exception as e:
        logger.error(f"Error creating reminder: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reminders")
async def get_user_reminders(
    user_id: str = Query(..., description="User ID"),
    db: Database = Depends(get_db)
):
    """
    Get all reminders for a user
    
    Returns:
        List of reminders
    """
    try:
        reminders = calendar_crud.get_user_reminders(
            db=db,
            user_id=user_id
        )
        
        return {
            "success": True,
            "count": len(reminders),
            "reminders": reminders
        }
        
    except Exception as e:
        logger.error(f"Error getting reminders: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/reminders/{reminder_id}")
async def delete_reminder(
    reminder_id: str,
    user_id: str = Query(..., description="User ID"),
    db: Database = Depends(get_db)
):
    """
    Delete a reminder
    
    Returns:
        Success status
    """
    try:
        result = calendar_crud.delete_reminder(
            db=db,
            reminder_id=reminder_id,
            user_id=user_id
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error deleting reminder: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/next-high-impact")
async def get_next_high_impact_event(
    timezone_offset: float = Query(0, description="Timezone offset in hours from UTC"),
    db: Database = Depends(get_db)
):
    """
    Get the next high-impact event for countdown timer
    
    Returns:
        Next high-impact event or null
    """
    try:
        event = economic_calendar_service.calculate_next_high_impact(db)
        
        if event and timezone_offset != 0:
            event = economic_calendar_service.convert_to_user_timezone(event, timezone_offset)
        
        return {
            "success": True,
            "event": event
        }
        
    except Exception as e:
        logger.error(f"Error getting next high-impact event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cron/sync")
async def manual_cron_sync(db: Database = Depends(get_db)):
    """
    Trigger a manual sync of the economic calendar.
    Can be called by Vercel Cron or a manual trigger.
    """
    try:
        logger.info("Manual cron sync triggered")
        await economic_calendar_service.auto_update_calendar(db)
        return {"success": True, "message": "Calendar sync triggered successfully"}
    except Exception as e:
        logger.error(f"Manual cron sync failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
