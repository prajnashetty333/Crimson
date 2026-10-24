-- OvaCare Community Module Migration for MySQL
-- Reversible DDL definitions

CREATE TABLE IF NOT EXISTS community_profiles (
    profile_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    avatar_key VARCHAR(50) NOT NULL DEFAULT 'avatar_lavender',
    bio VARCHAR(300) DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS community_categories (
    category_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    description VARCHAR(255),
    icon VARCHAR(50) DEFAULT 'Sparkles',
    display_order INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS community_posts (
    post_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    category_id VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    body TEXT NOT NULL,
    is_anonymous BOOLEAN DEFAULT FALSE,
    health_label VARCHAR(50) NOT NULL DEFAULT 'Personal Experience',
    is_verified BOOLEAN DEFAULT FALSE,
    verified_by VARCHAR(50) NULL,
    verified_at TIMESTAMP NULL,
    verification_source_url VARCHAR(500) NULL,
    verification_notes TEXT NULL,
    status VARCHAR(20) DEFAULT 'active',
    is_locked BOOLEAN DEFAULT FALSE,
    view_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES community_categories(category_id) ON DELETE RESTRICT,
    FOREIGN KEY (verified_by) REFERENCES users(user_id) ON DELETE SET NULL
);

CREATE INDEX idx_comm_posts_cat_created ON community_posts(category_id, created_at DESC);
CREATE INDEX idx_comm_posts_status_created ON community_posts(status, created_at DESC);
CREATE INDEX idx_comm_posts_user ON community_posts(user_id);

CREATE TABLE IF NOT EXISTS community_comments (
    comment_id VARCHAR(50) PRIMARY KEY,
    post_id VARCHAR(50) NOT NULL,
    user_id VARCHAR(50) NOT NULL,
    parent_comment_id VARCHAR(50) NULL,
    body TEXT NOT NULL,
    is_anonymous BOOLEAN DEFAULT FALSE,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (post_id) REFERENCES community_posts(post_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (parent_comment_id) REFERENCES community_comments(comment_id) ON DELETE CASCADE
);

CREATE INDEX idx_comm_comments_post ON community_comments(post_id, created_at ASC);
CREATE INDEX idx_comm_comments_parent ON community_comments(parent_comment_id);

CREATE TABLE IF NOT EXISTS community_reactions (
    reaction_id VARCHAR(50) PRIMARY KEY,
    post_id VARCHAR(50) NOT NULL,
    user_id VARCHAR(50) NOT NULL,
    reaction_type VARCHAR(20) NOT NULL, -- 'helpful', 'support', 'relatable'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (post_id) REFERENCES community_posts(post_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    UNIQUE KEY uniq_post_user_reaction (post_id, user_id, reaction_type)
);

CREATE TABLE IF NOT EXISTS community_reports (
    report_id VARCHAR(50) PRIMARY KEY,
    reporter_user_id VARCHAR(50) NOT NULL,
    content_type VARCHAR(20) NOT NULL, -- 'post', 'comment'
    content_id VARCHAR(50) NOT NULL,
    reason VARCHAR(100) NOT NULL,
    explanation TEXT,
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'reviewed', 'resolved', 'dismissed'
    reviewed_by VARCHAR(50) NULL,
    reviewed_at TIMESTAMP NULL,
    resolution_notes TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (reporter_user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (reviewed_by) REFERENCES users(user_id) ON DELETE SET NULL,
    UNIQUE KEY uniq_reporter_content (reporter_user_id, content_type, content_id)
);

CREATE INDEX idx_comm_reports_status ON community_reports(status, created_at DESC);

CREATE TABLE IF NOT EXISTS community_blocks (
    block_id VARCHAR(50) PRIMARY KEY,
    blocker_user_id VARCHAR(50) NOT NULL,
    blocked_user_id VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (blocker_user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (blocked_user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    UNIQUE KEY uniq_blocker_blocked (blocker_user_id, blocked_user_id)
);

CREATE TABLE IF NOT EXISTS community_moderation_logs (
    log_id VARCHAR(50) PRIMARY KEY,
    moderator_user_id VARCHAR(50) NOT NULL,
    action VARCHAR(50) NOT NULL,
    target_type VARCHAR(30) NOT NULL, -- 'post', 'comment', 'user', 'report'
    target_id VARCHAR(50) NOT NULL,
    reason TEXT NOT NULL,
    details TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (moderator_user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE INDEX idx_comm_mod_logs_date ON community_moderation_logs(created_at DESC);

CREATE TABLE IF NOT EXISTS community_user_restrictions (
    restriction_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    restricted_by VARCHAR(50) NOT NULL,
    restriction_type VARCHAR(30) NOT NULL, -- 'mute_posting', 'temporary_ban', 'permanent_ban'
    expires_at TIMESTAMP NULL,
    reason TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (restricted_by) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE INDEX idx_comm_restrictions_active ON community_user_restrictions(user_id, is_active);
