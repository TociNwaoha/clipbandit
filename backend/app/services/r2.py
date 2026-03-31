import logging
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from app.config import settings

logger = logging.getLogger(__name__)


class R2Client:
    def __init__(self):
        self._client = None
        self._available = False
        self._init_client()

    def _init_client(self):
        if settings.r2_account_id == "placeholder" or settings.r2_access_key_id == "placeholder":
            logger.warning("R2 credentials are placeholders — storage operations will be skipped")
            return
        try:
            self._client = boto3.client(
                "s3",
                endpoint_url=settings.r2_endpoint_url,
                aws_access_key_id=settings.r2_access_key_id,
                aws_secret_access_key=settings.r2_secret_access_key,
                region_name="auto",
            )
            self._available = True
        except Exception as exc:
            logger.warning(f"Failed to initialize R2 client: {exc}")

    @property
    def available(self) -> bool:
        return self._available

    def upload_file(self, file_path: str, storage_key: str, content_type: str = "application/octet-stream") -> bool:
        if not self._available:
            logger.warning(f"R2 not available — skipping upload of {storage_key}")
            return False
        try:
            self._client.upload_file(
                file_path,
                settings.r2_bucket_name,
                storage_key,
                ExtraArgs={"ContentType": content_type},
            )
            return True
        except (ClientError, NoCredentialsError) as exc:
            logger.error(f"R2 upload failed for {storage_key}: {exc}")
            return False

    def get_presigned_upload_url(self, storage_key: str, expires_in: int = 3600) -> str | None:
        if not self._available:
            return None
        try:
            return self._client.generate_presigned_url(
                "put_object",
                Params={"Bucket": settings.r2_bucket_name, "Key": storage_key},
                ExpiresIn=expires_in,
            )
        except ClientError as exc:
            logger.error(f"Failed to generate upload URL for {storage_key}: {exc}")
            return None

    def get_presigned_download_url(self, storage_key: str, expires_in: int = 3600) -> str | None:
        if not self._available:
            return None
        try:
            return self._client.generate_presigned_url(
                "get_object",
                Params={"Bucket": settings.r2_bucket_name, "Key": storage_key},
                ExpiresIn=expires_in,
            )
        except ClientError as exc:
            logger.error(f"Failed to generate download URL for {storage_key}: {exc}")
            return None

    def delete_file(self, storage_key: str) -> bool:
        if not self._available:
            return False
        try:
            self._client.delete_object(Bucket=settings.r2_bucket_name, Key=storage_key)
            return True
        except ClientError as exc:
            logger.error(f"R2 delete failed for {storage_key}: {exc}")
            return False


r2_client = R2Client()
