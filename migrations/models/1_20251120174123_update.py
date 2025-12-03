from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "kill_events" RENAME COLUMN "victim_id" TO "victim_user_id";
        ALTER TABLE "kill_events" RENAME COLUMN "killer_id" TO "killer_user_id";"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
           ALTER TABLE "kill_events" RENAME COLUMN "victim_user_id" TO "victim_id";
           ALTER TABLE "kill_events" RENAME COLUMN "killer_user_id" TO "killer_id";"""


MODELS_STATE = (
    "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"
    "c76ERG7Q3fcbS1f/AzS3LbE="
)
