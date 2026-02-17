ALTER TABLE "users" ADD COLUMN IF NOT EXISTS "allow_hugging_on_kill" BOOL NOT NULL DEFAULT False;
ALTER TABLE "pending_profiles" ADD COLUMN IF NOT EXISTS "allow_hugging_on_kill" BOOL NOT NULL DEFAULT False;
