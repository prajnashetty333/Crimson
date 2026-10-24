-- OvaCare Community Module Rollback Script for MySQL / SQLite
-- Drops community module tables and indexes

DROP TABLE IF EXISTS community_user_restrictions;
DROP TABLE IF EXISTS community_moderation_logs;
DROP TABLE IF EXISTS community_blocks;
DROP TABLE IF EXISTS community_reports;
DROP TABLE IF EXISTS community_reactions;
DROP TABLE IF EXISTS community_comments;
DROP TABLE IF EXISTS community_posts;
DROP TABLE IF EXISTS community_categories;
DROP TABLE IF EXISTS community_profiles;
