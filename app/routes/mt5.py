from fastapi import APIRouter, Depends, HTTPException
from pymongo.database import Database
from typing import List

from app.mongo_database import get_db
from app.services.mt5_service import fetch_mt5_trades
from app.crud.mt5_crud import create_mt5_credentials, get_mt5_credentials, update_mt5_credentials, delete_mt5_credentials
from app.schemas.mt5_schema import MT5CredentialsCreate, MT5CredentialsResponse

router = APIRouter()

@router.post("/connect", response_model=dict)
async def connect_mt5(credentials: MT5CredentialsCreate, db: Database = Depends(get_db)):
    """
    Connect to MT5 and store/update credentials
    """
    try:
        print(f"🔌 MT5 Connection attempt:")
        print(f"   Account: {credentials.account}")
        print(f"   Server: {credentials.server}")
        print(f"   User ID: {credentials.user_id}")
        print(f"   Days: {credentials.days}")
        
        # Validate input
        if not credentials.account:
            raise HTTPException(status_code=400, detail="Account number is required")
        if not credentials.password:
            raise HTTPException(status_code=400, detail="Password is required")
        if not credentials.server:
            raise HTTPException(status_code=400, detail="Server is required")
        if not credentials.user_id:
            raise HTTPException(status_code=400, detail="User ID is required")
        
        # Check if user exists first
        from app.crud.user_crud import get_user_by_id
        user = get_user_by_id(db, credentials.user_id)
        if not user:
            raise HTTPException(
                status_code=404, 
                detail=f"User with ID {credentials.user_id} not found. Please register first."
            )
        
        # Test MT5 connection
        try:
            trades = fetch_mt5_trades(
                account=credentials.account,
                password=credentials.password,
                server=credentials.server,
                days=credentials.days
            )
            print(f"✅ MT5 Connection successful, found {len(trades) if trades else 0} trades")
        except Exception as mt5_error:
            error_msg = str(mt5_error)
            print(f"❌ MT5 connection error: {error_msg}")
            # Check for specific MT5 errors
            if "disconnected" in error_msg.lower() or "connection lost" in error_msg.lower():
                raise HTTPException(
                    status_code=503,
                    detail="MT5 account disconnected from broker server. Please ensure MT5 terminal is connected to the broker server (check the connection status in MT5). Wait for the connection to stabilize, then try again."
                )
            elif "IPC timeout" in error_msg or "(-10005" in error_msg:
                raise HTTPException(
                    status_code=503,
                    detail="MT5 terminal is not responding (IPC timeout). This may occur if the account disconnected from the server. Please check MT5 connection status, wait for it to reconnect, then try again."
                )
            elif "Authorization failed" in error_msg or "(-6" in error_msg:
                raise HTTPException(
                    status_code=401,
                    detail="MT5 authorization failed. Please check your account number, password, and server name."
                )
            elif "initialization failed" in error_msg.lower():
                raise HTTPException(
                    status_code=503,
                    detail="MT5 terminal is not available. Please ensure MetaTrader 5 is installed and running."
                )
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"MT5 connection failed: {error_msg}"
                )
        
        # Check if credentials already exist for this user
        existing_credentials = get_mt5_credentials(db, credentials.user_id)
        
        if existing_credentials:
            print("🔄 Updating existing MT5 credentials")
            # Update existing credentials
            updated_credentials = update_mt5_credentials(db, credentials.user_id, {
                "account": str(credentials.account),
                "password": credentials.password,
                "server": credentials.server,
                "days": credentials.days
            })
            action = "updated"
        else:
            print("💾 Creating new MT5 credentials")
            # Store new credentials in database
            updated_credentials = create_mt5_credentials(db, {
                "account": str(credentials.account),
                "password": credentials.password,
                "server": credentials.server,
                "user_id": credentials.user_id,
                "days": credentials.days
            })
            action = "created"
        
        return {
            "status": "connected",
            "message": "Successfully connected to MT5",
            "trades_count": len(trades) if trades else 0,
            "account": credentials.account,
            "server": credentials.server,
            "action": action
        }
        
    except HTTPException:
        # Re-raise HTTPExceptions as-is
        raise
    except Exception as e:
        print(f"❌ Unexpected error in MT5 connection: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}"
        )

@router.post("/disconnect", response_model=dict)
async def disconnect_mt5(user_id: str, db: Database = Depends(get_db)):  # ✅ CHANGED to str
    """
    Disconnect from MT5 and remove credentials
    """
    try:
        deleted = delete_mt5_credentials(db, user_id)
        if deleted:
            return {"status": "disconnected", "message": "Successfully disconnected from MT5"}
        else:
            return {"status": "error", "message": "No active connection found"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Disconnection failed: {str(e)}")

@router.get("/account-info", response_model=dict)
async def get_account_info(user_id: str, db: Database = Depends(get_db)):  # ✅ CHANGED to str
    """
    Get MT5 account information
    """
    try:
        credentials = get_mt5_credentials(db, user_id)
        if not credentials:
            raise HTTPException(status_code=404, detail="No MT5 credentials found")
        
        # Mock response - replace with actual MT5 API calls
        return {
            "account": credentials.account,
            "server": credentials.server,
            "balance": 12500.00,
            "equity": 12800.50,
            "margin": 1200.75,
            "free_margin": 11600.25,
            "leverage": 100,
            "currency": "USD"
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to get account info: {str(e)}")