from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "players" ADD "rating" INT NOT NULL DEFAULT 600;
        UPDATE "players" SET "rating" = users.rating FROM "users" WHERE players.user_id=users.id;
        ALTER TABLE "users" DROP COLUMN "rating";"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "users" ADD "rating" INT NOT NULL DEFAULT 0;
        ALTER TABLE "players" DROP COLUMN "rating";"""


MODELS_STATE = (
    "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"
    "yA26h35n6ep/GGkuFw=="
)
