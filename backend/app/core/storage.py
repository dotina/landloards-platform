"""MinIO (S3-compatible) storage client wrapper."""
from __future__ import annotations

from datetime import timedelta
from functools import lru_cache
from io import BytesIO
from typing import IO, BinaryIO, cast

from minio import Minio

from app.core.config import get_settings


@lru_cache(maxsize=1)
def get_minio_client() -> Minio:
    settings = get_settings()
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_use_ssl,
    )


def ensure_bucket(bucket: str | None = None) -> str:
    """Make sure the bucket exists; return the bucket name."""
    settings = get_settings()
    name = bucket or settings.minio_bucket
    client = get_minio_client()
    if not client.bucket_exists(name):
        client.make_bucket(name)
    return name


def put_object(
    *,
    key: str,
    data: bytes | IO[bytes],
    content_type: str,
    bucket: str | None = None,
) -> str:
    """Upload a blob; return its object key."""
    name = ensure_bucket(bucket)
    if isinstance(data, (bytes, bytearray)):
        stream: BinaryIO = BytesIO(data)
        length = len(data)
    else:
        stream = cast(BinaryIO, data)
        try:
            stream.seek(0, 2)
            length = stream.tell()
            stream.seek(0)
        except Exception:
            length = -1
    get_minio_client().put_object(
        bucket_name=name,
        object_name=key,
        data=stream,
        length=length,
        content_type=content_type,
        part_size=10 * 1024 * 1024 if length < 0 else 0,
    )
    return key


def presigned_get_url(*, key: str, expires_seconds: int = 300, bucket: str | None = None) -> str:
    """Return a short-lived presigned GET URL — default 5 min per design §3.3."""
    name = ensure_bucket(bucket)
    return get_minio_client().presigned_get_object(
        name, key, expires=timedelta(seconds=expires_seconds)
    )


def remove_object(*, key: str, bucket: str | None = None) -> None:
    name = ensure_bucket(bucket)
    get_minio_client().remove_object(name, key)
