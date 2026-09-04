from pydantic import BaseModel, Field
from typing import Optional

class PreferencesBase(BaseModel):
    currency: str = Field(default="USD", description="Preferred currency")
    timezone: str = Field(default="UTC", description="Preferred timezone")

class PreferencesCreate(PreferencesBase):
    pass

class PreferencesUpdate(BaseModel):
    currency: Optional[str] = None
    timezone: Optional[str] = None

class PreferencesResponse(PreferencesBase):
    user_id: str
    updated_at: str

    class Config:
        from_attributes = True
