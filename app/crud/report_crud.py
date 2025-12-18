from pymongo.database import Database
from datetime import datetime
import uuid
from typing import List, Optional

def create_report_metadata(db: Database, report_data: dict):
    report_data["id"] = str(uuid.uuid4())
    report_data["created_at"] = datetime.now()
    try:
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"📝 Inserting report metadata: {report_data['id']}")
        db.reports.insert_one(report_data)
        logger.info(f"✅ Metadata inserted for {report_data['id']}")
    except Exception as e:
        logger.error(f"❌ Failed to insert report metadata: {e}", exc_info=True)
        raise
    return report_data

def get_user_reports(db: Database, user_id: str) -> List[dict]:
    return list(db.reports.find({"user_id": user_id}).sort("created_at", -1))

def get_report(db: Database, report_id: str) -> Optional[dict]:
    return db.reports.find_one({"id": report_id})
