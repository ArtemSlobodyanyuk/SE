# Практична робота: Docker Volumes

## Мета

Зрозуміти, навіщо потрібні Docker volumes, на прикладі PostgreSQL. Спочатку запустимо контейнер **без volume** і побачимо, що дані зникають після видалення контейнера. Потім повторимо те саме **з volume** і переконаємось, що дані зберігаються.

---

## Частина 1: PostgreSQL БЕЗ volume (дані зникнуть)

### Крок 1. Запустити PostgreSQL без volume

```bash
docker run -d \
  --name pg-no-volume \
  -e POSTGRES_USER=student \
  -e POSTGRES_PASSWORD=secret123 \
  -e POSTGRES_DB=testdb \
  -p 5432:5432 \
  postgres:16
```

### Крок 2. Зачекати 3-5 секунд, поки PostgreSQL стартує

```bash
sleep 5
```

### Крок 3. Підключитись до бази та створити таблицю з даними

```bash
docker exec -it pg-no-volume psql -U student -d testdb
```

Виконати SQL-запити всередині psql:

```sql
CREATE TABLE students (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    grade INT NOT NULL
);

INSERT INTO students (name, grade) VALUES
    ('Олексій Шевченко', 95),
    ('Марія Коваленко', 88),
    ('Андрій Бондаренко', 72),
    ('Катерина Мельник', 91),
    ('Дмитро Ткаченко', 85);

SELECT * FROM students;
```

Ви побачите 5 записів у таблиці. Вийти з psql:

```sql
\q
```

### Крок 4. Зупинити та видалити контейнер

```bash
docker stop pg-no-volume
docker rm pg-no-volume
```

### Крок 5. Запустити новий контейнер з тими ж параметрами

```bash
docker run -d \
  --name pg-no-volume \
  -e POSTGRES_USER=student \
  -e POSTGRES_PASSWORD=secret123 \
  -e POSTGRES_DB=testdb \
  -p 5432:5432 \
  postgres:16
```

```bash
sleep 5
```

### Крок 6. Перевірити, чи збереглись дані

```bash
docker exec -it pg-no-volume psql -U student -d testdb
```

```sql
SELECT * FROM students;
```

**Результат:** помилка — таблиці `students` не існує. Дані були втрачені разом з контейнером.

```sql
\q
```

### Крок 7. Прибрати за собою

```bash
docker stop pg-no-volume
docker rm pg-no-volume
```

---

## Частина 2: PostgreSQL З volume (дані збережуться)

### Крок 1. Створити Docker volume

```bash
docker volume create pg-data
```

### Крок 2. Запустити PostgreSQL з підключеним volume

```bash
docker run -d \
  --name pg-with-volume \
  -e POSTGRES_USER=student \
  -e POSTGRES_PASSWORD=secret123 \
  -e POSTGRES_DB=testdb \
  -v pg-data:/var/lib/postgresql/data \
  -p 5432:5432 \
  postgres:16
```

### Крок 3. Зачекати та створити таблицю з даними

```bash
sleep 5
```

```bash
docker exec -it pg-with-volume psql -U student -d testdb
```

```sql
CREATE TABLE students (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    grade INT NOT NULL
);

INSERT INTO students (name, grade) VALUES
    ('Олексій Шевченко', 95),
    ('Марія Коваленко', 88),
    ('Андрій Бондаренко', 72),
    ('Катерина Мельник', 91),
    ('Дмитро Ткаченко', 85);

SELECT * FROM students;
```

```sql
\q
```

### Крок 4. Зупинити та ВИДАЛИТИ контейнер

```bash
docker stop pg-with-volume
docker rm pg-with-volume
```

### Крок 5. Запустити НОВИЙ контейнер з тим самим volume

```bash
docker run -d \
  --name pg-with-volume-2 \
  -e POSTGRES_USER=student \
  -e POSTGRES_PASSWORD=secret123 \
  -e POSTGRES_DB=testdb \
  -v pg-data:/var/lib/postgresql/data \
  -p 5432:5432 \
  postgres:16
```

```bash
sleep 5
```

### Крок 6. Перевірити, чи збереглись дані

```bash
docker exec -it pg-with-volume-2 psql -U student -d testdb
```

```sql
SELECT * FROM students;
```

**Результат:** всі 5 записів на місці! Дані збереглись завдяки volume.

```sql
\q
```

### Крок 7. Прибрати за собою

```bash
docker stop pg-with-volume-2
docker rm pg-with-volume-2
docker volume rm pg-data
```

---

## Частина 3: Корисні команди для роботи з volumes

Переглянути всі volumes:

```bash
docker volume ls
```

Детальна інформація про volume:

```bash
docker volume inspect pg-data
```

Видалити всі невикористовувані volumes:

```bash
docker volume prune
```

---

## Контрольні запитання

1. Що сталось з даними в Частині 1, коли ми видалили контейнер? Чому?
2. Чому в Частині 2 дані збереглись після видалення контейнера?
3. Куди фізично зберігаються дані Docker volume на хост-машині?
4. Яка різниця між named volume (`-v pg-data:/path`) та bind mount (`-v /host/path:/path`)?
5. Що станеться, якщо видалити volume командою `docker volume rm`?
