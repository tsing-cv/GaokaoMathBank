"""SQLAlchemy 数据模型:papers / questions / assets。"""
from datetime import datetime, timezone

from sqlalchemy import (JSON, DateTime, Float, ForeignKey, Integer, String,
                        Text, create_engine)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from . import DB_PATH


class Base(DeclarativeBase):
    pass


class Paper(Base):
    __tablename__ = "papers"
    id: Mapped[int] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(Integer, index=True)
    province: Mapped[str] = mapped_column(String(64), index=True)  # 省份/卷种
    exam_type: Mapped[str] = mapped_column(String(16), index=True)  # 真题/一模/二模/三模/联考/机构卷
    subject: Mapped[str] = mapped_column(String(16))  # 理科/文科/新高考/通用
    name: Mapped[str] = mapped_column(String(255))
    source_name: Mapped[str] = mapped_column(String(128), default="")
    source_url: Mapped[str] = mapped_column(Text, default="")
    pdf_path: Mapped[str] = mapped_column(Text, default="")  # 原卷PDF(相对项目根)
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending/parsed/partial/failed
    question_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc))


class Question(Base):
    __tablename__ = "questions"
    id: Mapped[int] = mapped_column(primary_key=True)
    paper_id: Mapped[int] = mapped_column(ForeignKey("papers.id"), index=True)
    seq: Mapped[int] = mapped_column(Integer)  # 题号
    qtype: Mapped[str] = mapped_column(String(8))  # 选择/填空/解答
    stem: Mapped[list] = mapped_column(JSON)      # 分段JSON
    options: Mapped[list] = mapped_column(JSON, default=list)  # [{"label":"A","segs":[...]}]
    answer: Mapped[list] = mapped_column(JSON, default=list)
    analysis: Mapped[list] = mapped_column(JSON, default=list)
    knowledge_tags: Mapped[list] = mapped_column(JSON, default=list)
    difficulty: Mapped[float] = mapped_column(Float, nullable=True)
    source_hash: Mapped[str] = mapped_column(String(64), index=True)


class Asset(Base):
    __tablename__ = "assets"
    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), index=True)
    url: Mapped[str] = mapped_column(Text, default="")
    local_path: Mapped[str] = mapped_column(Text)  # web路径 /assets/xxx
    kind: Mapped[str] = mapped_column(String(16), default="figure")  # figure/formula_img


def _make_engine(db_path: str):
    return create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})


engine = _make_engine(str(DB_PATH))
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def rebind_db(db_path: str) -> None:
    """测试用:切换到独立临时库。

    注意:用 configure 换 bind 而非替换 SessionLocal 对象,
    保证各模块 from ... import SessionLocal 持有的引用同步生效。
    """
    global engine
    engine = _make_engine(db_path)
    SessionLocal.configure(bind=engine)
    Base.metadata.create_all(engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
