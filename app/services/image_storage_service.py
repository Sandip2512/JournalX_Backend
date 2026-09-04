from pymongo.database import Database
from gridfs import GridFS
from typing import Optional
import logging
from io import BytesIO

logger = logging.getLogger(__name__)


class ImageStorageService:
    """
    Image storage service using MongoDB GridFS.
    Designed with abstraction layer for easy migration to AWS S3 in the future.
    """
    
    def __init__(self, db: Database):
        self.db = db
        self.fs = GridFS(db)
    
    def upload_image(self, image_data: bytes, filename: str, content_type: str = "image/jpeg") -> str:
        """
        Upload an image to GridFS.
        
        Args:
            image_data: Binary image data
            filename: Original filename
            content_type: MIME type of the image
            
        Returns:
            file_id: GridFS file ID as string
        """
        try:
            file_id = self.fs.put(
                image_data,
                filename=filename,
                content_type=content_type
            )
            logger.info(f"Uploaded image {filename} to GridFS with ID {file_id}")
            return str(file_id)
        except Exception as e:
            logger.error(f"Error uploading image to GridFS: {str(e)}")
            raise
    
    def get_image(self, file_id: str) -> Optional[tuple]:
        """
        Retrieve an image from GridFS.
        
        Args:
            file_id: GridFS file ID
            
        Returns:
            Tuple of (image_data, content_type, filename) or None if not found
        """
        try:
            from bson.objectid import ObjectId
            
            grid_out = self.fs.get(ObjectId(file_id))
            image_data = grid_out.read()
            content_type = grid_out.content_type or "image/jpeg"
            filename = grid_out.filename or "image.jpg"
            
            logger.info(f"Retrieved image {file_id} from GridFS")
            return (image_data, content_type, filename)
        except Exception as e:
            logger.error(f"Error retrieving image from GridFS: {str(e)}")
            return None
    
    def delete_image(self, file_id: str) -> bool:
        """
        Delete an image from GridFS.
        
        Args:
            file_id: GridFS file ID
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            from bson.objectid import ObjectId
            
            self.fs.delete(ObjectId(file_id))
            logger.info(f"Deleted image {file_id} from GridFS")
            return True
        except Exception as e:
            logger.error(f"Error deleting image from GridFS: {str(e)}")
            return False
    
    def get_image_url(self, file_id: str) -> str:
        """
        Generate URL for image retrieval.
        
        Args:
            file_id: GridFS file ID
            
        Returns:
            URL path for the image
        """
        return f"/api/posts/images/{file_id}"


def get_image_storage_service(db: Database) -> ImageStorageService:
    """Factory function to get image storage service"""
    return ImageStorageService(db)
