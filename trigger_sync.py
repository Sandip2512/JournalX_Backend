import requests
import pymongo

def main():
    try:
        client = pymongo.MongoClient('mongodb://localhost:27017')
        db = client['journalx']
        user = db.users.find_one({'email': 'sandipsalunkhe6640@gmail.com'})
        
        if not user:
            print("User not found.")
            return

        print(f"Triggering sync for user: {user['user_id']}")
        r = requests.post(f"http://localhost:8000/users/{user['user_id']}/fetch-mt5-trades")
        print("Sync Status:", r.status_code)
        print("Response:", r.json())

    except Exception as e:
        print("Error:", e)

if __name__ == '__main__':
    main()
