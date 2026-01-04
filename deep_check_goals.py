from app.mongo_database import get_db
import json
from bson import json_util

def deep_check():
    db = get_db()
    goals = list(db.goals.find())
    print(json.dumps(goals, default=json_util.default, indent=2))

if __name__ == "__main__":
    deep_check()
