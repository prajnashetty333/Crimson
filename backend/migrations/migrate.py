import os
import sys
import argparse
from sqlalchemy import (
    MetaData, Table, Column, String, Integer, Text, Boolean, 
    TIMESTAMP, ForeignKey, text, inspect
)

# Ensure backend directory is in path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from db import engine, execute_query, execute_write

metadata = MetaData()

# Stub for existing users table so foreign keys resolve in SQLAlchemy
users_table = Table(
    'users', metadata,
    Column('user_id', String(50), primary_key=True)
)

# Define tables
community_profiles = Table(
    'community_profiles', metadata,
    Column('profile_id', String(50), primary_key=True),
    Column('user_id', String(50), ForeignKey('users.user_id', ondelete='CASCADE'), unique=True, nullable=False),
    Column('display_name', String(100), nullable=False),
    Column('avatar_key', String(50), default='avatar_lavender', nullable=False),
    Column('bio', String(300), default=''),
    Column('created_at', TIMESTAMP, server_default=text('CURRENT_TIMESTAMP')),
    Column('updated_at', TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
)

community_categories = Table(
    'community_categories', metadata,
    Column('category_id', String(50), primary_key=True),
    Column('name', String(100), unique=True, nullable=False),
    Column('slug', String(100), unique=True, nullable=False),
    Column('description', String(255)),
    Column('icon', String(50), default='Sparkles'),
    Column('display_order', Integer, default=0),
    Column('created_at', TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
)

community_posts = Table(
    'community_posts', metadata,
    Column('post_id', String(50), primary_key=True),
    Column('user_id', String(50), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False),
    Column('category_id', String(50), ForeignKey('community_categories.category_id', ondelete='RESTRICT'), nullable=False),
    Column('title', String(255), nullable=False),
    Column('body', Text, nullable=False),
    Column('is_anonymous', Boolean, default=False),
    Column('health_label', String(50), default='Personal Experience', nullable=False),
    Column('is_verified', Boolean, default=False),
    Column('verified_by', String(50), ForeignKey('users.user_id', ondelete='SET NULL'), nullable=True),
    Column('verified_at', TIMESTAMP, nullable=True),
    Column('verification_source_url', String(500), nullable=True),
    Column('verification_notes', Text, nullable=True),
    Column('status', String(20), default='active'),
    Column('is_locked', Boolean, default=False),
    Column('view_count', Integer, default=0),
    Column('created_at', TIMESTAMP, server_default=text('CURRENT_TIMESTAMP')),
    Column('updated_at', TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
)

community_comments = Table(
    'community_comments', metadata,
    Column('comment_id', String(50), primary_key=True),
    Column('post_id', String(50), ForeignKey('community_posts.post_id', ondelete='CASCADE'), nullable=False),
    Column('user_id', String(50), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False),
    Column('parent_comment_id', String(50), ForeignKey('community_comments.comment_id', ondelete='CASCADE'), nullable=True),
    Column('body', Text, nullable=False),
    Column('is_anonymous', Boolean, default=False),
    Column('status', String(20), default='active'),
    Column('created_at', TIMESTAMP, server_default=text('CURRENT_TIMESTAMP')),
    Column('updated_at', TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
)

community_reactions = Table(
    'community_reactions', metadata,
    Column('reaction_id', String(50), primary_key=True),
    Column('post_id', String(50), ForeignKey('community_posts.post_id', ondelete='CASCADE'), nullable=False),
    Column('user_id', String(50), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False),
    Column('reaction_type', String(20), nullable=False),
    Column('created_at', TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
)

community_reports = Table(
    'community_reports', metadata,
    Column('report_id', String(50), primary_key=True),
    Column('reporter_user_id', String(50), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False),
    Column('content_type', String(20), nullable=False),
    Column('content_id', String(50), nullable=False),
    Column('reason', String(100), nullable=False),
    Column('explanation', Text),
    Column('status', String(20), default='pending'),
    Column('reviewed_by', String(50), ForeignKey('users.user_id', ondelete='SET NULL'), nullable=True),
    Column('reviewed_at', TIMESTAMP, nullable=True),
    Column('resolution_notes', Text, nullable=True),
    Column('created_at', TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
)

community_blocks = Table(
    'community_blocks', metadata,
    Column('block_id', String(50), primary_key=True),
    Column('blocker_user_id', String(50), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False),
    Column('blocked_user_id', String(50), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False),
    Column('created_at', TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
)

community_moderation_logs = Table(
    'community_moderation_logs', metadata,
    Column('log_id', String(50), primary_key=True),
    Column('moderator_user_id', String(50), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False),
    Column('action', String(50), nullable=False),
    Column('target_type', String(30), nullable=False),
    Column('target_id', String(50), nullable=False),
    Column('reason', Text, nullable=False),
    Column('details', Text, nullable=True),
    Column('created_at', TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
)

community_user_restrictions = Table(
    'community_user_restrictions', metadata,
    Column('restriction_id', String(50), primary_key=True),
    Column('user_id', String(50), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False),
    Column('restricted_by', String(50), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False),
    Column('restriction_type', String(30), nullable=False),
    Column('expires_at', TIMESTAMP, nullable=True),
    Column('reason', Text, nullable=False),
    Column('is_active', Boolean, default=True),
    Column('created_at', TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
)

CHANNELS_SEED = [
    {
        "category_id": "cat_pcos_symptoms",
        "name": "PCOS and Symptoms",
        "slug": "pcos-symptoms",
        "description": "Discuss symptoms, hormonal fluctuations, cycle tracking, and lived experiences.",
        "icon": "Heart",
        "display_order": 1
    },
    {
        "category_id": "cat_nutrition_lifestyle",
        "name": "Nutrition and Lifestyle",
        "slug": "nutrition-lifestyle",
        "description": "Anti-inflammatory diets, balanced meals, supplements, and lifestyle habits.",
        "icon": "Apple",
        "display_order": 2
    },
    {
        "category_id": "cat_mental_wellbeing",
        "name": "Mental Well-being",
        "slug": "mental-wellbeing",
        "description": "A compassionate safe haven for mood support, anxiety, and emotional wellness.",
        "icon": "Smile",
        "display_order": 3
    },
    {
        "category_id": "cat_exercise_sleep",
        "name": "Exercise, Sleep and Energy",
        "slug": "exercise-sleep-energy",
        "description": "Low-impact workouts, restorative sleep practices, and combating chronic fatigue.",
        "icon": "Moon",
        "display_order": 4
    },
    {
        "category_id": "cat_treatments",
        "name": "Treatment Experiences",
        "slug": "treatment-experiences",
        "description": "Navigating doctor visits, therapies, medications, and holistic care pathways.",
        "icon": "Activity",
        "display_order": 5
    },
    {
        "category_id": "cat_general",
        "name": "General Discussion",
        "slug": "general-discussion",
        "description": "Community check-ins, celebratory milestones, encouragement, and open chats.",
        "icon": "MessageCircle",
        "display_order": 6
    }
]

def apply_migrations():
    print("Applying Community Module migrations...")
    inspector = inspect(engine)
    
    # 1. Update users table if role or community restriction columns are missing
    user_columns = [c['name'] for c in inspector.get_columns('users')]
    with engine.begin() as conn:
        if 'role' not in user_columns:
            print("Adding 'role' column to users table...")
            conn.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'member'"))
        if 'is_community_banned' not in user_columns:
            print("Adding 'is_community_banned' column to users table...")
            conn.execute(text("ALTER TABLE users ADD COLUMN is_community_banned BOOLEAN DEFAULT 0"))
    
    # 2. Create community tables
    metadata.create_all(engine)
    print("Community tables created successfully.")
    
    # 3. Seed Topic Channels
    existing_cats = {row['category_id'] for row in execute_query("SELECT category_id FROM community_categories")}
    for cat in CHANNELS_SEED:
        if cat['category_id'] not in existing_cats:
            print(f"Seeding channel: {cat['name']}...")
            execute_write(
                """
                INSERT INTO community_categories (category_id, name, slug, description, icon, display_order)
                VALUES (:category_id, :name, :slug, :description, :icon, :display_order)
                """,
                cat
            )
            
    # 4. Initialize default community profiles for existing users who do not have one
    existing_users = execute_query("SELECT user_id, username FROM users")
    existing_profiles = {p['user_id'] for p in execute_query("SELECT user_id FROM community_profiles")}
    
    avatars = ['avatar_lavender', 'avatar_blush', 'avatar_lotus', 'avatar_sage', 'avatar_rose', 'avatar_sun']
    profiles_to_create = []
    import uuid, random
    for u in existing_users:
        if u['user_id'] not in existing_profiles:
            # Generate safe pseudonymous display name from username (e.g., 'Ananya' -> 'Ananya_P' or 'Member_4821')
            base_name = u['username'].split()[0] if u.get('username') else 'Member'
            clean_name = ''.join(c for c in base_name if c.isalnum()) or 'Member'
            pseudonym = f"{clean_name}_{uuid.uuid4().hex[:4]}"
            avatar = random.choice(avatars)
            profiles_to_create.append({
                "profile_id": f"prof_{uuid.uuid4().hex[:12]}",
                "user_id": u['user_id'],
                "display_name": pseudonym,
                "avatar_key": avatar,
                "bio": "Fellow warrior on the wellness journey ✨"
            })
            
    if profiles_to_create:
        print(f"Creating pseudonymous profiles for {len(profiles_to_create)} existing users...")
        for p in profiles_to_create:
            execute_write(
                """
                INSERT INTO community_profiles (profile_id, user_id, display_name, avatar_key, bio)
                VALUES (:profile_id, :user_id, :display_name, :avatar_key, :bio)
                """,
                p
            )
            
    # 5. Ensure demo user has moderator role for test demonstration purposes
    execute_write(
        "UPDATE users SET role = 'moderator' WHERE email = 'demo@ovacare.app'"
    )
    print("Demo account (demo@ovacare.app) assigned 'moderator' role for testing.")
    print("Migration completed successfully!")

def rollback_migrations():
    print("Rolling back Community Module tables...")
    metadata.drop_all(engine)
    print("Rollback completed successfully.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Run or rollback Community Module migrations.")
    parser.add_argument("--rollback", action="store_true", help="Drop all community tables.")
    args = parser.parse_args()
    
    if args.rollback:
        rollback_migrations()
    else:
        apply_migrations()
