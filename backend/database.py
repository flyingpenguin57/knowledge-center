# database.py
# ============================================================================
# 数据库连接管理
#
# 使用 SQLAlchemy 同步引擎连接 PostgreSQL。
# 所有表通过 declarative_base() 创建的 Base 类定义（见下方）。
#
# 表定义在 models.py 中，通过 Base.metadata.create_all() 批量创建。
# ============================================================================
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from config import DATABASE_URL

# 创建同步引擎
engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 声明基类（所有 ORM 模型都继承此类）
# Base 在这里定义，models.py 通过 from database import Base 引入
Base = declarative_base()


def get_db():
    """
    FastAPI 依赖：提供数据库会话

    用法：
        def endpoint(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
