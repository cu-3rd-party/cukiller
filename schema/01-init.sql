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
);
