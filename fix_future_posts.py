from pymongo import MongoClient
from datetime import datetime, timezone
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME", "journal")

def fix_future_timestamps():
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    
    now = datetime.now(timezone.utc)
    print(f"🕒 Current UTC Time: {now}")
    
    # 1. Fix Posts
    future_posts = list(db.posts.find({"created_at": {"$gt": now}}))
    print(f"📝 Found {len(future_posts)} future posts.")
    for post in future_posts:
        print(f"  - Fixing post {post.get('post_id')} (was {post.get('created_at')})")
        db.posts.update_one(
            {"_id": post["_id"]},
            {"$set": {"created_at": now}}
        )
        
    # 2. Fix Comments
    future_comments = list(db.post_comments.find({"created_at": {"$gt": now}}))
    print(f"💬 Found {len(future_comments)} future comments.")
    for comment in future_comments:
        print(f"  - Fixing comment {comment.get('comment_id')} (was {comment.get('created_at')})")
        db.post_comments.update_one(
            {"_id": comment["_id"]},
            {"$set": {"created_at": now}}
        )
        
    print("✅ Done.")

if __name__ == "__main__":
    fix_future_timestamps()
