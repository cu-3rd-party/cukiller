
-- Initial schema for cukiller based on db/models
-- Dialect: PostgreSQL

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Helper function to update updated_at timestamp
CREATE OR REPLACE FUNCTION trigger_set_timestamp()
RETURNS TRIGGER AS $$
BEGIN
	NEW.updated_at = NOW();
	RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Table: users
CREATE TABLE IF NOT EXISTS users (
	id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
	created_at timestamptz NOT NULL DEFAULT now(),
	updated_at timestamptz NOT NULL DEFAULT now(),

	tg_id bigint NOT NULL UNIQUE,
	tg_username varchar(32),
	name varchar(511),
	type varchar(32),
	course_number smallint CHECK (course_number IS NULL OR (course_number >= 1 AND course_number <= 8)),
	group_name varchar(255),

	is_in_game boolean NOT NULL DEFAULT false,
	is_admin boolean NOT NULL DEFAULT false,
	rating integer NOT NULL DEFAULT 0 CHECK (rating >= 0),

	photo text,
	about_user text,

	status varchar(32) NOT NULL DEFAULT 'active'
);

CREATE UNIQUE INDEX IF NOT EXISTS users_tg_username_idx ON users(tg_username);
CREATE INDEX IF NOT EXISTS users_status_idx ON users(status);
CREATE INDEX IF NOT EXISTS users_tg_id_idx ON users(tg_id);

-- Table: games
CREATE TABLE IF NOT EXISTS games (
	id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
	created_at timestamptz NOT NULL DEFAULT now(),
	updated_at timestamptz NOT NULL DEFAULT now(),

	name varchar(255) NOT NULL,
	start_date timestamptz,
	end_date timestamptz
);

CREATE INDEX IF NOT EXISTS games_start_date_idx ON games(start_date);

-- Table: players
CREATE TABLE IF NOT EXISTS players (
	id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
	created_at timestamptz NOT NULL DEFAULT now(),
	updated_at timestamptz NOT NULL DEFAULT now(),

	user_id uuid NOT NULL,
	game_id uuid NOT NULL,

	CONSTRAINT players_user_fk FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
	CONSTRAINT players_game_fk FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE,
	CONSTRAINT players_user_game_unique UNIQUE (user_id, game_id)
);

CREATE INDEX IF NOT EXISTS players_user_idx ON players(user_id);
CREATE INDEX IF NOT EXISTS players_game_idx ON players(game_id);

-- Table: chats
-- Note: original model references a `thread` field in unique_together; adding thread bigint NULLABLE
CREATE TABLE IF NOT EXISTS chats (
	id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
	created_at timestamptz NOT NULL DEFAULT now(),
	updated_at timestamptz NOT NULL DEFAULT now(),

	chat_id bigint NOT NULL,
	thread bigint,
	key varchar(1024) NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS chats_chat_thread_unique ON chats(chat_id, thread);
CREATE INDEX IF NOT EXISTS chats_chat_id_idx ON chats(chat_id);

-- Table: kill_events
-- Added occurred_at timestamptz because __str__ references it
CREATE TABLE IF NOT EXISTS kill_events (
	id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
	created_at timestamptz NOT NULL DEFAULT now(),
	updated_at timestamptz NOT NULL DEFAULT now(),

	game_id uuid NOT NULL,

	killer_user_id uuid NOT NULL,
	victim_user_id uuid NOT NULL,

	killer_confirmed boolean NOT NULL DEFAULT false,
	killer_confirmed_at timestamptz,

	victim_confirmed boolean NOT NULL DEFAULT false,
	victim_confirmed_at timestamptz,

	status varchar(16) NOT NULL DEFAULT 'pending',

	moderator_id uuid,
	moderated_at timestamptz,

	is_approved boolean NOT NULL DEFAULT false,

	occurred_at timestamptz NOT NULL DEFAULT now(),

	CONSTRAINT kill_events_game_fk FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE,
	CONSTRAINT kill_events_killer_fk FOREIGN KEY (killer_user_id) REFERENCES users(id) ON DELETE RESTRICT,
	CONSTRAINT kill_events_victim_fk FOREIGN KEY (victim_user_id) REFERENCES users(id) ON DELETE RESTRICT,
	CONSTRAINT kill_events_moderator_fk FOREIGN KEY (moderator_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS kill_events_game_occurred_idx ON kill_events(game_id, occurred_at);
CREATE INDEX IF NOT EXISTS kill_events_killer_idx ON kill_events(killer_user_id);
CREATE INDEX IF NOT EXISTS kill_events_victim_idx ON kill_events(victim_user_id);
CREATE INDEX IF NOT EXISTS kill_events_status_idx ON kill_events(status);

-- Triggers to keep updated_at current
CREATE TRIGGER users_set_timestamp BEFORE UPDATE ON users
FOR EACH ROW EXECUTE FUNCTION trigger_set_timestamp();

CREATE TRIGGER games_set_timestamp BEFORE UPDATE ON games
FOR EACH ROW EXECUTE FUNCTION trigger_set_timestamp();

CREATE TRIGGER players_set_timestamp BEFORE UPDATE ON players
FOR EACH ROW EXECUTE FUNCTION trigger_set_timestamp();

CREATE TRIGGER chats_set_timestamp BEFORE UPDATE ON chats
FOR EACH ROW EXECUTE FUNCTION trigger_set_timestamp();

CREATE TRIGGER kill_events_set_timestamp BEFORE UPDATE ON kill_events
FOR EACH ROW EXECUTE FUNCTION trigger_set_timestamp();

-- End of migration
