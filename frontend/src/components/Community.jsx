import React, { useState, useEffect } from 'react';
import {
  MessageSquare,
  Heart,
  Smile,
  Sparkles,
  Shield,
  ShieldAlert,
  CheckCircle2,
  Filter,
  Search,
  MoreVertical,
  Trash2,
  Edit3,
  AlertTriangle,
  X,
  Send,
  ExternalLink,
  Lock,
  Unlock,
  Ban,
  UserX,
  Apple,
  Moon,
  Activity,
  FileText,
  Check,
  CornerDownRight,
  PlusCircle,
  Lightbulb,
  HeartHandshake,
  Users,
  Flag,
  User,
  Info,
  Plus
} from 'lucide-react';

// Built-in avatar icons mapped to safe styling
const AVATAR_OPTIONS = [
  { key: 'avatar_lavender', label: 'Lavender Bloom', bg: 'bg-purple-100 text-purple-600', emoji: '🌸' },
  { key: 'avatar_blush', label: 'Blush Petal', bg: 'bg-pink-100 text-pink-600', emoji: '🌺' },
  { key: 'avatar_lotus', label: 'Lotus Calm', bg: 'bg-teal-100 text-teal-600', emoji: '🪷' },
  { key: 'avatar_sage', label: 'Sage Leaf', bg: 'bg-emerald-100 text-emerald-600', emoji: '🌿' },
  { key: 'avatar_rose', label: 'Rose Radiance', bg: 'bg-rose-100 text-rose-600', emoji: '🌷' },
  { key: 'avatar_sun', label: 'Morning Glow', bg: 'bg-amber-100 text-amber-600', emoji: '🌻' },
];

const COMMUNITY_ICON_OPTIONS = [
  { key: 'Sparkles', label: 'Sparkles', emoji: '✨' },
  { key: 'Heart', label: 'Heart & Care', emoji: '💜' },
  { key: 'Smile', label: 'Bloom', emoji: '🌸' },
  { key: 'Apple', label: 'Nutrition', emoji: '🥑' },
  { key: 'Moon', label: 'Sleep & Calm', emoji: '🌙' },
  { key: 'Activity', label: 'Movement', emoji: '🏃' },
  { key: 'Lightbulb', label: 'Insight', emoji: '💡' },
  { key: 'Users', label: 'Peer Group', emoji: '👥' },
  { key: 'HeartHandshake', label: 'Support', emoji: '🤝' }
];

const CHANNEL_ICONS = {
  'pcos-symptoms': Heart,
  'nutrition-lifestyle': Apple,
  'mental-wellbeing': Smile,
  'exercise-sleep-energy': Moon,
  'treatment-experiences': Activity,
  'general-discussion': MessageSquare,
  'Sparkles': Sparkles,
  'Heart': Heart,
  'Smile': Smile,
  'Apple': Apple,
  'Moon': Moon,
  'Activity': Activity,
  'Lightbulb': Lightbulb,
  'Users': Users,
  'HeartHandshake': HeartHandshake,
  'MessageSquare': MessageSquare
};

const getCategoryIcon = (cat) => {
  if (!cat) return Sparkles;
  if (cat.icon && CHANNEL_ICONS[cat.icon]) return CHANNEL_ICONS[cat.icon];
  if (cat.slug && CHANNEL_ICONS[cat.slug]) return CHANNEL_ICONS[cat.slug];
  return Sparkles;
};

// Short readable channel labels as requested
const CHANNEL_SHORT_NAMES = {
  'pcos-symptoms': 'PCOS & Symptoms',
  'nutrition-lifestyle': 'Nutrition & Lifestyle',
  'mental-wellbeing': 'Mental Well-being',
  'exercise-sleep-energy': 'Exercise & Sleep',
  'treatment-experiences': 'Treatment Experiences',
  'general-discussion': 'General Discussion'
};

const formatPostDate = (isoStr) => {
  if (!isoStr) return '';
  const date = new Date(isoStr);
  const now = new Date();
  const diffMs = now - date;
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHrs = Math.floor(diffMin / 60);
  const diffDays = Math.floor(diffHrs / 24);

  if (diffSec < 60) return 'just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHrs < 24) return `${diffHrs}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
};

export default function Community({ user, token, apiBase }) {
  // Helper to ensure valid token is retrieved from props or localStorage
  const getAuthToken = () => token || localStorage.getItem('ovacare_token') || '';

  // Navigation & Data States
  const [categories, setCategories] = useState([]);
  const [selectedChannel, setSelectedChannel] = useState(null); // null = all
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedSort, setSelectedSort] = useState('newest'); // 'newest' | 'top' | 'discussed'
  const [selectedHealthLabel, setSelectedHealthLabel] = useState('all');
  
  // Profile State
  const [myProfile, setMyProfile] = useState(null);
  const [showProfileModal, setShowProfileModal] = useState(false);
  const [editDisplayName, setEditDisplayName] = useState('');
  const [editAvatarKey, setEditAvatarKey] = useState('avatar_lavender');
  const [editBio, setEditBio] = useState('');
  const [profileSaving, setProfileSaving] = useState(false);

  // Create Community Circle State
  const [showCreateCommunityModal, setShowCreateCommunityModal] = useState(false);
  const [newCommunityName, setNewCommunityName] = useState('');
  const [newCommunityDescription, setNewCommunityDescription] = useState('');
  const [newCommunityIcon, setNewCommunityIcon] = useState('Sparkles');
  const [createCommunitySubmitting, setCreateCommunitySubmitting] = useState(false);
  const [createCommunityError, setCreateCommunityError] = useState(null);
  
  // Post Composer State
  const [showComposerModal, setShowComposerModal] = useState(false);
  const [composerTitle, setComposerTitle] = useState('');
  const [composerBody, setComposerBody] = useState('');
  const [composerCategory, setComposerCategory] = useState('');
  const [composerAnonymous, setComposerAnonymous] = useState(false);
  const [composerHealthLabel, setComposerHealthLabel] = useState('Personal Experience');
  const [composerSubmitting, setComposerSubmitting] = useState(false);
  const [composerError, setComposerError] = useState(null);
  
  // Single Post Detail & Comments View
  const [activePost, setActivePost] = useState(null);
  const [comments, setComments] = useState([]);
  const [commentsLoading, setCommentsLoading] = useState(false);
  const [commentText, setCommentText] = useState('');
  const [commentAnonymous, setCommentAnonymous] = useState(false);
  const [replyingToCommentId, setReplyingToCommentId] = useState(null);
  const [replyText, setReplyText] = useState('');
  
  // Post Edit State
  const [editingPost, setEditingPost] = useState(null);
  const [editTitle, setEditTitle] = useState('');
  const [editBody, setEditBody] = useState('');
  const [editCategory, setEditCategory] = useState('');
  const [editAnonymous, setEditAnonymous] = useState(false);
  
  // Reporting State
  const [reportingItem, setReportingItem] = useState(null); // { type: 'post'|'comment', id: string, title?: string }
  const [reportReason, setReportReason] = useState('Harassment or bullying');
  const [reportExplanation, setReportExplanation] = useState('');
  const [reportSubmitting, setReportSubmitting] = useState(false);
  
  // Blocking State
  const [showBlockedModal, setShowBlockedModal] = useState(false);
  const [blockedUsers, setBlockedUsers] = useState([]);
  
  // Moderator Portal State
  const [showModModal, setShowModModal] = useState(false);
  const [modTab, setModTab] = useState('reports'); // 'reports' | 'logs'
  const [modStats, setModStats] = useState(null);
  const [modReports, setModReports] = useState([]);
  const [modLogs, setModLogs] = useState([]);
  const [modActionReason, setModActionReason] = useState('');
  const [verifyingPostId, setVerifyingPostId] = useState(null);
  const [verifySourceUrl, setVerifySourceUrl] = useState('');
  const [verifyNotes, setVerifyNotes] = useState('');
  const [restrictUserId, setRestrictUserId] = useState(null);
  const [restrictType, setRestrictType] = useState('mute_posting');
  const [restrictReason, setRestrictReason] = useState('');
  
  // Alerts / Feedback
  const [alertMsg, setAlertMsg] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);

  // Redesign state: Guidelines dialog, 3-dot menu dropdown, inline content expansion
  const [showGuidelinesModal, setShowGuidelinesModal] = useState(false);
  const [activeMenuPostId, setActiveMenuPostId] = useState(null);
  const [expandedPostIds, setExpandedPostIds] = useState(new Set());

  const toggleExpandPost = (postId) => {
    setExpandedPostIds(prev => {
      const next = new Set(prev);
      if (next.has(postId)) {
        next.delete(postId);
      } else {
        next.add(postId);
      }
      return next;
    });
  };

  // Close post 3-dot menu when clicking outside
  useEffect(() => {
    const handleOutsideClick = (e) => {
      if (!e.target.closest('.post-menu-container')) {
        setActiveMenuPostId(null);
      }
    };
    document.addEventListener('mousedown', handleOutsideClick);
    return () => document.removeEventListener('mousedown', handleOutsideClick);
  }, []);

  const isModerator = user && (user.role === 'moderator' || user.role === 'admin');

  // Trigger feedback banner
  const notifySuccess = (msg) => {
    setAlertMsg(msg);
    setTimeout(() => setAlertMsg(null), 4000);
  };
  const notifyError = (msg) => {
    setErrorMsg(msg);
    setTimeout(() => setErrorMsg(null), 5000);
  };

  // 1. Load initial categories and user profile
  useEffect(() => {
    fetchCategories();
    if (getAuthToken()) {
      fetchMyProfile();
    }
  }, [token]);

  // 2. Load feed whenever filters change
  useEffect(() => {
    fetchPosts();
  }, [selectedChannel, selectedSort, selectedHealthLabel, searchQuery]);

  const fetchCategories = async () => {
    try {
      const res = await fetch(`${apiBase}/community/categories`);
      if (res.ok) {
        const data = await res.json();
        const cats = data.categories || [];
        setCategories(cats);
        if (cats.length > 0 && !composerCategory) {
          setComposerCategory(cats[0].category_id);
        }
      }
    } catch (err) {
      console.error("Failed to load community channels", err);
    }
  };

  const fetchMyProfile = async () => {
    const authToken = getAuthToken();
    if (!authToken) return;
    try {
      const res = await fetch(`${apiBase}/community/profile`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
      });
      if (res.ok) {
        const data = await res.json();
        setMyProfile(data.profile);
        setEditDisplayName(data.profile.display_name);
        setEditAvatarKey(data.profile.avatar_key || 'avatar_lavender');
        setEditBio(data.profile.bio || '');
      }
    } catch (err) {
      console.error("Failed to load community profile", err);
    }
  };

  const fetchPosts = async () => {
    setLoading(true);
    try {
      let url = `${apiBase}/community/posts?sort=${selectedSort}`;
      if (selectedChannel) url += `&category_id=${selectedChannel}`;
      if (selectedHealthLabel !== 'all') url += `&health_label=${encodeURIComponent(selectedHealthLabel)}`;
      if (searchQuery.trim()) url += `&search=${encodeURIComponent(searchQuery.trim())}`;

      const authToken = getAuthToken();
      const headers = authToken ? { 'Authorization': `Bearer ${authToken}` } : {};
      const res = await fetch(url, { headers });
      if (res.ok) {
        const data = await res.json();
        setPosts(data.posts || []);
      }
    } catch (err) {
      console.error("Failed to fetch community posts", err);
      notifyError("Failed to load community discussions.");
    } finally {
      setLoading(false);
    }
  };

  const handleOpenComposer = () => {
    setComposerError(null);
    const defaultCat = selectedChannel || (categories.length > 0 ? categories[0].category_id : '');
    setComposerCategory(defaultCat);
    setShowComposerModal(true);
  };

  const handleSaveProfile = async (e) => {
    if (e && e.preventDefault) e.preventDefault();
    if (!editDisplayName.trim()) {
      notifyError("Display name is required.");
      return;
    }
    const authToken = getAuthToken();
    if (!authToken) {
      notifyError("Please log in to update your profile.");
      return;
    }
    setProfileSaving(true);
    try {
      const res = await fetch(`${apiBase}/community/profile`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify({
          display_name: editDisplayName.trim(),
          avatar_key: editAvatarKey,
          bio: editBio.trim()
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Could not update profile");

      setMyProfile(data.profile);
      setShowProfileModal(false);
      notifySuccess("Pseudonymous profile updated successfully!");
      fetchPosts();
    } catch (err) {
      notifyError(err.message);
    } finally {
      setProfileSaving(false);
    }
  };

  const handleCreatePost = async (e) => {
    if (e && e.preventDefault) e.preventDefault();
    setComposerError(null);

    const authToken = getAuthToken();
    if (!authToken) {
      setComposerError("Authentication required. Please sign in or use Demo Mode.");
      return;
    }

    const trimmedTitle = composerTitle.trim();
    const trimmedBody = composerBody.trim();
    const activeCat = composerCategory || selectedChannel || (categories.length > 0 ? categories[0].category_id : '');

    if (!trimmedTitle) {
      setComposerError("Please enter a title for your post.");
      return;
    }
    if (trimmedTitle.length < 3) {
      setComposerError("Title must be at least 3 characters long.");
      return;
    }
    if (!trimmedBody) {
      setComposerError("Please enter your post details.");
      return;
    }
    if (trimmedBody.length < 3) {
      setComposerError("Post content must be at least 3 characters long.");
      return;
    }
    if (!activeCat) {
      setComposerError("Please select a topic channel.");
      return;
    }

    setComposerSubmitting(true);
    try {
      const res = await fetch(`${apiBase}/community/posts`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify({
          title: trimmedTitle,
          body: trimmedBody,
          category_id: activeCat,
          is_anonymous: composerAnonymous,
          health_label: composerHealthLabel
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to publish post");

      setShowComposerModal(false);
      setComposerTitle('');
      setComposerBody('');
      setComposerAnonymous(false);
      setComposerHealthLabel('Personal Experience');
      setComposerError(null);
      notifySuccess("Your post has been shared with the community! 🌸");
      fetchPosts();
      fetchCategories();
    } catch (err) {
      setComposerError(err.message);
      notifyError(err.message);
    } finally {
      setComposerSubmitting(false);
    }
  };

  const handleCreateCommunity = async (e) => {
    if (e && e.preventDefault) e.preventDefault();
    const authToken = getAuthToken();
    if (!authToken) {
      setCreateCommunityError("Please sign in or use Demo Mode to create a community.");
      return;
    }

    const trimmedName = newCommunityName.trim();
    if (!trimmedName || trimmedName.length < 3) {
      setCreateCommunityError("Community name must be at least 3 characters long.");
      return;
    }
    if (trimmedName.length > 50) {
      setCreateCommunityError("Community name cannot exceed 50 characters.");
      return;
    }

    setCreateCommunitySubmitting(true);
    setCreateCommunityError(null);
    try {
      const res = await fetch(`${apiBase}/community/categories`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify({
          name: trimmedName,
          description: newCommunityDescription.trim(),
          icon: newCommunityIcon
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to create community");

      notifySuccess(`Community circle '${trimmedName}' created! 🌸`);
      setShowCreateCommunityModal(false);
      setNewCommunityName('');
      setNewCommunityDescription('');
      setNewCommunityIcon('Sparkles');

      await fetchCategories();
      if (data.category && data.category.category_id) {
        setSelectedChannel(data.category.category_id);
      }
    } catch (err) {
      setCreateCommunityError(err.message);
    } finally {
      setCreateCommunitySubmitting(false);
    }
  };

  const handleUpdatePost = async (e) => {
    if (e && e.preventDefault) e.preventDefault();
    if (!editingPost) return;
    const authToken = getAuthToken();
    try {
      const res = await fetch(`${apiBase}/community/posts/${editingPost.post_id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify({
          title: editTitle.trim(),
          body: editBody.trim(),
          category_id: editCategory,
          is_anonymous: editAnonymous
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to update post");

      setEditingPost(null);
      notifySuccess("Post updated successfully.");
      fetchPosts();
      if (activePost && activePost.post_id === editingPost.post_id) {
        openPostDetail(editingPost.post_id);
      }
    } catch (err) {
      notifyError(err.message);
    }
  };

  const handleDeletePost = async (postId) => {
    if (!window.confirm("Are you sure you want to delete this discussion post?")) return;
    const authToken = getAuthToken();
    try {
      const res = await fetch(`${apiBase}/community/posts/${postId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${authToken}` }
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Could not delete post");

      notifySuccess("Post removed.");
      if (activePost && activePost.post_id === postId) {
        setActivePost(null);
      }
      fetchPosts();
      fetchCategories();
    } catch (err) {
      notifyError(err.message);
    }
  };

  const handleToggleReaction = async (postId, reactionType) => {
    const authToken = getAuthToken();
    if (!authToken) {
      notifyError("Please sign in to react to community posts.");
      return;
    }
    try {
      const res = await fetch(`${apiBase}/community/posts/${postId}/reactions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify({ reaction_type: reactionType })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Reaction failed");

      // Update post in list state
      setPosts(prev => prev.map(p => {
        if (p.post_id === postId) {
          const wasActive = p.user_reactions.includes(reactionType);
          const newReactions = wasActive
            ? p.user_reactions.filter(r => r !== reactionType)
            : [...p.user_reactions, reactionType];
          const newReactionCount = wasActive ? p.reaction_count - 1 : p.reaction_count + 1;
          return {
            ...p,
            user_reactions: newReactions,
            reaction_count: Math.max(0, newReactionCount)
          };
        }
        return p;
      }));

      // Update active post if open
      if (activePost && activePost.post_id === postId) {
        setActivePost(prev => ({
          ...prev,
          reactions_breakdown: data.reactions_breakdown,
          user_reactions: data.user_reactions
        }));
      }
    } catch (err) {
      notifyError(err.message);
    }
  };

  const openPostDetail = async (postId) => {
    try {
      const authToken = getAuthToken();
      const headers = authToken ? { 'Authorization': `Bearer ${authToken}` } : {};
      const res = await fetch(`${apiBase}/community/posts/${postId}`, { headers });
      if (res.ok) {
        const data = await res.json();
        setActivePost(data.post);
        fetchComments(postId);
      }
    } catch (err) {
      notifyError("Failed to open discussion.");
    }
  };

  const fetchComments = async (postId) => {
    setCommentsLoading(true);
    try {
      const authToken = getAuthToken();
      const headers = authToken ? { 'Authorization': `Bearer ${authToken}` } : {};
      const res = await fetch(`${apiBase}/community/posts/${postId}/comments`, { headers });
      if (res.ok) {
        const data = await res.json();
        setComments(data.comments || []);
      }
    } catch (err) {
      console.error("Failed to load comments", err);
    } finally {
      setCommentsLoading(false);
    }
  };

  const handleAddComment = async (e, parentId = null) => {
    if (e && e.preventDefault) e.preventDefault();
    const textContent = parentId ? replyText : commentText;
    if (!textContent.trim()) return;

    const authToken = getAuthToken();
    if (!authToken) {
      notifyError("Please sign in to leave a comment.");
      return;
    }

    try {
      const res = await fetch(`${apiBase}/community/posts/${activePost.post_id}/comments`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify({
          body: textContent.trim(),
          parent_comment_id: parentId,
          is_anonymous: commentAnonymous
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to post comment");

      if (parentId) {
        setReplyText('');
        setReplyingToCommentId(null);
      } else {
        setCommentText('');
      }
      notifySuccess(parentId ? "Reply posted." : "Comment posted.");
      fetchComments(activePost.post_id);
      setActivePost(prev => ({ ...prev, comment_count: prev.comment_count + 1 }));
      setPosts(prev => prev.map(p => p.post_id === activePost.post_id ? { ...p, comment_count: p.comment_count + 1 } : p));
    } catch (err) {
      notifyError(err.message);
    }
  };

  const handleDeleteComment = async (commentId) => {
    if (!window.confirm("Delete this comment?")) return;
    const authToken = getAuthToken();
    try {
      const res = await fetch(`${apiBase}/community/comments/${commentId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${authToken}` }
      });
      if (res.ok) {
        notifySuccess("Comment deleted.");
        fetchComments(activePost.post_id);
      }
    } catch (err) {
      notifyError("Failed to delete comment.");
    }
  };

  const handleSubmitReport = async (e) => {
    if (e && e.preventDefault) e.preventDefault();
    if (!reportingItem) return;
    const authToken = getAuthToken();
    if (!authToken) {
      notifyError("Please sign in to submit a report.");
      return;
    }
    setReportSubmitting(true);
    try {
      const res = await fetch(`${apiBase}/community/reports`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify({
          content_type: reportingItem.type,
          content_id: reportingItem.id,
          reason: reportReason,
          explanation: reportExplanation.trim()
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to submit report");

      notifySuccess(data.message || "Report submitted. Thank you for keeping our community safe.");
      setReportingItem(null);
      setReportExplanation('');
    } catch (err) {
      notifyError(err.message);
    } finally {
      setReportSubmitting(false);
    }
  };

  const handleBlockUser = async (targetUserId, targetName) => {
    if (!window.confirm(`Block ${targetName || 'this member'}? Their discussions and comments will be hidden from your feed.`)) return;
    const authToken = getAuthToken();
    if (!authToken) {
      notifyError("Please sign in to block a member.");
      return;
    }
    try {
      const res = await fetch(`${apiBase}/community/block/${targetUserId}`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${authToken}` }
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Could not block member");

      notifySuccess(data.message || "Member blocked.");
      if (activePost) setActivePost(null);
      fetchPosts();
    } catch (err) {
      notifyError(err.message);
    }
  };

  const fetchBlockedUsers = async () => {
    const authToken = getAuthToken();
    if (!authToken) return;
    try {
      const res = await fetch(`${apiBase}/community/blocks`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
      });
      if (res.ok) {
        const data = await res.json();
        setBlockedUsers(data.blocked_members || []);
      }
    } catch (err) {
      console.error("Failed to load blocks", err);
    }
  };

  const handleUnblockUser = async (targetUserId) => {
    const authToken = getAuthToken();
    try {
      const res = await fetch(`${apiBase}/community/block/${targetUserId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${authToken}` }
      });
      if (res.ok) {
        notifySuccess("Member unblocked.");
        fetchBlockedUsers();
        fetchPosts();
      }
    } catch (err) {
      notifyError("Failed to unblock member.");
    }
  };

  // Moderator Actions
  const openModeratorPortal = async () => {
    setShowModModal(true);
    fetchModStats();
    fetchModReports();
    fetchModLogs();
  };

  const fetchModStats = async () => {
    const authToken = getAuthToken();
    try {
      const res = await fetch(`${apiBase}/community/moderator/stats`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
      });
      if (res.ok) setModStats(await res.json());
    } catch (err) {}
  };

  const fetchModReports = async () => {
    const authToken = getAuthToken();
    try {
      const res = await fetch(`${apiBase}/community/moderator/reports?status=pending`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
      });
      if (res.ok) {
        const data = await res.json();
        setModReports(data.reports || []);
      }
    } catch (err) {}
  };

  const fetchModLogs = async () => {
    const authToken = getAuthToken();
    try {
      const res = await fetch(`${apiBase}/community/moderator/logs`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
      });
      if (res.ok) {
        const data = await res.json();
        setModLogs(data.logs || []);
      }
    } catch (err) {}
  };

  const handleResolveReport = async (reportId, resolution) => {
    const authToken = getAuthToken();
    try {
      const res = await fetch(`${apiBase}/community/moderator/reports/${reportId}/resolve`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify({ resolution, resolution_notes: "Reviewed by moderator" })
      });
      if (res.ok) {
        notifySuccess(`Report marked as ${resolution}`);
        fetchModReports();
        fetchModStats();
      }
    } catch (err) {
      notifyError("Failed to update report");
    }
  };

  const handleModPostAction = async (postId, action) => {
    const authToken = getAuthToken();
    const reason = modActionReason.trim() || `Moderator performed ${action}`;
    try {
      const res = await fetch(`${apiBase}/community/moderator/posts/${postId}/action`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify({ action, reason })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error);
      notifySuccess(`Post ${action}ed successfully.`);
      setModActionReason('');
      fetchPosts();
      if (activePost && activePost.post_id === postId) {
        openPostDetail(postId);
      }
      fetchModStats();
      fetchModLogs();
    } catch (err) {
      notifyError(err.message);
    }
  };

  const handleVerifyPost = async (e) => {
    if (e && e.preventDefault) e.preventDefault();
    if (!verifyingPostId) return;
    const authToken = getAuthToken();
    try {
      const res = await fetch(`${apiBase}/community/moderator/posts/${verifyingPostId}/verify`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify({
          action: 'verify',
          source_url: verifySourceUrl.trim(),
          notes: verifyNotes.trim()
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error);

      notifySuccess("Verified Health Resource badge applied.");
      setVerifyingPostId(null);
      setVerifySourceUrl('');
      setVerifyNotes('');
      fetchPosts();
      fetchModLogs();
      fetchModStats();
    } catch (err) {
      notifyError(err.message);
    }
  };

  const handleRestrictUser = async (e) => {
    if (e && e.preventDefault) e.preventDefault();
    if (!restrictUserId) return;
    const authToken = getAuthToken();
    try {
      const res = await fetch(`${apiBase}/community/moderator/users/${restrictUserId}/restrict`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify({
          restriction_type: restrictType,
          reason: restrictReason.trim() || "Policy violation"
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error);

      notifySuccess(data.message || "User restriction applied");
      setRestrictUserId(null);
      setRestrictReason('');
      fetchModLogs();
      fetchModStats();
    } catch (err) {
      notifyError(err.message);
    }
  };

  const getAvatarBadge = (avatarKey) => {
    const found = AVATAR_OPTIONS.find(a => a.key === avatarKey);
    return found ? found : AVATAR_OPTIONS[0];
  };

  return (
    <div className="space-y-6">
      {/* Feedback Alerts */}
      {alertMsg && (
        <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 px-4 py-3 rounded-2xl text-xs flex items-center justify-between shadow-soft animate-fade-in">
          <div className="flex items-center space-x-2">
            <CheckCircle2 size={16} className="text-emerald-500" />
            <span className="font-medium">{alertMsg}</span>
          </div>
          <button onClick={() => setAlertMsg(null)} className="text-emerald-600 hover:text-emerald-900">
            <X size={14} />
          </button>
        </div>
      )}
      {errorMsg && (
        <div className="bg-rose-50 border border-rose-200 text-rose-800 px-4 py-3 rounded-2xl text-xs flex items-center justify-between shadow-soft animate-fade-in">
          <div className="flex items-center space-x-2">
            <AlertTriangle size={16} className="text-rose-500" />
            <span className="font-medium">{errorMsg}</span>
          </div>
          <button onClick={() => setErrorMsg(null)} className="text-rose-600 hover:text-rose-900">
            <X size={14} />
          </button>
        </div>
      )}

      {/* Compact Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-purple-100/70">
        <div>
          <div className="flex items-center space-x-2.5">
            <h1 className="text-xl sm:text-2xl font-bold text-textPrimary tracking-tight">
              Community
            </h1>
            <button
              onClick={() => setShowGuidelinesModal(true)}
              className="inline-flex items-center space-x-1 text-xs text-primary hover:text-primary-dark font-medium transition cursor-pointer py-1 px-2.5 rounded-xl hover:bg-purple-100/60"
              title="Community Guidelines & Label Guide"
            >
              <Info size={13} className="text-primary" />
              <span className="underline underline-offset-2">Community guidelines</span>
            </button>
          </div>
          <p className="text-xs sm:text-sm text-textSecondary mt-0.5">
            A space to share, connect and support.
          </p>
        </div>

        <div className="flex items-center space-x-2 shrink-0">
          <button
            onClick={() => {
              setCreateCommunityError(null);
              setShowCreateCommunityModal(true);
            }}
            className="bg-primary hover:bg-primary-dark text-white text-xs font-semibold px-3 py-1.5 rounded-xl shadow-2xs transition flex items-center space-x-1.5 cursor-pointer"
            title="Create a new community circle"
          >
            <Plus size={13} />
            <span>Create Community</span>
          </button>

          {myProfile && (
            <button
              onClick={() => setShowProfileModal(true)}
              className="lg:hidden flex items-center space-x-1.5 text-xs text-textPrimary hover:bg-purple-100/60 py-1 px-2.5 rounded-xl border border-purple-100 cursor-pointer"
              title="Edit profile"
            >
              <span>{getAvatarBadge(myProfile.avatar_key).emoji}</span>
              <span className="font-semibold truncate max-w-[85px]">{myProfile.display_name}</span>
            </button>
          )}
          {isModerator && (
            <button
              onClick={openModeratorPortal}
              className="bg-amber-50 hover:bg-amber-100 text-amber-800 text-xs font-semibold px-3 py-1.5 rounded-xl border border-amber-200 transition flex items-center space-x-1.5 shadow-2xs cursor-pointer"
              title="Moderator Portal"
            >
              <Shield size={13} className="text-amber-700" />
              <span>Mod Portal</span>
            </button>
          )}
        </div>
      </div>

      {/* Two-Column Responsive Layout: Left Sidebar + Main Feed */}
      <div className="flex flex-col lg:flex-row gap-6 items-start">
        {/* Left Sidebar (~240px, sticky on desktop, hidden on mobile) */}
        <aside className="hidden lg:block w-[240px] shrink-0 space-y-3.5 lg:sticky lg:top-4 self-start">
          {/* Member Pseudonymous Status Card */}
          {myProfile && (
            <div className="bg-white rounded-2xl p-3 border border-purple-100/80 shadow-2xs flex items-center justify-between">
              <div className="flex items-center space-x-2.5 min-w-0">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm shrink-0 ${getAvatarBadge(myProfile.avatar_key).bg}`}>
                  {getAvatarBadge(myProfile.avatar_key).emoji}
                </div>
                <div className="min-w-0">
                  <div className="flex items-center space-x-1">
                    <span className="text-xs font-bold text-textPrimary truncate">{myProfile.display_name}</span>
                    {myProfile.role === 'moderator' && (
                      <span className="bg-amber-100 text-amber-700 text-[9px] px-1 py-0.2 rounded font-semibold shrink-0">Mod</span>
                    )}
                  </div>
                  <button
                    onClick={() => setShowProfileModal(true)}
                    className="text-[11px] text-primary hover:underline font-medium block truncate text-left cursor-pointer"
                  >
                    Edit profile
                  </button>
                </div>
              </div>
              <button
                onClick={() => {
                  fetchBlockedUsers();
                  setShowBlockedModal(true);
                }}
                className="p-1.5 text-textLight hover:text-textSecondary hover:bg-purple-50 rounded-lg transition cursor-pointer"
                title="Manage Blocked Members"
                aria-label="Manage Blocked Members"
              >
                <UserX size={14} />
              </button>
            </div>
          )}

          {/* Desktop Topic Channels List */}
          <div className="hidden lg:block bg-white rounded-2xl p-2.5 border border-purple-100/80 shadow-2xs space-y-0.5">
            <div className="flex items-center justify-between px-2.5 py-1.5">
              <span className="text-[10px] font-bold text-textLight uppercase tracking-wider">
                Topics
              </span>
              <button
                onClick={() => {
                  setCreateCommunityError(null);
                  setShowCreateCommunityModal(true);
                }}
                className="text-[11px] text-primary hover:text-primary-dark font-semibold flex items-center space-x-0.5 cursor-pointer transition hover:underline"
                title="Create a new community circle"
              >
                <Plus size={12} />
                <span>Create</span>
              </button>
            </div>

            {/* All Discussions Option */}
            <button
              onClick={() => setSelectedChannel(null)}
              className={`w-full text-left px-2.5 py-2 rounded-xl text-xs font-medium transition flex items-center justify-between cursor-pointer ${
                selectedChannel === null
                  ? 'bg-purple-100/90 text-primary font-semibold border-l-2 border-primary'
                  : 'text-textSecondary hover:bg-purple-50/70 hover:text-textPrimary'
              }`}
            >
              <div className="flex items-center space-x-2 truncate">
                <Sparkles size={14} className={selectedChannel === null ? 'text-primary' : 'text-textLight'} />
                <span className="truncate">All Discussions</span>
              </div>
              <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${selectedChannel === null ? 'bg-primary/10 text-primary font-semibold' : 'text-textLight'}`}>
                {posts.length}
              </span>
            </button>

            {/* Topic Channels */}
            {categories.map(cat => {
              const IconComponent = getCategoryIcon(cat);
              const isSelected = selectedChannel === cat.category_id;
              const shortName = CHANNEL_SHORT_NAMES[cat.slug] || cat.name;
              return (
                <button
                  key={cat.category_id}
                  onClick={() => setSelectedChannel(cat.category_id)}
                  className={`w-full text-left px-2.5 py-2 rounded-xl text-xs font-medium transition flex items-center justify-between cursor-pointer ${
                    isSelected
                      ? 'bg-purple-100/90 text-primary font-semibold border-l-2 border-primary'
                      : 'text-textSecondary hover:bg-purple-50/70 hover:text-textPrimary'
                  }`}
                >
                  <div className="flex items-center space-x-2 truncate pr-1">
                    <IconComponent size={14} className={isSelected ? 'text-primary' : 'text-textLight'} />
                    <span className="truncate">{shortName}</span>
                  </div>
                  {cat.post_count > 0 && (
                    <span className={`text-[10px] px-1.5 py-0.5 rounded-full shrink-0 ${isSelected ? 'bg-primary/10 text-primary font-semibold' : 'text-textLight'}`}>
                      {cat.post_count}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </aside>

        {/* Main Feed Column (Max ~760px) */}
        <main className="flex-1 max-w-[760px] min-w-0 w-full space-y-3.5">
          {/* Mobile Topic Channel Scroll Bar */}
          <div className="lg:hidden flex items-center gap-1.5 overflow-x-auto no-scrollbar pb-1">
            <button
              onClick={() => setSelectedChannel(null)}
              className={`px-3 py-1.5 rounded-xl text-xs font-medium whitespace-nowrap transition cursor-pointer flex items-center space-x-1.5 ${
                selectedChannel === null
                  ? 'bg-purple-100 text-purple-900 font-semibold border border-purple-200'
                  : 'bg-white text-textSecondary hover:bg-purple-50 border border-purple-100/80'
              }`}
            >
              <Sparkles size={13} className={selectedChannel === null ? 'text-primary' : 'text-textLight'} />
              <span>All Discussions</span>
            </button>
            {categories.map(cat => {
              const isSelected = selectedChannel === cat.category_id;
              const shortName = CHANNEL_SHORT_NAMES[cat.slug] || cat.name;
              const IconComponent = getCategoryIcon(cat);
              return (
                <button
                  key={cat.category_id}
                  onClick={() => setSelectedChannel(cat.category_id)}
                  className={`px-3 py-1.5 rounded-xl text-xs font-medium whitespace-nowrap transition cursor-pointer flex items-center space-x-1.5 ${
                    isSelected
                      ? 'bg-purple-100 text-purple-900 font-semibold border border-purple-200'
                      : 'bg-white text-textSecondary hover:bg-purple-50 border border-purple-100/80'
                  }`}
                >
                  <IconComponent size={13} className={isSelected ? 'text-primary' : 'text-textLight'} />
                  <span>{shortName}</span>
                </button>
              );
            })}
            <button
              onClick={() => {
                setCreateCommunityError(null);
                setShowCreateCommunityModal(true);
              }}
              className="px-3 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap transition cursor-pointer flex items-center space-x-1.5 bg-purple-50 hover:bg-purple-100 text-primary border border-purple-200"
              title="Create a new community circle"
            >
              <Plus size={13} />
              <span>+ New Circle</span>
            </button>
          </div>

          {/* Compact Post Composer Bar */}
          <div
            onClick={handleOpenComposer}
            className="bg-white rounded-2xl p-3 border border-purple-100/80 shadow-2xs hover:shadow-soft hover:border-purple-200 transition cursor-pointer flex items-center space-x-3 group"
          >
            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm shrink-0 ${myProfile ? getAvatarBadge(myProfile.avatar_key).bg : 'bg-purple-100 text-purple-600'}`}>
              {myProfile ? getAvatarBadge(myProfile.avatar_key).emoji : '🌸'}
            </div>
            <div className="flex-1 text-xs text-textLight group-hover:text-textSecondary transition truncate">
              Share a question or something on your mind…
            </div>
            <button
              type="button"
              className="bg-primary hover:bg-primary-dark text-white text-xs font-semibold px-3.5 py-1.5 rounded-xl shadow-2xs group-hover:shadow-sm transition cursor-pointer shrink-0"
            >
              Write a post
            </button>
          </div>

          {/* Search, Health Label Chips & Sort Controls */}
          <div className="bg-white rounded-2xl p-3 border border-purple-100/80 shadow-2xs space-y-2.5">
            {/* Search Input */}
            <div className="relative">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-textLight" />
              <input
                type="text"
                placeholder="Search discussions, questions, experiences..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-8 py-1.5 rounded-xl bg-purple-50/50 border border-purple-100 text-xs focus:ring-1 focus:ring-primary outline-none transition"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-textLight hover:text-textSecondary cursor-pointer"
                  aria-label="Clear search"
                >
                  <X size={13} />
                </button>
              )}
            </div>

            {/* Health Labels Row & Sorting Filter */}
            <div className="flex flex-wrap items-center justify-between gap-2 pt-0.5">
              <div className="flex items-center space-x-1.5 overflow-x-auto no-scrollbar text-xs">
                {[
                  { key: 'all', label: 'All labels' },
                  { key: 'Personal Experience', label: 'Personal experience' },
                  { key: 'General Discussion', label: 'General discussion' },
                  { key: 'Verified Health Resource', label: 'Verified health resource' }
                ].map(chip => {
                  const isSelected = selectedHealthLabel === chip.key;
                  return (
                    <button
                      key={chip.key}
                      onClick={() => setSelectedHealthLabel(chip.key)}
                      className={`px-2.5 py-1 rounded-full whitespace-nowrap transition text-[11px] font-medium cursor-pointer ${
                        isSelected
                          ? 'bg-purple-100 text-purple-900 font-semibold border border-purple-200'
                          : 'bg-purple-50/60 text-textSecondary hover:bg-purple-100/50 border border-transparent'
                      }`}
                    >
                      {chip.label}
                    </button>
                  );
                })}
              </div>

              <div className="flex items-center space-x-1.5 shrink-0 text-xs">
                <span className="text-[11px] text-textLight">Sort:</span>
                <select
                  value={selectedSort}
                  onChange={(e) => setSelectedSort(e.target.value)}
                  aria-label="Sort discussions"
                  className="bg-transparent text-xs text-textSecondary border border-purple-100 rounded-xl px-2 py-1 outline-none font-medium cursor-pointer focus:ring-1 focus:ring-primary"
                >
                  <option value="newest">Newest</option>
                  <option value="top">Most Supportive</option>
                  <option value="discussed">Most Discussed</option>
                </select>
              </div>
            </div>
          </div>

          {/* Posts Feed List */}
          {loading ? (
            <div className="text-center py-12 space-y-2">
              <div className="w-7 h-7 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto"></div>
              <p className="text-xs text-textLight">Loading discussions...</p>
            </div>
          ) : posts.length === 0 ? (
            <div className="bg-white rounded-2xl p-8 text-center space-y-3 border border-purple-100/80 shadow-2xs">
              <div className="w-10 h-10 rounded-full bg-purple-100 text-primary flex items-center justify-center mx-auto text-lg">
                🌸
              </div>
              <h3 className="text-sm font-semibold text-textPrimary">No discussions found</h3>
              <p className="text-xs text-textSecondary max-w-sm mx-auto">
                {searchQuery || selectedChannel || selectedHealthLabel !== 'all'
                  ? "No posts match your current search or topic filter. Try clearing filters."
                  : "Be the first member to start a supportive discussion in this circle!"}
              </p>
              <button
                onClick={handleOpenComposer}
                className="bg-primary text-white text-xs font-semibold px-4 py-2 rounded-xl cursor-pointer hover:bg-primary-dark transition"
              >
                Write First Post
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              {posts.map(post => {
                const authorBadge = getAvatarBadge(post.author.avatar_key);
                const hasReactedHelpful = post.user_reactions && post.user_reactions.includes('helpful');
                const hasReactedSupport = post.user_reactions && post.user_reactions.includes('support');
                const hasReactedRelatable = post.user_reactions && post.user_reactions.includes('relatable');
                const isExpanded = expandedPostIds.has(post.post_id);
                const isLongBody = (post.body || '').length > 200 || (post.body || '').split('\n').length > 3;
                const channelLabel = CHANNEL_SHORT_NAMES[post.category_slug] || post.category_name;

                return (
                  <article
                    key={post.post_id}
                    className="bg-white rounded-2xl p-4 sm:p-5 border border-purple-100/70 shadow-2xs hover:shadow-soft transition space-y-3 relative"
                  >
                    {/* Header: Avatar, Name, Date, Topic, Health Label, 3-Dot Menu */}
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center space-x-2.5 min-w-0">
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm shrink-0 ${authorBadge.bg}`}>
                          {post.author.is_anonymous ? '🌿' : authorBadge.emoji}
                        </div>
                        <div className="min-w-0">
                          <div className="flex items-center space-x-1.5 flex-wrap">
                            <span className="text-xs font-bold text-textPrimary">
                              {post.author.display_name}
                            </span>
                            {post.author.is_anonymous && (
                              <span className="bg-slate-100 text-slate-600 text-[9px] px-1.5 py-0.2 rounded font-medium">
                                Anonymous
                              </span>
                            )}
                            <span className="text-[10px] text-textLight">•</span>
                            <span className="text-[10px] text-textLight">
                              {formatPostDate(post.created_at)}
                            </span>
                          </div>
                          <span className="text-[10px] font-medium text-primary block truncate">
                            in {channelLabel}
                          </span>
                        </div>
                      </div>

                      {/* Right Header: Label Badge & 3-Dot Menu */}
                      <div className="flex items-center space-x-1.5 shrink-0">
                        {post.is_verified ? (
                          <span className="bg-emerald-50 text-emerald-700 border border-emerald-200 text-[10px] font-semibold px-2 py-0.5 rounded-full flex items-center space-x-1">
                            <CheckCircle2 size={11} className="text-emerald-600" />
                            <span>Verified Resource</span>
                          </span>
                        ) : post.health_label === 'Personal Experience' ? (
                          <span className="bg-purple-50 text-purple-700 border border-purple-200/70 text-[10px] font-medium px-2 py-0.5 rounded-full">
                            Personal Experience
                          </span>
                        ) : (
                          <span className="bg-slate-50 text-slate-600 border border-slate-200/70 text-[10px] font-medium px-2 py-0.5 rounded-full">
                            General Discussion
                          </span>
                        )}

                        {post.is_locked && (
                          <span className="text-amber-600 p-0.5" title="Locked Discussion">
                            <Lock size={12} />
                          </span>
                        )}

                        {/* Three-dot Action Menu */}
                        <div className="relative post-menu-container">
                          <button
                            onClick={() => setActiveMenuPostId(activeMenuPostId === post.post_id ? null : post.post_id)}
                            className="p-1 text-textLight hover:text-textPrimary rounded-lg hover:bg-purple-50 transition cursor-pointer"
                            aria-label="Post options"
                          >
                            <MoreVertical size={14} />
                          </button>

                          {activeMenuPostId === post.post_id && (
                            <div className="absolute right-0 top-7 w-40 bg-white rounded-xl shadow-lg border border-purple-100 py-1 z-30 animate-fade-in text-xs">
                              {post.is_author ? (
                                <>
                                  <button
                                    onClick={() => {
                                      setActiveMenuPostId(null);
                                      setEditingPost(post);
                                      setEditTitle(post.title);
                                      setEditBody(post.body);
                                      setEditCategory(post.category_id);
                                      setEditAnonymous(post.author.is_anonymous);
                                    }}
                                    className="w-full text-left px-3 py-1.5 hover:bg-purple-50 flex items-center space-x-2 text-textPrimary cursor-pointer"
                                  >
                                    <Edit3 size={12} className="text-textLight" />
                                    <span>Edit post</span>
                                  </button>
                                  <button
                                    onClick={() => {
                                      setActiveMenuPostId(null);
                                      handleDeletePost(post.post_id);
                                    }}
                                    className="w-full text-left px-3 py-1.5 hover:bg-rose-50 flex items-center space-x-2 text-rose-600 cursor-pointer"
                                  >
                                    <Trash2 size={12} />
                                    <span>Delete post</span>
                                  </button>
                                </>
                              ) : (
                                <>
                                  <button
                                    onClick={() => {
                                      setActiveMenuPostId(null);
                                      setReportingItem({ type: 'post', id: post.post_id, title: post.title });
                                    }}
                                    className="w-full text-left px-3 py-1.5 hover:bg-rose-50 flex items-center space-x-2 text-rose-600 cursor-pointer"
                                  >
                                    <Flag size={12} />
                                    <span>Report post</span>
                                  </button>
                                  <button
                                    onClick={() => {
                                      setActiveMenuPostId(null);
                                      handleBlockUser(post.author.user_id, post.author.display_name);
                                    }}
                                    className="w-full text-left px-3 py-1.5 hover:bg-purple-50 flex items-center space-x-2 text-textSecondary cursor-pointer"
                                  >
                                    <UserX size={12} />
                                    <span>Block member</span>
                                  </button>
                                </>
                              )}

                              {isModerator && (
                                <div className="border-t border-purple-100/80 my-1 pt-1">
                                  <button
                                    onClick={() => {
                                      setActiveMenuPostId(null);
                                      handleModPostAction(post.post_id, post.is_locked ? 'unlock' : 'lock');
                                    }}
                                    className="w-full text-left px-3 py-1.5 hover:bg-amber-50 flex items-center space-x-2 text-amber-800 cursor-pointer"
                                  >
                                    {post.is_locked ? <Unlock size={12} /> : <Lock size={12} />}
                                    <span>{post.is_locked ? 'Unlock' : 'Lock'}</span>
                                  </button>
                                  <button
                                    onClick={() => {
                                      setActiveMenuPostId(null);
                                      setVerifyingPostId(post.post_id);
                                    }}
                                    className="w-full text-left px-3 py-1.5 hover:bg-emerald-50 flex items-center space-x-2 text-emerald-700 cursor-pointer"
                                  >
                                    <CheckCircle2 size={12} />
                                    <span>Verify resource</span>
                                  </button>
                                  <button
                                    onClick={() => {
                                      setActiveMenuPostId(null);
                                      handleModPostAction(post.post_id, 'remove');
                                    }}
                                    className="w-full text-left px-3 py-1.5 hover:bg-rose-50 flex items-center space-x-2 text-rose-700 cursor-pointer"
                                  >
                                    <Ban size={12} />
                                    <span>Remove (Mod)</span>
                                  </button>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Content: Title & Body with Read More */}
                    <div className="space-y-1.5">
                      <h2
                        onClick={() => openPostDetail(post.post_id)}
                        className="text-sm sm:text-base font-semibold text-textPrimary hover:text-primary transition cursor-pointer leading-snug"
                      >
                        {post.title}
                      </h2>
                      <p className={`text-xs text-textSecondary leading-relaxed whitespace-pre-line ${isExpanded ? '' : 'line-clamp-3'}`}>
                        {post.body}
                      </p>
                      {isLongBody && (
                        <button
                          onClick={() => toggleExpandPost(post.post_id)}
                          className="text-[11px] font-semibold text-primary hover:text-primary-dark transition cursor-pointer pt-0.5"
                        >
                          {isExpanded ? 'Show less' : 'Read more'}
                        </button>
                      )}
                    </div>

                    {/* Verified Resource Citation Reference */}
                    {post.is_verified && post.verification_source_url && (
                      <div className="bg-emerald-50/60 border border-emerald-100 rounded-xl p-2.5 text-[11px] text-emerald-800 space-y-1">
                        <div className="flex items-center justify-between">
                          <span className="font-semibold flex items-center space-x-1">
                            <CheckCircle2 size={12} className="text-emerald-600" />
                            <span>Clinical Reference:</span>
                          </span>
                          <a
                            href={post.verification_source_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-primary hover:underline flex items-center space-x-0.5"
                          >
                            <span>Open Source</span>
                            <ExternalLink size={10} />
                          </a>
                        </div>
                        {post.verification_notes && (
                          <p className="text-[10px] text-emerald-700 italic">
                            Reviewer: "{post.verification_notes}"
                          </p>
                        )}
                      </div>
                    )}

                    {/* Footer: Compact Reactions & Comments */}
                    <div className="pt-2.5 border-t border-purple-100/60 flex items-center justify-between text-xs">
                      {/* Reaction Badges */}
                      <div className="flex items-center space-x-1 sm:space-x-1.5">
                        <button
                          onClick={() => handleToggleReaction(post.post_id, 'helpful')}
                          className={`px-2 py-1 rounded-lg text-[11px] font-medium transition flex items-center space-x-1 cursor-pointer ${
                            hasReactedHelpful
                              ? 'bg-amber-100 text-amber-800 font-semibold'
                              : 'text-textSecondary hover:bg-purple-50'
                          }`}
                          title="Helpful insight"
                        >
                          <span>💡</span>
                          <span className="hidden sm:inline">Helpful</span>
                          {(post.reactions_breakdown?.helpful || 0) > 0 && (
                            <span className="text-[10px] text-textLight font-semibold ml-0.5">
                              {post.reactions_breakdown.helpful}
                            </span>
                          )}
                        </button>

                        <button
                          onClick={() => handleToggleReaction(post.post_id, 'support')}
                          className={`px-2 py-1 rounded-lg text-[11px] font-medium transition flex items-center space-x-1 cursor-pointer ${
                            hasReactedSupport
                              ? 'bg-purple-100 text-primary font-semibold'
                              : 'text-textSecondary hover:bg-purple-50'
                          }`}
                          title="Sending support"
                        >
                          <span>💜</span>
                          <span className="hidden sm:inline">Support</span>
                          {(post.reactions_breakdown?.support || 0) > 0 && (
                            <span className="text-[10px] text-textLight font-semibold ml-0.5">
                              {post.reactions_breakdown.support}
                            </span>
                          )}
                        </button>

                        <button
                          onClick={() => handleToggleReaction(post.post_id, 'relatable')}
                          className={`px-2 py-1 rounded-lg text-[11px] font-medium transition flex items-center space-x-1 cursor-pointer ${
                            hasReactedRelatable
                              ? 'bg-pink-100 text-pink-800 font-semibold'
                              : 'text-textSecondary hover:bg-purple-50'
                          }`}
                          title="Relatable experience"
                        >
                          <span>🌸</span>
                          <span className="hidden sm:inline">Relatable</span>
                          {(post.reactions_breakdown?.relatable || 0) > 0 && (
                            <span className="text-[10px] text-textLight font-semibold ml-0.5">
                              {post.reactions_breakdown.relatable}
                            </span>
                          )}
                        </button>
                      </div>

                      {/* Comments Count */}
                      <button
                        onClick={() => openPostDetail(post.post_id)}
                        className="text-textSecondary hover:text-primary transition flex items-center space-x-1 text-[11px] font-medium px-2 py-1 rounded-lg hover:bg-purple-50 cursor-pointer"
                      >
                        <MessageSquare size={13} className="text-textLight" />
                        <span>{post.comment_count} {post.comment_count === 1 ? 'comment' : 'comments'}</span>
                      </button>
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </main>
      </div>

      {/* ======================================================== */}
      {/* MODAL 0: Community Guidelines & Label Guide Modal */}
      {/* ======================================================== */}
      {showGuidelinesModal && (
        <div className="fixed inset-0 bg-purple-950/20 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-fade-in">
          <div className="bg-white w-full max-w-md rounded-2xl p-6 shadow-xl border border-purple-100 relative max-h-[90vh] overflow-y-auto space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-purple-100">
              <div className="flex items-center space-x-2">
                <HeartHandshake size={18} className="text-primary" />
                <h3 className="text-base font-bold text-textPrimary">Community Guidelines</h3>
              </div>
              <button
                onClick={() => setShowGuidelinesModal(false)}
                className="text-textLight hover:text-textPrimary cursor-pointer p-1 rounded-lg hover:bg-purple-50"
              >
                <X size={18} />
              </button>
            </div>

            <div className="space-y-4 text-xs text-textSecondary leading-relaxed">
              {/* Community Care Pledge */}
              <div className="space-y-2">
                <h4 className="font-semibold text-textPrimary flex items-center space-x-1.5">
                  <Sparkles size={14} className="text-primary" />
                  <span>Community Care Pledge</span>
                </h4>
                <ul className="space-y-1.5 pl-4 list-disc marker:text-primary">
                  <li><strong>Empathy & Kindness:</strong> Every hormonal path is unique. Practice deep empathy and respect.</li>
                  <li><strong>Protect Privacy:</strong> Do not share personal emails, phone numbers, or private lab identifiers. Pseudonyms protect your privacy.</li>
                  <li><strong>Not Medical Advice:</strong> Community discussions reflect individual lived experiences and do not constitute clinical prescriptions. Consult your healthcare provider.</li>
                </ul>
              </div>

              {/* Health Labels Guide */}
              <div className="space-y-2 pt-2 border-t border-purple-100">
                <h4 className="font-semibold text-textPrimary flex items-center space-x-1.5">
                  <Shield size={14} className="text-primary" />
                  <span>Health-Information Content Labels</span>
                </h4>
                <div className="space-y-2 text-[11px]">
                  <div className="p-2.5 rounded-xl bg-purple-50/70 border border-purple-100">
                    <span className="font-semibold text-purple-900">🌸 Personal Experience</span>
                    <p className="text-textSecondary mt-0.5">Author's personal journey. May not apply to every body.</p>
                  </div>
                  <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200">
                    <span className="font-semibold text-slate-800">💬 General Discussion</span>
                    <p className="text-textSecondary mt-0.5">Questions, supportive reflections, lifestyle habits, and peer discussions.</p>
                  </div>
                  <div className="p-2.5 rounded-xl bg-emerald-50 border border-emerald-200">
                    <span className="font-semibold text-emerald-900">✅ Verified Health Resource</span>
                    <p className="text-textSecondary mt-0.5">Vetted by an authorized reviewer with clinical reference links (e.g., PubMed, NIH, ACOG).</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="flex justify-end pt-3 border-t border-purple-100">
              <button
                onClick={() => setShowGuidelinesModal(false)}
                className="bg-primary hover:bg-primary-dark text-white text-xs font-semibold px-4 py-2 rounded-xl transition cursor-pointer"
              >
                Understood
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ======================================================== */}
      {/* MODAL 0B: Create Community Circle Modal */}
      {/* ======================================================== */}
      {showCreateCommunityModal && (
        <div className="fixed inset-0 bg-purple-950/20 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-fade-in">
          <div className="bg-white w-full max-w-md rounded-2xl p-6 shadow-xl border border-purple-100 relative max-h-[90vh] overflow-y-auto space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-purple-100">
              <div className="flex items-center space-x-2.5">
                <div className="p-2 bg-purple-100 text-primary rounded-xl">
                  <Users size={18} />
                </div>
                <div>
                  <h3 className="text-base font-bold text-textPrimary">Create a Community Circle</h3>
                  <p className="text-[11px] text-textSecondary">Start a dedicated space for peer discussions & support</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setShowCreateCommunityModal(false)}
                className="text-textLight hover:text-textPrimary cursor-pointer p-1 rounded-lg hover:bg-purple-50 transition"
              >
                <X size={18} />
              </button>
            </div>

            {createCommunityError && (
              <div className="bg-rose-50 border border-rose-200 text-rose-800 px-3.5 py-2.5 rounded-xl text-xs flex items-center space-x-2 animate-fade-in">
                <AlertTriangle size={15} className="text-rose-500 shrink-0" />
                <span className="font-medium">{createCommunityError}</span>
              </div>
            )}

            <form onSubmit={handleCreateCommunity} className="space-y-4 pt-1">
              <div>
                <label className="block text-[11px] font-semibold text-textSecondary uppercase tracking-wider mb-1.5">
                  Circle Name *
                </label>
                <input
                  type="text"
                  placeholder="e.g. Herbal Remedies, Fertility Journey, Low-GI Recipes..."
                  value={newCommunityName}
                  onChange={(e) => setNewCommunityName(e.target.value)}
                  maxLength={50}
                  className="w-full px-3.5 py-2 rounded-xl border border-purple-100 text-xs focus:ring-1 focus:ring-primary focus:border-primary outline-none transition bg-purple-50/20"
                  required
                />
                <div className="flex justify-between items-center mt-1 text-[10px] text-textLight">
                  <span>Between 3 and 50 characters</span>
                  <span>{newCommunityName.length}/50</span>
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-textSecondary uppercase tracking-wider mb-1.5">
                  Select Theme Icon
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {COMMUNITY_ICON_OPTIONS.map((opt) => {
                    const isSelected = newCommunityIcon === opt.key;
                    return (
                      <button
                        type="button"
                        key={opt.key}
                        onClick={() => setNewCommunityIcon(opt.key)}
                        className={`px-2.5 py-2 rounded-xl text-xs font-medium border transition cursor-pointer flex items-center space-x-1.5 ${
                          isSelected
                            ? 'bg-purple-100 text-purple-900 border-primary shadow-2xs font-semibold'
                            : 'bg-white text-textSecondary hover:bg-purple-50/70 border-purple-100'
                        }`}
                      >
                        <span className="text-base">{opt.emoji}</span>
                        <span className="truncate text-[11px]">{opt.label}</span>
                      </button>
                    );
                  })}
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-textSecondary uppercase tracking-wider mb-1.5">
                  Purpose / About this Circle <span className="text-textLight font-normal">(Optional)</span>
                </label>
                <textarea
                  placeholder="Share what topics members will explore here..."
                  value={newCommunityDescription}
                  onChange={(e) => setNewCommunityDescription(e.target.value)}
                  maxLength={255}
                  rows={3}
                  className="w-full px-3.5 py-2 rounded-xl border border-purple-100 text-xs focus:ring-1 focus:ring-primary focus:border-primary outline-none transition resize-none bg-purple-50/20"
                />
                <div className="text-right text-[10px] text-textLight mt-1">
                  {newCommunityDescription.length}/255
                </div>
              </div>

              <div className="p-2.5 rounded-xl bg-purple-50/70 border border-purple-100 text-[11px] text-textSecondary flex items-start space-x-2">
                <Sparkles size={14} className="text-primary shrink-0 mt-0.5" />
                <span>
                  All community circles are open to OvaCare members and adhere to our shared respect pledge and moderation guidelines.
                </span>
              </div>

              <div className="flex items-center justify-end space-x-2 pt-3 border-t border-purple-100">
                <button
                  type="button"
                  onClick={() => setShowCreateCommunityModal(false)}
                  className="px-3.5 py-2 rounded-xl text-xs text-textSecondary hover:bg-purple-50 font-medium transition cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createCommunitySubmitting || !newCommunityName.trim()}
                  className="bg-primary hover:bg-primary-dark disabled:opacity-50 text-white text-xs font-semibold px-4 py-2 rounded-xl transition cursor-pointer shadow-2xs flex items-center space-x-1.5"
                >
                  {createCommunitySubmitting ? (
                    <>
                      <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                      <span>Creating...</span>
                    </>
                  ) : (
                    <>
                      <Plus size={14} />
                      <span>Create Circle</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ======================================================== */}
      {/* MODAL 1: Post Composer Modal */}
      {/* ======================================================== */}
      {showComposerModal && (
        <div className="fixed inset-0 bg-purple-950/20 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fade-in">
          <div className="glass-panel w-full max-w-lg rounded-3xl p-6 shadow-premium relative max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-3 border-b border-purple-100">
              <div className="flex items-center space-x-2">
                <div className="p-1.5 bg-primary/10 text-primary rounded-xl">
                  <PlusCircle size={18} />
                </div>
                <h3 className="text-base font-bold text-textPrimary">Create Community Post</h3>
              </div>
              <button
                onClick={() => setShowComposerModal(false)}
                className="text-textLight hover:text-textPrimary cursor-pointer"
              >
                <X size={18} />
              </button>
            </div>

            {/* Error banner inside modal */}
            {composerError && (
              <div className="mt-3 bg-rose-50 border border-rose-200 text-rose-800 px-3.5 py-2.5 rounded-xl text-xs flex items-center space-x-2 animate-fade-in">
                <AlertTriangle size={15} className="text-rose-500 shrink-0" />
                <span className="font-medium">{composerError}</span>
              </div>
            )}

            <form onSubmit={handleCreatePost} noValidate className="space-y-4 pt-3">
              {/* Channel Selector */}
              <div>
                <label className="block text-[10px] font-semibold text-textSecondary uppercase tracking-wider mb-1">
                  Topic Channel *
                </label>
                <select
                  value={composerCategory || (categories[0]?.category_id || '')}
                  onChange={(e) => setComposerCategory(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl border border-purple-100 text-xs focus:ring-1 focus:ring-primary outline-none bg-purple-50/50 cursor-pointer"
                >
                  {categories.map(c => (
                    <option key={c.category_id} value={c.category_id}>
                      {CHANNEL_SHORT_NAMES[c.slug] || c.name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Health Label Choice */}
              <div>
                <label className="block text-[10px] font-semibold text-textSecondary uppercase tracking-wider mb-1">
                  Content Label *
                </label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setComposerHealthLabel('Personal Experience')}
                    className={`p-2.5 rounded-xl text-left border text-xs transition cursor-pointer ${
                      composerHealthLabel === 'Personal Experience'
                        ? 'border-primary bg-purple-50 text-primary font-bold'
                        : 'border-purple-100 text-textSecondary hover:bg-purple-50/40'
                    }`}
                  >
                    🌸 Personal Experience
                    <p className="text-[10px] font-normal text-textLight mt-0.5">My individual symptom journey</p>
                  </button>

                  <button
                    type="button"
                    onClick={() => setComposerHealthLabel('General Discussion')}
                    className={`p-2.5 rounded-xl text-left border text-xs transition cursor-pointer ${
                      composerHealthLabel === 'General Discussion'
                        ? 'border-primary bg-purple-50 text-primary font-bold'
                        : 'border-purple-100 text-textSecondary hover:bg-purple-50/40'
                    }`}
                  >
                    💬 General Discussion
                    <p className="text-[10px] font-normal text-textLight mt-0.5">Questions & encouragement</p>
                  </button>
                </div>
                <p className="text-[10px] text-textLight mt-1 italic">
                  Note: The "Verified Health Resource" badge is awarded after clinical reviewer appraisal.
                </p>
              </div>

              {/* Title */}
              <div>
                <div className="flex justify-between items-center mb-1">
                  <label className="block text-[10px] font-semibold text-textSecondary uppercase tracking-wider">
                    Post Title *
                  </label>
                  <span className="text-[10px] text-textLight">{composerTitle.length}/150</span>
                </div>
                <input
                  type="text"
                  placeholder="Summarize your question or experience..."
                  value={composerTitle}
                  onChange={(e) => setComposerTitle(e.target.value)}
                  maxLength={150}
                  className="w-full px-3 py-2 rounded-xl border border-purple-100 text-xs focus:ring-1 focus:ring-primary outline-none"
                />
              </div>

              {/* Body */}
              <div>
                <div className="flex justify-between items-center mb-1">
                  <label className="block text-[10px] font-semibold text-textSecondary uppercase tracking-wider">
                    Post Details *
                  </label>
                  <span className="text-[10px] text-textLight">{composerBody.length}/5000</span>
                </div>
                <textarea
                  placeholder="Share details, context, questions, or supportive tips..."
                  value={composerBody}
                  onChange={(e) => setComposerBody(e.target.value)}
                  rows={5}
                  maxLength={5000}
                  className="w-full px-3 py-2 rounded-xl border border-purple-100 text-xs focus:ring-1 focus:ring-primary outline-none resize-none leading-relaxed"
                />
              </div>

              {/* Anonymous Checkbox */}
              <div className="flex items-center space-x-2 pt-1">
                <input
                  type="checkbox"
                  id="anon_check"
                  checked={composerAnonymous}
                  onChange={(e) => setComposerAnonymous(e.target.checked)}
                  className="rounded text-primary focus:ring-primary w-4 h-4 cursor-pointer"
                />
                <label htmlFor="anon_check" className="text-xs text-textPrimary cursor-pointer font-medium">
                  Post anonymously (hides your public pseudonym from community members)
                </label>
              </div>

              <div className="flex items-center justify-end space-x-3 pt-3 border-t border-purple-100">
                <button
                  type="button"
                  onClick={() => setShowComposerModal(false)}
                  className="px-4 py-2 rounded-xl text-xs text-textSecondary hover:bg-purple-50 font-medium cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleCreatePost}
                  disabled={composerSubmitting}
                  className="bg-primary hover:bg-primary-dark text-white text-xs font-semibold px-5 py-2.5 rounded-xl shadow-soft hover:shadow-premium transition disabled:opacity-50 cursor-pointer"
                >
                  {composerSubmitting ? 'Publishing...' : 'Publish to Community'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ======================================================== */}
      {/* MODAL 2: Full Post Detail & Comments View */}
      {/* ======================================================== */}
      {activePost && (
        <div className="fixed inset-0 bg-purple-950/20 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fade-in">
          <div className="glass-panel w-full max-w-2xl rounded-3xl p-6 shadow-premium relative max-h-[90vh] overflow-y-auto space-y-4">
            {/* Header */}
            <div className="flex items-start justify-between pb-3 border-b border-purple-100">
              <div className="flex items-center space-x-2.5">
                <div className={`w-10 h-10 rounded-2xl flex items-center justify-center text-lg ${getAvatarBadge(activePost.author.avatar_key).bg}`}>
                  {activePost.author.is_anonymous ? '🌿' : getAvatarBadge(activePost.author.avatar_key).emoji}
                </div>
                <div>
                  <div className="flex items-center space-x-1.5">
                    <span className="text-xs font-bold text-textPrimary">{activePost.author.display_name}</span>
                    {activePost.author.is_anonymous && (
                      <span className="bg-slate-100 text-slate-600 text-[9px] px-1.5 py-0.2 rounded font-semibold">Anonymous</span>
                    )}
                  </div>
                  <span className="text-[10px] text-textLight">
                    Posted on {new Date(activePost.created_at).toLocaleDateString()} in {activePost.category_name}
                  </span>
                </div>
              </div>

              <div className="flex items-center space-x-2">
                {activePost.is_verified && (
                  <span className="bg-emerald-50 text-emerald-700 border border-emerald-200 text-[10px] font-bold px-2 py-0.5 rounded-full flex items-center space-x-1">
                    <CheckCircle2 size={11} className="text-emerald-600" />
                    <span>Verified Resource</span>
                  </span>
                )}
                <button
                  onClick={() => setActivePost(null)}
                  className="text-textLight hover:text-textPrimary p-1 cursor-pointer"
                >
                  <X size={18} />
                </button>
              </div>
            </div>

            {/* Post Content */}
            <div className="space-y-2">
              <h2 className="text-base font-bold text-textPrimary">{activePost.title}</h2>
              <p className="text-xs text-textSecondary leading-relaxed whitespace-pre-line">
                {activePost.body}
              </p>
            </div>

            {/* Verified Health Resource Info */}
            {activePost.is_verified && activePost.verification_source_url && (
              <div className="bg-emerald-50/70 border border-emerald-200 rounded-2xl p-3 text-xs text-emerald-900 space-y-1">
                <div className="flex items-center justify-between">
                  <span className="font-bold flex items-center space-x-1.5">
                    <CheckCircle2 size={14} className="text-emerald-600" />
                    <span>Evidence-based Clinical Source:</span>
                  </span>
                  <a
                    href={activePost.verification_source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary font-semibold hover:underline flex items-center space-x-0.5"
                  >
                    <span>View PubMed / Source</span>
                    <ExternalLink size={11} />
                  </a>
                </div>
                {activePost.verification_notes && (
                  <p className="text-[11px] text-emerald-800 italic">
                    Review Summary: {activePost.verification_notes}
                  </p>
                )}
              </div>
            )}

            {/* Reactions Bar */}
            <div className="flex items-center justify-between py-2 border-y border-purple-100 text-xs">
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => handleToggleReaction(activePost.post_id, 'helpful')}
                  className={`px-3 py-1.5 rounded-xl text-xs font-medium transition flex items-center space-x-1 cursor-pointer ${
                    activePost.user_reactions && activePost.user_reactions.includes('helpful')
                      ? 'bg-amber-100 text-amber-800 font-bold border border-amber-200'
                      : 'bg-purple-50 text-textSecondary hover:bg-amber-50'
                  }`}
                >
                  <span>💡 Helpful</span>
                  <span>({activePost.reactions_breakdown?.helpful || 0})</span>
                </button>

                <button
                  onClick={() => handleToggleReaction(activePost.post_id, 'support')}
                  className={`px-3 py-1.5 rounded-xl text-xs font-medium transition flex items-center space-x-1 cursor-pointer ${
                    activePost.user_reactions && activePost.user_reactions.includes('support')
                      ? 'bg-purple-200 text-purple-900 font-bold border border-purple-300'
                      : 'bg-purple-50 text-textSecondary hover:bg-purple-100'
                  }`}
                >
                  <span>💜 Support</span>
                  <span>({activePost.reactions_breakdown?.support || 0})</span>
                </button>

                <button
                  onClick={() => handleToggleReaction(activePost.post_id, 'relatable')}
                  className={`px-3 py-1.5 rounded-xl text-xs font-medium transition flex items-center space-x-1 cursor-pointer ${
                    activePost.user_reactions && activePost.user_reactions.includes('relatable')
                      ? 'bg-pink-100 text-pink-800 font-bold border border-pink-200'
                      : 'bg-purple-50 text-textSecondary hover:bg-pink-50'
                  }`}
                >
                  <span>🌸 Relatable</span>
                  <span>({activePost.reactions_breakdown?.relatable || 0})</span>
                </button>
              </div>

              {!activePost.is_author && (
                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => setReportingItem({ type: 'post', id: activePost.post_id, title: activePost.title })}
                    className="text-textLight hover:text-rose-500 text-[11px] flex items-center space-x-1 cursor-pointer"
                  >
                    <Flag size={12} />
                    <span>Report</span>
                  </button>
                </div>
              )}
            </div>

            {/* Comments Thread Section */}
            <div className="space-y-3 pt-2">
              <h3 className="text-xs font-bold text-textPrimary uppercase tracking-wider flex items-center space-x-1.5">
                <MessageSquare size={13} className="text-primary" />
                <span>Discussion ({comments.length})</span>
              </h3>

              {/* Add Comment Input */}
              {!activePost.is_locked ? (
                <form onSubmit={(e) => handleAddComment(e, null)} className="space-y-2">
                  <div className="relative">
                    <textarea
                      placeholder="Write a supportive reply or ask a follow-up question..."
                      value={commentText}
                      onChange={(e) => setCommentText(e.target.value)}
                      rows={2}
                      maxLength={2000}
                      className="w-full px-3 py-2 rounded-2xl border border-purple-100 text-xs focus:ring-1 focus:ring-primary outline-none resize-none leading-relaxed"
                    />
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <label className="flex items-center space-x-1.5 text-[11px] text-textSecondary cursor-pointer">
                      <input
                        type="checkbox"
                        checked={commentAnonymous}
                        onChange={(e) => setCommentAnonymous(e.target.checked)}
                        className="rounded text-primary focus:ring-primary w-3.5 h-3.5 cursor-pointer"
                      />
                      <span>Reply anonymously</span>
                    </label>

                    <button
                      type="submit"
                      disabled={!commentText.trim()}
                      className="bg-primary hover:bg-primary-dark text-white text-xs font-semibold px-4 py-1.5 rounded-xl shadow-soft transition disabled:opacity-40 flex items-center space-x-1 cursor-pointer"
                    >
                      <Send size={12} />
                      <span>Reply</span>
                    </button>
                  </div>
                </form>
              ) : (
                <div className="bg-amber-50 border border-amber-200 text-amber-800 text-xs p-3 rounded-2xl flex items-center space-x-2">
                  <Lock size={14} className="text-amber-600" />
                  <span>This discussion has been locked by a community moderator. New comments are disabled.</span>
                </div>
              )}

              {/* Comments List */}
              {commentsLoading ? (
                <div className="text-center py-4 text-xs text-textLight">Loading comments...</div>
              ) : comments.length === 0 ? (
                <p className="text-xs text-textLight text-center py-3 italic">
                  No replies yet. Be the first to share encouragement!
                </p>
              ) : (
                <div className="space-y-3 pt-2">
                  {comments.map(c => {
                    const cBadge = getAvatarBadge(c.author.avatar_key);
                    return (
                      <div key={c.comment_id} className="space-y-2">
                        {/* Top Level Comment */}
                        <div className="bg-purple-50/50 rounded-2xl p-3 border border-purple-100/60 space-y-1.5">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center space-x-2">
                              <span className={`w-6 h-6 rounded-lg text-xs flex items-center justify-center ${cBadge.bg}`}>
                                {c.author.is_anonymous ? '🌿' : cBadge.emoji}
                              </span>
                              <span className="text-xs font-bold text-textPrimary">{c.author.display_name}</span>
                              <span className="text-[10px] text-textLight">
                                {new Date(c.created_at).toLocaleDateString()}
                              </span>
                            </div>

                            <div className="flex items-center space-x-2 text-[11px]">
                              {!activePost.is_locked && (
                                <button
                                  onClick={() => setReplyingToCommentId(replyingToCommentId === c.comment_id ? null : c.comment_id)}
                                  className="text-primary hover:underline font-medium cursor-pointer"
                                >
                                  Reply
                                </button>
                              )}
                              {(c.is_author || isModerator) && (
                                <button
                                  onClick={() => handleDeleteComment(c.comment_id)}
                                  className="text-textLight hover:text-rose-500 cursor-pointer"
                                  title="Delete comment"
                                >
                                  <Trash2 size={11} />
                                </button>
                              )}
                              {!c.is_author && (
                                <button
                                  onClick={() => setReportingItem({ type: 'comment', id: c.comment_id })}
                                  className="text-textLight hover:text-rose-500 cursor-pointer"
                                  title="Report comment"
                                >
                                  <Flag size={11} />
                                </button>
                              )}
                            </div>
                          </div>

                          <p className="text-xs text-textSecondary whitespace-pre-line leading-relaxed pl-8">
                            {c.body}
                          </p>
                        </div>

                        {/* Nested Replies */}
                        {c.replies && c.replies.length > 0 && (
                          <div className="pl-6 space-y-2 border-l-2 border-purple-100 ml-3">
                            {c.replies.map(r => {
                              const rBadge = getAvatarBadge(r.author.avatar_key);
                              return (
                                <div key={r.comment_id} className="bg-white/80 rounded-2xl p-2.5 border border-purple-100/60 space-y-1">
                                  <div className="flex items-center justify-between">
                                    <div className="flex items-center space-x-1.5">
                                      <span className={`w-5 h-5 rounded-lg text-xs flex items-center justify-center ${rBadge.bg}`}>
                                        {r.author.is_anonymous ? '🌿' : rBadge.emoji}
                                      </span>
                                      <span className="text-xs font-bold text-textPrimary">{r.author.display_name}</span>
                                      <span className="text-[10px] text-textLight">
                                        {new Date(r.created_at).toLocaleDateString()}
                                      </span>
                                    </div>
                                    {(r.is_author || isModerator) && (
                                      <button
                                        onClick={() => handleDeleteComment(r.comment_id)}
                                        className="text-textLight hover:text-rose-500 cursor-pointer"
                                      >
                                        <Trash2 size={11} />
                                      </button>
                                    )}
                                  </div>
                                  <p className="text-xs text-textSecondary whitespace-pre-line pl-6">
                                    {r.body}
                                  </p>
                                </div>
                              );
                            })}
                          </div>
                        )}

                        {/* Inline Reply Box for this Comment */}
                        {replyingToCommentId === c.comment_id && !activePost.is_locked && (
                          <form
                            onSubmit={(e) => handleAddComment(e, c.comment_id)}
                            className="pl-6 space-y-2 border-l-2 border-primary ml-3 pt-1"
                          >
                            <input
                              type="text"
                              placeholder={`Reply to ${c.author.display_name}...`}
                              value={replyText}
                              onChange={(e) => setReplyText(e.target.value)}
                              className="w-full px-3 py-1.5 rounded-xl border border-purple-200 text-xs focus:ring-1 focus:ring-primary outline-none"
                              autoFocus
                            />
                            <div className="flex items-center justify-end space-x-2">
                              <button
                                type="button"
                                onClick={() => setReplyingToCommentId(null)}
                                className="text-[11px] text-textLight hover:text-textSecondary px-2 py-1 cursor-pointer"
                              >
                                Cancel
                              </button>
                              <button
                                type="submit"
                                disabled={!replyText.trim()}
                                className="bg-primary text-white text-[11px] font-semibold px-3 py-1 rounded-lg cursor-pointer"
                              >
                                Send Reply
                              </button>
                            </div>
                          </form>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ======================================================== */}
      {/* MODAL 3: Pseudonymous Profile Settings Modal */}
      {/* ======================================================== */}
      {showProfileModal && (
        <div className="fixed inset-0 bg-purple-950/20 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fade-in">
          <div className="glass-panel w-full max-w-md rounded-3xl p-6 shadow-premium relative">
            <div className="flex items-center justify-between pb-3 border-b border-purple-100">
              <h3 className="text-base font-bold text-textPrimary">Configure Pseudonymous Profile</h3>
              <button onClick={() => setShowProfileModal(false)} className="text-textLight hover:text-textPrimary cursor-pointer">
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleSaveProfile} className="space-y-4 pt-4">
              <p className="text-xs text-textSecondary">
                Your pseudonymous profile protects your privacy. Your real name, email, and private cycle logs are never displayed to the community.
              </p>

              {/* Avatar Selector Grid */}
              <div>
                <label className="block text-[10px] font-semibold text-textSecondary uppercase tracking-wider mb-2">
                  Select Safe Avatar Icon
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {AVATAR_OPTIONS.map(a => (
                    <button
                      key={a.key}
                      type="button"
                      onClick={() => setEditAvatarKey(a.key)}
                      className={`p-2.5 rounded-2xl flex flex-col items-center space-y-1 border transition cursor-pointer ${
                        editAvatarKey === a.key
                          ? 'border-primary bg-purple-100/70 shadow-sm'
                          : 'border-purple-100 hover:bg-purple-50'
                      }`}
                    >
                      <span className="text-2xl">{a.emoji}</span>
                      <span className="text-[10px] font-medium text-textPrimary text-center">{a.label}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Display Name Input */}
              <div>
                <label className="block text-[10px] font-semibold text-textSecondary uppercase tracking-wider mb-1">
                  Public Display Pseudonym *
                </label>
                <input
                  type="text"
                  value={editDisplayName}
                  onChange={(e) => setEditDisplayName(e.target.value)}
                  maxLength={30}
                  placeholder="e.g. Lavender_Warrior or Gentle_Ova"
                  className="w-full px-3 py-2 rounded-xl border border-purple-100 text-xs focus:ring-1 focus:ring-primary outline-none"
                  required
                />
                <span className="text-[10px] text-textLight">Letters, numbers, underscores, and hyphens (3-30 chars).</span>
              </div>

              {/* Bio Input */}
              <div>
                <label className="block text-[10px] font-semibold text-textSecondary uppercase tracking-wider mb-1">
                  Short Bio (Optional)
                </label>
                <textarea
                  value={editBio}
                  onChange={(e) => setEditBio(e.target.value)}
                  maxLength={300}
                  rows={2}
                  placeholder="Share a short note about your goals or favorite self-care ritual..."
                  className="w-full px-3 py-2 rounded-xl border border-purple-100 text-xs focus:ring-1 focus:ring-primary outline-none resize-none"
                />
              </div>

              <div className="flex items-center justify-end space-x-3 pt-3 border-t border-purple-100">
                <button
                  type="button"
                  onClick={() => setShowProfileModal(false)}
                  className="px-4 py-2 rounded-xl text-xs text-textSecondary hover:bg-purple-50 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={profileSaving}
                  className="bg-primary hover:bg-primary-dark text-white text-xs font-semibold px-5 py-2 rounded-xl shadow-soft transition disabled:opacity-50 cursor-pointer"
                >
                  {profileSaving ? 'Saving...' : 'Save Profile'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ======================================================== */}
      {/* MODAL 3.5: Edit Post Modal */}
      {/* ======================================================== */}
      {editingPost && (
        <div className="fixed inset-0 bg-purple-950/20 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fade-in">
          <div className="bg-white w-full max-w-lg rounded-2xl p-6 shadow-xl border border-purple-100 relative max-h-[90vh] overflow-y-auto space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-purple-100">
              <div className="flex items-center space-x-2">
                <Edit3 size={18} className="text-primary" />
                <h3 className="text-base font-bold text-textPrimary">Edit Discussion Post</h3>
              </div>
              <button
                onClick={() => setEditingPost(null)}
                className="text-textLight hover:text-textPrimary cursor-pointer p-1 rounded-lg hover:bg-purple-50"
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleUpdatePost} className="space-y-4">
              <div>
                <label className="block text-[10px] font-semibold text-textSecondary uppercase tracking-wider mb-1">
                  Topic Channel *
                </label>
                <select
                  value={editCategory}
                  onChange={(e) => setEditCategory(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl border border-purple-100 text-xs focus:ring-1 focus:ring-primary outline-none bg-purple-50/50 cursor-pointer"
                >
                  {categories.map(c => (
                    <option key={c.category_id} value={c.category_id}>
                      {CHANNEL_SHORT_NAMES[c.slug] || c.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <div className="flex justify-between items-center mb-1">
                  <label className="block text-[10px] font-semibold text-textSecondary uppercase tracking-wider">
                    Post Title *
                  </label>
                  <span className="text-[10px] text-textLight">{editTitle.length}/150</span>
                </div>
                <input
                  type="text"
                  value={editTitle}
                  onChange={(e) => setEditTitle(e.target.value)}
                  maxLength={150}
                  className="w-full px-3 py-2 rounded-xl border border-purple-100 text-xs focus:ring-1 focus:ring-primary outline-none"
                  required
                />
              </div>

              <div>
                <div className="flex justify-between items-center mb-1">
                  <label className="block text-[10px] font-semibold text-textSecondary uppercase tracking-wider">
                    Post Details *
                  </label>
                  <span className="text-[10px] text-textLight">{editBody.length}/5000</span>
                </div>
                <textarea
                  value={editBody}
                  onChange={(e) => setEditBody(e.target.value)}
                  rows={5}
                  maxLength={5000}
                  className="w-full px-3 py-2 rounded-xl border border-purple-100 text-xs focus:ring-1 focus:ring-primary outline-none resize-none leading-relaxed"
                  required
                />
              </div>

              <div className="flex items-center space-x-2 pt-1">
                <input
                  type="checkbox"
                  id="edit_anon_check"
                  checked={editAnonymous}
                  onChange={(e) => setEditAnonymous(e.target.checked)}
                  className="rounded text-primary focus:ring-primary w-4 h-4 cursor-pointer"
                />
                <label htmlFor="edit_anon_check" className="text-xs text-textPrimary cursor-pointer font-medium">
                  Post anonymously
                </label>
              </div>

              <div className="flex items-center justify-end space-x-3 pt-3 border-t border-purple-100">
                <button
                  type="button"
                  onClick={() => setEditingPost(null)}
                  className="px-4 py-2 rounded-xl text-xs text-textSecondary hover:bg-purple-50 font-medium cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="bg-primary hover:bg-primary-dark text-white text-xs font-semibold px-5 py-2 rounded-xl shadow-soft hover:shadow-premium transition cursor-pointer"
                >
                  Save Changes
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ======================================================== */}
      {/* MODAL 4: Report Content Modal */}
      {/* ======================================================== */}
      {reportingItem && (
        <div className="fixed inset-0 bg-purple-950/20 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fade-in">
          <div className="glass-panel w-full max-w-md rounded-3xl p-6 shadow-premium relative">
            <div className="flex items-center justify-between pb-3 border-b border-purple-100">
              <div className="flex items-center space-x-2 text-rose-600">
                <Flag size={18} />
                <h3 className="text-base font-bold text-textPrimary">Report {reportingItem.type}</h3>
              </div>
              <button onClick={() => setReportingItem(null)} className="text-textLight hover:text-textPrimary cursor-pointer">
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleSubmitReport} className="space-y-4 pt-4">
              <p className="text-xs text-textSecondary">
                Our moderator team takes safety and compassionate discourse seriously. Please indicate why this content violates community guidelines:
              </p>

              <div>
                <label className="block text-[10px] font-semibold text-textSecondary uppercase tracking-wider mb-2">
                  Reason for Reporting *
                </label>
                <div className="space-y-1.5">
                  {[
                    'Harassment or bullying',
                    'Misinformation or unsafe medical advice',
                    'Spam or scams',
                    'Privacy violation',
                    'Inappropriate content',
                    'Other'
                  ].map(r => (
                    <label
                      key={r}
                      className="flex items-center space-x-2.5 p-2 rounded-xl border border-purple-50 hover:bg-purple-50/50 cursor-pointer text-xs"
                    >
                      <input
                        type="radio"
                        name="report_reason"
                        value={r}
                        checked={reportReason === r}
                        onChange={(e) => setReportReason(e.target.value)}
                        className="text-primary focus:ring-primary"
                      />
                      <span className="text-textPrimary font-medium">{r}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-[10px] font-semibold text-textSecondary uppercase tracking-wider mb-1">
                  Additional Context (Optional)
                </label>
                <textarea
                  value={reportExplanation}
                  onChange={(e) => setReportExplanation(e.target.value)}
                  maxLength={1000}
                  rows={2}
                  placeholder="Help the review team understand what made this unsafe..."
                  className="w-full px-3 py-2 rounded-xl border border-purple-100 text-xs focus:ring-1 focus:ring-primary outline-none resize-none"
                />
              </div>

              <div className="flex items-center justify-end space-x-3 pt-2 border-t border-purple-100">
                <button
                  type="button"
                  onClick={() => setReportingItem(null)}
                  className="px-4 py-2 rounded-xl text-xs text-textSecondary hover:bg-purple-50 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={reportSubmitting}
                  className="bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold px-5 py-2 rounded-xl shadow-soft transition disabled:opacity-50 cursor-pointer"
                >
                  {reportSubmitting ? 'Submitting...' : 'Submit Report'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ======================================================== */}
      {/* MODAL 5: Blocked Members List */}
      {/* ======================================================== */}
      {showBlockedModal && (
        <div className="fixed inset-0 bg-purple-950/20 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fade-in">
          <div className="glass-panel w-full max-w-md rounded-3xl p-6 shadow-premium relative space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-purple-100">
              <div className="flex items-center space-x-2">
                <UserX size={18} className="text-primary" />
                <h3 className="text-base font-bold text-textPrimary">Manage Blocked Members</h3>
              </div>
              <button onClick={() => setShowBlockedModal(false)} className="text-textLight hover:text-textPrimary cursor-pointer">
                <X size={18} />
              </button>
            </div>

            <p className="text-xs text-textSecondary">
              Blocked members cannot see your discussions and their posts/replies are hidden from your feed.
            </p>

            {blockedUsers.length === 0 ? (
              <p className="text-xs text-textLight text-center py-6 italic">
                You have not blocked any members.
              </p>
            ) : (
              <div className="space-y-2 max-h-60 overflow-y-auto">
                {blockedUsers.map(b => (
                  <div key={b.blocked_user_id} className="flex items-center justify-between p-2.5 rounded-2xl bg-purple-50/60 border border-purple-100 text-xs">
                    <div className="flex items-center space-x-2">
                      <span className="text-base">{getAvatarBadge(b.avatar_key).emoji}</span>
                      <span className="font-semibold text-textPrimary">{b.display_name}</span>
                    </div>
                    <button
                      onClick={() => handleUnblockUser(b.blocked_user_id)}
                      className="text-primary hover:underline font-medium text-[11px] cursor-pointer"
                    >
                      Unblock
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ======================================================== */}
      {/* MODAL 6: Moderator Portal Console */}
      {/* ======================================================== */}
      {showModModal && isModerator && (
        <div className="fixed inset-0 bg-purple-950/30 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fade-in">
          <div className="glass-panel w-full max-w-4xl rounded-3xl p-6 shadow-premium relative max-h-[90vh] overflow-y-auto space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-purple-100">
              <div className="flex items-center space-x-2">
                <Shield size={20} className="text-amber-600" />
                <h3 className="text-base font-bold text-textPrimary">OvaCare Community Moderation Portal</h3>
              </div>
              <button onClick={() => setShowModModal(false)} className="text-textLight hover:text-textPrimary cursor-pointer">
                <X size={18} />
              </button>
            </div>

            {/* Metric Overview Counters */}
            {modStats && (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3 rounded-2xl bg-amber-50 border border-amber-200">
                  <span className="text-[10px] font-bold text-amber-800 uppercase">Pending Reports</span>
                  <p className="text-xl font-bold text-amber-900 mt-1">{modStats.pending_reports}</p>
                </div>
                <div className="p-3 rounded-2xl bg-purple-50 border border-purple-200">
                  <span className="text-[10px] font-bold text-purple-800 uppercase">Total Active Posts</span>
                  <p className="text-xl font-bold text-purple-900 mt-1">{modStats.total_posts}</p>
                </div>
                <div className="p-3 rounded-2xl bg-emerald-50 border border-emerald-200">
                  <span className="text-[10px] font-bold text-emerald-800 uppercase">Verified Resources</span>
                  <p className="text-xl font-bold text-emerald-900 mt-1">{modStats.verified_posts}</p>
                </div>
                <div className="p-3 rounded-2xl bg-rose-50 border border-rose-200">
                  <span className="text-[10px] font-bold text-rose-800 uppercase">Active Restrictions</span>
                  <p className="text-xl font-bold text-rose-900 mt-1">{modStats.active_restrictions}</p>
                </div>
              </div>
            )}

            {/* Mod Tabs */}
            <div className="flex items-center space-x-2 border-b border-purple-100 pb-2">
              <button
                onClick={() => setModTab('reports')}
                className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition cursor-pointer ${
                  modTab === 'reports' ? 'bg-primary text-white' : 'text-textSecondary hover:bg-purple-50'
                }`}
              >
                Review Reports ({modReports.length})
              </button>
              <button
                onClick={() => setModTab('logs')}
                className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition cursor-pointer ${
                  modTab === 'logs' ? 'bg-primary text-white' : 'text-textSecondary hover:bg-purple-50'
                }`}
              >
                Audit Trail Log
              </button>
            </div>

            {/* Tab 1: Reports Queue */}
            {modTab === 'reports' && (
              <div className="space-y-3">
                {modReports.length === 0 ? (
                  <p className="text-xs text-textLight text-center py-6 italic">
                    All clear! No pending reports at this time.
                  </p>
                ) : (
                  modReports.map(rep => (
                    <div key={rep.report_id} className="p-3.5 rounded-2xl bg-purple-50/60 border border-purple-100 space-y-2 text-xs">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-rose-700 bg-rose-50 border border-rose-200 px-2 py-0.5 rounded-full text-[10px]">
                          {rep.reason}
                        </span>
                        <span className="text-[10px] text-textLight">
                          Reported on {new Date(rep.created_at).toLocaleDateString()}
                        </span>
                      </div>

                      {rep.context && (
                        <div className="p-2.5 rounded-xl bg-white/80 border border-purple-100">
                          {rep.content_type === 'post' && (
                            <h4 className="font-bold text-textPrimary text-xs mb-1">{rep.context.title}</h4>
                          )}
                          <p className="text-textSecondary text-[11px] italic">"{rep.context.body}"</p>
                        </div>
                      )}

                      {rep.explanation && (
                        <p className="text-[11px] text-textSecondary">
                          <strong>Reporter Note:</strong> {rep.explanation}
                        </p>
                      )}

                      <div className="flex items-center justify-end space-x-2 pt-2 border-t border-purple-100">
                        {rep.content_type === 'post' && (
                          <button
                            onClick={() => handleModPostAction(rep.content_id, 'remove')}
                            className="bg-rose-100 text-rose-700 hover:bg-rose-200 px-2.5 py-1 rounded-xl text-[11px] font-semibold cursor-pointer"
                          >
                            Remove Post
                          </button>
                        )}
                        <button
                          onClick={() => handleResolveReport(rep.report_id, 'dismissed')}
                          className="text-textSecondary hover:bg-purple-100 px-2.5 py-1 rounded-xl text-[11px] cursor-pointer"
                        >
                          Dismiss
                        </button>
                        <button
                          onClick={() => handleResolveReport(rep.report_id, 'resolved')}
                          className="bg-emerald-600 hover:bg-emerald-700 text-white px-3 py-1 rounded-xl text-[11px] font-semibold cursor-pointer"
                        >
                          Mark Resolved
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}

            {/* Tab 2: Audit Logs */}
            {modTab === 'logs' && (
              <div className="space-y-2 max-h-72 overflow-y-auto">
                {modLogs.length === 0 ? (
                  <p className="text-xs text-textLight text-center py-4">No audit logs recorded yet.</p>
                ) : (
                  modLogs.map(log => (
                    <div key={log.log_id} className="p-2.5 rounded-xl bg-purple-50/50 border border-purple-100 text-xs flex items-start justify-between">
                      <div className="space-y-0.5">
                        <span className="font-bold text-textPrimary">{log.action}</span>
                        <span className="text-[10px] text-textSecondary block">Target ID: {log.target_id} ({log.target_type})</span>
                        <p className="text-[11px] text-textSecondary italic">{log.reason}</p>
                      </div>
                      <span className="text-[10px] text-textLight shrink-0">
                        {new Date(log.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ======================================================== */}
      {/* MODAL 7: Health Verification Input Modal (Moderator) */}
      {/* ======================================================== */}
      {verifyingPostId && isModerator && (
        <div className="fixed inset-0 bg-purple-950/25 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fade-in">
          <div className="glass-panel w-full max-w-md rounded-3xl p-6 shadow-premium relative space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-purple-100">
              <h3 className="text-sm font-bold text-textPrimary flex items-center space-x-1.5">
                <CheckCircle2 size={16} className="text-emerald-600" />
                <span>Appraise Verified Health Resource</span>
              </h3>
              <button onClick={() => setVerifyingPostId(null)} className="text-textLight hover:text-textPrimary cursor-pointer">
                <X size={16} />
              </button>
            </div>

            <form onSubmit={handleVerifyPost} className="space-y-3 pt-2">
              <div>
                <label className="block text-[10px] font-semibold text-textSecondary uppercase tracking-wider mb-1">
                  Trusted Clinical Reference URL *
                </label>
                <input
                  type="url"
                  placeholder="https://www.ncbi.nlm.nih.gov/... or PubMed source"
                  value={verifySourceUrl}
                  onChange={(e) => setVerifySourceUrl(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl border border-purple-100 text-xs focus:ring-1 focus:ring-primary outline-none"
                  required
                />
              </div>

              <div>
                <label className="block text-[10px] font-semibold text-textSecondary uppercase tracking-wider mb-1">
                  Reviewer Notes *
                </label>
                <textarea
                  placeholder="Summary of peer-reviewed clinical guidelines or validation criteria..."
                  value={verifyNotes}
                  onChange={(e) => setVerifyNotes(e.target.value)}
                  rows={3}
                  className="w-full px-3 py-2 rounded-xl border border-purple-100 text-xs focus:ring-1 focus:ring-primary outline-none resize-none"
                  required
                />
              </div>

              <div className="flex items-center justify-end space-x-2 pt-2 border-t border-purple-100">
                <button
                  type="button"
                  onClick={() => setVerifyingPostId(null)}
                  className="px-3 py-1.5 rounded-xl text-xs text-textSecondary hover:bg-purple-50 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold px-4 py-1.5 rounded-xl cursor-pointer"
                >
                  Confirm Verification Badge
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
