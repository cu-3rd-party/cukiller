DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'kill_events' AND column_name = 'victim_id'
    ) THEN
        ALTER TABLE "kill_events" RENAME COLUMN "victim_id" TO "victim_user_id";
    END IF;
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'kill_events' AND column_name = 'killer_id'
    ) THEN
        ALTER TABLE "kill_events" RENAME COLUMN "killer_id" TO "killer_user_id";
    END IF;
END $$;
