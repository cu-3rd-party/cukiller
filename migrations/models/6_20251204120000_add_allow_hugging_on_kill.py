from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "users" ADD "allow_hugging_on_kill" BOOL NOT NULL DEFAULT False;
        ALTER TABLE "pending_profiles" ADD "allow_hugging_on_kill" BOOL NOT NULL DEFAULT False;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "pending_profiles" DROP COLUMN "allow_hugging_on_kill";
        ALTER TABLE "users" DROP COLUMN "allow_hugging_on_kill";"""


MODELS_STATE = (
    "",
)
