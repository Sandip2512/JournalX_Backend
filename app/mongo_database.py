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
        if self.client is not None:
            return

        mongo_uri = os.getenv("MONGO_URI")
        if not mongo_uri:
            logger.error("MONGO_URI not found in environment variables")
            raise ValueError("MONGO_URI not set")

        try:
            # Add serverSelectionTimeoutMS to avoid long hangs
            self.client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
            db_name = os.getenv("DB_NAME", "JournalX") 
            self.db = self.client.get_database(db_name)
            
            # Verify connection
            self.client.admin.command('ping')
            logger.info(f"✅ Connected to MongoDB Atlas (DB: {db_name})")
            
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
