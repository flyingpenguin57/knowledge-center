# api/routes/auth.py
# ============================================================================
# 认证路由
#
# 提供用户注册、登录接口，返回 JWT token。
# JWT token 在后续所有需要认证的请求中通过 header 传递：
#   Authorization: Bearer <token>
#
# 数据隔离机制：
#   所有业务数据（文档、chunk）通过 user_id 字段关联用户，
#   API 依赖 get_current_user_id() 从 token 中解析出 user_id，
#   确保用户只能访问自己的数据。
# ============================================================================
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from database import get_db
from models import User
from core.security import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user_id,
)
from schemas.schemas import UserRegister, UserLogin, Token, UserInfo

router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/register", response_model=Token)
def register(body: UserRegister, db: Session = Depends(get_db)):
    """
    用户注册

    - 检查用户名唯一性
    - 密码 bcrypt 哈希存储（永不明文）
    - 返回 JWT access_token
    """
    # 检查用户名是否已存在
    existing = db.query(User).filter(User.username == body.username).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在",
        )

    # 创建用户，密码哈希存储
    user = User(
        username=body.username,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # 生成 JWT token
    token = create_access_token(user.id)
    return Token(access_token=token)


@router.post("/login", response_model=Token)
def login(body: UserLogin, db: Session = Depends(get_db)):
    """
    用户登录

    - 校验用户名和密码
    - 密码匹配成功则返回 JWT token
    """
    user = db.query(User).filter(User.username == body.username).first()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账户已被禁用",
        )

    token = create_access_token(user.id)
    return Token(access_token=token)


@router.get("/me", response_model=UserInfo)
def get_me(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    获取当前登录用户信息

    需要在请求 header 中携带有效的 JWT token：
      Authorization: Bearer <token>
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return UserInfo.model_validate(user)
