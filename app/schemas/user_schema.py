from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
import re

class UserBase(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    mobile_number: str

class UserCreate(UserBase):
    password: str
    confirm_password: str

    @field_validator('mobile_number')
    def validate_mobile_number(cls, v):
        if not re.match(r'^\+?[1-9]\d{1,14}$', v):
            raise ValueError('Invalid mobile number format')
        return v

    @field_validator('confirm_password')
    def passwords_match(cls, v, info):
        if 'password' in info.data and v != info.data['password']:
            raise ValueError('Passwords do not match')
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(UserBase):
    user_id: str
    role: str
    is_active: bool
    username: Optional[str] = None
    is_verified: Optional[bool] = True
    daily_loss_limit: Optional[float] = 0.0
    max_daily_trades: Optional[int] = 0
    max_risk_per_trade: Optional[float] = 2.0
    max_losing_streak: Optional[int] = 3
    risk_reward_ratio: Optional[str] = "1:2"
    preferred_sessions: Optional[list[str]] = []
    favorite_pairs: Optional[list[str]] = []
    currency: Optional[str] = "USD"
    timezone: Optional[str] = "UTC"

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    mobile_number: Optional[str] = None
    username: Optional[str] = None
    daily_loss_limit: Optional[float] = None
    max_daily_trades: Optional[int] = None
    max_risk_per_trade: Optional[float] = None
    max_losing_streak: Optional[int] = None
    risk_reward_ratio: Optional[str] = None
    preferred_sessions: Optional[list[str]] = None
    favorite_pairs: Optional[list[str]] = None
    currency: Optional[str] = None
    timezone: Optional[str] = None


class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str
    confirm_password: str

    @field_validator('confirm_password')
    def passwords_match(cls, v, info):
        if 'new_password' in info.data and v != info.data['new_password']:
            raise ValueError('Passwords do not match')
        return v

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str

    @field_validator('confirm_password')
    def passwords_match(cls, v, info):
        if 'new_password' in info.data and v != info.data['new_password']:
            raise ValueError('Passwords do not match')
        return v