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
    "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"
)
