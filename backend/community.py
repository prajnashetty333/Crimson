import os
import uuid
import re
from datetime import datetime, timedelta
from functools import wraps
from flask import Blueprint, request, jsonify
from db import execute_query, execute_write

community_bp = Blueprint('community', __name__)

# Auth helper will be imported lazily inside get_current_user_from_request to avoid circular imports

ALLOWED_AVATARS = [
    'avatar_lavender',
    'avatar_blush', 
    'avatar_lotus',
    'avatar_sage',
    'avatar_rose',
    'avatar_sun'
]

VALID_HEALTH_LABELS = [
    'Personal Experience',
    'General Discussion',
    'Verified Health Resource'
]

VALID_REACTION_TYPES = ['helpful', 'support', 'relatable']

VALID_REPORT_REASONS = [
    'Harassment or bullying',
    'Misinformation or unsafe medical advice',
    'Spam or scams',
    'Privacy violation',
    'Inappropriate content',
    'Other'
]

RESERVED_DISPLAY_NAMES = {'admin', 'administrator', 'moderator', 'system', 'ovacare', 'support', 'official'}

# ==========================================
# Auth & Permission Decorators
# ==========================================

def get_current_user_from_request():
    """Extracts and verifies user from Authorization header. Returns dict or None."""
    from app import verify_auth_token
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ", 1)[1].strip()
    user_id = verify_auth_token(token)
    if not user_id:
        return None
    users = execute_query(
        "SELECT user_id, username, email, role, is_community_banned FROM users WHERE user_id = :uid",
        {"uid": user_id}
    )
    if not users:
        return None
    return users[0]

def community_token_required(f):
    """Enforces authentication for community state-changing endpoints."""
    @wraps(f)
    def decorated(*args, **kwargs):
        current_user = get_current_user_from_request()
        if not current_user:
            return jsonify({"error": "Unauthorized: Valid authentication token required"}), 401
            
        # Check active account restrictions
        if current_user.get("is_community_banned"):
            return jsonify({"error": "Forbidden: Your community posting access is currently restricted."}), 403
            
        # Check temporary active restrictions in restrictions table
        active_bans = execute_query(
            """
            SELECT restriction_type, expires_at, reason 
            FROM community_user_restrictions 
            WHERE user_id = :uid AND is_active = 1
            """,
            {"uid": current_user["user_id"]}
        )
        for ban in active_bans:
            expires_at = ban.get("expires_at")
            if expires_at:
                try:
                    exp_dt = datetime.fromisoformat(str(expires_at))
                    if exp_dt > datetime.now():
                        return jsonify({
                            "error": f"Forbidden: Community access restricted ({ban['restriction_type']}) until {expires_at}. Reason: {ban.get('reason')}"
                        }), 403
                    else:
                        # Expired: update is_active to 0
                        execute_write(
                            "UPDATE community_user_restrictions SET is_active = 0 WHERE user_id = :uid",
                            {"uid": current_user["user_id"]}
                        )
                except Exception:
                    pass
            else:
                return jsonify({
                    "error": f"Forbidden: Community access permanently restricted. Reason: {ban.get('reason')}"
                }), 403
                
        return f(current_user, *args, **kwargs)
    return decorated

def moderator_required(f):
    """Enforces moderator or admin role for moderation endpoints."""
    @wraps(f)
    def decorated(*args, **kwargs):
        current_user = get_current_user_from_request()
        if not current_user:
            return jsonify({"error": "Unauthorized: Valid authentication token required"}), 401
        role = current_user.get("role", "member")
        if role not in ("moderator", "admin"):
            return jsonify({"error": "Forbidden: Moderator privileges required"}), 403
        return f(current_user, *args, **kwargs)
    return decorated

# ==========================================
# Helper: Profile & Privacy Resolution
# ==========================================

def get_or_create_profile(user_id, default_username="Member"):
    """Fetches a user's community profile or creates a default pseudonymous profile."""
    profiles = execute_query(
        "SELECT profile_id, user_id, display_name, avatar_key, bio FROM community_profiles WHERE user_id = :uid",
        {"uid": user_id}
    )
    if profiles:
        return profiles[0]
        
    # Auto-generate pseudonymous display name
    clean_base = re.sub(r'[^a-zA-Z0-9]', '', default_username) or 'Member'
    pseudonym = f"{clean_base}_{uuid.uuid4().hex[:4]}"
    profile_id = f"prof_{uuid.uuid4().hex[:12]}"
    execute_write(
        """
        INSERT INTO community_profiles (profile_id, user_id, display_name, avatar_key, bio)
        VALUES (:pid, :uid, :name, 'avatar_lavender', 'OvaCare Community Member ✨')
        """,
        {"pid": profile_id, "uid": user_id, "name": pseudonym}
    )
    return {
        "profile_id": profile_id,
        "user_id": user_id,
        "display_name": pseudonym,
        "avatar_key": "avatar_lavender",
        "bio": "OvaCare Community Member ✨"
    }

def get_blocked_user_ids(user_id):
    """Returns a set of user_ids blocked by the given user or who blocked the given user."""
    if not user_id:
        return set()
    rows = execute_query(
        """
        SELECT blocked_user_id AS other_id FROM community_blocks WHERE blocker_user_id = :uid
        UNION
        SELECT blocker_user_id AS other_id FROM community_blocks WHERE blocked_user_id = :uid
        """,
        {"uid": user_id}
    )
    return {r["other_id"] for r in rows}

# ==========================================
# 1. Profile Management Endpoints
# ==========================================

@community_bp.route('/profile', methods=['GET'])
@community_token_required
def get_my_profile(current_user):
    """Returns the authenticated member's pseudonymous community profile."""
    profile = get_or_create_profile(current_user['user_id'], current_user.get('username', 'Member'))
    return jsonify({
        "profile": {
            "display_name": profile["display_name"],
            "avatar_key": profile["avatar_key"],
            "bio": profile.get("bio", ""),
            "role": current_user.get("role", "member")
        }
    }), 200

@community_bp.route('/profile', methods=['PUT'])
@community_token_required
def update_my_profile(current_user):
    """Updates the authenticated member's pseudonymous profile."""
    data = request.get_json() or {}
    display_name = str(data.get("display_name", "")).strip()
    avatar_key = str(data.get("avatar_key", "avatar_lavender")).strip()
    bio = str(data.get("bio", "")).strip()
    
    # Validate display name
    if not display_name or len(display_name) < 3 or len(display_name) > 30:
        return jsonify({"error": "Display name must be between 3 and 30 characters"}), 400
    if not re.match(r'^[a-zA-Z0-9_\-\s]+$', display_name):
        return jsonify({"error": "Display name can only contain letters, numbers, underscores, hyphens, and spaces"}), 400
    if display_name.lower() in RESERVED_DISPLAY_NAMES:
        return jsonify({"error": "That display name is reserved. Please choose a different pseudonym."}), 400
        
    # Check if another user already has this display name
    existing = execute_query(
        "SELECT user_id FROM community_profiles WHERE LOWER(display_name) = :name AND user_id != :uid",
        {"name": display_name.lower(), "uid": current_user["user_id"]}
    )
    if existing:
        return jsonify({"error": "Display name is already taken. Please pick another unique name."}), 400
        
    if avatar_key not in ALLOWED_AVATARS:
        avatar_key = 'avatar_lavender'
        
    if len(bio) > 300:
        return jsonify({"error": "Bio cannot exceed 300 characters"}), 400
        
    # Ensure profile row exists
    get_or_create_profile(current_user['user_id'], current_user.get('username', 'Member'))
    
    execute_write(
        """
        UPDATE community_profiles 
        SET display_name = :name, avatar_key = :avatar, bio = :bio, updated_at = CURRENT_TIMESTAMP
        WHERE user_id = :uid
        """,
        {
            "name": display_name,
            "avatar": avatar_key,
            "bio": bio,
            "uid": current_user["user_id"]
        }
    )
    
    return jsonify({
        "message": "Profile updated successfully",
        "profile": {
            "display_name": display_name,
            "avatar_key": avatar_key,
            "bio": bio,
            "role": current_user.get("role", "member")
        }
    }), 200

# ==========================================
# 2. Topic Channels Endpoints
# ==========================================

@community_bp.route('/categories', methods=['GET'])
def list_categories():
    """Returns all active community topic channels with active post counts."""
    categories = execute_query(
        """
        SELECT c.category_id, c.name, c.slug, c.description, c.icon, c.display_order,
               COUNT(p.post_id) AS post_count
        FROM community_categories c
        LEFT JOIN community_posts p ON c.category_id = p.category_id AND p.status = 'active'
        GROUP BY c.category_id, c.name, c.slug, c.description, c.icon, c.display_order
        ORDER BY c.display_order ASC
        """
    )
    return jsonify({"categories": categories}), 200

@community_bp.route('/categories', methods=['POST'])
@community_token_required
def create_category(current_user):
    """Allows an authenticated user to create a new community circle / topic channel."""
    data = request.get_json() or {}
    name = str(data.get("name", "")).strip()
    description = str(data.get("description", "")).strip()
    icon = str(data.get("icon", "Sparkles")).strip()
    
    if not name or len(name) < 3 or len(name) > 60:
        return jsonify({"error": "Community name must be between 3 and 60 characters"}), 400
        
    # Generate clean URL slug
    clean_slug = re.sub(r'[^a-zA-Z0-9\s-]', '', name).strip().lower()
    slug = re.sub(r'[\s_-]+', '-', clean_slug).strip('-')
    if not slug:
        slug = f"circle-{uuid.uuid4().hex[:6]}"
        
    # Check if name or slug already exists
    existing = execute_query(
        "SELECT category_id, name FROM community_categories WHERE LOWER(name) = :name OR slug = :slug",
        {"name": name.lower(), "slug": slug}
    )
    if existing:
        return jsonify({"error": f"A community named '{name}' already exists. Please choose a unique name."}), 400
        
    category_id = f"cat_{uuid.uuid4().hex[:12]}"
    
    # Calculate next display_order
    order_row = execute_query("SELECT MAX(display_order) AS max_order FROM community_categories")
    next_order = ((order_row[0]["max_order"] or 0) + 1) if order_row else 1
    
    execute_write(
        """
        INSERT INTO community_categories (category_id, name, slug, description, icon, display_order)
        VALUES (:cid, :name, :slug, :desc, :icon, :ord)
        """,
        {
            "cid": category_id,
            "name": name,
            "slug": slug,
            "desc": description or f"A dedicated community circle for {name}",
            "icon": icon or "Sparkles",
            "ord": next_order
        }
    )
    
    new_cat = {
        "category_id": category_id,
        "name": name,
        "slug": slug,
        "description": description or f"A dedicated community circle for {name}",
        "icon": icon or "Sparkles",
        "display_order": next_order,
        "post_count": 0
    }
    
    return jsonify({
        "message": f"Community '{name}' created successfully!",
        "category": new_cat
    }), 201

# ==========================================
# 3. Posts & Feed Endpoints
# ==========================================

@community_bp.route('/posts', methods=['GET'])
def list_posts():
    """
    Returns paginated feed of community posts with search, channel filter, and sorting.
    Enforces privacy, anonymous flags, and blocking filters on the server.
    """
    current_user = get_current_user_from_request()
    current_user_id = current_user["user_id"] if current_user else None
    blocked_ids = get_blocked_user_ids(current_user_id) if current_user_id else set()
    
    # Query parameters
    category_id = request.args.get("category_id")
    slug = request.args.get("slug")
    search_query = request.args.get("search", "").strip()
    sort_by = request.args.get("sort", "newest") # newest, top, discussed
    health_label = request.args.get("health_label")
    page = max(1, int(request.args.get("page", 1)))
    limit = min(50, max(1, int(request.args.get("limit", 10))))
    offset = (page - 1) * limit
    
    # Build filter conditions
    conditions = ["p.status = 'active'"]
    params = {"limit": limit, "offset": offset}
    
    if category_id:
        conditions.append("p.category_id = :category_id")
        params["category_id"] = category_id
    elif slug:
        conditions.append("c.slug = :slug")
        params["slug"] = slug
        
    if health_label and health_label in VALID_HEALTH_LABELS:
        conditions.append("p.health_label = :health_label")
        params["health_label"] = health_label
        
    if search_query:
        conditions.append("(p.title LIKE :search OR p.body LIKE :search)")
        params["search"] = f"%{search_query}%"
        
    where_clause = " AND ".join(conditions)
    
    # Sorting logic
    if sort_by == "discussed":
        order_clause = "comment_count DESC, p.created_at DESC"
    elif sort_by == "top":
        order_clause = "reaction_count DESC, p.created_at DESC"
    else:
        order_clause = "p.created_at DESC"
        
    sql = f"""
        SELECT 
            p.post_id, p.user_id, p.category_id, p.title, p.body, p.is_anonymous, 
            p.health_label, p.is_verified, p.verified_at, p.verification_source_url, 
            p.verification_notes, p.status, p.is_locked, p.created_at, p.updated_at,
            c.name AS category_name, c.slug AS category_slug,
            prof.display_name, prof.avatar_key,
            (SELECT COUNT(*) FROM community_comments comm WHERE comm.post_id = p.post_id AND comm.status = 'active') AS comment_count,
            (SELECT COUNT(*) FROM community_reactions r WHERE r.post_id = p.post_id) AS reaction_count
        FROM community_posts p
        JOIN community_categories c ON p.category_id = c.category_id
        LEFT JOIN community_profiles prof ON p.user_id = prof.user_id
        WHERE {where_clause}
        ORDER BY {order_clause}
    """
    
    # Execute and filter out blocked users in memory (or query)
    all_rows = execute_query(sql, params)
    
    filtered_rows = []
    for r in all_rows:
        post_author_id = r["user_id"]
        # Skip if post author is in viewer's block relationship
        if post_author_id in blocked_ids:
            continue
            
        # Format author pseudonymous presentation
        is_author = (current_user_id == post_author_id)
        if r["is_anonymous"]:
            author_info = {
                "display_name": "Anonymous Member",
                "avatar_key": "avatar_sage",
                "is_anonymous": True
            }
        else:
            author_info = {
                "display_name": r.get("display_name") or "Community Member",
                "avatar_key": r.get("avatar_key") or "avatar_lavender",
                "is_anonymous": False
            }
            
        # Get user reactions on this post
        user_reactions = []
        if current_user_id:
            reactions_rows = execute_query(
                "SELECT reaction_type FROM community_reactions WHERE post_id = :pid AND user_id = :uid",
                {"pid": r["post_id"], "uid": current_user_id}
            )
            user_reactions = [rx["reaction_type"] for rx in reactions_rows]
            
        filtered_rows.append({
            "post_id": r["post_id"],
            "title": r["title"],
            "body": r["body"],
            "category_id": r["category_id"],
            "category_name": r["category_name"],
            "category_slug": r["category_slug"],
            "health_label": r["health_label"],
            "is_verified": bool(r["is_verified"]),
            "verification_source_url": r["verification_source_url"] if r["is_verified"] else None,
            "verification_notes": r["verification_notes"] if r["is_verified"] else None,
            "is_locked": bool(r["is_locked"]),
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
            "comment_count": r["comment_count"],
            "reaction_count": r["reaction_count"],
            "user_reactions": user_reactions,
            "author": author_info,
            "is_author": is_author
        })
        
    return jsonify({
        "posts": filtered_rows[offset:offset + limit] if offset > 0 else filtered_rows[:limit],
        "page": page,
        "limit": limit,
        "total": len(filtered_rows)
    }), 200

@community_bp.route('/posts', methods=['POST'])
@community_token_required
def create_post(current_user):
    """
    Creates a new community post.
    Validates input length, channel validity, and enforces that regular users
    cannot assign the 'Verified Health Resource' label.
    """
    data = request.get_json() or {}
    title = str(data.get("title", "")).strip()
    body = str(data.get("body", "")).strip()
    category_id = str(data.get("category_id", "")).strip()
    is_anonymous = bool(data.get("is_anonymous", False))
    requested_label = str(data.get("health_label", "Personal Experience")).strip()
    
    # Validation
    if not title or len(title) < 3 or len(title) > 200:
        return jsonify({"error": "Post title must be between 3 and 200 characters"}), 400
    if not body or len(body) < 3 or len(body) > 5000:
        return jsonify({"error": "Post content must be between 3 and 5,000 characters"}), 400
        
    # Verify channel exists
    category = execute_query(
        "SELECT category_id, name FROM community_categories WHERE category_id = :cid",
        {"cid": category_id}
    )
    if not category:
        return jsonify({"error": "Please select a valid topic channel"}), 400
        
    # Enforce Health Label rules: Regular members cannot assign 'Verified Health Resource'
    if requested_label == "Verified Health Resource" and current_user.get("role") not in ("moderator", "admin"):
        return jsonify({
            "error": "The 'Verified Health Resource' label can only be assigned after review by an authorized moderator."
        }), 403
        
    if requested_label not in VALID_HEALTH_LABELS:
        requested_label = "Personal Experience"
        
    post_id = f"post_{uuid.uuid4().hex[:12]}"
    
    # Ensure profile exists for user
    get_or_create_profile(current_user["user_id"], current_user.get("username", "Member"))
    
    execute_write(
        """
        INSERT INTO community_posts (
            post_id, user_id, category_id, title, body, is_anonymous, 
            health_label, status, is_locked, created_at, updated_at
        ) VALUES (
            :post_id, :user_id, :category_id, :title, :body, :is_anonymous,
            :health_label, 'active', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        )
        """,
        {
            "post_id": post_id,
            "user_id": current_user["user_id"],
            "category_id": category_id,
            "title": title,
            "body": body,
            "is_anonymous": 1 if is_anonymous else 0,
            "health_label": requested_label
        }
    )
    
    return jsonify({
        "message": "Post created successfully",
        "post_id": post_id
    }), 201

@community_bp.route('/posts/<post_id>', methods=['GET'])
def get_post(post_id):
    """Retrieves full details of a single post."""
    current_user = get_current_user_from_request()
    current_user_id = current_user["user_id"] if current_user else None
    blocked_ids = get_blocked_user_ids(current_user_id) if current_user_id else set()
    
    posts = execute_query(
        """
        SELECT 
            p.post_id, p.user_id, p.category_id, p.title, p.body, p.is_anonymous, 
            p.health_label, p.is_verified, p.verified_at, p.verification_source_url, 
            p.verification_notes, p.status, p.is_locked, p.created_at, p.updated_at,
            c.name AS category_name, c.slug AS category_slug,
            prof.display_name, prof.avatar_key,
            (SELECT COUNT(*) FROM community_comments comm WHERE comm.post_id = p.post_id AND comm.status = 'active') AS comment_count,
            (SELECT COUNT(*) FROM community_reactions r WHERE r.post_id = p.post_id) AS reaction_count
        FROM community_posts p
        JOIN community_categories c ON p.category_id = c.category_id
        LEFT JOIN community_profiles prof ON p.user_id = prof.user_id
        WHERE p.post_id = :pid
        """,
        {"pid": post_id}
    )
    if not posts:
        return jsonify({"error": "Post not found"}), 404
        
    p = posts[0]
    if p["status"] == "removed" and (not current_user or current_user.get("role") not in ("moderator", "admin")):
        return jsonify({"error": "This post has been removed by moderation."}), 404
        
    if p["user_id"] in blocked_ids:
        return jsonify({"error": "Content not available"}), 403
        
    is_author = (current_user_id == p["user_id"])
    if p["is_anonymous"]:
        author_info = {"display_name": "Anonymous Member", "avatar_key": "avatar_sage", "is_anonymous": True}
    else:
        author_info = {
            "display_name": p.get("display_name") or "Community Member",
            "avatar_key": p.get("avatar_key") or "avatar_lavender",
            "is_anonymous": False
        }
        
    # Get reaction tallies breakdown
    reaction_counts = {"helpful": 0, "support": 0, "relatable": 0}
    rx_breakdown = execute_query(
        "SELECT reaction_type, COUNT(*) as cnt FROM community_reactions WHERE post_id = :pid GROUP BY reaction_type",
        {"pid": post_id}
    )
    for row in rx_breakdown:
        if row["reaction_type"] in reaction_counts:
            reaction_counts[row["reaction_type"]] = row["cnt"]
            
    # User's own reactions
    user_reactions = []
    if current_user_id:
        rx_rows = execute_query(
            "SELECT reaction_type FROM community_reactions WHERE post_id = :pid AND user_id = :uid",
            {"pid": post_id, "uid": current_user_id}
        )
        user_reactions = [rx["reaction_type"] for rx in rx_rows]
        
    return jsonify({
        "post": {
            "post_id": p["post_id"],
            "title": p["title"],
            "body": p["body"],
            "category_id": p["category_id"],
            "category_name": p["category_name"],
            "category_slug": p["category_slug"],
            "health_label": p["health_label"],
            "is_verified": bool(p["is_verified"]),
            "verification_source_url": p["verification_source_url"] if p["is_verified"] else None,
            "verification_notes": p["verification_notes"] if p["is_verified"] else None,
            "is_locked": bool(p["is_locked"]),
            "created_at": p["created_at"],
            "updated_at": p["updated_at"],
            "comment_count": p["comment_count"],
            "reaction_count": p["reaction_count"],
            "reactions_breakdown": reaction_counts,
            "user_reactions": user_reactions,
            "author": author_info,
            "is_author": is_author
        }
    }), 200

@community_bp.route('/posts/<post_id>', methods=['PUT'])
@community_token_required
def update_post(current_user, post_id):
    """
    Edits a member's own post.
    Enforces server-side ownership. If post was verified, resets verification.
    """
    post = execute_query("SELECT user_id, is_verified, is_locked, status FROM community_posts WHERE post_id = :pid", {"pid": post_id})
    if not post:
        return jsonify({"error": "Post not found"}), 404
    p = post[0]
    
    # Ownership check
    if p["user_id"] != current_user["user_id"] and current_user.get("role") not in ("moderator", "admin"):
        return jsonify({"error": "Forbidden: You can only edit your own posts"}), 403
        
    if p["is_locked"]:
        return jsonify({"error": "This post is locked by a moderator and cannot be edited"}), 403
        
    data = request.get_json() or {}
    title = str(data.get("title", "")).strip()
    body = str(data.get("body", "")).strip()
    category_id = str(data.get("category_id", "")).strip()
    is_anonymous = bool(data.get("is_anonymous", False))
    
    if not title or len(title) < 5 or len(title) > 200:
        return jsonify({"error": "Post title must be between 5 and 200 characters"}), 400
    if not body or len(body) < 10 or len(body) > 5000:
        return jsonify({"error": "Post content must be between 10 and 5,000 characters"}), 400
        
    # If the post had a verified label, revoking verification upon content change is mandatory (Section 10)
    reset_verification = bool(p["is_verified"])
    
    execute_write(
        """
        UPDATE community_posts 
        SET title = :title, body = :body, category_id = :cat_id, is_anonymous = :anon,
            is_verified = CASE WHEN :reset_ver = 1 THEN 0 ELSE is_verified END,
            health_label = CASE WHEN :reset_ver = 1 THEN 'Personal Experience' ELSE health_label END,
            updated_at = CURRENT_TIMESTAMP
        WHERE post_id = :pid
        """,
        {
            "title": title,
            "body": body,
            "cat_id": category_id,
            "anon": 1 if is_anonymous else 0,
            "reset_ver": 1 if reset_verification else 0,
            "pid": post_id
        }
    )
    
    return jsonify({
        "message": "Post updated successfully",
        "verification_reset": reset_verification
    }), 200

@community_bp.route('/posts/<post_id>', methods=['DELETE'])
@community_token_required
def delete_post(current_user, post_id):
    """Deletes a post. Enforces server-side ownership or moderator role."""
    post = execute_query("SELECT user_id, title FROM community_posts WHERE post_id = :pid", {"pid": post_id})
    if not post:
        return jsonify({"error": "Post not found"}), 404
    p = post[0]
    
    is_moderator = current_user.get("role") in ("moderator", "admin")
    if p["user_id"] != current_user["user_id"] and not is_moderator:
        return jsonify({"error": "Forbidden: You cannot delete another member's post"}), 403
        
    execute_write("DELETE FROM community_posts WHERE post_id = :pid", {"pid": post_id})
    
    if is_moderator and p["user_id"] != current_user["user_id"]:
        # Log moderation action
        execute_write(
            """
            INSERT INTO community_moderation_logs (log_id, moderator_user_id, action, target_type, target_id, reason)
            VALUES (:lid, :mid, 'delete_post', 'post', :pid, 'Moderator deletion of post')
            """,
            {"lid": f"mod_{uuid.uuid4().hex[:12]}", "mid": current_user["user_id"], "pid": post_id}
        )
        
    return jsonify({"message": "Post deleted successfully"}), 200

# ==========================================
# 4. Comments and Replies Endpoints
# ==========================================

@community_bp.route('/posts/<post_id>/comments', methods=['GET'])
def list_comments(post_id):
    """Returns top-level comments and 1-level nested replies, omitting blocked users."""
    current_user = get_current_user_from_request()
    current_user_id = current_user["user_id"] if current_user else None
    blocked_ids = get_blocked_user_ids(current_user_id) if current_user_id else set()
    
    rows = execute_query(
        """
        SELECT 
            c.comment_id, c.post_id, c.user_id, c.parent_comment_id, c.body, 
            c.is_anonymous, c.status, c.created_at, c.updated_at,
            prof.display_name, prof.avatar_key
        FROM community_comments c
        LEFT JOIN community_profiles prof ON c.user_id = prof.user_id
        WHERE c.post_id = :pid AND c.status = 'active'
        ORDER BY c.created_at ASC
        """,
        {"pid": post_id}
    )
    
    # Structure into top-level and nested replies
    comments_map = {}
    top_level_comments = []
    
    for r in rows:
        if r["user_id"] in blocked_ids:
            continue
            
        is_author = (current_user_id == r["user_id"])
        if r["is_anonymous"]:
            author_info = {"display_name": "Anonymous Member", "avatar_key": "avatar_sage", "is_anonymous": True}
        else:
            author_info = {
                "display_name": r.get("display_name") or "Community Member",
                "avatar_key": r.get("avatar_key") or "avatar_lavender",
                "is_anonymous": False
            }
            
        comment_obj = {
            "comment_id": r["comment_id"],
            "post_id": r["post_id"],
            "parent_comment_id": r["parent_comment_id"],
            "body": r["body"],
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
            "author": author_info,
            "is_author": is_author,
            "replies": []
        }
        
        comments_map[r["comment_id"]] = comment_obj
        
        if not r["parent_comment_id"]:
            top_level_comments.append(comment_obj)
        else:
            # Nest under parent comment if present
            parent = comments_map.get(r["parent_comment_id"])
            if parent:
                parent["replies"].append(comment_obj)
            else:
                top_level_comments.append(comment_obj)
                
    return jsonify({
        "comments": top_level_comments,
        "total": len(rows)
    }), 200

@community_bp.route('/posts/<post_id>/comments', methods=['POST'])
@community_token_required
def create_comment(current_user, post_id):
    """Adds a comment or reply to a post. Checks locked/removed status."""
    post = execute_query("SELECT is_locked, status FROM community_posts WHERE post_id = :pid", {"pid": post_id})
    if not post:
        return jsonify({"error": "Post not found"}), 404
    p = post[0]
    
    if p["status"] == "removed":
        return jsonify({"error": "Cannot comment on a removed post"}), 400
    if p["is_locked"]:
        return jsonify({"error": "This discussion has been locked by a moderator"}), 403
        
    data = request.get_json() or {}
    body = str(data.get("body", "")).strip()
    parent_comment_id = data.get("parent_comment_id")
    is_anonymous = bool(data.get("is_anonymous", False))
    
    if not body or len(body) < 2 or len(body) > 2000:
        return jsonify({"error": "Comment must be between 2 and 2,000 characters"}), 400
        
    # If reply, verify parent comment exists and belongs to the same post
    if parent_comment_id:
        parent = execute_query(
            "SELECT comment_id, post_id, parent_comment_id FROM community_comments WHERE comment_id = :cid AND status = 'active'",
            {"cid": parent_comment_id}
        )
        if not parent or parent[0]["post_id"] != post_id:
            return jsonify({"error": "Invalid parent comment"}), 400
            
    comment_id = f"cmt_{uuid.uuid4().hex[:12]}"
    get_or_create_profile(current_user["user_id"], current_user.get("username", "Member"))
    
    execute_write(
        """
        INSERT INTO community_comments (
            comment_id, post_id, user_id, parent_comment_id, body, is_anonymous, status, created_at, updated_at
        ) VALUES (
            :cid, :pid, :uid, :parent_id, :body, :anon, 'active', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        )
        """,
        {
            "cid": comment_id,
            "pid": post_id,
            "uid": current_user["user_id"],
            "parent_id": parent_comment_id,
            "body": body,
            "anon": 1 if is_anonymous else 0
        }
    )
    
    return jsonify({
        "message": "Comment posted successfully",
        "comment_id": comment_id
    }), 201

@community_bp.route('/comments/<comment_id>', methods=['PUT'])
@community_token_required
def update_comment(current_user, comment_id):
    """Edits a member's own comment."""
    comment = execute_query("SELECT user_id, post_id FROM community_comments WHERE comment_id = :cid", {"cid": comment_id})
    if not comment:
        return jsonify({"error": "Comment not found"}), 404
    c = comment[0]
    
    if c["user_id"] != current_user["user_id"]:
        return jsonify({"error": "Forbidden: You can only edit your own comment"}), 403
        
    data = request.get_json() or {}
    body = str(data.get("body", "")).strip()
    if not body or len(body) < 2 or len(body) > 2000:
        return jsonify({"error": "Comment must be between 2 and 2,000 characters"}), 400
        
    execute_write(
        "UPDATE community_comments SET body = :body, updated_at = CURRENT_TIMESTAMP WHERE comment_id = :cid",
        {"body": body, "cid": comment_id}
    )
    return jsonify({"message": "Comment updated successfully"}), 200

@community_bp.route('/comments/<comment_id>', methods=['DELETE'])
@community_token_required
def delete_comment(current_user, comment_id):
    """Deletes a comment. Enforces ownership or moderator permission."""
    comment = execute_query("SELECT user_id, post_id FROM community_comments WHERE comment_id = :cid", {"cid": comment_id})
    if not comment:
        return jsonify({"error": "Comment not found"}), 404
    c = comment[0]
    
    is_moderator = current_user.get("role") in ("moderator", "admin")
    if c["user_id"] != current_user["user_id"] and not is_moderator:
        return jsonify({"error": "Forbidden: You cannot delete another member's comment"}), 403
        
    execute_write("DELETE FROM community_comments WHERE comment_id = :cid", {"cid": comment_id})
    return jsonify({"message": "Comment deleted successfully"}), 200

# ==========================================
# 5. Supportive Reactions Endpoints
# ==========================================

@community_bp.route('/posts/<post_id>/reactions', methods=['POST'])
@community_token_required
def toggle_reaction(current_user, post_id):
    """
    Toggles a supportive reaction ('helpful', 'support', 'relatable').
    Adding if not present; removing if clicked again. Prevents duplicate rows.
    """
    data = request.get_json() or {}
    rx_type = str(data.get("reaction_type", "")).strip().lower()
    
    if rx_type not in VALID_REACTION_TYPES:
        return jsonify({"error": f"Invalid reaction type. Must be one of: {', '.join(VALID_REACTION_TYPES)}"}), 400
        
    post = execute_query("SELECT post_id FROM community_posts WHERE post_id = :pid AND status = 'active'", {"pid": post_id})
    if not post:
        return jsonify({"error": "Post not found"}), 404
        
    # Check if reaction already exists
    existing = execute_query(
        "SELECT reaction_id FROM community_reactions WHERE post_id = :pid AND user_id = :uid AND reaction_type = :rx",
        {"pid": post_id, "uid": current_user["user_id"], "rx": rx_type}
    )
    
    if existing:
        # Remove reaction (toggle off)
        execute_write(
            "DELETE FROM community_reactions WHERE reaction_id = :rid",
            {"rid": existing[0]["reaction_id"]}
        )
        action = "removed"
    else:
        # Add reaction
        execute_write(
            """
            INSERT INTO community_reactions (reaction_id, post_id, user_id, reaction_type)
            VALUES (:rid, :pid, :uid, :rx)
            """,
            {
                "rid": f"rx_{uuid.uuid4().hex[:12]}",
                "pid": post_id,
                "uid": current_user["user_id"],
                "rx": rx_type
            }
        )
        action = "added"
        
    # Return updated counts
    breakdown = {"helpful": 0, "support": 0, "relatable": 0}
    counts = execute_query(
        "SELECT reaction_type, COUNT(*) as cnt FROM community_reactions WHERE post_id = :pid GROUP BY reaction_type",
        {"pid": post_id}
    )
    for c in counts:
        if c["reaction_type"] in breakdown:
            breakdown[c["reaction_type"]] = c["cnt"]
            
    my_reactions = [
        r["reaction_type"] for r in execute_query(
            "SELECT reaction_type FROM community_reactions WHERE post_id = :pid AND user_id = :uid",
            {"pid": post_id, "uid": current_user["user_id"]}
        )
    ]
    
    return jsonify({
        "message": f"Reaction {action}",
        "action": action,
        "reactions_breakdown": breakdown,
        "user_reactions": my_reactions
    }), 200

# ==========================================
# 6. Reporting & Blocking Endpoints
# ==========================================

@community_bp.route('/reports', methods=['POST'])
@community_token_required
def submit_report(current_user):
    """Submits a report for a post or comment."""
    data = request.get_json() or {}
    content_type = str(data.get("content_type", "")).strip().lower()
    content_id = str(data.get("content_id", "")).strip()
    reason = str(data.get("reason", "")).strip()
    explanation = str(data.get("explanation", "")).strip()
    
    if content_type not in ('post', 'comment'):
        return jsonify({"error": "Content type must be 'post' or 'comment'"}), 400
    if not content_id:
        return jsonify({"error": "Content ID is required"}), 400
    if reason not in VALID_REPORT_REASONS:
        return jsonify({"error": "Please select a valid report reason"}), 400
    if len(explanation) > 1000:
        return jsonify({"error": "Explanation must be 1,000 characters or less"}), 400
        
    # Check duplicate report by same user
    existing = execute_query(
        """
        SELECT report_id FROM community_reports 
        WHERE reporter_user_id = :uid AND content_type = :ctype AND content_id = :cid
        """,
        {"uid": current_user["user_id"], "ctype": content_type, "cid": content_id}
    )
    if existing:
        return jsonify({"message": "You have already submitted a report for this content. Our moderation team is reviewing it."}), 200
        
    report_id = f"rep_{uuid.uuid4().hex[:12]}"
    execute_write(
        """
        INSERT INTO community_reports (
            report_id, reporter_user_id, content_type, content_id, reason, explanation, status
        ) VALUES (
            :rid, :uid, :ctype, :cid, :reason, :exp, 'pending'
        )
        """,
        {
            "rid": report_id,
            "uid": current_user["user_id"],
            "ctype": content_type,
            "cid": content_id,
            "reason": reason,
            "exp": explanation
        }
    )
    
    return jsonify({"message": "Report submitted. Thank you for keeping our community safe and supportive."}), 201

@community_bp.route('/block/<target_user_id>', methods=['POST'])
@community_token_required
def block_member(current_user, target_user_id):
    """Blocks another member. Prevents self-blocking."""
    if current_user["user_id"] == target_user_id:
        return jsonify({"error": "You cannot block yourself"}), 400
        
    target_user = execute_query("SELECT user_id FROM users WHERE user_id = :uid", {"uid": target_user_id})
    if not target_user:
        return jsonify({"error": "User does not exist"}), 404
        
    existing = execute_query(
        "SELECT block_id FROM community_blocks WHERE blocker_user_id = :bid AND blocked_user_id = :tid",
        {"bid": current_user["user_id"], "tid": target_user_id}
    )
    if not existing:
        execute_write(
            "INSERT INTO community_blocks (block_id, blocker_user_id, blocked_user_id) VALUES (:bid, :uid, :tid)",
            {"bid": f"blk_{uuid.uuid4().hex[:12]}", "uid": current_user["user_id"], "tid": target_user_id}
        )
        
    return jsonify({"message": "Member blocked. Their posts and comments are now hidden from your feed."}), 200

@community_bp.route('/block/<target_user_id>', methods=['DELETE'])
@community_token_required
def unblock_member(current_user, target_user_id):
    """Unblocks a previously blocked member."""
    execute_write(
        "DELETE FROM community_blocks WHERE blocker_user_id = :uid AND blocked_user_id = :tid",
        {"uid": current_user["user_id"], "tid": target_user_id}
    )
    return jsonify({"message": "Member unblocked successfully"}), 200

@community_bp.route('/blocks', methods=['GET'])
@community_token_required
def list_blocks(current_user):
    """Returns the list of members blocked by the logged-in member (pseudonymous)."""
    blocks = execute_query(
        """
        SELECT b.block_id, b.blocked_user_id, b.created_at, p.display_name, p.avatar_key
        FROM community_blocks b
        LEFT JOIN community_profiles p ON b.blocked_user_id = p.user_id
        WHERE b.blocker_user_id = :uid
        ORDER BY b.created_at DESC
        """,
        {"uid": current_user["user_id"]}
    )
    return jsonify({
        "blocked_members": [
            {
                "blocked_user_id": b["blocked_user_id"],
                "display_name": b.get("display_name") or "Blocked Member",
                "avatar_key": b.get("avatar_key") or "avatar_lavender",
                "blocked_at": b["created_at"]
            }
            for b in blocks
        ]
    }), 200

# ==========================================
# 7. Moderator Dashboard & Control Endpoints
# ==========================================

@community_bp.route('/moderator/stats', methods=['GET'])
@moderator_required
def moderator_stats(current_user):
    """Returns statistical metrics for the moderator dashboard."""
    pending_reports = execute_query("SELECT COUNT(*) as cnt FROM community_reports WHERE status = 'pending'")[0]["cnt"]
    total_posts = execute_query("SELECT COUNT(*) as cnt FROM community_posts WHERE status = 'active'")[0]["cnt"]
    removed_posts = execute_query("SELECT COUNT(*) as cnt FROM community_posts WHERE status = 'removed'")[0]["cnt"]
    verified_posts = execute_query("SELECT COUNT(*) as cnt FROM community_posts WHERE is_verified = 1")[0]["cnt"]
    active_restrictions = execute_query("SELECT COUNT(*) as cnt FROM community_user_restrictions WHERE is_active = 1")[0]["cnt"]
    
    return jsonify({
        "pending_reports": pending_reports,
        "total_posts": total_posts,
        "removed_posts": removed_posts,
        "verified_posts": verified_posts,
        "active_restrictions": active_restrictions
    }), 200

@community_bp.route('/moderator/reports', methods=['GET'])
@moderator_required
def list_reports(current_user):
    """Lists moderation reports with filters for status, reason, content_type."""
    status = request.args.get("status", "pending")
    reason = request.args.get("reason")
    content_type = request.args.get("content_type")
    
    conditions = []
    params = {}
    
    if status and status != "all":
        conditions.append("r.status = :status")
        params["status"] = status
    if reason:
        conditions.append("r.reason = :reason")
        params["reason"] = reason
    if content_type:
        conditions.append("r.content_type = :ctype")
        params["ctype"] = content_type
        
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    
    reports = execute_query(
        f"""
        SELECT 
            r.report_id, r.reporter_user_id, r.content_type, r.content_id, 
            r.reason, r.explanation, r.status, r.reviewed_by, r.reviewed_at, 
            r.resolution_notes, r.created_at
        FROM community_reports r
        {where}
        ORDER BY r.created_at DESC
        """,
        params
    )
    
    # Attach content context for each report
    detailed_reports = []
    for rep in reports:
        item_context = None
        if rep["content_type"] == "post":
            p = execute_query(
                "SELECT title, body, status, is_locked, user_id FROM community_posts WHERE post_id = :id",
                {"id": rep["content_id"]}
            )
            if p:
                item_context = {
                    "title": p[0]["title"],
                    "body": p[0]["body"][:200] + "..." if len(p[0]["body"]) > 200 else p[0]["body"],
                    "status": p[0]["status"],
                    "author_user_id": p[0]["user_id"]
                }
        else:
            c = execute_query(
                "SELECT body, status, post_id, user_id FROM community_comments WHERE comment_id = :id",
                {"id": rep["content_id"]}
            )
            if c:
                item_context = {
                    "body": c[0]["body"],
                    "status": c[0]["status"],
                    "post_id": c[0]["post_id"],
                    "author_user_id": c[0]["user_id"]
                }
                
        detailed_reports.append({
            "report_id": rep["report_id"],
            "content_type": rep["content_type"],
            "content_id": rep["content_id"],
            "reason": rep["reason"],
            "explanation": rep["explanation"],
            "status": rep["status"],
            "created_at": rep["created_at"],
            "resolution_notes": rep["resolution_notes"],
            "context": item_context
        })
        
    return jsonify({"reports": detailed_reports}), 200

@community_bp.route('/moderator/reports/<report_id>/resolve', methods=['POST'])
@moderator_required
def resolve_report(current_user, report_id):
    """Resolves or dismisses a report."""
    data = request.get_json() or {}
    resolution = str(data.get("resolution", "resolved")).strip() # 'resolved' or 'dismissed'
    notes = str(data.get("resolution_notes", "")).strip()
    
    if resolution not in ('resolved', 'dismissed'):
        return jsonify({"error": "Resolution status must be 'resolved' or 'dismissed'"}), 400
        
    execute_write(
        """
        UPDATE community_reports
        SET status = :res, reviewed_by = :mid, reviewed_at = CURRENT_TIMESTAMP, resolution_notes = :notes
        WHERE report_id = :rid
        """,
        {"res": resolution, "mid": current_user["user_id"], "notes": notes, "rid": report_id}
    )
    
    # Audit log
    execute_write(
        """
        INSERT INTO community_moderation_logs (log_id, moderator_user_id, action, target_type, target_id, reason, details)
        VALUES (:lid, :mid, :action, 'report', :rid, :reason, :details)
        """,
        {
            "lid": f"mod_{uuid.uuid4().hex[:12]}",
            "mid": current_user["user_id"],
            "action": f"report_{resolution}",
            "rid": report_id,
            "reason": notes or f"Marked report {resolution}",
            "details": f"Status changed to {resolution}"
        }
    )
    
    return jsonify({"message": f"Report successfully marked as {resolution}"}), 200

@community_bp.route('/moderator/posts/<post_id>/action', methods=['POST'])
@moderator_required
def moderate_post_action(current_user, post_id):
    """Moderator actions on a post: remove, restore, lock, unlock."""
    data = request.get_json() or {}
    action = str(data.get("action", "")).strip().lower()
    reason = str(data.get("reason", "")).strip()
    
    if action not in ('remove', 'restore', 'lock', 'unlock'):
        return jsonify({"error": "Action must be 'remove', 'restore', 'lock', or 'unlock'"}), 400
    if not reason:
        return jsonify({"error": "A reason is required for moderation audit logging"}), 400
        
    post = execute_query("SELECT post_id, title FROM community_posts WHERE post_id = :pid", {"pid": post_id})
    if not post:
        return jsonify({"error": "Post not found"}), 404
        
    if action == 'remove':
        execute_write("UPDATE community_posts SET status = 'removed', updated_at = CURRENT_TIMESTAMP WHERE post_id = :pid", {"pid": post_id})
    elif action == 'restore':
        execute_write("UPDATE community_posts SET status = 'active', updated_at = CURRENT_TIMESTAMP WHERE post_id = :pid", {"pid": post_id})
    elif action == 'lock':
        execute_write("UPDATE community_posts SET is_locked = 1, updated_at = CURRENT_TIMESTAMP WHERE post_id = :pid", {"pid": post_id})
    elif action == 'unlock':
        execute_write("UPDATE community_posts SET is_locked = 0, updated_at = CURRENT_TIMESTAMP WHERE post_id = :pid", {"pid": post_id})
        
    # Log moderation action
    execute_write(
        """
        INSERT INTO community_moderation_logs (log_id, moderator_user_id, action, target_type, target_id, reason, details)
        VALUES (:lid, :mid, :action, 'post', :pid, :reason, :details)
        """,
        {
            "lid": f"mod_{uuid.uuid4().hex[:12]}",
            "mid": current_user["user_id"],
            "action": f"post_{action}",
            "pid": post_id,
            "reason": reason,
            "details": f"Post status modified by {current_user.get('username')}"
        }
    )
    
    return jsonify({"message": f"Post successfully updated: {action}"}), 200

@community_bp.route('/moderator/posts/<post_id>/verify', methods=['POST'])
@moderator_required
def moderate_post_verify(current_user, post_id):
    """
    Approves or revokes the 'Verified Health Resource' label for a post.
    Requires trusted medical reference link and notes upon approval.
    """
    data = request.get_json() or {}
    action = str(data.get("action", "verify")).strip().lower() # 'verify' or 'revoke'
    source_url = str(data.get("source_url", "")).strip()
    notes = str(data.get("notes", "")).strip()
    
    post = execute_query("SELECT post_id, title FROM community_posts WHERE post_id = :pid", {"pid": post_id})
    if not post:
        return jsonify({"error": "Post not found"}), 404
        
    if action == "verify":
        if not source_url or not (source_url.startswith("http://") or source_url.startswith("https://")):
            return jsonify({"error": "A valid trusted medical source URL (starting with http/https) is required for verification."}), 400
        if not notes or len(notes) < 5:
            return jsonify({"error": "Verification notes summarizing medical review are required."}), 400
            
        execute_write(
            """
            UPDATE community_posts 
            SET is_verified = 1, 
                health_label = 'Verified Health Resource', 
                verified_by = :mid, 
                verified_at = CURRENT_TIMESTAMP, 
                verification_source_url = :url, 
                verification_notes = :notes,
                updated_at = CURRENT_TIMESTAMP
            WHERE post_id = :pid
            """,
            {"mid": current_user["user_id"], "url": source_url, "notes": notes, "pid": post_id}
        )
        log_action = "verify_post"
        log_reason = f"Verified with source: {source_url}"
    else:
        execute_write(
            """
            UPDATE community_posts 
            SET is_verified = 0, 
                health_label = 'General Discussion', 
                verified_by = NULL, 
                verified_at = NULL, 
                verification_source_url = NULL, 
                verification_notes = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE post_id = :pid
            """,
            {"pid": post_id}
        )
        log_action = "revoke_verification"
        log_reason = notes or "Health verification revoked by moderator"
        
    execute_write(
        """
        INSERT INTO community_moderation_logs (log_id, moderator_user_id, action, target_type, target_id, reason, details)
        VALUES (:lid, :mid, :action, 'post', :pid, :reason, :details)
        """,
        {
            "lid": f"mod_{uuid.uuid4().hex[:12]}",
            "mid": current_user["user_id"],
            "action": log_action,
            "pid": post_id,
            "reason": log_reason,
            "details": f"Notes: {notes}"
        }
    )
    
    return jsonify({
        "message": "Health resource verification updated successfully",
        "action": action
    }), 200

@community_bp.route('/moderator/users/<user_id>/restrict', methods=['POST'])
@moderator_required
def restrict_user(current_user, user_id):
    """
    Applies or lifts account restrictions (mute, temporary ban, permanent ban).
    """
    if current_user["user_id"] == user_id:
        return jsonify({"error": "You cannot restrict your own account"}), 400
        
    data = request.get_json() or {}
    restriction_type = str(data.get("restriction_type", "")).strip() # 'mute_posting', 'temporary_ban', 'permanent_ban', 'lift'
    reason = str(data.get("reason", "")).strip()
    duration_days = int(data.get("duration_days", 7))
    
    if restriction_type not in ('mute_posting', 'temporary_ban', 'permanent_ban', 'lift'):
        return jsonify({"error": "Invalid restriction type. Must be 'mute_posting', 'temporary_ban', 'permanent_ban', or 'lift'"}), 400
    if not reason:
        return jsonify({"error": "Reason is required for moderation records"}), 400
        
    if restriction_type == 'lift':
        execute_write(
            "UPDATE community_user_restrictions SET is_active = 0 WHERE user_id = :uid",
            {"uid": user_id}
        )
        execute_write(
            "UPDATE users SET is_community_banned = 0 WHERE user_id = :uid",
            {"uid": user_id}
        )
        action_msg = "Restrictions lifted"
    else:
        expires_at = None
        if restriction_type in ('mute_posting', 'temporary_ban'):
            expires_at = (datetime.now() + timedelta(days=duration_days)).isoformat()
            
        is_perm = (restriction_type == 'permanent_ban')
        
        # Deactivate old restrictions
        execute_write(
            "UPDATE community_user_restrictions SET is_active = 0 WHERE user_id = :uid",
            {"uid": user_id}
        )
        
        # Insert restriction record
        execute_write(
            """
            INSERT INTO community_user_restrictions (
                restriction_id, user_id, restricted_by, restriction_type, expires_at, reason, is_active
            ) VALUES (
                :rid, :uid, :mid, :rtype, :exp, :reason, 1
            )
            """,
            {
                "rid": f"rst_{uuid.uuid4().hex[:12]}",
                "uid": user_id,
                "mid": current_user["user_id"],
                "rtype": restriction_type,
                "exp": expires_at,
                "reason": reason
            }
        )
        
        if is_perm:
            execute_write(
                "UPDATE users SET is_community_banned = 1 WHERE user_id = :uid",
                {"uid": user_id}
            )
            
        action_msg = f"User restricted ({restriction_type})"
        
    execute_write(
        """
        INSERT INTO community_moderation_logs (log_id, moderator_user_id, action, target_type, target_id, reason, details)
        VALUES (:lid, :mid, :action, 'user', :uid, :reason, :details)
        """,
        {
            "lid": f"mod_{uuid.uuid4().hex[:12]}",
            "mid": current_user["user_id"],
            "action": f"user_restriction_{restriction_type}",
            "uid": user_id,
            "reason": reason,
            "details": action_msg
        }
    )
    
    return jsonify({"message": action_msg}), 200

@community_bp.route('/moderator/logs', methods=['GET'])
@moderator_required
def list_moderator_logs(current_user):
    """Returns the immutable moderation audit log."""
    logs = execute_query(
        """
        SELECT 
            m.log_id, m.moderator_user_id, m.action, m.target_type, m.target_id, 
            m.reason, m.details, m.created_at, u.username as moderator_name
        FROM community_moderation_logs m
        LEFT JOIN users u ON m.moderator_user_id = u.user_id
        ORDER BY m.created_at DESC
        LIMIT 100
        """
    )
    return jsonify({"logs": logs}), 200
