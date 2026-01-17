import os
import logging
from threading import Lock
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class MongoDB:
    _instance = None
    _lock = Lock()
    client: MongoClient = None
    db = None

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(MongoDB, cls).__new__(cls)
            return cls._instance

    def connect(self):
        with self._lock:
            if self.client is not None:
                try:
                    # Quick check if client is still alive
                    self.client.admin.command('ping')
                    return self.db
                except (ConnectionFailure, ServerSelectionTimeoutError):
                    logger.warning("⚠️ Lost connection to MongoDB. Reconnecting...")
                    self.client = None

            mongo_uri = os.getenv("MONGO_URI")
            db_name = os.getenv("DB_NAME", "JournalX")
            
            if not mongo_uri:
                logger.error("🚫 MONGO_URI not found in environment variables")
                raise ValueError("MONGO_URI not set")

            try:
                # serverSelectionTimeoutMS=5000 is a good balance
                # connectTimeoutMS=10000 for initial handshake
                self.client = MongoClient(
                    mongo_uri, 
                    serverSelectionTimeoutMS=5000,
                    connectTimeoutMS=10000,
                    maxPoolSize=50
                )
                
                # Perform a single ping to verify connectivity
                self.client.admin.command('ping')
                self.db = self.client[db_name]
                logger.info(f"✅ Successfully connected to MongoDB Atlas (DB: {db_name})")
                return self.db
            except (ConnectionFailure, ServerSelectionTimeoutError) as e:
                logger.error(f"❌ Could not connect to MongoDB: {e}")
                self.client = None
                self.db = None
                raise

    def close(self):
        with self._lock:
            if self.client:
                self.client.close()
                self.client = None
                self.db = None
                logger.info("MongoDB connection closed")

db_client = MongoDB()

def get_db():
    if db_client.db is None:
        try:
            db_client.connect()
        except Exception as e:
            logger.error(f"Failed to get database connection: {e}")
            # We don't raise here to allow standard FastAPI error handling if needed,
            # or we let it raise if the route depends on it.
            raise
    return db_client.db
