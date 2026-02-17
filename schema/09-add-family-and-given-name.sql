ALTER TABLE "users" ADD COLUMN IF NOT EXISTS "given_name" VARCHAR(255);
ALTER TABLE "users" ADD COLUMN IF NOT EXISTS "family_name" VARCHAR(255);
ALTER TABLE "users" ADD COLUMN IF NOT EXISTS "family_name_required" BOOL NOT NULL DEFAULT False;
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'users' AND column_name = 'name'
    ) THEN
        UPDATE "users" SET "given_name" = COALESCE("given_name", "name");
        ALTER TABLE "users" DROP COLUMN "name";
    END IF;
END $$;

ALTER TABLE "pending_profiles" ADD COLUMN IF NOT EXISTS "given_name" VARCHAR(255);
ALTER TABLE "pending_profiles" ADD COLUMN IF NOT EXISTS "family_name" VARCHAR(255);
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'pending_profiles' AND column_name = 'name'
    ) THEN
        UPDATE "pending_profiles" SET "given_name" = COALESCE("given_name", "name");
        ALTER TABLE "pending_profiles" DROP COLUMN "name";
    END IF;
END $$;
