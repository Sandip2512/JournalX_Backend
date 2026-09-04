from pymongo.database import Database
from typing import Optional, List
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


def mark_event_important(db: Database, user_id: str, event_id: str, is_marked: bool) -> dict:
    """
    Mark or unmark an event as important for a user
    
    Args:
        db: MongoDB database instance
        user_id: User ID
        event_id: Event ID
        is_marked: True to mark, False to unmark
        
    Returns:
        Result dictionary
    """
    try:
        result = db.user_event_marks.update_one(
            {"user_id": user_id, "event_id": event_id},
            {
                "$set": {
                    "is_marked": is_marked,
                    "updated_at": datetime.utcnow()
                },
                "$setOnInsert": {
                    "created_at": datetime.utcnow()
                }
            },
            upsert=True
        )
        
        return {
            "success": True,
            "is_marked": is_marked,
            "modified": result.modified_count > 0
        }
        
    except Exception as e:
        logger.error(f"Error marking event: {e}")
        raise


def add_event_note(db: Database, user_id: str, event_id: str, note_text: str) -> dict:
    """
    Add or update a note for an event
    
    Args:
        db: MongoDB database instance
        user_id: User ID
        event_id: Event ID
        note_text: Note content
        
    Returns:
        Note document
    """
    try:
        # Check if note exists
        existing_note = db.event_notes.find_one({
            "user_id": user_id,
            "event_id": event_id
        })
        
        if existing_note:
            # Update existing note
            db.event_notes.update_one(
                {"_id": existing_note["_id"]},
                {
                    "$set": {
                        "note_text": note_text,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            existing_note["note_text"] = note_text
            existing_note["updated_at"] = datetime.utcnow()
            existing_note["_id"] = str(existing_note["_id"])
            
            return existing_note
        else:
            # Create new note
            note = {
                "user_id": user_id,
                "event_id": event_id,
                "note_text": note_text,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            result = db.event_notes.insert_one(note)
            note["_id"] = str(result.inserted_id)
            
            return note
            
    except Exception as e:
        logger.error(f"Error adding note: {e}")
        raise


def get_event_notes(db: Database, user_id: str, event_id: str) -> List[dict]:
    """
    Get all notes for an event
    
    Args:
        db: MongoDB database instance
        user_id: User ID
        event_id: Event ID
        
    Returns:
        List of note documents
    """
    try:
        notes = list(db.event_notes.find({
            "user_id": user_id,
            "event_id": event_id
        }).sort("created_at", -1))
        
        for note in notes:
            note["_id"] = str(note["_id"])
        
        return notes
        
    except Exception as e:
        logger.error(f"Error getting notes: {e}")
        raise


def link_event_to_trade(db: Database, user_id: str, event_id: str, trade_id: str) -> dict:
    """
    Link an event to a trade
    
    Args:
        db: MongoDB database instance
        user_id: User ID
        event_id: Event ID
        trade_id: Trade ID
        
    Returns:
        Link document
    """
    try:
        # Check if link already exists
        existing_link = db.event_trade_links.find_one({
            "user_id": user_id,
            "event_id": event_id,
            "trade_id": trade_id
        })
        
        if existing_link:
            existing_link["_id"] = str(existing_link["_id"])
            return existing_link
        
        # Create new link
        link = {
            "user_id": user_id,
            "event_id": event_id,
            "trade_id": trade_id,
            "created_at": datetime.utcnow()
        }
        
        result = db.event_trade_links.insert_one(link)
        link["_id"] = str(result.inserted_id)
        
        return link
        
    except Exception as e:
        logger.error(f"Error linking event to trade: {e}")
        raise


def get_linked_trades(db: Database, user_id: str, event_id: str) -> List[dict]:
    """
    Get all trades linked to an event
    
    Args:
        db: MongoDB database instance
        user_id: User ID
        event_id: Event ID
        
    Returns:
        List of trade documents
    """
    try:
        # Get links
        links = list(db.event_trade_links.find({
            "user_id": user_id,
            "event_id": event_id
        }))
        
        # Get trade details
        trade_ids = [link["trade_id"] for link in links]
        trades = list(db.trades.find({"trade_no": {"$in": trade_ids}}))
        
        for trade in trades:
            trade["_id"] = str(trade["_id"])
        
        return trades
        
    except Exception as e:
        logger.error(f"Error getting linked trades: {e}")
        raise


def create_reminder(db: Database, user_id: str, event_id: str, minutes_before: int) -> dict:
    """
    Create a reminder for an event
    
    Args:
        db: MongoDB database instance
        user_id: User ID
        event_id: Event ID
        minutes_before: Minutes before event to remind
        
    Returns:
        Reminder document
    """
    try:
        # Get event to calculate reminder time
        event = db.economic_events.find_one({"_id": event_id})
        if not event:
            raise ValueError("Event not found")
        
        event_time = event["event_time_utc"]
        reminder_time = event_time - timedelta(minutes=minutes_before)
        
        # Create reminder
        reminder = {
            "user_id": user_id,
            "event_id": event_id,
            "event_time": event_time,
            "minutes_before": minutes_before,
            "reminder_time": reminder_time,
            "is_sent": False,
            "created_at": datetime.utcnow()
        }
        
        result = db.event_reminders.insert_one(reminder)
        reminder["_id"] = str(result.inserted_id)
        
        return reminder
        
    except Exception as e:
        logger.error(f"Error creating reminder: {e}")
        raise


def get_user_reminders(db: Database, user_id: str) -> List[dict]:
    """
    Get all reminders for a user
    
    Args:
        db: MongoDB database instance
        user_id: User ID
        
    Returns:
        List of reminder documents
    """
    try:
        reminders = list(db.event_reminders.find({
            "user_id": user_id,
            "is_sent": False
        }).sort("reminder_time", 1))
        
        for reminder in reminders:
            reminder["_id"] = str(reminder["_id"])
        
        return reminders
        
    except Exception as e:
        logger.error(f"Error getting reminders: {e}")
        raise


def delete_reminder(db: Database, reminder_id: str, user_id: str) -> dict:
    """
    Delete a reminder
    
    Args:
        db: MongoDB database instance
        reminder_id: Reminder ID
        user_id: User ID
        
    Returns:
        Result dictionary
    """
    try:
        from bson import ObjectId
        
        result = db.event_reminders.delete_one({
            "_id": ObjectId(reminder_id),
            "user_id": user_id
        })
        
        return {
            "success": result.deleted_count > 0,
            "deleted_count": result.deleted_count
        }
        
    except Exception as e:
        logger.error(f"Error deleting reminder: {e}")
        raise
