from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE INDEX IF NOT EXISTS "idx_chats_key_65a335" ON "chats" ("key");
        CREATE INDEX IF NOT EXISTS "idx_chats_chat_id_32de2a" ON "chats" ("chat_id");
        CREATE INDEX IF NOT EXISTS "idx_games_end_dat_85144d" ON "games" ("end_date");
        CREATE INDEX IF NOT EXISTS "idx_games_start_d_fd08c2" ON "games" ("start_date");
        CREATE INDEX IF NOT EXISTS "idx_users_is_admi_70b49f" ON "users" ("is_admin");
        CREATE INDEX IF NOT EXISTS "idx_users_is_in_g_f33c24" ON "users" ("is_in_game");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS "idx_users_is_in_g_f33c24";
        DROP INDEX IF EXISTS "idx_users_is_admi_70b49f";
        DROP INDEX IF EXISTS "idx_games_start_d_fd08c2";
        DROP INDEX IF EXISTS "idx_games_end_dat_85144d";
        DROP INDEX IF EXISTS "idx_chats_chat_id_32de2a";
        DROP INDEX IF EXISTS "idx_chats_key_65a335";"""


MODELS_STATE = (
    "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"
)
