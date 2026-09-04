from pydantic import BaseModel, field_validator
from typing import List, Optional
from datetime import datetime


# ─── Credential-based connection (existing, unchanged) ───────────────────────

class MT5CredentialsBase(BaseModel):
    account: int
    password: str
    server: str
    days: int = 365

class MT5CredentialsCreate(MT5CredentialsBase):
    user_id: str

    @field_validator('user_id', mode='before')
    def convert_user_id_to_string(cls, v):
        if isinstance(v, int):
            return str(v)
        return v

class MT5CredentialsResponse(MT5CredentialsBase):
    user_id: str
    account: int
    server: str

    class Config:
        from_attributes = True


# ─── EA / Token-based connection (new) ───────────────────────────────────────

class MT5TokenRequest(BaseModel):
    """Request body for generating a connection token."""
    user_id: str


class MT5TokenResponse(BaseModel):
    """Returned after token generation."""
    token: str
    user_id: str
    created_at: datetime


class MT5TradeItem(BaseModel):
    """A single closed trade posted by the EA."""
    mt5_ticket: int            # MT5 deal/ticket ID — used for deduplication
    symbol: str
    type: str                  # "buy" or "sell"
    volume: float
    price_open: float
    price_close: float
    net_profit: float
    open_time: datetime
    close_time: datetime


class MT5EASyncPayload(BaseModel):
    """Payload sent by the EA to /mt5/ea/sync."""
    trades: List[MT5TradeItem]

    @field_validator("trades")
    @classmethod
    def cap_trades(cls, v: list) -> list:
        """Reject oversized payloads — protects the DB under high user load."""
        if len(v) > 500:
            raise ValueError("Batch size exceeds limit (max 500 trades per sync)")
        return v


class MT5ConnectionStatus(BaseModel):
    """Response for /mt5/connection-status."""
    connected: bool
    token_preview: Optional[str] = None   # first 8 chars of token for display
    last_sync_at: Optional[datetime] = None
    synced_trades_count: int = 0