from fastapi import APIRouter, Depends, HTTPException
from pymongo.database import Database
from typing import List, Optional
from app.mongo_database import get_db
from app.crud.user_crud import get_all_users

router = APIRouter()

from app.routes.auth import SECRET_KEY, ALGORITHM
from jose import jwt, JWTError
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

def get_current_user_role(token: str = Depends(oauth2_scheme), db: Database = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
            
        user = db.users.find_one({"email": email})
        if user is None:
             raise HTTPException(status_code=401, detail="User not found")
             
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

@router.get("/users")
def get_all_users_stats(
    current_user: dict = Depends(get_current_user_role),
    db: Database = Depends(get_db)
):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
        
    users = get_all_users(db)
    results = []
    
    for user in users:
        # Calculate summary stats for each user
        # Avoid N+1 efficiently? This is admin endpoint, heavy load maybe ok or use aggregation later.
        # For now, query trades for each user.
        trades = list(db.trades.find({"user_id": user["user_id"]}))
        
        total_trades = len(trades)
        net_profit = sum((t.get("net_profit") or 0) for t in trades)
        wins = sum(1 for t in trades if (t.get("net_profit") or 0) > 0)
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
        
        results.append({
            "user_id": user["user_id"],
            "name": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip(),
            "email": user["email"],
            "role": user.get("role", "user"),
            "is_active": user.get("is_active", True),
            "total_trades": total_trades,
            "net_profit": net_profit,
            "win_rate": win_rate,
            "joined_at": user.get("created_at")
        })
        
    return results
