# Практична робота: Docker Compose — REST API + PostgreSQL

## Мета
Навчитись розгортати бекенд-застосунок з базою даних за допомогою Docker Compose.

Що будемо будувати: REST API сервер (Python/Flask) який працює з PostgreSQL.

---

## Підготовка

```bash
docker --version
docker compose version
```

```bash
mkdir ~/compose-api-lab && cd ~/compose-api-lab
```

---

## Крок 1: Запускаємо PostgreSQL

Почнемо з самої бази даних. Створіть файл `compose.yaml`:

```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: taskdb
      POSTGRES_USER: apiuser
      POSTGRES_PASSWORD: apipass123
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

```bash
docker compose up -d
```

Перевіримо, що БД працює:

```bash
docker compose exec db psql -U apiuser -d taskdb -c "SELECT version();"
```

Зупиняємо — далі будемо запускати все разом:

```bash
docker compose down
```

**Питання для самоперевірки:**
- Навіщо потрібен named volume `pgdata`?
- Що станеться з даними при `docker compose down`? А при `docker compose down -v`?

---

## Крок 2: Створюємо REST API

Створіть файл `app.py` — Flask-додаток з CRUD операціями для сутності "Task":

```python
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, request, jsonify

app = Flask(__name__)

def get_db():
    return psycopg2.connect(
        host=os.environ["DB_HOST"],
        port=os.environ.get("DB_PORT", "5432"),
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASS"],
        cursor_factory=RealDictCursor
    )

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id SERIAL PRIMARY KEY,
            title VARCHAR(200) NOT NULL,
            description TEXT DEFAULT '',
            done BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

# GET /tasks — список всіх задач
@app.route("/tasks", methods=["GET"])
def get_tasks():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM tasks ORDER BY created_at DESC")
    tasks = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(tasks)

# POST /tasks — створити задачу
@app.route("/tasks", methods=["POST"])
def create_task():
    data = request.get_json()
    if not data or not data.get("title"):
        return jsonify({"error": "title is required"}), 400

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO tasks (title, description) VALUES (%s, %s) RETURNING *",
        (data["title"], data.get("description", ""))
    )
    task = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return jsonify(task), 201

# GET /tasks/<id> — отримати задачу за id
@app.route("/tasks/<int:task_id>", methods=["GET"])
def get_task(task_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM tasks WHERE id = %s", (task_id,))
    task = cur.fetchone()
    cur.close()
    conn.close()
    if not task:
        return jsonify({"error": "not found"}), 404
    return jsonify(task)

# PUT /tasks/<id> — оновити задачу
@app.route("/tasks/<int:task_id>", methods=["PUT"])
def update_task(task_id):
    data = request.get_json()
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """UPDATE tasks
           SET title = COALESCE(%s, title),
               description = COALESCE(%s, description),
               done = COALESCE(%s, done)
           WHERE id = %s RETURNING *""",
        (data.get("title"), data.get("description"), data.get("done"), task_id)
    )
    task = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    if not task:
        return jsonify({"error": "not found"}), 404
    return jsonify(task)

# DELETE /tasks/<id> — видалити задачу
@app.route("/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM tasks WHERE id = %s RETURNING id", (task_id,))
    deleted = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    if not deleted:
        return jsonify({"error": "not found"}), 404
    return jsonify({"deleted": task_id})

# GET /health — перевірка стану
@app.route("/health", methods=["GET"])
def health():
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        conn.close()
        return jsonify({"status": "ok", "db": "connected"})
    except Exception as e:
        return jsonify({"status": "error", "db": str(e)}), 500

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
```

Створіть файл `requirements.txt`:

```
flask
psycopg2-binary
```

---

## Крок 3: Dockerfile для API

Створіть файл `Dockerfile`:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

EXPOSE 5000

CMD ["python", "app.py"]
```

**Питання для самоперевірки:**
- Чому `COPY requirements.txt` та `RUN pip install` йдуть перед `COPY app.py`?
- Що дає `--no-cache-dir`?

---

## Крок 4: Compose — API + PostgreSQL разом

Оновіть `compose.yaml`:

```yaml
services:
  api:
    build: .
    ports:
      - "5000:5000"
    environment:
      DB_HOST: db
      DB_PORT: 5432
      DB_NAME: taskdb
      DB_USER: apiuser
      DB_PASS: apipass123
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: taskdb
      POSTGRES_USER: apiuser
      POSTGRES_PASSWORD: apipass123
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U apiuser -d taskdb"]
      interval: 5s
      timeout: 3s
      retries: 5
      start_period: 10s

volumes:
  pgdata:
```

Запускаємо:

```bash
docker compose up -d --build
```

Чекаємо поки db стане healthy:

```bash
docker compose ps
```

**Питання для самоперевірки:**
- Чому `DB_HOST` = `db`, а не `localhost`?
- Що відбудеться, якщо прибрати `healthcheck` і `condition: service_healthy`?

---

## Крок 5: Тестуємо API через curl

Перевірка здоров'я:

```bash
curl -s http://localhost:5000/health | python3 -m json.tool
```

Створюємо задачі:

```bash
curl -s -X POST http://localhost:5000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "Вивчити Docker Compose", "description": "Пройти практичну роботу"}' \
  | python3 -m json.tool
```

```bash
curl -s -X POST http://localhost:5000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "Написати Dockerfile", "description": "Для Flask API"}' \
  | python3 -m json.tool
```

```bash
curl -s -X POST http://localhost:5000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "Налаштувати healthcheck"}' \
  | python3 -m json.tool
```

Отримуємо всі задачі:

```bash
curl -s http://localhost:5000/tasks | python3 -m json.tool
```

Отримуємо задачу за id:

```bash
curl -s http://localhost:5000/tasks/1 | python3 -m json.tool
```

Позначаємо задачу як виконану:

```bash
curl -s -X PUT http://localhost:5000/tasks/1 \
  -H "Content-Type: application/json" \
  -d '{"done": true}' \
  | python3 -m json.tool
```

Видаляємо задачу:

```bash
curl -s -X DELETE http://localhost:5000/tasks/3 | python3 -m json.tool
```

Перевіряємо що залишилось:

```bash
curl -s http://localhost:5000/tasks | python3 -m json.tool
```

---

## Крок 6: Виносимо конфігурацію в .env

Створіть файл `.env`:

```env
DB_HOST=db
DB_PORT=5432
DB_NAME=taskdb
DB_USER=apiuser
DB_PASS=apipass123
API_PORT=5000
```

Оновіть `compose.yaml` щоб використовувати змінні:

```yaml
services:
  api:
    build: .
    ports:
      - "${API_PORT}:5000"
    environment:
      DB_HOST: ${DB_HOST}
      DB_PORT: ${DB_PORT}
      DB_NAME: ${DB_NAME}
      DB_USER: ${DB_USER}
      DB_PASS: ${DB_PASS}
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: ${DB_NAME}
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASS}
    ports:
      - "${DB_PORT}:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER} -d ${DB_NAME}"]
      interval: 5s
      timeout: 3s
      retries: 5
      start_period: 10s

volumes:
  pgdata:
```

Перевірте підстановку змінних:

```bash
docker compose config
```

Перезапустіть з новою конфігурацією:

```bash
docker compose down
docker compose up -d --build
curl -s http://localhost:5000/health | python3 -m json.tool
```

**Питання для самоперевірки:**
- Чому `.env` не треба вказувати в compose-файлі явно?
- Як би ви зробили окремі `.env` файли для dev та prod середовищ?

---

## Крок 7: Ініціалізація БД через SQL-скрипт

Замість ініціалізації в коді, створимо SQL-скрипти, які виконаються автоматично при першому запуску PostgreSQL.

```bash
mkdir -p initdb
```

Створіть файл `initdb/01-schema.sql`:

```sql
CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    description TEXT DEFAULT '',
    done BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

Створіть файл `initdb/02-seed.sql`:

```sql
INSERT INTO tasks (title, description) VALUES
    ('Встановити Docker', 'Завантажити та встановити Docker Desktop'),
    ('Вивчити Dockerfile', 'FROM, COPY, RUN, CMD, EXPOSE'),
    ('Вивчити Docker Compose', 'services, volumes, networks, depends_on'),
    ('Створити REST API', 'Flask + PostgreSQL в контейнерах');
```

Додайте монтування initdb у сервіс `db`. Оновіть `compose.yaml`:

```yaml
services:
  api:
    build: .
    ports:
      - "${API_PORT}:5000"
    environment:
      DB_HOST: ${DB_HOST}
      DB_PORT: ${DB_PORT}
      DB_NAME: ${DB_NAME}
      DB_USER: ${DB_USER}
      DB_PASS: ${DB_PASS}
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: ${DB_NAME}
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASS}
    ports:
      - "${DB_PORT}:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./initdb:/docker-entrypoint-initdb.d:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER} -d ${DB_NAME}"]
      interval: 5s
      timeout: 3s
      retries: 5
      start_period: 10s

volumes:
  pgdata:
```

Видаляємо старий volume і запускаємо заново (щоб спрацював initdb):

```bash
docker compose down -v
docker compose up -d --build
```

Перевірте що seed-дані на місці:

```bash
curl -s http://localhost:5000/tasks | python3 -m json.tool
```

**Питання для самоперевірки:**
- Коли виконуються скрипти з `/docker-entrypoint-initdb.d/`?
- Чому файли мають префікси `01-`, `02-`?
- Що станеться, якщо volume `pgdata` вже існує і має дані?

---

## Крок 8: Додаємо pgAdmin

Додамо веб-інтерфейс для перегляду бази даних. Оновіть `compose.yaml`:

```yaml
services:
  api:
    build: .
    ports:
      - "${API_PORT}:5000"
    environment:
      DB_HOST: ${DB_HOST}
      DB_PORT: ${DB_PORT}
      DB_NAME: ${DB_NAME}
      DB_USER: ${DB_USER}
      DB_PASS: ${DB_PASS}
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: ${DB_NAME}
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASS}
    ports:
      - "${DB_PORT}:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./initdb:/docker-entrypoint-initdb.d:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER} -d ${DB_NAME}"]
      interval: 5s
      timeout: 3s
      retries: 5
      start_period: 10s

  pgadmin:
    image: dpage/pgadmin4:latest
    environment:
      PGADMIN_DEFAULT_EMAIL: admin@lab.com
      PGADMIN_DEFAULT_PASSWORD: admin123
    ports:
      - "8888:80"
    depends_on:
      db:
        condition: service_healthy

volumes:
  pgdata:
```

```bash
docker compose up -d
```

Відкрийте `http://localhost:8888` у браузері:
- Логін: `admin@lab.com` / `admin123`
- Add New Server → Name: `taskdb`
- Connection → Host: `db`, Port: `5432`, User: `apiuser`, Password: `apipass123`

Знайдіть таблицю `tasks` і перегляньте дані.

---

## Крок 9: Логи та дебаг

Корисні команди для діагностики:

```bash
# Логи всіх сервісів
docker compose logs

# Логи API в реальному часі
docker compose logs -f api

# Останні 20 рядків логів БД
docker compose logs --tail 20 db

# Стан сервісів
docker compose ps

# Зайти всередину контейнера API
docker compose exec api sh

# Зайти в psql напряму
docker compose exec db psql -U apiuser -d taskdb

# Подивитись таблиці
docker compose exec db psql -U apiuser -d taskdb -c "\dt"

# Подивитись дані
docker compose exec db psql -U apiuser -d taskdb -c "SELECT * FROM tasks;"

# Процеси в контейнерах
docker compose top
```

---

## Прибирання

```bash
cd ~/compose-api-lab
docker compose down -v
cd ~
rm -rf ~/compose-api-lab
docker system prune -f
```

---

## Підсумок

Що ви навчились:

| Концепція | Де використали |
|-----------|---------------|
| `build` | Збірка Docker-образу для API з Dockerfile |
| `environment` | Передача конфігурації БД в контейнер |
| `depends_on` + `healthcheck` | API чекає поки БД буде готова |
| `volumes` (named) | Збереження даних PostgreSQL між перезапусками |
| `volumes` (bind mount) | SQL-скрипти для ініціалізації БД |
| `.env` файл | Винесення конфігурації з compose-файлу |
| `ports` | Доступ до API та pgAdmin з хост-машини |
| `docker compose exec` | Виконання команд всередині контейнера |
| `docker compose logs` | Перегляд логів для дебагу |

### Структура проєкту

```
compose-api-lab/
├── compose.yaml
├── .env
├── Dockerfile
├── app.py
├── requirements.txt
└── initdb/
    ├── 01-schema.sql
    └── 02-seed.sql
```
