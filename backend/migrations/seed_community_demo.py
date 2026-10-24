import os
import sys
import uuid
from datetime import datetime, timedelta

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from db import execute_query, execute_write

def seed_demo_posts():
    users = execute_query("SELECT user_id, username FROM users LIMIT 10")
    if not users:
        print("No users found to seed posts.")
        return
        
    demo_user = execute_query("SELECT user_id FROM users WHERE email = 'demo@ovacare.app'")
    demo_uid = demo_user[0]["user_id"] if demo_user else users[0]["user_id"]
    
    posts_data = [
        {
            "post_id": "post_seed_001",
            "user_id": users[1]["user_id"] if len(users) > 1 else demo_uid,
            "category_id": "cat_nutrition_lifestyle",
            "title": "My Favorite Anti-Inflammatory Morning Smoothie for Insulin Sensitivity",
            "body": "Hi everyone! After months of trial and error with fasting glucose spikes, I wanted to share my go-to morning breakfast. It has ground flaxseeds, baby spinach, unsweetened almond milk, half a green apple, chia seeds, and clean pea protein. It keeps my energy steady until lunchtime without that post-breakfast slump. What are your favorite breakfast staples that don't trigger crashes?",
            "is_anonymous": 0,
            "health_label": "Personal Experience",
            "is_verified": 0,
            "verified_by": None,
            "verification_source_url": None,
            "verification_notes": None
        },
        {
            "post_id": "post_seed_002",
            "user_id": demo_uid,
            "category_id": "cat_treatments",
            "title": "Clinical Summary: Understanding Myo-Inositol & D-Chiro Inositol in a 40:1 Ratio",
            "body": "For members inquiring about inositol supplementation for ovulatory function and metabolic markers in PCOS:\n\nResearch indicates that the physiological ratio found in human plasma is approximately 40:1 (Myo-Inositol to D-Chiro Inositol). When supplementing, excessive D-Chiro inositol alone can sometimes paradoxically impair oocyte quality, whereas the 40:1 combination has demonstrated significant clinical benefits for restoring spontaneous ovulation and insulin sensitivity.\n\nAlways review supplement dosages with your endocrinologist or gynecologist before starting any new regimen.",
            "is_anonymous": 0,
            "health_label": "Verified Health Resource",
            "is_verified": 1,
            "verified_by": demo_uid,
            "verification_source_url": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5655679/",
            "verification_notes": "Reviewed against peer-reviewed clinical trials on inositol stereoisomers in PCOS management (European Review for Medical and Pharmacological Sciences)."
        },
        {
            "post_id": "post_seed_003",
            "user_id": users[2]["user_id"] if len(users) > 2 else demo_uid,
            "category_id": "cat_mental_wellbeing",
            "title": "Managing cycle anxiety and feeling out of sync with my body",
            "body": "Some days it feels like a marathon just managing the emotional weight of unpredictable cycles and acne flare-ups. I've started doing 10 minutes of gentle yoga and breathwork before bed, which has helped quiet the racing thoughts. Sending love to anyone else having a tough mental health week — remember you are not defined by your symptoms.",
            "is_anonymous": 1,
            "health_label": "Personal Experience",
            "is_verified": 0,
            "verified_by": None,
            "verification_source_url": None,
            "verification_notes": None
        },
        {
            "post_id": "post_seed_004",
            "user_id": users[3]["user_id"] if len(users) > 3 else demo_uid,
            "category_id": "cat_pcos_symptoms",
            "title": "Preparing for your first ultrasound or hormone panel: Key questions to ask",
            "body": "When I first suspected PCOS, I walked into the clinic completely unprepared and overwhelmed. If you're scheduling your initial diagnostic tests, here are three things that made a big difference:\n1. Ask for fasting insulin, not just fasting glucose.\n2. Inquire about Day 3 LH/FSH and total vs free testosterone.\n3. Keep a 3-month symptom journal of your cycle lengths and spotting.\n\nWhat other questions did you find most helpful during your diagnosis?",
            "is_anonymous": 0,
            "health_label": "General Discussion",
            "is_verified": 0,
            "verified_by": None,
            "verification_source_url": None,
            "verification_notes": None
        }
    ]
    
    for p in posts_data:
        existing = execute_query("SELECT post_id FROM community_posts WHERE post_id = :pid", {"pid": p["post_id"]})
        if not existing:
            execute_write(
                """
                INSERT INTO community_posts (
                    post_id, user_id, category_id, title, body, is_anonymous, health_label, 
                    is_verified, verified_by, verified_at, verification_source_url, verification_notes,
                    status, is_locked, created_at, updated_at
                ) VALUES (
                    :post_id, :user_id, :category_id, :title, :body, :is_anonymous, :health_label,
                    :is_verified, :verified_by, CASE WHEN :is_verified = 1 THEN CURRENT_TIMESTAMP ELSE NULL END,
                    :verification_source_url, :verification_notes, 'active', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                )
                """,
                p
            )
            print(f"Seeded post: {p['title'][:40]}...")
            
    # Seed comments for post_seed_001
    comments_data = [
        {
            "comment_id": "cmt_seed_001",
            "post_id": "post_seed_001",
            "user_id": users[4]["user_id"] if len(users) > 4 else demo_uid,
            "parent_comment_id": None,
            "body": "Adding ground cinnamon also helps regulate blood glucose response! I love adding a pinch to my flax smoothies.",
            "is_anonymous": 0
        },
        {
            "comment_id": "cmt_seed_002",
            "post_id": "post_seed_001",
            "user_id": users[1]["user_id"] if len(users) > 1 else demo_uid,
            "parent_comment_id": "cmt_seed_001",
            "body": "Yes! Ceylon cinnamon has been wonderful for me too. Great tip!",
            "is_anonymous": 0
        }
    ]
    for c in comments_data:
        existing = execute_query("SELECT comment_id FROM community_comments WHERE comment_id = :cid", {"cid": c["comment_id"]})
        if not existing:
            execute_write(
                """
                INSERT INTO community_comments (
                    comment_id, post_id, user_id, parent_comment_id, body, is_anonymous, status, created_at, updated_at
                ) VALUES (
                    :comment_id, :post_id, :user_id, :parent_comment_id, :body, :is_anonymous, 'active', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                )
                """,
                c
            )
            
    # Seed supportive reactions
    reactions = [
        {"post_id": "post_seed_001", "user_id": demo_uid, "rx": "helpful"},
        {"post_id": "post_seed_001", "user_id": users[2]["user_id"] if len(users) > 2 else demo_uid, "rx": "support"},
        {"post_id": "post_seed_002", "user_id": users[1]["user_id"] if len(users) > 1 else demo_uid, "rx": "helpful"},
        {"post_id": "post_seed_002", "user_id": users[3]["user_id"] if len(users) > 3 else demo_uid, "rx": "relatable"},
        {"post_id": "post_seed_003", "user_id": demo_uid, "rx": "support"},
        {"post_id": "post_seed_003", "user_id": users[1]["user_id"] if len(users) > 1 else demo_uid, "rx": "relatable"}
    ]
    for r in reactions:
        rx_id = f"rx_{uuid.uuid4().hex[:12]}"
        existing = execute_query(
            "SELECT reaction_id FROM community_reactions WHERE post_id = :pid AND user_id = :uid AND reaction_type = :rx",
            {"pid": r["post_id"], "uid": r["user_id"], "rx": r["rx"]}
        )
        if not existing:
            execute_write(
                "INSERT INTO community_reactions (reaction_id, post_id, user_id, reaction_type) VALUES (:rid, :pid, :uid, :rx)",
                {"rid": rx_id, "pid": r["post_id"], "uid": r["user_id"], "rx": r["rx"]}
            )
            
    print("Seed community posts, comments, and reactions completed.")

if __name__ == '__main__':
    seed_demo_posts()
