import io
from datetime import datetime, timedelta
from minio import Minio
from minio.error import S3Error
from config import MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, MINIO_BUCKET, MINIO_SECURE


class MinioClient:
    def __init__(self):
        self.client = Minio(
            MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=MINIO_SECURE,
        )
        self.bucket = MINIO_BUCKET
        self._ensure_bucket()

    def _ensure_bucket(self):
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
        except S3Error as e:
            print(f"MinIO bucket check error: {e}")

    def upload_file(self, filename: str, data: bytes) -> str:
        """上传文件到 MinIO，返回对象存储路径"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        key = f"uploads/{timestamp}_{filename}"

        buffer = io.BytesIO(data)
        buffer.seek(0)

        self.client.put_object(
            self.bucket,
            key,
            buffer,
            length=len(data),
        )
        return key

    def get_file_url(self, key: str, expires_hours: int = 24) -> str:
        """获取文件预签名 URL"""
        return self.client.presigned_get_object(self.bucket, key, expires=timedelta(hours=expires_hours))

    def get_file_data(self, key: str) -> bytes:
        """获取文件内容"""
        response = self.client.get_object(self.bucket, key)
        return response.read()

    def delete_file(self, key: str):
        """删除文件"""
        self.client.remove_object(self.bucket, key)

    def list_files(self) -> list[dict]:
        """列出所有上传的文件"""
        files = []
        try:
            objects = self.client.list_objects(self.bucket, prefix="uploads/", recursive=True)
            for obj in objects:
                files.append({
                    "filename": obj.object_name.split("/")[-1],
                    "minio_key": obj.object_name,
                    "size": obj.size,
                    "last_modified": obj.last_modified.isoformat() if obj.last_modified else None,
                })
        except S3Error as e:
            print(f"MinIO list error: {e}")
        return files


minio_client = MinioClient()
