# core/security.py
# ============================================================================
# 安全认证工具
# 提供：
#   - JWT Token 的创建与验证
#   - 密码哈希与校验（bcrypt）
# 所有 API 路由通过 token 验证用户身份，实现用户级别数据隔离
# ============================================================================
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
import bcrypt

from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

# OAuth2 密码模式，token 从 Authorization header 提取
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# ============================================================================
# 密码操作
# ============================================================================

def hash_password(password: str) -> str:
    """
    对明文密码进行 bcrypt 哈希
    用于用户注册时保护密码
    """
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    校验明文密码与存储的 bcrypt 哈希是否匹配
    """
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8")
    )


# ============================================================================
# JWT Token 操作
# ============================================================================

def create_access_token(user_id: int, expires_delta: Optional[timedelta] = None) -> str:
    """
    创建 JWT 访问令牌

    Args:
        user_id: 用户 ID，作为 token payload 中的 sub 声明
        expires_delta: 可选过期时间，默认 24 小时

    Returns:
        JWT 字符串，供客户端后续请求使用
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": str(user_id),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[int]:
    """
    验证并解析 JWT token

    Args:
        token: JWT 字符串

    Returns:
        成功返回 user_id，失败返回 None
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
        return int(user_id)
    except jwt.ExpiredSignatureError:
        return None
    except jwt.PyJWTError:
        return None


# ============================================================================
# 依赖注入：获取当前登录用户
# ============================================================================

async def get_current_user_id(token: str = Depends(oauth2_scheme)) -> int:
    """
    FastAPI 依赖：从请求头提取并验证 token，返回当前登录用户的 ID

    适用于需要用户登录才能访问的 API 端点
    未携带有效 token 的请求会返回 401
    """
    user_id = decode_token(token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效或已过期的 token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_id
