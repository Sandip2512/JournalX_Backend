from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime

class MistakeBase(BaseModel):
    name: str
    category: Literal['Behavioral', 'Psychological', 'Cognitive', 'Technical']
    severity: Literal['High', 'Medium', 'Low']
    impact: Literal['Critical', 'Moderate', 'Minor']
    description: Optional[str] = None
    user_id: str

class MistakeCreate(MistakeBase):
    pass

class MistakeUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[Literal['Behavioral', 'Psychological', 'Cognitive', 'Technical']] = None
    severity: Optional[Literal['High', 'Medium', 'Low']] = None
    impact: Optional[Literal['Critical', 'Moderate', 'Minor']] = None
    description: Optional[str] = None

class Mistake(MistakeBase):
    id: str
    count: int = 0
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
