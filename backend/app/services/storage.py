import logging
import uuid
from datetime import datetime, timezone

import boto3
from botocore.config import Config

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def upload_audio(data: bytes, content_type: str, patient_id: str) -> str:
    if not settings.bucket_configured:
        raise RuntimeError("Object storage is not configured")

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
        region_name=settings.bucket_region,
        config=Config(signature_version="s3v4"),
    )

    client.put_object(
        Bucket=settings.bucket_name,
        Key=key,
        Body=data,
        ContentType=content_type,
    )

    return f"{settings.bucket_endpoint.rstrip('/')}/{settings.bucket_name}/{key}"
