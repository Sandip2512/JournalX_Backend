from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class ImpactLevel(str, Enum):
    """Impact level of economic event"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class EventStatus(str, Enum):
    """Status of economic event"""
    UPCOMING = "upcoming"
    RELEASED = "released"


class EconomicEventBase(BaseModel):
    """Base schema for economic calendar events"""
    unique_id: str = Field(..., description="Unique identifier: {date}_{time}_{event_name}")
    event_date: datetime = Field(..., description="Date of the event")
    event_time_utc: datetime = Field(..., description="Event time in UTC")
    country: str = Field(..., description="Country code (e.g., USD, EUR)")
    currency: str = Field(..., description="Currency affected")
    impact_level: ImpactLevel = Field(..., description="Impact level: low, medium, high")
    event_name: str = Field(..., description="Name of the economic event")
    actual: Optional[str] = Field(None, description="Actual value (null if not released)")
    forecast: Optional[str] = Field(None, description="Forecast value")
    previous: Optional[str] = Field(None, description="Previous value")
    status: EventStatus = Field(default=EventStatus.UPCOMING, description="Event status")


class EconomicEventCreate(EconomicEventBase):
    """Schema for creating economic events"""
    pass


class EconomicEventUpdate(BaseModel):
    """Schema for updating economic events"""
    actual: Optional[str] = None
    forecast: Optional[str] = None
    previous: Optional[str] = None
    status: Optional[EventStatus] = None


class EconomicEventResponse(EconomicEventBase):
    """Schema for economic event API response with user-specific data"""
    id: str = Field(..., alias="_id", description="MongoDB ObjectId")
    is_marked: bool = Field(default=False, description="User marked as important")
    notes_count: int = Field(default=0, description="Number of notes")
    linked_trades_count: int = Field(default=0, description="Number of linked trades")
    created_at: datetime
    updated_at: datetime
    
    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class EventFilterParams(BaseModel):
    """Filter parameters for economic calendar events"""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    currencies: Optional[List[str]] = Field(default=None, description="List of currency codes")
    impacts: Optional[List[ImpactLevel]] = Field(default=None, description="List of impact levels")
    high_impact_only: bool = Field(default=False, description="Show only high impact events")
    search_query: Optional[str] = Field(default=None, description="Search in event names")
    status: Optional[EventStatus] = None


class EventNoteCreate(BaseModel):
    """Schema for creating event notes"""
    event_id: str
    note_text: str = Field(..., min_length=1, max_length=5000)


class EventNoteUpdate(BaseModel):
    """Schema for updating event notes"""
    note_text: str = Field(..., min_length=1, max_length=5000)


class EventNoteResponse(BaseModel):
    """Schema for event note response"""
    id: str = Field(..., alias="_id")
    user_id: str
    event_id: str
    note_text: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        populate_by_name = True


class EventReminderCreate(BaseModel):
    """Schema for creating event reminders"""
    event_id: str
    minutes_before: int = Field(..., ge=1, description="Minutes before event (e.g., 15, 30, 60)")


class EventReminderResponse(BaseModel):
    """Schema for event reminder response"""
    id: str = Field(..., alias="_id")
    user_id: str
    event_id: str
    event_time: datetime
    minutes_before: int
    reminder_time: datetime
    is_sent: bool = Field(default=False)
    created_at: datetime
    
    class Config:
        populate_by_name = True


class EventTradeLinkCreate(BaseModel):
    """Schema for linking event to trade"""
    event_id: str
    trade_id: str


class EventTradeLinkResponse(BaseModel):
    """Schema for event-trade link response"""
    id: str = Field(..., alias="_id")
    user_id: str
    event_id: str
    trade_id: str
    created_at: datetime
    
    class Config:
        populate_by_name = True


class EventMarkRequest(BaseModel):
    """Schema for marking event as important"""
    is_marked: bool
