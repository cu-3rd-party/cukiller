from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "users" ADD "given_name" VARCHAR(255);
        ALTER TABLE "users" ADD "family_name" VARCHAR(255);
        ALTER TABLE "users" ADD "family_name_required" BOOL NOT NULL DEFAULT False;
        UPDATE "users" SET "given_name" = COALESCE("given_name", "name");
        ALTER TABLE "users" DROP COLUMN "name";

        ALTER TABLE "pending_profiles" ADD "given_name" VARCHAR(255);
        ALTER TABLE "pending_profiles" ADD "family_name" VARCHAR(255);
        UPDATE "pending_profiles" SET "given_name" = COALESCE("given_name", "name");
        ALTER TABLE "pending_profiles" DROP COLUMN "name";
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "pending_profiles" ADD "name" VARCHAR(511);
        UPDATE "pending_profiles" SET "name" = COALESCE("family_name", '') || ' ' || COALESCE("given_name", '');
        ALTER TABLE "pending_profiles" DROP COLUMN "family_name";
        ALTER TABLE "pending_profiles" DROP COLUMN "given_name";

        ALTER TABLE "users" ADD "name" VARCHAR(511);
        UPDATE "users" SET "name" = COALESCE("family_name", '') || ' ' || COALESCE("given_name", '');
        ALTER TABLE "users" DROP COLUMN "family_name_required";
        ALTER TABLE "users" DROP COLUMN "family_name";
        ALTER TABLE "users" DROP COLUMN "given_name";
    """


MODELS_STATE = ""
