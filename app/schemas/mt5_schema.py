from pydantic import BaseModel, field_validator

class MT5CredentialsBase(BaseModel):
    account: int
    password: str
    server: str
    days: int = 365

class MT5CredentialsCreate(MT5CredentialsBase):
    user_id: str  # ✅ CHANGED to str

    @field_validator('user_id', mode='before')
    def convert_user_id_to_string(cls, v):
        if isinstance(v, int):
            return str(v)  # Convert int to string
        return v  # Already string

class MT5CredentialsResponse(MT5CredentialsBase):
    user_id: str
    account: int
    server: str

    class Config:
        from_attributes = True