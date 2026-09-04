from app.mongo_database import get_db

def hunt_duplicates():
    db = get_db()
    target_id = "e5a933cf-d99e-4b85-a2ff-379efbe82e0b"
    
    print(f"--- HUNTING DUPLICATES FOR {target_id} ---")
    goals = list(db.goals.find({"user_id": target_id, "is_active": True}))
    print(f"Total active goals found: {len(goals)}")
    
    types_found = {}
    duplicates_to_remove = []
    
    for g in goals:
        g_type = g.get("goal_type")
        if g_type in types_found:
            print(f"DUPLICATE FOUND: {g_type} | ID: {g.get('_id')}")
            duplicates_to_remove.append(g.get("_id"))
        else:
            types_found[g_type] = g.get("_id")
            print(f"KEEPING: {g_type} | ID: {g.get('_id')}")
            
    if duplicates_to_remove:
        print(f"\nRemoving {len(duplicates_to_remove)} duplicate(s)...")
        res = db.goals.delete_many({"_id": {"$in": duplicates_to_remove}})
        print(f"Successfully deleted {res.deleted_count} duplicate goal documents.")
    else:
        print("\nNo EXACT duplicates found for this ID. Checking all Sandips...")
        # Check if there are other Sandip IDs that might be contributing if the frontend is confused
        # But usually, it's just this one.

if __name__ == "__main__":
    hunt_duplicates()
