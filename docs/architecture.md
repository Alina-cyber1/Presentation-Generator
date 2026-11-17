# Архитектура решения «Презентатор»

## 1. Основной принцип
Разделение слоев. Сервис не должен быть монолитом, который «зависает» на 30 секунд, пока собирается слайд. Внедряем паттерн Producer-Consumer (постановщик задач — обработчик).

## 2. Слои системы
*   **Слой API (FastAPI + MCP Server):** Принимает запросы. Валидирует Pydantic. Возвращает `202 Accepted` и `task_id`. Не занимается генерацией.
*   **Слой очередей (Redis + ARQ):** Ставит задачу в очередь. Используем Redis с самого начала (P0), а не `BackgroundTasks`, чтобы не терять задачи при рестарте контейнера.
*   **Слой хранения (PostgreSQL + MinIO/S3):** В PostgreSQL храним статусы (`pending` → `processing` → `completed`), историю, метаданные стилей и поле `correlation_id` (для идемпотентности — если пришел дубликат запроса, возвращаем существующий `task_id`). В MinIO/S3 храним файлы шаблонов и сгенерированные `.pptx`.
*   **Слой исполнения (Worker + PipelineRunner):** Забирает задачу из очереди. Скачивает шаблон из S3. Запускает `run_factory.py` через асинхронный subprocess (`asyncio.create_subprocess_exec`), чтобы не блокировать Event Loop. Собирает итоговый файл через `DeckGenerator`.

## 3. Ключевые технические решения
*   **Параллелизм:** В ТЗ (раздел 6.1) указано, что генерация 1 слайда занимает 5-30 секунд. Если генерировать 10 слайдов последовательно, это 300 секунд, что нарушает KPI. **Решение:** Запускать subprocess-ы параллельно. `PipelineRunner` создает пул задач для независимых слайдов и собирает их результаты.
*   **Идемпотентность:** В ТЗ (раздел 3, п. A8) требуется защита от дублей. При создании задачи проверяем `correlation_id` в PostgreSQL. Если задача с таким ID уже есть (и она не упала с ошибкой), возвращаем её статус.
*   **Безопасность:** Секреты не храним в коде (ТЗ A9). Используем `.env` для dev и Vault/переменные окружения для prod. Внешние LLM (если это не локальный сервер) не должны получать персональные данные — маскируем PII перед отправкой.
*   **MCP-сервер:** Делаем не просто как обертку над REST, а с поддержкой **SSE (Server-Sent Events)**, чтобы внешний AI-агент мог получать стрим статуса («слайд 1 готов, слайд 2 готов...»), а не оборвал соединение по таймауту.

## 4. Схема архитектуры (Mermaid)

```mermaid
graph TD
    %% Клиенты
    ClientREST[REST Клиент]
    ClientMCP[MCP Клиент / AI-Агент]

    %% Слой API
    subgraph "Слой API (P0)"
        API[FastAPI REST]
        MCP[MCP Server SSE]
    end

    ClientREST --> API
    ClientMCP --> MCP

    %% Ядро и Очереди
    subgraph "Core (P0)"
        TM[TaskManager]
        Q[(Redis / ARQ)]
        W[Worker / PipelineRunner]
        DG[DeckGenerator]
    end

    API --> TM
    MCP --> TM
    TM --> Q
    Q --> W
    W --> DG

    %% AI Слой (P1)
    subgraph "AI Layer (P1/P2)"
        VA[VisualAdvisor]
        LLM[LLM Processor]
    end
    W -.-> VA
    VA -.-> LLM

    %% Legacy & Subprocess
    subgraph "Legacy (P0)"
        RF[run_factory.py]
    end
    W -- "subprocess (parallel)" --> RF

    %% Хранилища
    subgraph "Storage"
        DB[(PostgreSQL)]
        S3[(MinIO / S3)]
    end

    TM --> DB
    W --> S3
    DG --> S3
    
    %% Результат
    API -- "202 Accepted + task_id" --> ClientREST
    MCP -- "SSE Stream" --> ClientMCP
