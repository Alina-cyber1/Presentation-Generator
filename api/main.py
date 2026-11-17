from fastapi import FastAPI
import uuid

app = FastAPI(
    title="Presentation Generator API",
    description="API для генерации презентаций",
    version="0.1.0"
)

@app.get("/api/v1/health")
def health_check():
    """Проверка работоспособности сервиса"""
    return {"status": "ok", "version": "0.1.0"}

@app.post("/api/v1/presentation/generate")
def generate_presentation():
    """Заглушка для приема задачи на генерацию"""
    task_id = str(uuid.uuid4())
    return {
        "task_id": task_id,
        "status": "pending",
        "polling_url": f"/api/v1/presentation/{task_id}/status"
    }
