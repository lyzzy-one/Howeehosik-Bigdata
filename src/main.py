"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import health, safety_score
from src.config import get_settings

settings = get_settings()

app = FastAPI(
    title="안전귀가Navi API",
    description="서울시 주소 기반 안심 주거환경 점수 분석 서비스",
    version="1.0.0",
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(safety_score.router, prefix="/api/v1", tags=["Safety Score"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "안전귀가Navi API",
        "version": "1.0.0",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=settings.debug)
