from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from pymongo.database import Database
from typing import List, Optional
from app.mongo_database import get_db
from app.routes.auth import get_current_user_role
from app.crud.subscription_crud import (
    get_user_subscription, get_user_transactions, 
    get_all_transactions, get_sales_analytics, get_transaction
)
from app.crud.coupon_crud import redeem_coupon
from app.schemas.subscription_schema import SubscriptionResponse, TransactionResponse, SalesAnalytics, CouponRedeem
from app.services.invoice_service import invoice_service

router = APIRouter()

# ------------------- Admin Routes -------------------

@router.get("/admin/sales/analytics", response_model=SalesAnalytics)
def admin_get_sales_analytics(
    db: Database = Depends(get_db),
    admin: dict = Depends(get_current_user_role)
):
    if admin.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    return get_sales_analytics(db)

@router.get("/admin/sales/transactions", response_model=List[dict])
def admin_get_transactions(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    db: Database = Depends(get_db),
    admin: dict = Depends(get_current_user_role)
):
    if admin.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    filters = {}
    if status:
        filters["status"] = status
        
    transactions = get_all_transactions(db, skip, limit, filters)
    # Pydantic likes dictionaries with string IDs
    for tx in transactions:
        tx["id"] = str(tx.get("id") or "")
        if "_id" in tx:
            tx["_id"] = str(tx["_id"])
    return transactions

# ------------------- User Routes -------------------

@router.get("/my-subscription")
def get_my_subscription(
    db: Database = Depends(get_db),
    user: dict = Depends(get_current_user_role) # Reuse the same dependency for role/auth
):
    sub = get_user_subscription(db, user["user_id"])
    if not sub:
        return {"plan_name": "Free", "status": "active"}
    return sub

@router.post("/redeem-coupon")
def redeem_coupon_code(
    coupon_data: CouponRedeem,
    db: Database = Depends(get_db),
    user: dict = Depends(get_current_user_role)
):
    print(f"🎟️ Coupon redemption attempt: User {user['user_id']} with code {coupon_data.code}")
    result = redeem_coupon(db, user["user_id"], coupon_data.code)
    if not result["success"]:
        print(f"❌ Coupon redemption failed: {result['message']}")
        raise HTTPException(status_code=400, detail=result["message"])
    print(f"✅ Coupon redemption successful: {result['message']}")
    return result

@router.get("/my-transactions", response_model=List[dict])
def get_my_transactions(
    db: Database = Depends(get_db),
    user: dict = Depends(get_current_user_role)
):
    transactions = get_user_transactions(db, user["user_id"])
    for tx in transactions:
        tx["id"] = str(tx.get("id") or "")
        if "_id" in tx:
            tx["_id"] = str(tx["_id"])
    return transactions

@router.get("/transactions/{transaction_id}/invoice")
def download_invoice(
    transaction_id: str,
    db: Database = Depends(get_db),
    user: dict = Depends(get_current_user_role)
):
    transaction = get_transaction(db, transaction_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # Check authorization: Admin can see all, Users can only see their own
    if user.get("role") != "admin" and transaction["user_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Not authorized to access this invoice")
    
    try:
        pdf_buffer = invoice_service.generate_invoice_pdf(transaction)
        
        invoice_name = transaction.get('invoice_number', transaction_id)
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=invoice_{invoice_name}.pdf"}
        )
    except Exception as e:
        print(f"Error generating invoice: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating invoice PDF: {str(e)}")
