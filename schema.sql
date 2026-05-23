CREATE TABLE IF NOT EXISTS user_entries (
    id           SERIAL PRIMARY KEY,
    user_id      BIGINT NOT NULL,
    entry_date   DATE NOT NULL DEFAULT CURRENT_DATE,
    mood         INTEGER NOT NULL CHECK (mood BETWEEN 1 AND 5),
    work_hours   NUMERIC(4,2) NOT NULL CHECK (work_hours >= 0 AND work_hours <= 24),
    sleep_hours  NUMERIC(4,2) NOT NULL CHECK (sleep_hours >= 0 AND sleep_hours <= 24),
    comment      TEXT,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_user_entry_date UNIQUE (user_id, entry_date)
);

CREATE INDEX IF NOT EXISTS idx_user_entries_user_date
    ON user_entries (user_id, entry_date DESC);

CREATE INDEX IF NOT EXISTS idx_user_entries_mood
    ON user_entries (mood);

CREATE INDEX IF NOT EXISTS idx_user_entries_date_only
    ON user_entries (entry_date);