# api/routes/config.py
# ============================================================================
# 系统配置路由
#
# 管理用户级别的配置项：
#   - MinerU Token：用于调用 MinerU 文档解析 API
#   - LLM 配置：Base URL、API Key、模型名称
#
# 配置存储：
#   每个用户的配置以 user_id 为后缀的 key 存储在 Config 表，
#   例如 user_id=1 的 MinerU Token key 为 mineru_token_1，
#   这样实现用户级别的配置隔离。
# ============================================================================
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Config
from core.security import get_current_user_id
from schemas.schemas import (
    LLMConfigUpdate, LLMConfigResponse,
    MineruTokenUpdate, MineruTokenResponse,
    MessageResponse,
)

router = APIRouter(prefix="/api/config", tags=["系统配置"])


def _config_key(base: str, user_id: int) -> str:
    """生成用户级别的配置 key"""
    return f"{base}_{user_id}"


# ============================================================================
# MinerU Token
# ============================================================================

@router.put("/mineru", response_model=MessageResponse)
def update_mineru_token(
    body: MineruTokenUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    保存用户的 MinerU API Token

    Token 存储时以 user_id 为后缀，确保多用户配置隔离。
    """
    key = _config_key("mineru_token", user_id)
    cfg = db.query(Config).filter(Config.key == key).first()
    if cfg:
        cfg.value = body.token
    else:
        cfg = Config(key=key, value=body.token)
        db.add(cfg)
    db.commit()
    return MessageResponse(status="ok", message="MinerU Token 已保存")


@router.get("/mineru", response_model=MineruTokenResponse)
def get_mineru_token_status(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """查询 MinerU Token 是否已配置"""
    key = _config_key("mineru_token", user_id)
    cfg = db.query(Config).filter(Config.key == key).first()
    return MineruTokenResponse(configured=bool(cfg and cfg.value))


# ============================================================================
# LLM 配置
# ============================================================================

@router.put("/llm", response_model=MessageResponse)
def update_llm_config(
    body: LLMConfigUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    保存用户的 LLM 配置（Base URL、API Key、模型）

    三个配置项分别存储，支持单独更新。
    """
    configs = {
        "llm_base_url": body.base_url,
        "llm_api_key": body.api_key,
        "llm_model": body.model,
    }
    for k, v in configs.items():
        key = _config_key(k, user_id)
        cfg = db.query(Config).filter(Config.key == key).first()
        if cfg:
            cfg.value = v
        else:
            cfg = Config(key=key, value=v)
            db.add(cfg)

    db.commit()
    return MessageResponse(status="ok", message="LLM 配置已保存")


@router.get("/llm", response_model=LLMConfigResponse)
def get_llm_config(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    查询用户的 LLM 配置（不返回 api_key）
    """
    base_url_cfg = db.query(Config).filter(
        Config.key == _config_key("llm_base_url", user_id)
    ).first()
    model_cfg = db.query(Config).filter(
        Config.key == _config_key("llm_model", user_id)
    ).first()

    configured = all([
        base_url_cfg and base_url_cfg.value,
        model_cfg and model_cfg.value,
    ])

    return LLMConfigResponse(
        base_url=base_url_cfg.value if base_url_cfg else "",
        model=model_cfg.value if model_cfg else "",
        configured=configured,
    )
