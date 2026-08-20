from pathlib import Path
import sys

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

if __package__:
    from .api import router
    from .db import Base, engine
    from . import models  # noqa: F401 - 确保 SQLAlchemy 注册全部模型
else:
    # 允许在 PyCharm 中直接运行此文件；正常服务启动仍推荐 `uvicorn family_fund.main:app`。
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from family_fund.api import router
    from family_fund.db import Base, engine
    from family_fund import models  # noqa: F401 - 确保 SQLAlchemy 注册全部模型


Base.metadata.create_all(bind=engine)

app = FastAPI(title="家庭基金管理系统", version="0.1.0")
app.include_router(router)
STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8102)
