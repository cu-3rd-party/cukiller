from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "pending_profiles" (
    "id" UUID NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "name" VARCHAR(511),
    "type" VARCHAR(32),
    "course_number" SMALLINT,
    "group_name" VARCHAR(255),
    "photo" TEXT,
    "about_user" TEXT,
    "status" VARCHAR(32) NOT NULL DEFAULT 'pending',
    "is_new_profile" BOOL NOT NULL DEFAULT False,
    "reason" TEXT,
    "changed_fields" JSONB NOT NULL DEFAULT '[]'::JSONB,
    "chat_id" BIGINT,
    "message_id" BIGINT,
    "submitted_username" VARCHAR(32),
    "user_id" UUID NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE,
    "moderator_id" UUID REFERENCES "users" ("id") ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS "idx_pending_profiles_status" ON "pending_profiles" ("status");
CREATE INDEX IF NOT EXISTS "idx_pending_profiles_user_id" ON "pending_profiles" ("user_id");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "pending_profiles";"""


MODELS_STATE = ""
