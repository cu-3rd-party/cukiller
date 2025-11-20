from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "chats" (
    "id" UUID NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "chat_id" BIGINT NOT NULL,
    "key" VARCHAR(1024) NOT NULL,
    CONSTRAINT "uid_chats_chat_id_eade16" UNIQUE ("chat_id", "key")
);
CREATE INDEX IF NOT EXISTS "idx_chats_chat_id_32de2a" ON "chats" ("chat_id");
CREATE INDEX IF NOT EXISTS "idx_chats_key_65a335" ON "chats" ("key");
COMMENT ON TABLE "chats" IS 'Админ-чаты Telegram';
CREATE TABLE IF NOT EXISTS "games" (
    "id" UUID NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "name" VARCHAR(255) NOT NULL,
    "start_date" TIMESTAMPTZ,
    "end_date" TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS "idx_games_start_d_fd08c2" ON "games" ("start_date");
COMMENT ON TABLE "games" IS 'Игры';
CREATE TABLE IF NOT EXISTS "users" (
    "id" UUID NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "tg_id" BIGINT NOT NULL UNIQUE,
    "tg_username" VARCHAR(32) UNIQUE,
    "name" VARCHAR(511),
    "type" VARCHAR(32),
    "course_number" SMALLINT,
    "group_name" VARCHAR(255),
    "is_in_game" BOOL NOT NULL DEFAULT False,
    "is_admin" BOOL NOT NULL DEFAULT False,
    "rating" INT NOT NULL DEFAULT 0,
    "photo" TEXT,
    "about_user" TEXT,
    "status" VARCHAR(32) NOT NULL DEFAULT 'active'
);
CREATE INDEX IF NOT EXISTS "idx_users_status_941fc1" ON "users" ("status");
CREATE INDEX IF NOT EXISTS "idx_users_tg_id_826a93" ON "users" ("tg_id");
COMMENT ON TABLE "users" IS 'Пользователи';
CREATE TABLE IF NOT EXISTS "kill_events" (
    "id" UUID NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "killer_confirmed" BOOL NOT NULL DEFAULT False,
    "killer_confirmed_at" TIMESTAMPTZ,
    "victim_confirmed" BOOL NOT NULL DEFAULT False,
    "victim_confirmed_at" TIMESTAMPTZ,
    "status" VARCHAR(16) NOT NULL DEFAULT 'pending',
    "moderated_at" TIMESTAMPTZ,
    "is_approved" BOOL NOT NULL DEFAULT False,
    "game_id" UUID NOT NULL REFERENCES "games" ("id") ON DELETE CASCADE,
    "killer_id" UUID NOT NULL REFERENCES "users" ("id") ON DELETE RESTRICT,
    "moderator_id" UUID REFERENCES "users" ("id") ON DELETE SET NULL,
    "victim_id" UUID NOT NULL REFERENCES "users" ("id") ON DELETE RESTRICT
);
CREATE INDEX IF NOT EXISTS "idx_kill_events_status_001745" ON "kill_events" ("status");
CREATE INDEX IF NOT EXISTS "idx_kill_events_game_id_a0ae34" ON "kill_events" ("game_id");
CREATE INDEX IF NOT EXISTS "idx_kill_events_killer__e5b69d" ON "kill_events" ("killer_id");
CREATE INDEX IF NOT EXISTS "idx_kill_events_victim__f088e3" ON "kill_events" ("victim_id");
COMMENT ON TABLE "kill_events" IS 'События «киллов»';
CREATE TABLE IF NOT EXISTS "players" (
    "id" UUID NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "game_id" UUID NOT NULL REFERENCES "games" ("id") ON DELETE CASCADE,
    "user_id" UUID NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_players_user_id_cc71c8" UNIQUE ("user_id", "game_id")
);
CREATE INDEX IF NOT EXISTS "idx_players_user_id_132ee4" ON "players" ("user_id");
CREATE INDEX IF NOT EXISTS "idx_players_game_id_44198d" ON "players" ("game_id");
COMMENT ON TABLE "players" IS 'Игроки в игре';
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """


MODELS_STATE = (
    "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"
    "+RISvUF33+8pXf4PQJ4pdQ=="
)
