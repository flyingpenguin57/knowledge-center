import httpx
import io
import zipfile
from config import MINERU_API_URL


class MineruClient:
    """MinerU 精准解析 API 客户端"""

    def __init__(self, token: str):
        self.token = token
        self.base_url = MINERU_API_URL.rstrip("/")

    def _headers(self, json: bool = True) -> dict:
        headers = {"Authorization": f"Bearer {self.token}"}
        if json:
            headers["Content-Type"] = "application/json"
        return headers

    # ---- 批量文件上传（获取上传链接）----
    def get_upload_urls(self, files: list[dict], model_version: str = "vlm") -> dict:
        """调用批量接口，获取文件上传预签名 URL"""
        url = f"{self.base_url.replace('/extract/task', '')}/file-urls/batch"
        payload = {
            "files": files,
            "model_version": model_version,
        }
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(url, headers=self._headers(), json=payload)
            return resp.json()

    def upload_to_url(self, upload_url: str, file_path: str):
        """上传本地文件到 MinerU 预签名 URL，使用 curl -T"""
        import subprocess
        result = subprocess.run(
            ["curl", "-s", "-T", file_path, upload_url, "-w", "%{http_code}"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.stdout.strip() not in ("200", "201"):
            raise Exception(f"上传到 MinerU 失败: HTTP {result.stdout} {result.stderr}")

    # ---- 解析任务 ----
    def create_task(self, file_url: str, model_version: str = "vlm") -> dict:
        """提交解析任务（URL 方式）"""
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(
                f"{self.base_url}",
                headers=self._headers(),
                json={
                    "url": file_url,
                    "model_version": model_version,
                    "enable_formula": True,
                    "enable_table": True,
                    "language": "ch",
                }
            )
            return resp.json()

    def get_task_result(self, task_id: str) -> dict:
        """查询任务状态和结果"""
        url = f"{self.base_url.replace('/extract/task', '')}/extract/task/{task_id}"
        with httpx.Client(timeout=60.0) as client:
            resp = client.get(url, headers=self._headers())
            return resp.json()

    def download_and_extract_markdown(self, zip_url: str) -> str:
        """下载 ZIP 并提取 full.md 内容"""
        with httpx.Client(timeout=120.0, follow_redirects=True) as client:
            resp = client.get(zip_url)
            if resp.status_code != 200:
                raise Exception(f"下载失败: {resp.status_code}")

            with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
                for name in zf.namelist():
                    if name.endswith("full.md"):
                        return zf.read(name).decode("utf-8")
                raise Exception(f"ZIP 中未找到 full.md，文件列表: {zf.namelist()}")

    def get_batch_results(self, batch_id: str) -> dict:
        """批量查询解析结果"""
        url = f"{self.base_url.replace('/extract/task', '')}/extract-results/batch/{batch_id}"
        with httpx.Client(timeout=60.0) as client:
            resp = client.get(url, headers=self._headers())
            return resp.json()
