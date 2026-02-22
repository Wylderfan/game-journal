-- Issue #46: Per-profile categories and mood preferences
-- Run these in order against your database.
-- Replace 'Player 1' with your actual first PROFILES value from .env if different.

-- 1. Add profile_id to categories (default '' so existing rows get '')
ALTER TABLE categories
    ADD COLUMN profile_id VARCHAR(100) NOT NULL DEFAULT '' AFTER id;

-- 2. Assign existing categories to the first profile
UPDATE categories SET profile_id = 'Player 1' WHERE profile_id = '';

-- 3. Add profile_id to mood_preferences
ALTER TABLE mood_preferences
    ADD COLUMN profile_id VARCHAR(100) NOT NULL DEFAULT '' AFTER id;

-- 4. Assign existing mood_preferences row to the first profile
UPDATE mood_preferences SET profile_id = 'Player 1' WHERE profile_id = '';

-- 5. Fix mood_preferences.id: the old singleton used DEFAULT 1 with no AUTO_INCREMENT.
--    Change it to proper AUTO_INCREMENT so new per-profile rows can be inserted.
ALTER TABLE mood_preferences
    MODIFY COLUMN id INT NOT NULL AUTO_INCREMENT;

-- 6. Add unique constraint on mood_preferences.profile_id
ALTER TABLE mood_preferences
    ADD UNIQUE KEY uq_mood_prefs_profile (profile_id);
