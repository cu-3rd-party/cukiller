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


MODELS_STATE = (
    "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"
    "8rL4Hyx6LL0="
)
