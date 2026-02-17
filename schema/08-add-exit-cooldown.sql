ALTER TABLE "users" ADD COLUMN IF NOT EXISTS "exit_cooldown_until" TIMESTAMPTZ;
CREATE INDEX IF NOT EXISTS "idx_users_exit_co_44e781" ON "users" ("exit_cooldown_until");
