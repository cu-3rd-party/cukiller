ALTER TABLE "players" ADD COLUMN IF NOT EXISTS "rating" INT NOT NULL DEFAULT 600;
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'users' AND column_name = 'rating'
    ) THEN
        UPDATE "players" SET "rating" = users.rating FROM "users" WHERE players.user_id=users.id;
    END IF;
END $$;
ALTER TABLE "users" DROP COLUMN IF EXISTS "rating";
