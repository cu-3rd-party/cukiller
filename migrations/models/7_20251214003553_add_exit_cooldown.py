from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "users" ADD "exit_cooldown_until" TIMESTAMPTZ;
        CREATE INDEX IF NOT EXISTS "idx_users_exit_co_44e781" ON "users" ("exit_cooldown_until");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS "idx_users_exit_co_44e781";
        ALTER TABLE "users" DROP COLUMN "exit_cooldown_until";"""


MODELS_STATE = (
    "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"
    "pamp+5sU2nBZyYzauX+f/SIbNa"
)
