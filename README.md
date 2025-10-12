# CU killer bot

Бот для игры в Killer в Telegram для Центрального Университета

## Запуск

-   Скачайте проект

```bash
git clone <>
```

-   Скопируйте и изменить настройки .env

```bash
cp .env.example .env
```

-   Поднимите контейнер

```bash
docker compose up -d
```

-   Чтобы остановить

```bash
docker compose down
```

## Просмотр БД через Adminer

Посетите http://localhost:8080/ и введите следующие параметры:

-   System: PostgreSQL
-   Server: db
-   Username: admin
-   Password: admin
-   Database: db
