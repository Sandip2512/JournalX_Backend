from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import os
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)

class MongoDB:
    client: MongoClient = None
    db = None

    def connect(self):
        mongo_uri = os.getenv("MONGO_URI")
        if not mongo_uri:
            logger.error("MONGO_URI not found in environment variables")
            raise ValueError("MONGO_URI not set")

        try:
            self.client = MongoClient(mongo_uri)
            # The 'get_database' method is better than attribute access for creating/getting db
            # Assuming the URI might have the db name, or we use a default
            db_name = os.getenv("DB_NAME", "JournalX") 
            # If URI has db name, pymongo might use it, but explicit is safer if needed.
            # However, typically Atlas URI allows .../dbname?params
            self.db = self.client.get_database(db_name)
            
            # Verify connection
            self.client.admin.command('ping')
            logger.info("✅ Connected to MongoDB Atlas")
            
        except ConnectionFailure as e:
            logger.error(f"❌ Could not connect to MongoDB: {e}")
            raise

    def close(self):
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")

db_client = MongoDB()

def get_db():
    if db_client.db is None:
        db_client.connect()
    return db_client.db
