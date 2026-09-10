import uvicorn
from backend.app.core.config import settings

if __name__ == "__main__":
    print(f"Starting {settings.APP_NAME} on http://{settings.HOST}:{settings.PORT}")
    print(f"Swagger API Documentation: http://localhost:{settings.PORT}/docs")
    print(f"Web Dashboard: http://localhost:{settings.PORT}/")
    uvicorn.run(
        "backend.app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False
    )
