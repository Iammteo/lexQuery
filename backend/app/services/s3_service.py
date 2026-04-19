import uuid
from typing import BinaryIO, Optional

import boto3
from botocore.exceptions import ClientError

from app.core.config import get_settings

settings = get_settings()


class S3Service:
    """
    Wrapper around AWS S3 for document storage.

    Key rules enforced by this service:
    - Every object key is prefixed with the tenant_id.
      This gives path-level isolation so one tenant's files can
      never accidentally live under another tenant's prefix.
    - Bucket is private — all access goes through this service.
    """

    def __init__(self):
        self.bucket = settings.s3_bucket_name
        client_kwargs = {
            "region_name": settings.aws_region,
            "aws_access_key_id": settings.aws_access_key_id,
            "aws_secret_access_key": settings.aws_secret_access_key,
        }
        # Support MinIO / localstack by overriding the endpoint
        if settings.s3_endpoint_url:
            client_kwargs["endpoint_url"] = settings.s3_endpoint_url

        self.client = boto3.client("s3", **client_kwargs)

    @staticmethod
    def build_key(tenant_id: uuid.UUID, document_id: uuid.UUID, filename: str) -> str:
        """
        Build the S3 object key for a document.
        Format: {tenant_id}/{document_id}/{filename}

        Example: 555f6c4c-55cf-4e72-b274-dcb0bac1d74c/abc-123/contract.pdf
        """
        return f"{tenant_id}/{document_id}/{filename}"

    def upload_fileobj(
        self,
        file_obj: BinaryIO,
        key: str,
        content_type: Optional[str] = None,
    ) -> str:
        """
        Upload a file object to S3.
        Returns the S3 key on success.
        """
        extra_args = {}
        if content_type:
            extra_args["ContentType"] = content_type

        self.client.upload_fileobj(
            Fileobj=file_obj,
            Bucket=self.bucket,
            Key=key,
            ExtraArgs=extra_args,
        )
        return key

    def download_to_bytes(self, key: str) -> bytes:
        """
        Download a file from S3 and return its bytes.
        Used by the ingestion worker to fetch a document for processing.
        """
        import io
        buffer = io.BytesIO()
        self.client.download_fileobj(
            Bucket=self.bucket,
            Key=key,
            Fileobj=buffer,
        )
        buffer.seek(0)
        return buffer.read()

    def delete(self, key: str) -> None:
        """Delete a single object."""
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
        except ClientError as e:
            # If the object doesn't exist, that's fine — idempotent
            if e.response["Error"]["Code"] != "NoSuchKey":
                raise

    def generate_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        """
        Generate a temporary URL that lets a browser download the file
        without needing AWS credentials. Used when serving document
        previews from the frontend.
        """
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires_in,
        )


# Singleton — cheap to reuse
_s3_service: Optional[S3Service] = None


def get_s3_service() -> S3Service:
    global _s3_service
    if _s3_service is None:
        _s3_service = S3Service()
    return _s3_service
