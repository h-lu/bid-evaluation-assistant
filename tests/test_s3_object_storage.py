"""Tests for S3ObjectStorage with mocked boto3."""

import sys
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_boto3():
    """Mock boto3 module for S3ObjectStorage tests."""
    mock_boto3_module = MagicMock()
    mock_client = MagicMock()
    mock_boto3_module.session.Session.return_value.client.return_value = mock_client

    with patch.dict(sys.modules, {"boto3": mock_boto3_module}):
        yield mock_boto3_module, mock_client


def test_s3_put_object_with_worm_mode(mock_boto3):
    """S3 WORM mode should not overwrite existing objects."""
    # Force reimport to pick up mocked boto3
    import importlib

    import app.object_storage as object_storage_module

    importlib.reload(object_storage_module)

    from app.object_storage import ObjectStorageConfig, S3ObjectStorage

    mock_boto3_module, mock_client = mock_boto3

    config = ObjectStorageConfig(
        backend="s3",
        bucket="test-bucket",
        root="/tmp",
        prefix="",
        worm_mode=True,
        endpoint="http://localhost:9000",
        region="us-east-1",
        access_key="key",
        secret_key="secret",
        force_path_style=True,
        retention_days=0,
        retention_mode="GOVERNANCE",
    )
    storage = S3ObjectStorage(config=config)

    # First call: object does not exist
    mock_client.head_object.side_effect = Exception("Not found")

    uri = storage.put_object(
        tenant_id="tenant_1",
        object_type="document",
        object_id="doc_1",
        filename="test.pdf",
        content_bytes=b"content",
        content_type="application/pdf",
    )

    assert uri == "object://s3/test-bucket/tenants/tenant_1/documents/doc_1/raw/test.pdf"
    mock_client.put_object.assert_called_once()


def test_s3_worm_mode_skips_existing_object(mock_boto3):
    """S3 WORM mode should skip upload if object already exists."""
    # Force reimport to pick up mocked boto3
    import importlib

    import app.object_storage as object_storage_module

    importlib.reload(object_storage_module)

    from app.object_storage import ObjectStorageConfig, S3ObjectStorage

    mock_boto3_module, mock_client = mock_boto3

    config = ObjectStorageConfig(
        backend="s3",
        bucket="test-bucket",
        root="/tmp",
        prefix="",
        worm_mode=True,
        endpoint="",
        region="",
        access_key="",
        secret_key="",
        force_path_style=True,
        retention_days=0,
        retention_mode="GOVERNANCE",
    )
    storage = S3ObjectStorage(config=config)

    # Object exists - head_object succeeds
    mock_client.head_object.return_value = {"ContentLength": 100}

    uri = storage.put_object(
        tenant_id="tenant_1",
        object_type="document",
        object_id="doc_1",
        filename="test.pdf",
        content_bytes=b"new content",
    )

    # Should return URI but NOT call put_object
    assert uri == "object://s3/test-bucket/tenants/tenant_1/documents/doc_1/raw/test.pdf"
    mock_client.put_object.assert_not_called()


def test_s3_get_presigned_url(mock_boto3):
    """S3ObjectStorage should generate presigned URLs."""
    import importlib

    import app.object_storage as object_storage_module

    importlib.reload(object_storage_module)

    from app.object_storage import ObjectStorageConfig, S3ObjectStorage

    mock_boto3_module, mock_client = mock_boto3

    config = ObjectStorageConfig(
        backend="s3",
        bucket="test-bucket",
        root="/tmp",
        prefix="",
        worm_mode=False,
        endpoint="",
        region="",
        access_key="",
        secret_key="",
        force_path_style=True,
        retention_days=0,
        retention_mode="GOVERNANCE",
    )
    storage = S3ObjectStorage(config=config)

    # Mock presigned URL generation
    mock_client.generate_presigned_url.return_value = "https://test-bucket.s3.amazonaws.com/key?signature=abc"

    url = storage.get_presigned_url(
        storage_uri="object://s3/test-bucket/tenants/tenant_1/documents/doc_1/raw/test.pdf",
        expires_in=3600,
    )

    assert url == "https://test-bucket.s3.amazonaws.com/key?signature=abc"
    mock_client.generate_presigned_url.assert_called_once_with(
        "get_object",
        Params={"Bucket": "test-bucket", "Key": "tenants/tenant_1/documents/doc_1/raw/test.pdf"},
        ExpiresIn=3600,
    )


def test_local_storage_presigned_url_returns_none():
    """LocalStorage should return None for presigned URLs (not supported)."""
    from app.object_storage import LocalObjectStorage, ObjectStorageConfig

    config = ObjectStorageConfig(
        backend="local",
        bucket="test-bucket",
        root="/tmp/test-local-storage",
        prefix="",
        worm_mode=False,
        endpoint="",
        region="",
        access_key="",
        secret_key="",
        force_path_style=True,
        retention_days=0,
        retention_mode="GOVERNANCE",
    )
    storage = LocalObjectStorage(config=config)

    # First store an object
    uri = storage.put_object(
        tenant_id="tenant_1",
        object_type="document",
        object_id="doc_1",
        filename="test.pdf",
        content_bytes=b"content",
    )

    # LocalStorage should return None (not supported)
    url = storage.get_presigned_url(storage_uri=uri, expires_in=3600)
    assert url is None
