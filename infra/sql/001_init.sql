CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS citext;

BEGIN;

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at := NOW();
  RETURN NEW;
END;
$$;


-- =====================================================================
CREATE TABLE users (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tg_id           BIGINT UNIQUE NOT NULL,
  tg_username     CITEXT UNIQUE,
  given_name      TEXT,
  family_name     TEXT,
  course_number   SMALLINT CHECK (course_number BETWEEN 1 AND 8),
  group_name      TEXT,
  is_in_game      BOOLEAN NOT NULL DEFAULT FALSE,
  is_admin        BOOLEAN NOT NULL DEFAULT FALSE,
  global_rating   INTEGER NOT NULL DEFAULT 0 CHECK (global_rating >= 0),
  photo           TEXT,
  about_user      TEXT,
  status          TEXT NOT NULL DEFAULT 'active',
  type            TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE users IS 'Пользователи';
COMMENT ON COLUMN users.id              IS 'ID';
COMMENT ON COLUMN users.tg_id           IS 'ID в Telegram';
COMMENT ON COLUMN users.tg_username     IS 'Логин Telegram';
COMMENT ON COLUMN users.given_name      IS 'Имя';
COMMENT ON COLUMN users.family_name     IS 'Фамилия';
COMMENT ON COLUMN users.course_number   IS 'Курс';
COMMENT ON COLUMN users.group_name      IS 'Группа/поток';
COMMENT ON COLUMN users.is_in_game      IS 'Сейчас в игре';
COMMENT ON COLUMN users.is_admin        IS 'Администратор';
COMMENT ON COLUMN users.global_rating   IS 'Общий рейтинг';
COMMENT ON COLUMN users.photo           IS 'Фото';
COMMENT ON COLUMN users.about_user      IS 'О себе';
COMMENT ON COLUMN users.status          IS 'Статус';
COMMENT ON COLUMN users.type            IS 'Тип (студент/сотрудник/абитуриент)';
COMMENT ON COLUMN users.created_at      IS 'Создано';
COMMENT ON COLUMN users.updated_at      IS 'Обновлено';

CREATE TRIGGER trg_users_set_updated_at
BEFORE UPDATE ON users
FOR EACH ROW EXECUTE FUNCTION set_updated_at();


-- =====================================================================
CREATE TABLE games (
  id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name                     TEXT NOT NULL,
  description              TEXT,
  start_date               TIMESTAMPTZ NOT NULL,
  end_date                 TIMESTAMPTZ,
  end_message              TEXT,
  max_players              INTEGER CHECK (max_players > 0),
  registration_start_date  TIMESTAMPTZ,
  registration_end_date    TIMESTAMPTZ,
  n_candidates             INTEGER NOT NULL DEFAULT 0 CHECK (n_candidates >= 0),
  visibility               TEXT NOT NULL DEFAULT 'private' CHECK (visibility IN ('public','private','unlisted')),
  created_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT games_dates_ok CHECK (
    (end_date IS NULL OR end_date > start_date)
    AND (registration_start_date IS NULL OR registration_end_date IS NULL OR registration_end_date > registration_start_date)
    AND (registration_end_date IS NULL OR start_date >= registration_end_date)
  )
);

COMMENT ON TABLE games IS 'Игры';
COMMENT ON COLUMN games.id                        IS 'ID';
COMMENT ON COLUMN games.name                      IS 'Название';
COMMENT ON COLUMN games.description               IS 'Описание';
COMMENT ON COLUMN games.start_date                IS 'Старт';
COMMENT ON COLUMN games.end_date                  IS 'Окончание';
COMMENT ON COLUMN games.end_message               IS 'Финальное сообщение';
COMMENT ON COLUMN games.max_players               IS 'Лимит игроков';
COMMENT ON COLUMN games.registration_start_date   IS 'Старт регистрации';
COMMENT ON COLUMN games.registration_end_date     IS 'Конец регистрации';
COMMENT ON COLUMN games.n_candidates              IS 'Число кандидатов';
COMMENT ON COLUMN games.visibility                IS 'Видимость: public/private/unlisted';
COMMENT ON COLUMN games.created_at                IS 'Создано';
COMMENT ON COLUMN games.updated_at                IS 'Обновлено';

CREATE TRIGGER trg_games_set_updated_at
BEFORE UPDATE ON games
FOR EACH ROW EXECUTE FUNCTION set_updated_at();


-- =====================================================================
CREATE TABLE players (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id        UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  game_id        UUID NOT NULL REFERENCES games(id) ON DELETE CASCADE,
  player_rating  INTEGER NOT NULL DEFAULT 0 CHECK (player_rating >= 0),
  player_victim  UUID REFERENCES players(id) DEFERRABLE INITIALLY DEFERRED,
  player_killer  UUID REFERENCES players(id) DEFERRABLE INITIALLY DEFERRED,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_players_user_game UNIQUE (user_id, game_id),
  CONSTRAINT players_self_links_ok CHECK (
    (player_victim IS NULL OR player_victim <> id)
    AND (player_killer IS NULL OR player_killer <> id)
  )
);

COMMENT ON TABLE players IS 'Игроки в игре';
COMMENT ON COLUMN players.id             IS 'ID';
COMMENT ON COLUMN players.user_id        IS 'Пользователь';
COMMENT ON COLUMN players.game_id        IS 'Игра';
COMMENT ON COLUMN players.player_rating  IS 'Рейтинг в игре';
COMMENT ON COLUMN players.player_victim  IS 'Текущая жертва';
COMMENT ON COLUMN players.player_killer  IS 'Текущий охотник';
COMMENT ON COLUMN players.created_at     IS 'Создано';
COMMENT ON COLUMN players.updated_at     IS 'Обновлено';

CREATE TRIGGER trg_players_set_updated_at
BEFORE UPDATE ON players
FOR EACH ROW EXECUTE FUNCTION set_updated_at();


-- =====================================================================
CREATE TABLE chats (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  chat_id    BIGINT NOT NULL,
  name       TEXT,
  slug       TEXT,
  type       TEXT,
  thread     INTEGER,
  purpose    TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_chats_chatid_thread UNIQUE (chat_id, thread)
);

COMMENT ON TABLE chats IS 'Админ-чаты Telegram';
COMMENT ON COLUMN chats.id         IS 'ID';
COMMENT ON COLUMN chats.chat_id    IS 'ID чата Telegram';
COMMENT ON COLUMN chats.name       IS 'Название';
COMMENT ON COLUMN chats.slug       IS 'Slug';
COMMENT ON COLUMN chats.type       IS 'Тип (supergroup/channel)';
COMMENT ON COLUMN chats.thread     IS 'ID темы';
COMMENT ON COLUMN chats.purpose    IS 'Назначение';
COMMENT ON COLUMN chats.created_at IS 'Создано';
COMMENT ON COLUMN chats.updated_at IS 'Обновлено';

CREATE TRIGGER trg_chats_set_updated_at
BEFORE UPDATE ON chats
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- =====================================================================
CREATE TABLE kill_events (
  id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  game_id              UUID NOT NULL REFERENCES games(id)  ON DELETE CASCADE,
  killer_user_id       UUID NOT NULL REFERENCES users(id)  ON DELETE RESTRICT,
  victim_user_id       UUID NOT NULL REFERENCES users(id)  ON DELETE RESTRICT,
  occurred_at          TIMESTAMPTZ NOT NULL,
  killer_confirmed     BOOLEAN NOT NULL DEFAULT FALSE,
  killer_confirmed_at  TIMESTAMPTZ,
  victim_confirmed     BOOLEAN NOT NULL DEFAULT FALSE,
  victim_confirmed_at  TIMESTAMPTZ,
  status               TEXT NOT NULL DEFAULT 'pending'
                         CHECK (status IN ('pending','confirmed','rejected','canceled')),
  moderator_id         UUID REFERENCES users(id) ON DELETE SET NULL,
  moderated_at         TIMESTAMPTZ,
  is_approved          BOOLEAN NOT NULL DEFAULT FALSE,
  created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT killer_ne_victim CHECK (killer_user_id <> victim_user_id)
);

COMMENT ON TABLE kill_events IS 'События «киллов»';
COMMENT ON COLUMN kill_events.id                   IS 'ID';
COMMENT ON COLUMN kill_events.game_id              IS 'Игра';
COMMENT ON COLUMN kill_events.killer_user_id       IS 'Киллер';
COMMENT ON COLUMN kill_events.victim_user_id       IS 'Жертва';
COMMENT ON COLUMN kill_events.occurred_at          IS 'Время события';
COMMENT ON COLUMN kill_events.killer_confirmed     IS 'Подтвердил киллер';
COMMENT ON COLUMN kill_events.killer_confirmed_at  IS 'Когда подтвердил киллер';
COMMENT ON COLUMN kill_events.victim_confirmed     IS 'Подтвердила жертва';
COMMENT ON COLUMN kill_events.victim_confirmed_at  IS 'Когда подтвердила жертва';
COMMENT ON COLUMN kill_events.status               IS 'Статус';
COMMENT ON COLUMN kill_events.moderator_id         IS 'Модератор';
COMMENT ON COLUMN kill_events.moderated_at         IS 'Когда промодерировано';
COMMENT ON COLUMN kill_events.is_approved          IS 'Одобрено модератором';
COMMENT ON COLUMN kill_events.created_at           IS 'Создано';
COMMENT ON COLUMN kill_events.updated_at           IS 'Обновлено';

CREATE TRIGGER trg_kill_events_set_updated_at
BEFORE UPDATE ON kill_events
FOR EACH ROW EXECUTE FUNCTION set_updated_at();


-- =====================================================================
CREATE TABLE message_templates (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  key        TEXT NOT NULL UNIQUE,
  text       TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE message_templates IS 'Шаблоны сообщений';
COMMENT ON COLUMN message_templates.id         IS 'ID';
COMMENT ON COLUMN message_templates.key        IS 'Ключ';
COMMENT ON COLUMN message_templates.text       IS 'Текст';
COMMENT ON COLUMN message_templates.created_at IS 'Создано';
COMMENT ON COLUMN message_templates.updated_at IS 'Обновлено';

CREATE TRIGGER trg_message_templates_set_updated_at
BEFORE UPDATE ON message_templates
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

COMMIT;
