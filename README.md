# Презентатор (Presentation Generator)

OpenSource-сервис для автоматической генерации многостраничных PPTX-презентаций с помощью AI-советника и шаблонов.

## О проекте
Сервис принимает JSON с данными слайдов или текстовый промпт, анализирует данные, выбирает оптимальный тип визуализации и собирает готовую презентацию в корпоративном стиле. 

**Стек технологий:**
*   **Backend:** Python 3.10+, FastAPI, Pydantic v2
*   **Очереди и кэш:** Redis, ARQ (Async Redis Queue)
*   **Базы данных:** PostgreSQL (метаданные, статусы), MinIO/S3 (хранение файлов)
*   **AI/LLM:** OpenAI-compatible API, Langfuse (трейсинг)
*   **Работа с PPTX:** python-pptx, run_factory.py (legacy)
*   **Интеграции:** MCP Server (Streamable HTTP)

## Архитектура решения
Подробное описание архитектуры, потоков данных и ключевых технических решений доступно в [docs/architecture.md](docs/architecture.md).

```mermaid
graph TD
    ClientREST[REST Клиент] --> API[FastAPI REST]
    ClientMCP[MCP Клиент] --> MCP[MCP Server SSE]
    
    API --> TM[TaskManager]
    MCP --> TM
    TM --> DB[(PostgreSQL)]
    TM --> Q[(Redis / ARQ)]
    
    Q --> W[Worker / PipelineRunner]
    W --> S3[(MinIO / S3)]
    W -- "subprocess" --> RF[run_factory.py]
    W --> DG[DeckGenerator]
    DG --> S3
