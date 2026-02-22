-- Issue #46: Per-profile categories and mood preferences
-- Run these in order against your database.

-- 1. Add profile_id to categories (default '' for existing rows, then update manually if needed)
ALTER TABLE categories
    ADD COLUMN profile_id VARCHAR(100) NOT NULL DEFAULT '' AFTER id;

-- 2. If you have existing categories and want to assign them to your first profile,
--    replace 'Player 1' with your actual first PROFILES value from .env:
-- UPDATE categories SET profile_id = 'Player 1' WHERE profile_id = '';

-- 3. Add profile_id to mood_preferences
ALTER TABLE mood_preferences
    ADD COLUMN profile_id VARCHAR(100) NOT NULL DEFAULT '' AFTER id;

-- 4. If you have an existing mood_preferences row (the old singleton), assign it:
-- UPDATE mood_preferences SET profile_id = 'Player 1' WHERE profile_id = '';

-- 5. Add unique constraint on mood_preferences.profile_id
ALTER TABLE mood_preferences
    ADD UNIQUE KEY uq_mood_prefs_profile (profile_id);
