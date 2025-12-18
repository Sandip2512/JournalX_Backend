from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class SubscriptionBase(BaseModel):
    user_id: str
    plan_name: str  # 'monthly', 'yearly', 'free'
    status: str     # 'active', 'expired', 'cancelled'
    price: float
    currency: str = "USD"
    start_date: datetime
    renewal_date: Optional[datetime] = None

class SubscriptionCreate(SubscriptionBase):
    pass

class SubscriptionResponse(SubscriptionBase):
    id: str

class TransactionBase(BaseModel):
    user_id: str
    subscription_id: Optional[str] = None
    invoice_number: str
    amount: float
    tax_amount: float
    total_amount: float
    currency: str = "USD"
    payment_method: str
    status: str  # 'paid', 'pending', 'failed'
    payment_date: datetime
    billing_details: dict

class TransactionCreate(TransactionBase):
    pass

class TransactionResponse(TransactionBase):
    id: str

class SalesAnalytics(BaseModel):
    total_revenue: float
    monthly_revenue: float
    yearly_revenue: float
    plan_breakdown: dict
    total_subscribers: int
    active_subscribers: int
