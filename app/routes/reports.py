from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import FileResponse
from pymongo.database import Database
from datetime import datetime, timedelta
import os

from app.mongo_database import get_db
from app.routes.auth import get_current_user_role
from app.crud.report_crud import create_report_metadata, get_user_reports, get_report
from app.services.performance_service import PerformanceService
from app.services.pdf_report_service import PDFReportService
from app.schemas.report_schema import PerformanceReportResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

pdf_service = PDFReportService()

def run_report_generation(user_id: str, user_name: str, report_type: str, report_id: str, start_date: datetime, end_date: datetime, db: Database):
    """Background task to generate report."""
    reports_coll = db.get_collection("reports")
    logger.info(f"🚀 Starting background report generation for user {user_id}, type {report_type}, id {report_id}")
    try:
        # 1. Get Performance Data
        perf_service = PerformanceService(db)
        data = perf_service.get_period_data(user_id, start_date, end_date)
        
        if not data:
            logger.warning(f"⚠️ No data found for report {report_id}")
            reports_coll.update_one({"id": report_id}, {"$set": {"status": "failed", "error": "No data found"}})
            return

        # 2. Generate PDF
        logger.info(f"📊 Data fetched, generating PDF for report {report_id}")
        filename = pdf_service.generate_report_pdf(user_name, report_type, data['stats'], data['insights'])

        # 3. Update Metadata
        logger.info(f"✅ PDF generated: {filename}, updating database for report {report_id}")
        result = reports_coll.update_one({"id": report_id}, {"$set": {
            "filename": filename,
            "status": "completed",
            "completed_at": datetime.now()
        }})
        
        if result.modified_count == 0:
            logger.error(f"❌ Failed to update report status in database for {report_id}. Result: {result.raw_result}")
        else:
            logger.info(f"🎉 Report {report_id} completed successfully")

    except Exception as e:
        logger.error(f"❌ Background Report Error for {report_id}: {str(e)}", exc_info=True)
        reports_coll.update_one({"id": report_id}, {"$set": {"status": "failed", "error": str(e)}})

@router.post("/generate")
async def generate_report(
    background_tasks: BackgroundTasks,
    report_type: str = Query(..., regex="^(weekly|monthly|yearly|custom)$"),
    start_date: str = Query(None),
    end_date: str = Query(None),
    db: Database = Depends(get_db),
    user: dict = Depends(get_current_user_role)
):
    # Tier Check
    user_tier = user.get("subscription_tier", "free").lower()
    if user_tier == "free":
        raise HTTPException(
            status_code=403, 
            detail="Performance Reports are only available for Pro and Elite members. Please upgrade your plan."
        )
    
    try:
        user_id = user["user_id"]
        user_name = f"{user.get('first_name', 'Trader')} {user.get('last_name', '')}".strip()
        
        # Calculate Dates
        dt_end = datetime.now()
        if report_type == "weekly":
            dt_start = dt_end - timedelta(days=7)
        elif report_type == "monthly":
            dt_start = dt_end - timedelta(days=30)
        elif report_type == "yearly":
            dt_start = dt_end - timedelta(days=365)
        else: # custom
            if not start_date or not end_date:
                raise HTTPException(status_code=400, detail="Start and end dates required for custom report")
            dt_start = datetime.fromisoformat(start_date.split('T')[0])
            dt_end = datetime.fromisoformat(end_date.split('T')[0]) + timedelta(days=1)

        # 1. Create Initial Metadata (Pending)
        report_metadata = {
            "user_id": user_id,
            "report_type": report_type,
            "start_date": dt_start,
            "end_date": dt_end,
            "filename": "", # Not yet generated
            "status": "pending"
        }
        report = create_report_metadata(db, report_metadata)
        
        # 2. Add to Background Tasks
        background_tasks.add_task(
            run_report_generation, 
            user_id, 
            user_name, 
            report_type, 
            report["id"], 
            dt_start, 
            dt_end, 
            db
        )
        
        return {"message": "Report generation started", "report_id": report["id"]}

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error starting report generation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/my-reports", response_model=list[PerformanceReportResponse])
def list_reports(
    db: Database = Depends(get_db),
    user: dict = Depends(get_current_user_role)
):
    reports = get_user_reports(db, user["user_id"])
    return reports

@router.get("/preview-data")
def get_report_preview_data(
    report_type: str = Query(..., regex="^(weekly|monthly|yearly|custom)$"),
    start_date: str = Query(None),
    end_date: str = Query(None),
    db: Database = Depends(get_db),
    user: dict = Depends(get_current_user_role)
):
    """Fetch aggregated data for frontend report preview."""
    # Tier Check
    user_tier = user.get("subscription_tier", "free").lower()
    if user_tier == "free":
        raise HTTPException(
            status_code=403, 
            detail="Performance Reports are only available for Pro and Elite members. Please upgrade your plan."
        )

    try:
        user_id = user["user_id"]
        perf_service = PerformanceService(db)
        
        # Calculate Dates
        dt_end = datetime.now()
        if report_type == "weekly":
            dt_start = dt_end - timedelta(days=7)
        elif report_type == "monthly":
            dt_start = dt_end - timedelta(days=30)
        elif report_type == "yearly":
            dt_start = dt_end - timedelta(days=365)
        else: # custom
            if not start_date or not end_date:
                raise HTTPException(status_code=400, detail="Start and end dates required for custom report")
            dt_start = datetime.fromisoformat(start_date.split('T')[0])
            dt_end = datetime.fromisoformat(end_date.split('T')[0]) + timedelta(days=1)
            
        data = perf_service.get_report_data(user_id, dt_start, dt_end)
        
        if not data:
             raise HTTPException(status_code=404, detail="No trading data found for this period.")
             
        return data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching preview data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{report_id}/download")
def download_report(
    report_id: str,
    db: Database = Depends(get_db),
    user: dict = Depends(get_current_user_role)
):
    report = get_report(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
        
    if report["user_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Unauthorized access to this report")

    file_path = os.path.join(pdf_service.reports_dir, report["filename"])
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Physical report file not found")
        
    return FileResponse(
        file_path, 
        media_type="application/pdf", 
        filename=report["filename"]
    )

@router.delete("/{report_id}")
def delete_report(
    report_id: str,
    db: Database = Depends(get_db),
    user: dict = Depends(get_current_user_role)
):
    logger.info(f"🗑️ Delete request for report {report_id} by user {user.get('user_id')}")
    report = get_report(db, report_id)
    if not report:
        logger.warning(f"❌ Report {report_id} not found in database")
        raise HTTPException(status_code=404, detail="Report not found")
        
    logger.info(f"📄 Found report: user_id={report.get('user_id')}, current_user_id={user.get('user_id')}")
    if str(report.get("user_id")) != str(user.get("user_id")):
        logger.warning(f"🚫 Unauthorized delete attempt: report owned by {report.get('user_id')}")
        raise HTTPException(status_code=403, detail="Unauthorized to delete this report")

    # 1. Delete File if exists
    if report.get("filename"):
        file_path = os.path.join(pdf_service.reports_dir, report["filename"])
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"🗑️ Deleted physical report file: {report['filename']}")
            else:
                logger.warning(f"⚠️ Physical report file not found: {report['filename']}")
        except Exception as e:
            logger.error(f"❌ Error deleting report file: {e}")

    # 2. Delete Metadata
    from app.crud.report_crud import delete_report_metadata
    success = delete_report_metadata(db, report_id)
    
    if not success:
        logger.error(f"❌ Failed to delete metadata for report {report_id}")
        raise HTTPException(status_code=500, detail="Failed to delete report metadata")
        
    logger.info(f"✅ Report {report_id} deleted successfully")
    return {"message": "Report deleted successfully"}
