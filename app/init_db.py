"""初始化数据库表与 FTS 索引。"""
from .models import Base, engine


def init() -> None:
    Base.metadata.create_all(engine)
    # FTS5 虚表:题干+答案+解析的纯文本(由 pipeline 写入)
    from sqlalchemy import text
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE VIRTUAL TABLE IF NOT EXISTS questions_fts USING fts5(
                question_id UNINDEXED, body, tokenize='trigram'
            )"""))
        conn.commit()
    print("数据库初始化完成")


if __name__ == "__main__":
    init()
