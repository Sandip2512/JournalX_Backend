from pymongo.database import Database
from datetime import datetime
from bson import ObjectId
from typing import List, Optional

def send_friend_request(db: Database, requester_id: str, recipient_id: str):
    # 1. Check if users exist
    recipient = db.users.find_one({"user_id": recipient_id})
    if not recipient:
        return None

    # 2. Check if already friends
    # We check if there's an 'accepted' request either way
    already_friends = db.friend_requests.find_one({
        "status": "accepted",
        "$or": [
            {"requester_id": requester_id, "recipient_id": recipient_id},
            {"requester_id": recipient_id, "recipient_id": requester_id}
        ]
    })
    if already_friends:
        return {"status": "already_friends"}

    # 3. Check if pending request exists
    existing = db.friend_requests.find_one({
        "status": "pending",
        "$or": [
            {"requester_id": requester_id, "recipient_id": recipient_id},
            {"requester_id": recipient_id, "recipient_id": requester_id} # If they sent one to simple accept, we could auto-accept, but simpler to block
        ]
    })
    
    if existing:
        return existing

    # 4. Create request
    request = {
        "requester_id": requester_id,
        "recipient_id": recipient_id,
        "status": "pending",
        "created_at": datetime.utcnow()
    }
    result = db.friend_requests.insert_one(request)
    request["request_id"] = str(result.inserted_id)
    return request

def get_pending_requests(db: Database, user_id: str):
    # Incoming requests (where I am recipient)
    requests = list(db.friend_requests.find({"recipient_id": user_id, "status": "pending"}))
    formatted = []
    for r in requests:
        r["request_id"] = str(r["_id"])
        # Fetch requester details
        requester = db.users.find_one({"user_id": r["requester_id"]})
        if requester:
            r["requester_name"] = f"{requester.get('first_name', '')} {requester.get('last_name', '')}"
            r["requester_username"] = requester.get("username")
        formatted.append(r)
    return formatted

def accept_friend_request(db: Database, request_id: str, user_id: str):
    try:
        oid = ObjectId(request_id)
    except:
        return None
        
    # Verify request belongs to user (as recipient)
    req = db.friend_requests.find_one({"_id": oid, "recipient_id": user_id, "status": "pending"})
    if not req:
        return None

    # Update status to accepted
    db.friend_requests.update_one(
        {"_id": oid}, 
        {"$set": {"status": "accepted", "updated_at": datetime.utcnow()}}
    )
    return True

def reject_friend_request(db: Database, request_id: str, user_id: str):
    try:
        oid = ObjectId(request_id)
    except:
        return None
    
    # Verify request
    req = db.friend_requests.find_one({"_id": oid, "recipient_id": user_id, "status": "pending"})
    if not req:
        return None
        
    # Delete or mark rejected
    db.friend_requests.delete_one({"_id": oid})
    return True

def get_friends(db: Database, user_id: str):
    # Find all accepted requests where user is involved
    connections = list(db.friend_requests.find({
        "status": "accepted",
        "$or": [{"requester_id": user_id}, {"recipient_id": user_id}]
    }))
    
    friends = []
    for c in connections:
        # Determine who is the 'friend'
        friend_id = c["recipient_id"] if c["requester_id"] == user_id else c["requester_id"]
        
        if not friend_id:
            continue
            
        friend_user = db.users.find_one({"user_id": friend_id})
        if friend_user:
            last_seen = friend_user.get("last_seen")
            is_online = False
            if last_seen:
                # Check if active in last 5 minutes
                if (datetime.utcnow() - last_seen).total_seconds() < 300:
                    is_online = True

            friends.append({
                "friendship_id": str(c["_id"]),
                "user_id": friend_id,
                "name": f"{friend_user.get('first_name', '')} {friend_user.get('last_name', '')}".strip(),
                "username": friend_user.get("username"),
                "connected_at": c.get("updated_at", c["created_at"]),
                "status": "connected",
                "last_seen": last_seen,
                "is_online": is_online
            })
    return friends

def search_users_for_friendship(db: Database, query: str, user_id: str):
    # Search by name or username
    regex = {"$regex": query, "$options": "i"}
    users = list(db.users.find({
        "$or": [
            {"username": regex},
            {"first_name": regex},
            {"last_name": regex},
            {"email": regex}
        ],
        "user_id": {"$ne": user_id} # Exclude self
    }).limit(20))
    
    results = []
    for u in users:
        is_self = u["user_id"] == user_id
        is_friend = False
        has_pending = False
        
        # Check friendship
        friend_check = db.friend_requests.find_one({
            "status": "accepted",
            "$or": [
                {"requester_id": user_id, "recipient_id": u["user_id"]},
                {"requester_id": u["user_id"], "recipient_id": user_id}
            ]
        })
        if friend_check:
            is_friend = True
        
        if not is_friend:
            pending = db.friend_requests.find_one({
                "status": "pending",
                "$or": [
                    {"requester_id": user_id, "recipient_id": u["user_id"]}, # I sent
                    {"requester_id": u["user_id"], "recipient_id": user_id}  # They sent
                ]
            })
            if pending:
                has_pending = True
        
        results.append({
            "user_id": u["user_id"],
            "username": u.get("username"),
            "first_name": u.get("first_name", ""),
            "last_name": u.get("last_name", ""),
            "is_friend": is_friend,
            "has_pending_request": has_pending,
            "is_self": is_self
        })
    return results
