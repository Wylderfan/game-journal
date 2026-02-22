-- Issue #47: Per-profile check-ins
-- Replaces checkins.game_id (FK → games) with profile_game_id (FK → profile_games).
--
-- NOTE: This drops all existing check-in rows because the old game_id values
-- cannot be automatically mapped to a specific profile_game_id.
-- If you have check-in data you want to keep, do a manual export first.

-- 1. Drop the old FK constraint
ALTER TABLE checkins DROP FOREIGN KEY checkins_ibfk_1;

-- 2. Rename the column
ALTER TABLE checkins CHANGE game_id profile_game_id INT NOT NULL;

-- 3. Add the new FK to profile_games
ALTER TABLE checkins
    ADD CONSTRAINT fk_checkins_profile_game
    FOREIGN KEY (profile_game_id) REFERENCES profile_games(id) ON DELETE CASCADE;
