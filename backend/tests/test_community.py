import os
import sys
import unittest
import json
from unittest.mock import patch

# Ensure backend directory is in path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app import app, generate_auth_token
from db import execute_query, execute_write, init_test_database

class TestCommunityModule(unittest.TestCase):
    """
    Comprehensive test suite for OvaCare 2.0 Community Module.
    Tests authorization, ownership, health verification, reactions,
    reporting, blocking, and moderator controls.
    """

    @classmethod
    def setUpClass(cls):
        init_test_database()
        app.config['TESTING'] = True
        cls.client = app.test_client()

        # Seed two distinct test users and one moderator
        cls.user_a_id = "usr_test_comm_alice"
        cls.user_b_id = "usr_test_comm_bob"
        cls.mod_id = "usr_test_comm_mod"

        execute_write(
            "INSERT OR IGNORE INTO users (user_id, username, email, password, age, lifestyle, has_pcos, role) "
            "VALUES (:uid, 'Alice Test', 'alice@commtest.app', 'hash123', 24, 'Active', 1, 'member')",
            {"uid": cls.user_a_id}
        )
        execute_write(
            "INSERT OR IGNORE INTO users (user_id, username, email, password, age, lifestyle, has_pcos, role) "
            "VALUES (:uid, 'Bob Test', 'bob@commtest.app', 'hash123', 29, 'Moderate', 0, 'member')",
            {"uid": cls.user_b_id}
        )
        execute_write(
            "INSERT OR IGNORE INTO users (user_id, username, email, password, age, lifestyle, has_pcos, role) "
            "VALUES (:uid, 'Moderator Test', 'mod@commtest.app', 'hash123', 35, 'Active', 0, 'moderator')",
            {"uid": cls.mod_id}
        )

        cls.token_a = generate_auth_token(cls.user_a_id)
        cls.token_b = generate_auth_token(cls.user_b_id)
        cls.token_mod = generate_auth_token(cls.mod_id)

    # ------------------------------------------------------------------
    # 1. Channels & Pseudonymous Profile
    # ------------------------------------------------------------------

    def test_list_categories_returns_channels(self):
        """Public channels endpoint must return active topic channels."""
        res = self.client.get('/api/community/categories')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("categories", data)
        self.assertGreaterEqual(len(data["categories"]), 6)
        slugs = [c["slug"] for c in data["categories"]]
        self.assertIn("pcos-symptoms", slugs)
        self.assertIn("nutrition-lifestyle", slugs)
        self.assertIn("mental-wellbeing", slugs)

    def test_create_custom_community(self):
        """Authenticated member can create a new community circle / topic channel."""
        execute_write("DELETE FROM community_categories WHERE slug = 'fertility-and-conception-support'")
        res = self.client.post(
            '/api/community/categories',
            headers={"Authorization": f"Bearer {self.token_a}"},
            json={
                "name": "Fertility and Conception Support",
                "description": "Safe haven for discussing ovulation, timing, and fertility journeys.",
                "icon": "Heart"
            }
        )
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertIn("category", data)
        self.assertEqual(data["category"]["name"], "Fertility and Conception Support")
        self.assertEqual(data["category"]["slug"], "fertility-and-conception-support")

    def test_get_and_update_profile(self):
        """Authenticated member can configure pseudonymous profile without exposing private data."""
        # Get profile
        res = self.client.get('/api/community/profile', headers={"Authorization": f"Bearer {self.token_a}"})
        self.assertEqual(res.status_code, 200)
        profile = res.get_json()["profile"]
        self.assertNotIn("email", profile)
        self.assertNotIn("password", profile)

        # Update profile
        update_res = self.client.put(
            '/api/community/profile',
            headers={"Authorization": f"Bearer {self.token_a}"},
            json={
                "display_name": "Alice_Warrior",
                "avatar_key": "avatar_lotus",
                "bio": "Holistic hormone healing journey 🌸"
            }
        )
        self.assertEqual(update_res.status_code, 200)
        updated = update_res.get_json()["profile"]
        self.assertEqual(updated["display_name"], "Alice_Warrior")
        self.assertEqual(updated["avatar_key"], "avatar_lotus")

    def test_update_profile_reserved_name_rejected(self):
        """Reserved names such as 'admin' or 'moderator' must be rejected."""
        res = self.client.put(
            '/api/community/profile',
            headers={"Authorization": f"Bearer {self.token_a}"},
            json={"display_name": "Admin", "avatar_key": "avatar_lavender"}
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("reserved", res.get_json().get("error", "").lower())

    # ------------------------------------------------------------------
    # 2. Post Creation, Ownership & Health Label Rules
    # ------------------------------------------------------------------

    def test_create_and_view_own_post(self):
        """Authenticated user can create a post and retrieve it."""
        res = self.client.post(
            '/api/community/posts',
            headers={"Authorization": f"Bearer {self.token_a}"},
            json={
                "title": "Alice's Journey with Spearmint Tea",
                "body": "I have been drinking two cups of spearmint tea daily for 3 months. My hormonal acne has noticeably calmed down.",
                "category_id": "cat_nutrition_lifestyle",
                "is_anonymous": False,
                "health_label": "Personal Experience"
            }
        )
        self.assertEqual(res.status_code, 201)
        post_id = res.get_json()["post_id"]

        # View post
        view_res = self.client.get(f'/api/community/posts/{post_id}', headers={"Authorization": f"Bearer {self.token_a}"})
        self.assertEqual(view_res.status_code, 200)
        post_data = view_res.get_json()["post"]
        self.assertEqual(post_data["title"], "Alice's Journey with Spearmint Tea")
        self.assertTrue(post_data["is_author"])
        self.assertNotIn("email", post_data["author"])

    def test_regular_user_cannot_self_assign_verified_health_resource(self):
        """A regular member cannot self-assign the 'Verified Health Resource' label."""
        res = self.client.post(
            '/api/community/posts',
            headers={"Authorization": f"Bearer {self.token_a}"},
            json={
                "title": "Unverified Clinical Claim Attempt",
                "body": "Attempting to declare my personal regimen as a clinically verified health resource.",
                "category_id": "cat_treatments",
                "health_label": "Verified Health Resource"
            }
        )
        self.assertEqual(res.status_code, 403)
        self.assertIn("authorized moderator", res.get_json().get("error", ""))

    def test_anonymous_post_conceals_author_identity(self):
        """When a post is anonymous, public responses must conceal the author's display name."""
        res = self.client.post(
            '/api/community/posts',
            headers={"Authorization": f"Bearer {self.token_a}"},
            json={
                "title": "Anonymous Cycle Question",
                "body": "Experiencing mid-cycle spotting for the second consecutive month.",
                "category_id": "cat_pcos_symptoms",
                "is_anonymous": True,
                "health_label": "General Discussion"
            }
        )
        self.assertEqual(res.status_code, 201)
        post_id = res.get_json()["post_id"]

        # Viewed by Bob
        view_res = self.client.get(f'/api/community/posts/{post_id}', headers={"Authorization": f"Bearer {self.token_b}"})
        self.assertEqual(view_res.status_code, 200)
        post_data = view_res.get_json()["post"]
        self.assertEqual(post_data["author"]["display_name"], "Anonymous Member")
        self.assertTrue(post_data["author"]["is_anonymous"])

    def test_user_cannot_edit_or_delete_another_members_post(self):
        """Bob cannot edit or delete Alice's post."""
        # Create Alice's post
        create_res = self.client.post(
            '/api/community/posts',
            headers={"Authorization": f"Bearer {self.token_a}"},
            json={
                "title": "Alice's Private Discussion",
                "body": "A post that belongs strictly to Alice for permissions testing.",
                "category_id": "cat_general",
                "health_label": "Personal Experience"
            }
        )
        post_id = create_res.get_json()["post_id"]

        # Bob attempts edit
        edit_res = self.client.put(
            f'/api/community/posts/{post_id}',
            headers={"Authorization": f"Bearer {self.token_b}"},
            json={"title": "Hacked Title", "body": "Hacked body content", "category_id": "cat_general"}
        )
        self.assertEqual(edit_res.status_code, 403)

        # Bob attempts delete
        del_res = self.client.delete(
            f'/api/community/posts/{post_id}',
            headers={"Authorization": f"Bearer {self.token_b}"}
        )
        self.assertEqual(del_res.status_code, 403)

    # ------------------------------------------------------------------
    # 3. Comments, 1-Level Replies & Supportive Reactions
    # ------------------------------------------------------------------

    def test_comments_and_nested_replies(self):
        """Members can post top-level comments and 1-level nested replies."""
        # Alice creates a post
        p_res = self.client.post(
            '/api/community/posts',
            headers={"Authorization": f"Bearer {self.token_a}"},
            json={
                "title": "Low Glycemic Snacks Discussion",
                "body": "What are your favorite afternoon low GI snacks that prevent glucose spikes?",
                "category_id": "cat_nutrition_lifestyle"
            }
        )
        post_id = p_res.get_json()["post_id"]

        # Bob comments
        c_res = self.client.post(
            f'/api/community/posts/{post_id}/comments',
            headers={"Authorization": f"Bearer {self.token_b}"},
            json={"body": "Greek yogurt with pumpkin seeds and blueberries works wonders for me!"}
        )
        self.assertEqual(c_res.status_code, 201)
        comment_id = c_res.get_json()["comment_id"]

        # Alice replies to Bob's comment
        r_res = self.client.post(
            f'/api/community/posts/{post_id}/comments',
            headers={"Authorization": f"Bearer {self.token_a}"},
            json={
                "body": "Pumpkin seeds are also great for zinc and progesterone support! Love that idea.",
                "parent_comment_id": comment_id
            }
        )
        self.assertEqual(r_res.status_code, 201)

        # Verify list of comments contains nested reply
        list_res = self.client.get(f'/api/community/posts/{post_id}/comments')
        self.assertEqual(list_res.status_code, 200)
        comments = list_res.get_json()["comments"]
        self.assertEqual(len(comments), 1)
        self.assertEqual(len(comments[0]["replies"]), 1)
        self.assertEqual(comments[0]["replies"][0]["parent_comment_id"], comment_id)

    def test_supportive_reactions_no_duplicates(self):
        """Toggling reactions works and prevents duplicate reaction rows."""
        p_res = self.client.post(
            '/api/community/posts',
            headers={"Authorization": f"Bearer {self.token_a}"},
            json={
                "title": "Reactions Test Post",
                "body": "Testing helpful, support, and relatable supportive reactions.",
                "category_id": "cat_general"
            }
        )
        post_id = p_res.get_json()["post_id"]

        # Bob adds 'helpful'
        rx1 = self.client.post(
            f'/api/community/posts/{post_id}/reactions',
            headers={"Authorization": f"Bearer {self.token_b}"},
            json={"reaction_type": "helpful"}
        )
        self.assertEqual(rx1.status_code, 200)
        self.assertEqual(rx1.get_json()["action"], "added")
        self.assertEqual(rx1.get_json()["reactions_breakdown"]["helpful"], 1)

        # Bob toggles 'helpful' off
        rx2 = self.client.post(
            f'/api/community/posts/{post_id}/reactions',
            headers={"Authorization": f"Bearer {self.token_b}"},
            json={"reaction_type": "helpful"}
        )
        self.assertEqual(rx2.status_code, 200)
        self.assertEqual(rx2.get_json()["action"], "removed")
        self.assertEqual(rx2.get_json()["reactions_breakdown"]["helpful"], 0)

    # ------------------------------------------------------------------
    # 4. Reporting & Blocking
    # ------------------------------------------------------------------

    def test_reporting_content(self):
        """Members can report inappropriate content with a valid reason."""
        p_res = self.client.post(
            '/api/community/posts',
            headers={"Authorization": f"Bearer {self.token_a}"},
            json={
                "title": "Content to be Reported",
                "body": "Spammy link promoting unauthorized medical claims.",
                "category_id": "cat_general"
            }
        )
        post_id = p_res.get_json()["post_id"]

        rep_res = self.client.post(
            '/api/community/reports',
            headers={"Authorization": f"Bearer {self.token_b}"},
            json={
                "content_type": "post",
                "content_id": post_id,
                "reason": "Misinformation or unsafe medical advice",
                "explanation": "Promotes unverified self-treatments."
            }
        )
        self.assertEqual(rep_res.status_code, 201)

    def test_member_blocking_hides_content(self):
        """When Bob blocks Alice, Alice's posts are omitted from Bob's feed."""
        # Alice creates a post
        p_res = self.client.post(
            '/api/community/posts',
            headers={"Authorization": f"Bearer {self.token_a}"},
            json={
                "title": "Alice's Post Before Block",
                "body": "This post should vanish from Bob's view once blocked.",
                "category_id": "cat_general"
            }
        )
        post_id = p_res.get_json()["post_id"]

        # Bob blocks Alice
        block_res = self.client.post(
            f'/api/community/block/{self.user_a_id}',
            headers={"Authorization": f"Bearer {self.token_b}"}
        )
        self.assertEqual(block_res.status_code, 200)

        # Bob fetches feed
        feed_res = self.client.get('/api/community/posts', headers={"Authorization": f"Bearer {self.token_b}"})
        feed_posts = feed_res.get_json()["posts"]
        post_ids = [p["post_id"] for p in feed_posts]
        self.assertNotIn(post_id, post_ids)

        # Bob unblocks Alice
        unblock_res = self.client.delete(
            f'/api/community/block/{self.user_a_id}',
            headers={"Authorization": f"Bearer {self.token_b}"}
        )
        self.assertEqual(unblock_res.status_code, 200)

    def test_self_blocking_prevented(self):
        """User cannot block themselves."""
        res = self.client.post(
            f'/api/community/block/{self.user_a_id}',
            headers={"Authorization": f"Bearer {self.token_a}"}
        )
        self.assertEqual(res.status_code, 400)

    # ------------------------------------------------------------------
    # 5. Moderator Controls & Health Resource Verification
    # ------------------------------------------------------------------

    def test_ordinary_user_cannot_access_moderator_routes(self):
        """Ordinary member receives 403 when trying to access moderator endpoints."""
        res = self.client.get('/api/community/moderator/reports', headers={"Authorization": f"Bearer {self.token_a}"})
        self.assertEqual(res.status_code, 403)

    def test_moderator_can_lock_and_verify_post(self):
        """Authorized moderator can lock discussions and verify health resources with source URLs."""
        # Create candidate post
        p_res = self.client.post(
            '/api/community/posts',
            headers={"Authorization": f"Bearer {self.token_a}"},
            json={
                "title": "Vitamin D and LH Receptor Sensitivity in PCOS",
                "body": "A post examining clinical literature on vitamin D insufficiency in PCOS patients.",
                "category_id": "cat_treatments"
            }
        )
        post_id = p_res.get_json()["post_id"]

        # Moderator locks discussion
        lock_res = self.client.post(
            f'/api/community/moderator/posts/{post_id}/action',
            headers={"Authorization": f"Bearer {self.token_mod}"},
            json={"action": "lock", "reason": "Standard archive lock"}
        )
        self.assertEqual(lock_res.status_code, 200)

        # Moderator verifies post
        verify_res = self.client.post(
            f'/api/community/moderator/posts/{post_id}/verify',
            headers={"Authorization": f"Bearer {self.token_mod}"},
            json={
                "action": "verify",
                "source_url": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4011048/",
                "notes": "Corroborated by randomized clinical trials on Vitamin D and metabolic parameters."
            }
        )
        self.assertEqual(verify_res.status_code, 200)

        # Check post reflects Verified Health Resource
        check_res = self.client.get(f'/api/community/posts/{post_id}')
        p_data = check_res.get_json()["post"]
        self.assertTrue(p_data["is_verified"])
        self.assertEqual(p_data["health_label"], "Verified Health Resource")
        self.assertTrue(p_data["is_locked"])

        # Check audit log contains record
        log_res = self.client.get('/api/community/moderator/logs', headers={"Authorization": f"Bearer {self.token_mod}"})
        self.assertEqual(log_res.status_code, 200)
        logs = log_res.get_json()["logs"]
        actions = [l["action"] for l in logs]
        self.assertIn("verify_post", actions)

    def test_editing_verified_post_resets_verification(self):
        """If the author modifies a verified post, the verified label is revoked (Section 10)."""
        # Create post
        p_res = self.client.post(
            '/api/community/posts',
            headers={"Authorization": f"Bearer {self.token_a}"},
            json={
                "title": "Initial Verified Post",
                "body": "Initial verified scientific text.",
                "category_id": "cat_treatments"
            }
        )
        post_id = p_res.get_json()["post_id"]

        # Moderator verifies it
        self.client.post(
            f'/api/community/moderator/posts/{post_id}/verify',
            headers={"Authorization": f"Bearer {self.token_mod}"},
            json={
                "action": "verify",
                "source_url": "https://pubmed.ncbi.nlm.nih.gov/12345678/",
                "notes": "Verified against clinical trial."
            }
        )

        # Alice edits the post body
        edit_res = self.client.put(
            f'/api/community/posts/{post_id}',
            headers={"Authorization": f"Bearer {self.token_a}"},
            json={
                "title": "Initial Verified Post",
                "body": "Modified text altering previous claims.",
                "category_id": "cat_treatments"
            }
        )
        self.assertEqual(edit_res.status_code, 200)
        self.assertTrue(edit_res.get_json().get("verification_reset"))

        # Verify label is no longer Verified Health Resource
        view_res = self.client.get(f'/api/community/posts/{post_id}')
        p_data = view_res.get_json()["post"]
        self.assertFalse(p_data["is_verified"])
        self.assertNotEqual(p_data["health_label"], "Verified Health Resource")

if __name__ == '__main__':
    unittest.main()
