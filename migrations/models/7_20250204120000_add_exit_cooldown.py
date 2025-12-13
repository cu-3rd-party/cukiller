from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
           ALTER TABLE "users" ADD "exit_cooldown_until" TIMESTAMPTZ;
           CREATE INDEX IF NOT EXISTS "idx_users_exit_cooldown" ON "users" ("exit_cooldown_until");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
           DROP INDEX IF EXISTS "idx_users_exit_cooldown";
           ALTER TABLE "users" DROP COLUMN "exit_cooldown_until";"""


MODELS_STATE = ""
