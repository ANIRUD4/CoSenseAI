import json
import shutil
import time
import os
import tempfile
import logging
from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, BackgroundTasks
from backend.export_import import (
    export_pickle_to_cloud, 
    import_pickle_from_cloud, 
    list_user_models,
    S3StorageError
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/share", tags=["share"])

# Metadata storage - using local JSON for now, can be migrated to DynamoDB later
METADATA_DIR = os.path.join(os.getcwd(), "marketplace_metadata")
os.makedirs(METADATA_DIR, exist_ok=True)

# Default user ID (in production, get from authentication)
DEFAULT_USER_ID = "default_user"

class ModelMetadata(BaseModel):
    id: str
    name: str
    description: str
    author: str
    created_at: float
    s3_key: str
    file_size: int
    user_id: str

class ShareRequest(BaseModel):
    name: str
    description: str
    author: str = "Anonymous"
    user_id: str = DEFAULT_USER_ID


def _save_metadata(metadata: ModelMetadata) -> None:
    """Save metadata to local JSON file"""
    metadata_path = os.path.join(METADATA_DIR, f"{metadata.id}.json")
    with open(metadata_path, "w") as f:
        f.write(metadata.model_dump_json(indent=2))
    logger.info(f"Metadata saved: {metadata.id}")


def _load_metadata(model_id: str) -> Optional[ModelMetadata]:
    """Load metadata from local JSON file"""
    metadata_path = os.path.join(METADATA_DIR, f"{model_id}.json")
    if not os.path.exists(metadata_path):
        return None
    
    with open(metadata_path, "r") as f:
        data = json.load(f)
        return ModelMetadata(**data)


def _cleanup_temp_file(file_path: str) -> None:
    """Background task to cleanup temporary files"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Cleaned up temporary file: {file_path}")
    except Exception as e:
        logger.error(f"Failed to cleanup temp file {file_path}: {e}")


@router.post("/export")
def export_model_to_marketplace(request: ShareRequest, background_tasks: BackgroundTasks):
    """
    Zips current model state and uploads it to AWS S3.
    
    Args:
        request: ShareRequest containing model metadata
        background_tasks: FastAPI background tasks for cleanup
        
    Returns:
        Success response with model ID and S3 details
        
    Raises:
        HTTPException: If models directory doesn't exist or S3 upload fails
    """
    try:
        # 1. Validate models directory exists
        current_models_path = os.path.join(os.getcwd(), "models")
        if not os.path.exists(current_models_path):
            raise HTTPException(status_code=404, detail="No models found to export")

        # 2. Create unique model ID
        model_id = f"model_{int(time.time())}"
        
        # 3. Create temporary zip file
        temp_dir = tempfile.gettempdir()
        zip_filename = f"{model_id}.zip"
        zip_base_path = os.path.join(temp_dir, model_id)
        
        logger.info(f"Creating zip archive for model: {model_id}")
        shutil.make_archive(zip_base_path, 'zip', current_models_path)
        zip_path = f"{zip_base_path}.zip"

        # 4. Upload to S3
        logger.info(f"Uploading to S3 for user: {request.user_id}")
        upload_metadata = {
            "name": request.name,
            "description": request.description,
            "author": request.author,
            "created_at": str(time.time())
        }
        
        s3_result = export_pickle_to_cloud(
            zip_path, 
            request.user_id,
            metadata=upload_metadata
        )

        # 5. Create and save metadata
        metadata = ModelMetadata(
            id=model_id,
            name=request.name,
            description=request.description,
            author=request.author,
            created_at=time.time(),
            s3_key=s3_result["s3_key"],
            file_size=s3_result["file_size"],
            user_id=request.user_id
        )
        
        _save_metadata(metadata)

        # 6. Schedule cleanup of temporary zip file
        background_tasks.add_task(_cleanup_temp_file, zip_path)

        logger.info(f"Model exported successfully: {model_id}")

        return {
            "status": "success",
            "message": f"Model '{request.name}' exported to marketplace successfully",
            "id": model_id,
            "s3_key": s3_result["s3_key"],
            "file_size_mb": round(s3_result["file_size"] / 1024 / 1024, 2)
        }

    except S3StorageError as e:
        logger.error(f"S3 storage error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Cloud storage error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error during export: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/list")
def list_marketplace_models():
    """
    List all available models in the marketplace.
    
    Returns:
        Dict containing list of all marketplace models with metadata
    """
    try:
        models = []
        
        # Read all metadata files
        for filename in os.listdir(METADATA_DIR):
            if filename.endswith(".json"):
                try:
                    with open(os.path.join(METADATA_DIR, filename), "r") as f:
                        data = json.load(f)
                        models.append(data)
                except Exception as e:
                    logger.error(f"Error reading metadata {filename}: {e}")
        
        # Sort by creation date (newest first)
        models.sort(key=lambda x: x.get('created_at', 0), reverse=True)
        
        logger.info(f"Listed {len(models)} marketplace models")
        
        return {
            "status": "success",
            "models": models,
            "count": len(models)
        }
        
    except Exception as e:
        logger.error(f"Error listing models: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list models: {str(e)}")


@router.post("/import/{model_id}")
def import_model_from_marketplace(model_id: str, background_tasks: BackgroundTasks):
    """
    Download model from S3 and extract to local models directory.
    
    Args:
        model_id: Unique identifier of the model to import
        background_tasks: FastAPI background tasks for cleanup
        
    Returns:
        Success response with import details
        
    Raises:
        HTTPException: If model not found or download fails
    """
    try:
        # 1. Load metadata
        metadata = _load_metadata(model_id)
        if not metadata:
            raise HTTPException(status_code=404, detail="Model not found in marketplace")

        # 2. Create temporary download path
        temp_dir = tempfile.gettempdir()
        temp_zip_path = os.path.join(temp_dir, f"{model_id}_download.zip")

        # 3. Download from S3
        logger.info(f"Downloading model {model_id} from S3: {metadata.s3_key}")
        download_result = import_pickle_from_cloud(metadata.s3_key, temp_zip_path)

        # 4. Extract to models directory
        target_dir = os.path.join(os.getcwd(), "models")
        os.makedirs(target_dir, exist_ok=True)

        logger.info(f"Extracting model to: {target_dir}")
        shutil.unpack_archive(temp_zip_path, target_dir)

        # 5. Schedule cleanup of temporary zip file
        background_tasks.add_task(_cleanup_temp_file, temp_zip_path)

        logger.info(f"Model imported successfully: {model_id}")

        return {
            "status": "success",
            "message": f"Model '{metadata.name}' imported successfully",
            "model_id": model_id,
            "name": metadata.name,
            "author": metadata.author,
            "file_size_mb": round(download_result["file_size"] / 1024 / 1024, 2)
        }

    except S3StorageError as e:
        logger.error(f"S3 storage error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Cloud storage error: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during import: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.get("/user/{user_id}/models")
def get_user_models(user_id: str):
    """
    Get all models uploaded by a specific user.
    
    Args:
        user_id: User ID to filter models
        
    Returns:
        List of models with metadata for the specified user
    """
    try:
        # Get models from metadata
        user_models = []
        for filename in os.listdir(METADATA_DIR):
            if filename.endswith(".json"):
                try:
                    with open(os.path.join(METADATA_DIR, filename), "r") as f:
                        data = json.load(f)
                        if data.get('user_id') == user_id:
                            user_models.append(data)
                except Exception as e:
                    logger.error(f"Error reading metadata {filename}: {e}")
        
        # Sort by creation date
        user_models.sort(key=lambda x: x.get('created_at', 0), reverse=True)
        
        logger.info(f"Found {len(user_models)} models for user {user_id}")
        
        return {
            "status": "success",
            "user_id": user_id,
            "models": user_models,
            "count": len(user_models)
        }
        
    except Exception as e:
        logger.error(f"Error getting user models: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get user models: {str(e)}")
