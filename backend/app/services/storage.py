import logging
import uuid

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.config import get_settings

logger = logging.getLogger(__name__)


def upload_audio(data: bytes, content_type: str, patient_id: str) -> str:
    settings = get_settings()

    if not settings.bucket_configured:
        raise RuntimeError(
            "Object storage is not configured. Set BUCKET (or BUCKET_NAME), "
            "ACCESS_KEY_ID, SECRET_ACCESS_KEY, and ENDPOINT."
        )

    ext = "webm"
    if "mp4" in content_type or "m4a" in content_type:
        ext = "m4a"
    elif "ogg" in content_type:
        ext = "ogg"
    elif "wav" in content_type:
        ext = "wav"

    key = f"voice/{patient_id}/{uuid.uuid4()}.{ext}"

    client = boto3.client(
        "s3",
        endpoint_url=settings.bucket_endpoint,
        aws_access_key_id=settings.bucket_access_key,
        aws_secret_access_key=settings.bucket_secret_key,
        region_name=settings.bucket_region if settings.bucket_region != "auto" else "us-east-1",
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "virtual"},
            retries={"max_attempts": 3, "mode": "standard"},
        ),
    )

    try:
        client.put_object(
            Bucket=settings.bucket_name,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
    except (ClientError, BotoCoreError) as exc:
        logger.exception(
            "S3 put_object failed for bucket=%s key=%s endpoint=%s",
            settings.bucket_name,
            key,
            settings.bucket_endpoint,
        )
        raise RuntimeError(f"Failed to upload audio to bucket: {exc}") from exc

    logger.info("Uploaded voice note to bucket=%s key=%s", settings.bucket_name, key)
    return f"{settings.bucket_endpoint.rstrip('/')}/{settings.bucket_name}/{key}"
