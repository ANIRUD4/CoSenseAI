import boto3
import os
import logging
from typing import Optional, Dict, Any
from botocore.exceptions import ClientError, NoCredentialsError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

S3_BUCKET_NAME = "intelshare-exports-2026"

# File size limit: 500MB
MAX_FILE_SIZE = 500 * 1024 * 1024


class S3StorageError(Exception):
    """Custom exception for S3 storage operations"""
    pass


def _get_s3_client():
    """
    Create and return S3 client using environment variables.
    
    Raises:
        S3StorageError: If AWS credentials are not configured
    """
    aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    aws_region = os.getenv("AWS_REGION", "eu-north-1")
    
    if not aws_access_key or not aws_secret_key:
        raise S3StorageError(
            "AWS credentials not configured. Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables."
        )
    
    try:
        return boto3.client(
            "s3",
            region_name=aws_region,
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key
        )
    except Exception as e:
        raise S3StorageError(f"Failed to create S3 client: {str(e)}")


def _validate_file(file_path: str) -> None:
    """
    Validate file exists and is within size limits.
    
    Args:
        file_path: Path to the file to validate
        
    Raises:
        FileNotFoundError: If file doesn't exist
        S3StorageError: If file exceeds size limit
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    file_size = os.path.getsize(file_path)
    if file_size > MAX_FILE_SIZE:
        raise S3StorageError(
            f"File size ({file_size / 1024 / 1024:.2f}MB) exceeds maximum allowed size ({MAX_FILE_SIZE / 1024 / 1024}MB)"
        )
    
    logger.info(f"File validation passed: {file_path} ({file_size / 1024 / 1024:.2f}MB)")


def export_pickle_to_cloud(local_pickle_path: str, user_id: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Upload a pickle file to S3 with error handling and validation.
    
    Args:
        local_pickle_path: Path to the local pickle file
        user_id: User ID for organizing files in S3
        metadata: Optional metadata to attach to the S3 object
        
    Returns:
        Dict containing status, message, s3_key, and file_size
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        S3StorageError: If upload fails or credentials are invalid
    """
    try:
        # Validate file
        _validate_file(local_pickle_path)
        
        s3 = _get_s3_client()
        
        filename = os.path.basename(local_pickle_path)
        s3_key = f"{user_id}/{filename}"
        file_size = os.path.getsize(local_pickle_path)
        
        logger.info(f"Starting upload: {filename} to s3://{S3_BUCKET_NAME}/{s3_key}")
        
        # Prepare extra args for upload
        extra_args = {}
        if metadata:
            extra_args['Metadata'] = {k: str(v) for k, v in metadata.items()}
        
        # Upload file
        s3.upload_file(local_pickle_path, S3_BUCKET_NAME, s3_key, ExtraArgs=extra_args if extra_args else None)
        
        logger.info(f"Upload successful: {s3_key}")
        
        return {
            "status": "success",
            "message": "Export completed successfully",
            "s3_key": s3_key,
            "file_size": file_size,
            "bucket": S3_BUCKET_NAME
        }
        
    except FileNotFoundError as e:
        logger.error(f"File not found: {str(e)}")
        raise
    except NoCredentialsError:
        error_msg = "AWS credentials not found or invalid"
        logger.error(error_msg)
        raise S3StorageError(error_msg)
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_msg = f"AWS S3 error ({error_code}): {str(e)}"
        logger.error(error_msg)
        raise S3StorageError(error_msg)
    except Exception as e:
        error_msg = f"Unexpected error during upload: {str(e)}"
        logger.error(error_msg)
        raise S3StorageError(error_msg)


def import_pickle_from_cloud(s3_key: str, local_destination_path: str) -> Dict[str, Any]:
    """
    Download a pickle file from S3 with error handling.
    
    Args:
        s3_key: S3 object key (path in bucket)
        local_destination_path: Local path where file should be saved
        
    Returns:
        Dict containing status, message, local_path, and file_size
        
    Raises:
        S3StorageError: If download fails or file doesn't exist in S3
    """
    try:
        # Create destination directory if it doesn't exist
        dest_dir = os.path.dirname(local_destination_path)
        if dest_dir:
            os.makedirs(dest_dir, exist_ok=True)
        
        s3 = _get_s3_client()
        
        logger.info(f"Starting download: s3://{S3_BUCKET_NAME}/{s3_key} to {local_destination_path}")
        
        # Check if object exists and get metadata
        try:
            response = s3.head_object(Bucket=S3_BUCKET_NAME, Key=s3_key)
            file_size = response.get('ContentLength', 0)
            logger.info(f"File found in S3: {file_size / 1024 / 1024:.2f}MB")
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                raise S3StorageError(f"File not found in S3: {s3_key}")
            raise
        
        # Download file
        s3.download_file(S3_BUCKET_NAME, s3_key, local_destination_path)
        
        logger.info(f"Download successful: {local_destination_path}")
        
        return {
            "status": "success",
            "message": "Import completed successfully",
            "local_path": local_destination_path,
            "file_size": file_size
        }
        
    except NoCredentialsError:
        error_msg = "AWS credentials not found or invalid"
        logger.error(error_msg)
        raise S3StorageError(error_msg)
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_msg = f"AWS S3 error ({error_code}): {str(e)}"
        logger.error(error_msg)
        raise S3StorageError(error_msg)
    except Exception as e:
        error_msg = f"Unexpected error during download: {str(e)}"
        logger.error(error_msg)
        raise S3StorageError(error_msg)


def list_user_models(user_id: str) -> Dict[str, Any]:
    """
    List all models uploaded by a specific user.
    
    Args:
        user_id: User ID to filter models
        
    Returns:
        Dict containing list of model keys and metadata
        
    Raises:
        S3StorageError: If listing fails
    """
    try:
        s3 = _get_s3_client()
        
        prefix = f"{user_id}/"
        logger.info(f"Listing models for user: {user_id}")
        
        response = s3.list_objects_v2(Bucket=S3_BUCKET_NAME, Prefix=prefix)
        
        models = []
        if 'Contents' in response:
            for obj in response['Contents']:
                models.append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'].isoformat()
                })
        
        logger.info(f"Found {len(models)} models for user {user_id}")
        
        return {
            "status": "success",
            "user_id": user_id,
            "models": models,
            "count": len(models)
        }
        
    except NoCredentialsError:
        error_msg = "AWS credentials not found or invalid"
        logger.error(error_msg)
        raise S3StorageError(error_msg)
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_msg = f"AWS S3 error ({error_code}): {str(e)}"
        logger.error(error_msg)
        raise S3StorageError(error_msg)
    except Exception as e:
        error_msg = f"Unexpected error during listing: {str(e)}"
        logger.error(error_msg)
        raise S3StorageError(error_msg)
