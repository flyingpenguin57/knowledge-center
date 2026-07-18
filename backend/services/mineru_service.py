# services/mineru_service.py
# ============================================================================
# MinerU 文档解析服务封装
#
# MinerU 是文档智能解析服务，能够将 PDF/Word/PPT/Excel/图片 等格式
# 的文档解析为结构化的 Markdown 内容，保留标题、表格、公式、图片等信息。
#
# 解析流程：
#   1. 获取上传预签名 URL（批量接口）
#   2. 通过 curl -T 上传文件到阿里云 OSS
#   3. 轮询批量任务状态，直到解析完成
#   4. 下载结果 ZIP，提取 full.md 内容
#
# 注意：MinerU API 需配合 Token 使用，Token 存储在数据库 Config 表
# ============================================================================
import subprocess
import tempfile
import os
import time
import zipfile
import io
import httpx


class MineruService:
    """
    MinerU 文档解析客户端

    通过云端 API 解析文档，返回 Markdown 格式的结构化内容。
    """

    # MinerU API 地址
    API_BASE = "https://mineru.net/api/v4"

    def __init__(self, token: str):
        self.token = token

    # =========================================================================
    # HTTP 工具
    # =========================================================================

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def _get(self, path: str) -> dict:
        with httpx.Client(timeout=60.0) as client:
            resp = client.get(f"{self.API_BASE}{path}", headers=self._headers())
            return resp.json()

    def _post(self, path: str, json: dict) -> dict:
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(f"{self.API_BASE}{path}", headers=self._headers(), json=json)
            return resp.json()

    # =========================================================================
    # 批量接口：获取上传 URL
    # =========================================================================

    def get_upload_urls(self, filenames: list[str], model_version: str = "vlm") -> dict:
        """
        向 MinerU 请求文件上传预签名 URL（批量接口）

        MinerU 返回阿里云 OSS 的上传地址，我们用 curl -T PUT 上传文件。

        Args:
            filenames: 文件名列表，用于 MinerU 识别文件类型
            model_version: 解析模型，vlm（推荐）或 pipeline

        Returns:
            包含 batch_id 和 file_urls 列表的响应
        """
        files = [{"name": name} for name in filenames]
        return self._post("/file-urls/batch", {
            "files": files,
            "model_version": model_version,
        })

    # =========================================================================
    # 文件上传（curl -T，等同于 PUT，行为与官方示例一致）
    # =========================================================================

    def upload_file(self, upload_url: str, file_path: str) -> bool:
        """
        使用 curl -T 上传本地文件到 MinerU 预签名 OSS 地址

        curl -T 会发送一个 PUT 请求，不设置额外的 Content-Type header，
        与阿里云 OSS 预签名 URL 的签名计算方式完全匹配。
        其他上传方式（如 httpx PUT）会导致签名不匹配。

        Args:
            upload_url: MinerU 返回的预签名上传 URL
            file_path: 本地文件的绝对路径

        Returns:
            True 表示上传成功（HTTP 200/201）
        """
        result = subprocess.run(
            ["curl", "-s", "-T", file_path, upload_url, "-w", "%{http_code}"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        status = result.stdout.strip()
        if status not in ("200", "201"):
            raise Exception(f"MinerU 上传失败: HTTP {status} {result.stderr}")
        return True

    # =========================================================================
    # 批量任务状态查询
    # =========================================================================

    def get_batch_results(self, batch_id: str) -> dict:
        """
        查询批量解析任务的结果

        返回各文件的解析状态（pending / running / done / failed）。

        Args:
            batch_id: 批量任务 ID

        Returns:
            包含 extract_result 列表的响应
        """
        return self._get(f"/extract-results/batch/{batch_id}")

    # =========================================================================
    # 单文件完整解析流程
    # =========================================================================

    def parse_file(self, file_path: str, filename: str, model_version: str = "vlm") -> str:
        """
        解析单个文件的完整流程（上传 → 轮询 → 下载结果）

        Args:
            file_path: 本地文件路径
            filename: 文件名（ MinerU 根据后缀识别类型）
            model_version: 解析模型

        Returns:
            解析后的 Markdown 内容字符串

        Raises:
            Exception: 上传失败、解析超时、结果提取失败时抛出
        """
        # 1. 获取上传 URL
        resp = self.get_upload_urls([filename], model_version)
        if resp.get("code") != 0:
            raise Exception(f"获取上传链接失败: {resp.get('msg')}")

        batch_id = resp["data"]["batch_id"]
        upload_url = resp["data"]["file_urls"][0]

        # 2. 上传文件（curl -T）
        self.upload_file(upload_url, file_path)

        # 3. 轮询等待解析完成（最多 5 分钟）
        max_wait = 300
        interval = 5
        for _ in range(max_wait // interval):
            time.sleep(interval)
            result = self.get_batch_results(batch_id)
            if result.get("code") != 0:
                continue

            extract_result = result["data"]["extract_result"]
            if not extract_result:
                continue

            state = extract_result[0]["state"]
            if state == "done":
                zip_url = extract_result[0].get("full_zip_url")
                if not zip_url:
                    raise Exception("MinerU 未返回结果 URL")
                return self._download_and_extract_markdown(zip_url)

            elif state == "failed":
                err = extract_result[0].get("err_msg", "解析失败")
                raise Exception(f"MinerU 解析失败: {err}")

        raise Exception("解析超时，请稍后重试")

    # =========================================================================
    # 下载 ZIP 并提取 full.md
    # =========================================================================

    def _download_and_extract_markdown(self, zip_url: str) -> str:
        """
        从 ZIP URL 下载并提取 full.md 内容

        MinerU 返回的是 ZIP 包，内含 layout.json、model.json、
        content_list.json 和 full.md（Markdown 格式解析结果）。

        Args:
            zip_url: ZIP 文件的下载 URL

        Returns:
            full.md 的文本内容
        """
        with httpx.Client(timeout=120.0, follow_redirects=True) as client:
            resp = client.get(zip_url)
            if resp.status_code != 200:
                raise Exception(f"下载解析结果失败: HTTP {resp.status_code}")

            with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
                # 查找 full.md（可能有多种命名，尝试多种模式）
                for name in zf.namelist():
                    if name.endswith("full.md"):
                        return zf.read(name).decode("utf-8")

                # 如果没找到，列出所有文件方便调试
                raise Exception(
                    f"ZIP 中未找到 full.md，文件列表: {zf.namelist()}"
                )
