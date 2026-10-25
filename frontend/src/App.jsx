import React, { useState, useEffect } from 'react';
import {
  Home,
  Calendar as CalendarIcon,
  Heart,
  BarChart2,
  User,
  Clock,
  Plus,
  Trash2,
  Check,
  AlertCircle,
  Sparkles,
  Users,
  Settings,
  Database,
  ArrowRight,
  LogOut,
  Bell,
  MessageSquare,
  Info,
  ChevronDown,
  ChevronUp,
  HelpCircle,
  CheckCircle2,
  Droplets,
  Activity,
  Flame,
  Zap,
  FileText,
  Edit3,
  Award,
  TrendingUp,
  Printer,
  Download
} from 'lucide-react';
import Community from './components/Community';
import Companion from './components/Companion';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
} from 'chart.js';
import { Bar, Line, Doughnut } from 'react-chartjs-2';

// Register ChartJS elements
ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  Title,
  Tooltip,
  Legend,
  ArcElement
);

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api';

function App() {
  // Navigation & Auth States
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('ovacare_user');
    return saved ? JSON.parse(saved) : null;
  });
  const [token, setToken] = useState(() => {
    return localStorage.getItem('ovacare_token') || null;
  });
  const [activeTab, setActiveTab] = useState('dashboard');
  
  // Data States
  const [cycles, setCycles] = useState([]);
  const [prediction, setPrediction] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [reminders, setReminders] = useState([]);
  const [logs, setLogs] = useState([]);
  const [adminStats, setAdminStats] = useState(null);
  
  // UI Control States
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);
  
  // Login/Registration Form States
  const [authMode, setAuthMode] = useState('login'); // 'login' | 'register'
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [username, setUsername] = useState('');
  const [age, setAge] = useState('');
  const [lifestyle, setLifestyle] = useState('Moderate');
  const [hasPcos, setHasPcos] = useState(false);

  // Logging Form States
  const [logDate, setLogDate] = useState(new Date().toISOString().split('T')[0]);
  const [logMood, setLogMood] = useState('Calm');
  const [logStress, setLogStress] = useState('Low');
  const [logSleep, setLogSleep] = useState(7);
  const [logCramps, setLogCramps] = useState('');
  const [logFatigue, setLogFatigue] = useState('');
  const [logFlow, setLogFlow] = useState('');
  const [logEnergy, setLogEnergy] = useState('');
  const [logNotes, setLogNotes] = useState('');
  const [editingLogId, setEditingLogId] = useState(null);
  const [logSaving, setLogSaving] = useState(false);

  // Cycle Modal/Form States
  const [cycleStartDate, setCycleStartDate] = useState(new Date().toISOString().split('T')[0]);
  const [cycleEndDate, setCycleEndDate] = useState('');
  const [showCycleModal, setShowCycleModal] = useState(false);

  // Cycle Gap Clarification Modal States
  const [clarifyCycleId, setClarifyCycleId] = useState(null);
  const [clarifyOption, setClarifyOption] = useState('forgotten_entry');
  const [showClarifyModal, setShowClarifyModal] = useState(false);
  const [clarifyingLoading, setClarifyingLoading] = useState(false);
  const [showExplainableDetails, setShowExplainableDetails] = useState(false);

  // Doctor Summary Modal States
  const [showDoctorModal, setShowDoctorModal] = useState(false);
  const [doctorSummaryData, setDoctorSummaryData] = useState(null);
  const [doctorSummaryLoading, setDoctorSummaryLoading] = useState(false);

  // Reminder Form States
  const [reminderType, setReminderType] = useState('Hydration');
  const [reminderDate, setReminderDate] = useState(new Date().toISOString().split('T')[0]);
  
  // Calendar Navigation State
  const [calendarYear, setCalendarYear] = useState(new Date().getFullYear());
  const [calendarMonth, setCalendarMonth] = useState(new Date().getMonth());

  // Show Toast Message Helper
  const triggerToast = (msg, isError = false) => {
    if (isError) {
      setError(msg);
      setTimeout(() => setError(null), 4000);
    } else {
      setSuccessMsg(msg);
      setTimeout(() => setSuccessMsg(null), 4000);
    }
  };

  // Authenticated Fetch Helper
  const authFetch = async (url, options = {}) => {
    const savedToken = token || localStorage.getItem('ovacare_token');
    const headers = {
      'Content-Type': 'application/json',
      ...(savedToken ? { 'Authorization': `Bearer ${savedToken}` } : {}),
      ...options.headers
    };
    const res = await fetch(url, { ...options, headers });
    if (res.status === 401) {
      handleLogout();
      triggerToast("Session expired. Please log in again.", true);
    }
    return res;
  };

  // Populate Form Fields For Selected Date
  const populateFormForDate = (dateStr, logsList = logs) => {
    setLogDate(dateStr);
    const existing = (logsList || []).find(l => l.date === dateStr);
    if (existing) {
      setLogMood(existing.mood || 'Calm');
      setLogStress(existing.stress || 'Low');
      setLogSleep(existing.sleep_hours !== null && existing.sleep_hours !== undefined ? existing.sleep_hours : 7);
      setLogCramps(existing.cramps !== null && existing.cramps !== undefined ? existing.cramps : '');
      setLogFatigue(existing.fatigue !== null && existing.fatigue !== undefined ? existing.fatigue : '');
      setLogFlow(existing.flow !== null && existing.flow !== undefined ? existing.flow : '');
      setLogEnergy(existing.energy_level || '');
      setLogNotes(existing.notes || '');
      setEditingLogId(existing.log_id || null);
    } else {
      setLogMood('Calm');
      setLogStress('Low');
      setLogSleep(7);
      setLogCramps('');
      setLogFatigue('');
      setLogFlow('');
      setLogEnergy('');
      setLogNotes('');
      setEditingLogId(null);
    }
  };

  // Fetch core data for active user
  const fetchUserData = async () => {
    const activeToken = token || localStorage.getItem('ovacare_token');
    if (!activeToken) return;
    setLoading(true);
    try {
      // 1. Fetch Cycles
      const cyclesRes = await authFetch(`${API_BASE}/cycles`);
      if (cyclesRes.ok) {
        const data = await cyclesRes.json();
        setCycles(data);
      }
      
      // 2. Fetch Prediction
      const predRes = await authFetch(`${API_BASE}/predictions`);
      if (predRes.ok) {
        const data = await predRes.json();
        setPrediction(data);
      }
      
      // 3. Fetch Analytics
      const analyticsRes = await authFetch(`${API_BASE}/analytics`);
      if (analyticsRes.ok) {
        const data = await analyticsRes.json();
        setAnalytics(data);
      }
      
      // 4. Fetch Reminders
      const remindersRes = await authFetch(`${API_BASE}/reminders`);
      if (remindersRes.ok) {
        const data = await remindersRes.json();
        setReminders(data);
      }

      // 5. Fetch recent wellness logs
      const logsRes = await authFetch(`${API_BASE}/logs`);
      if (logsRes.ok) {
        const data = await logsRes.json();
        setLogs(data);
        const currentDate = logDate || new Date().toISOString().split('T')[0];
        populateFormForDate(currentDate, data);
      }
    } catch (err) {
      console.error("Error loading user data:", err);
      triggerToast("Connection failed. Check backend status.", true);
    } finally {
      setLoading(false);
    }
  };

  // Fetch Admin Stats
  const fetchAdminStats = async () => {
    try {
      const statsRes = await authFetch(`${API_BASE}/admin/stats`);
      if (statsRes.ok) {
        const data = await statsRes.json();
        setAdminStats(data);
      }
    } catch (err) {
      console.error("Error loading admin stats:", err);
    }
  };

  // Trigger data load on user/tab changes
  useEffect(() => {
    if (user && (token || localStorage.getItem('ovacare_token'))) {
      fetchUserData();
      if (activeTab === 'admin') {
        fetchAdminStats();
      }
    }
  }, [user, token, activeTab]);

  // Auth Handlers
  const handleLogin = async (e) => {
    e.preventDefault();
    if (!email || !password) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });
      const data = await res.json();
      if (!res.ok) {
        triggerToast(data.error || "Login failed", true);
      } else {
        setUser(data.user);
        setToken(data.token);
        localStorage.setItem('ovacare_user', JSON.stringify(data.user));
        localStorage.setItem('ovacare_token', data.token);
        triggerToast(`Welcome back, ${data.user.username}!`);
      }
    } catch (err) {
      triggerToast("Backend server not responding. Run the backend or check connections.", true);
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    if (!username || !email || !password) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username,
          email,
          password,
          age: age ? parseInt(age) : null,
          lifestyle,
          has_pcos: hasPcos
        })
      });
      const data = await res.json();
      if (!res.ok) {
        triggerToast(data.error || "Registration failed", true);
      } else {
        setUser(data.user);
        setToken(data.token);
        localStorage.setItem('ovacare_user', JSON.stringify(data.user));
        localStorage.setItem('ovacare_token', data.token);
        triggerToast("Account created successfully!");
      }
    } catch (err) {
      triggerToast("Backend connection error.", true);
    } finally {
      setLoading(false);
    }
  };

  // Dedicated Demo Mode Handler (Task A)
  const handleDemoMode = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/auth/demo`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      const data = await res.json();
      if (res.ok) {
        setUser(data.user);
        setToken(data.token);
        localStorage.setItem('ovacare_user', JSON.stringify(data.user));
        localStorage.setItem('ovacare_token', data.token);
        triggerToast(`Demo Mode active as ${data.user.username}!`);
      } else {
        triggerToast(data.error || "Demo mode not available", true);
      }
    } catch (err) {
      triggerToast("Failed to initiate Demo Mode. Is backend running?", true);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    setUser(null);
    setToken(null);
    localStorage.removeItem('ovacare_user');
    localStorage.removeItem('ovacare_token');
    setCycles([]);
    setPrediction(null);
    setAnalytics(null);
    setReminders([]);
    setLogs([]);
    setAdminStats(null);
    setLogEnergy('');
    setLogNotes('');
    setEditingLogId(null);
    setLogSaving(false);
    triggerToast("Logged out successfully");
  };

  // Save or Update Daily Wellness Log
  const handleSaveLog = async (e) => {
    e.preventDefault();
    if (!user) return;
    setLogSaving(true);
    try {
      const payload = {
        date: logDate,
        mood: logMood,
        stress: logStress,
        sleep_hours: parseFloat(logSleep)
      };

      // Distinctly preserve/send fields without accidentally clearing omitted ones
      if (logCramps !== '') payload.cramps = logCramps;
      if (logFatigue !== '') payload.fatigue = logFatigue;
      if (logFlow !== '') payload.flow = logFlow;
      if (logEnergy !== '') payload.energy_level = logEnergy;
      if (logNotes && logNotes.trim() !== '') payload.notes = logNotes.trim();

      const res = await authFetch(`${API_BASE}/logs`, {
        method: 'POST',
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (res.ok) {
        triggerToast(editingLogId ? "Daily wellness log updated!" : "Daily wellness log saved!");
        if (data.log_id) {
          setEditingLogId(data.log_id);
        }
        fetchUserData();
      } else {
        triggerToast(data.error || "Failed to save log", true);
      }
    } catch (err) {
      triggerToast("Network error saving log.", true);
    } finally {
      setLogSaving(false);
    }
  };

  // Delete Wellness Log
  const handleDeleteLog = async (logId) => {
    if (!window.confirm("Are you sure you want to delete this daily wellness log?")) return;
    try {
      const res = await authFetch(`${API_BASE}/logs/${logId}`, { method: 'DELETE' });
      if (res.ok) {
        triggerToast("Daily wellness log deleted successfully.");
        if (editingLogId === logId) {
          populateFormForDate(logDate);
        }
        fetchUserData();
      } else {
        const data = await res.json();
        triggerToast(data.error || "Failed to delete log.", true);
      }
    } catch (err) {
      triggerToast("Network error deleting log.", true);
    }
  };

  // Edit Log Handler (from Logs tab)
  const handleEditLog = (log) => {
    populateFormForDate(log.date);
    setActiveTab('dashboard');
    triggerToast(`Loaded log for ${log.date}. You can edit and save.`);
    setTimeout(() => {
      const el = document.getElementById('wellness-log-form');
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }, 150);
  };

  // Open & Fetch Doctor-Visit Summary
  const handleOpenDoctorSummary = async () => {
    setShowDoctorModal(true);
    setDoctorSummaryLoading(true);
    try {
      const res = await authFetch(`${API_BASE}/reports/doctor-summary`);
      if (res.ok) {
        const data = await res.json();
        setDoctorSummaryData(data);
      } else {
        triggerToast("Failed to load doctor visit summary.", true);
      }
    } catch (err) {
      triggerToast("Error connecting to server for summary.", true);
    } finally {
      setDoctorSummaryLoading(false);
    }
  };

  // Print or Save PDF Clinical Summary
  const handlePrintDoctorSummary = async () => {
    try {
      const res = await authFetch(`${API_BASE}/reports/doctor-summary?format=html`);
      if (res.ok) {
        const html = await res.text();
        const printWindow = window.open('', '_blank');
        if (printWindow) {
          printWindow.document.write(html);
          printWindow.document.close();
        } else {
          triggerToast("Please allow popups to open the printable report.", true);
        }
      } else {
        triggerToast("Failed to generate printable report.", true);
      }
    } catch (err) {
      triggerToast("Error opening print report.", true);
    }
  };

  // Download JSON Clinical Summary
  const handleDownloadDoctorJson = () => {
    if (!doctorSummaryData) return;
    const blob = new Blob([JSON.stringify(doctorSummaryData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `ovacare_clinical_summary_${new Date().toISOString().split('T')[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);
    triggerToast("Doctor summary downloaded as JSON.");
  };

  // Add Cycle Handler
  const handleAddCycle = async (e) => {
    e.preventDefault();
    if (!user) return;
    try {
      const res = await authFetch(`${API_BASE}/cycles`, {
        method: 'POST',
        body: JSON.stringify({
          start_date: cycleStartDate,
          end_date: cycleEndDate || null
        })
      });
      const data = await res.json();
      if (res.ok) {
        triggerToast("Cycle start recorded!");
        setShowCycleModal(false);
        fetchUserData();
      } else {
        triggerToast(data.error || "Failed to log cycle", true);
      }
    } catch (err) {
      triggerToast("Network error creating cycle.", true);
    }
  };

  // Delete Cycle Handler
  const handleDeleteCycle = async (cycleId) => {
    if (!window.confirm("Are you sure you want to delete this cycle record?")) return;
    try {
      const res = await authFetch(`${API_BASE}/cycles/${cycleId}`, { method: 'DELETE' });
      if (res.ok) {
        triggerToast("Cycle entry deleted.");
        fetchUserData();
      } else {
        const data = await res.json();
        triggerToast(data.error || "Could not delete cycle record.", true);
      }
    } catch (err) {
      triggerToast("Network error deleting cycle.", true);
    }
  };

  // Open Clarification Modal
  const handleOpenClarifyModal = (cycleId) => {
    setClarifyCycleId(cycleId);
    const existing = cycles.find(c => c.cycle_id === cycleId);
    if (existing && existing.gap_type && ['forgotten_entry', 'missed_period', 'confirmed_long_cycle'].includes(existing.gap_type)) {
      setClarifyOption(existing.gap_type);
    } else {
      setClarifyOption('forgotten_entry');
    }
    setShowClarifyModal(true);
  };

  // Submit Clarification
  const handleClarifySubmit = async (e) => {
    e.preventDefault();
    if (!clarifyCycleId) return;
    setClarifyingLoading(true);
    try {
      const res = await authFetch(`${API_BASE}/cycles/${clarifyCycleId}/clarify`, {
        method: 'POST',
        body: JSON.stringify({ gap_clarification: clarifyOption })
      });
      const data = await res.json();
      if (res.ok) {
        triggerToast("Cycle interval updated successfully.");
        setShowClarifyModal(false);
        setClarifyCycleId(null);
        fetchUserData();
      } else {
        triggerToast(data.error || "Failed to clarify cycle interval.", true);
      }
    } catch (err) {
      triggerToast("Network error updating interval.", true);
    } finally {
      setClarifyingLoading(false);
    }
  };

  // Toggle Reminder Handler
  const handleToggleReminder = async (reminderId) => {
    try {
      const res = await authFetch(`${API_BASE}/reminders/${reminderId}/toggle`, { method: 'POST' });
      if (res.ok) {
        fetchUserData();
      }
    } catch (err) {
      triggerToast("Error updating reminder status.", true);
    }
  };

  // Add Reminder Handler
  const handleAddReminder = async (e) => {
    e.preventDefault();
    if (!user) return;
    try {
      const res = await authFetch(`${API_BASE}/reminders`, {
        method: 'POST',
        body: JSON.stringify({
          reminder_type: reminderType,
          reminder_date: reminderDate,
          completed: false
        })
      });
      if (res.ok) {
        triggerToast("Reminder set successfully!");
        fetchUserData();
      } else {
        const data = await res.json();
        triggerToast(data.error || "Failed to create reminder", true);
      }
    } catch (err) {
      triggerToast("Failed to create reminder.", true);
    }
  };

  // Delete Reminder Handler
  const handleDeleteReminder = async (reminderId) => {
    try {
      const res = await authFetch(`${API_BASE}/reminders/${reminderId}`, { method: 'DELETE' });
      if (res.ok) {
        fetchUserData();
      }
    } catch (err) {
      triggerToast("Error deleting reminder.", true);
    }
  };

  // Update Profile Settings Handler (Task B: PUT /api/users/<user_id>)
  const handleUpdateProfilePcos = async (pcosVal) => {
    if (!user) return;
    try {
      const res = await authFetch(`${API_BASE}/users/${user.user_id}`, {
        method: 'PUT',
        body: JSON.stringify({
          has_pcos: pcosVal,
          age: user.age,
          lifestyle: user.lifestyle
        })
      });
      const data = await res.json();
      if (res.ok) {
        const updatedUser = { ...user, has_pcos: pcosVal };
        setUser(updatedUser);
        localStorage.setItem('ovacare_user', JSON.stringify(updatedUser));
        triggerToast(`PCOS tracking settings updated (${pcosVal ? 'Active' : 'Off'}).`);
      } else {
        triggerToast(data.error || "Failed to update profile settings.", true);
      }
    } catch (e) {
      triggerToast("Network error updating profile settings.", true);
    }
  };

  // Dynamic emotional microcopy and phase description
  const getCyclePhaseDetails = () => {
    if (!prediction || prediction.history_count === 0) {
      return {
        phase: "Baseline Analysis",
        message: "Log your first cycle date below to begin generating personalized predictions and tracking your wellness phases.",
        color: "from-purple-400 to-fuchsia-400"
      };
    }

    if (cycles.length === 0) {
      return {
        phase: "Estimated Cycle Window",
        message: "Log a cycle to start building personal tracking records.",
        color: "from-purple-400 to-fuchsia-400"
      };
    }

    const lastStart = new Date(cycles[0].start_date);
    const today = new Date();
    const diffTime = Math.max(0, today - lastStart);
    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24)) + 1;
    const avgLen = prediction.average_cycle_length || 28;
    const cycleDay = ((diffDays - 1) % avgLen) + 1;
    const periodLen = prediction.average_period_length || 5;

    // Determine current estimated cycle window
    let windowKey = 'premenstrual';
    let phaseName = 'Estimated Premenstrual Window';
    let color = 'from-amber-400 to-orange-400';
    let defaultMsg = `Estimated Day ${cycleDay} of your cycle. Estimated windows are based on recorded history, not confirmed biological phases. Listen to your body and pace your activities as you prefer.`;

    if (cycleDay <= periodLen) {
      windowKey = 'menstrual';
      phaseName = 'Estimated Menstrual Window';
      color = 'from-rose-400 to-pink-400';
      defaultMsg = `Estimated Day ${cycleDay} of your cycle. Estimated window based on past cycle records. Prioritize gentle rest, nourishing hydration, and comfort as needed.`;
    } else if (cycleDay <= periodLen + 6) {
      windowKey = 'follicular';
      phaseName = 'Estimated Early Cycle Window';
      color = 'from-violet-400 to-indigo-400';
      defaultMsg = `Estimated Day ${cycleDay} of your cycle. Timeline calculated from past averages. Track your energy and mood today to build personalized patterns over time.`;
    } else if (cycleDay <= periodLen + 11) {
      windowKey = 'mid_cycle';
      phaseName = 'Estimated Mid-Cycle Window';
      color = 'from-emerald-400 to-teal-400';
      defaultMsg = `Estimated Day ${cycleDay} of your cycle. Mid-cycle timeline is an estimate based on recorded history. Calendar estimates do not confirm ovulation.`;
    }

    // Check if a backend-supported personal pattern exists for this window
    const patterns = analytics?.wellbeing_patterns?.patterns || [];
    const supportedMatch = patterns.find(p =>
      p.evidence_status === 'supported' &&
      (
        (windowKey === 'premenstrual' && (p.cycle_window === 'premenstrual' || p.cycle_window === 'luteal')) ||
        (windowKey === 'menstrual' && p.cycle_window === 'menstrual') ||
        (windowKey === 'follicular' && p.cycle_window === 'follicular') ||
        (windowKey === 'mid_cycle' && (p.cycle_window === 'ovulatory' || p.cycle_window === 'mid_cycle'))
      )
    );

    let message = defaultMsg;
    if (supportedMatch) {
      const tip = supportedMatch.supportive_recommendation ? ` ${supportedMatch.supportive_recommendation}` : '';
      message = `Personal Pattern (Estimated Day ${cycleDay}): ${supportedMatch.observation}${tip} (Estimated timing from history, not hormone testing.)`;
    }

    return {
      phase: phaseName,
      message,
      color
    };
  };

  // Milestone 3, Phase B.4: Subtle gamification and weekly rhythm derived strictly from user's actual logs
  const getWeeklyRhythmAndStreak = () => {
    const uniqueDates = Array.from(new Set((logs || []).map(l => l.date))).sort();
    const loggedDatesSet = new Set(uniqueDates);
    const totalLoggedDays = uniqueDates.length;

    // Last 7 days ending today (deterministic calendar window)
    const today = new Date();
    const weekDays = [];
    let loggedThisWeek = 0;

    for (let i = 6; i >= 0; i--) {
      const d = new Date(today);
      d.setDate(today.getDate() - i);
      const dateStr = d.toISOString().split('T')[0];
      const isLogged = loggedDatesSet.has(dateStr);
      if (isLogged) loggedThisWeek++;
      weekDays.push({
        dateStr,
        dayName: d.toLocaleDateString('en-US', { weekday: 'short' }),
        isToday: i === 0,
        isLogged
      });
    }

    // Streak calculation: strictly consecutive days ending today or yesterday
    const todayStr = today.toISOString().split('T')[0];
    const yesterday = new Date(today);
    yesterday.setDate(today.getDate() - 1);
    const yesterdayStr = yesterday.toISOString().split('T')[0];

    let currentStreak = 0;
    if (loggedDatesSet.has(todayStr) || loggedDatesSet.has(yesterdayStr)) {
      let checkDate = loggedDatesSet.has(todayStr) ? new Date(today) : new Date(yesterday);
      while (true) {
        const checkStr = checkDate.toISOString().split('T')[0];
        if (loggedDatesSet.has(checkStr)) {
          currentStreak++;
          checkDate.setDate(checkDate.getDate() - 1);
        } else {
          break;
        }
      }
    }

    // Milestones for consistent tracking
    let milestone = { label: "First Steps", target: 3, description: "Track 3 days to establish initial baseline" };
    if (totalLoggedDays >= 30) {
      milestone = { label: "Dedicated Rhythm", target: 60, description: "60 days of ongoing wellness history" };
    } else if (totalLoggedDays >= 14) {
      milestone = { label: "Two Weeks of Insight", target: 30, description: "30 days of consistent tracking" };
    } else if (totalLoggedDays >= 7) {
      milestone = { label: "Weekly Habit Formed", target: 14, description: "14 days of personal wellness patterns" };
    } else if (totalLoggedDays >= 3) {
      milestone = { label: "Building Consistency", target: 7, description: "7 days of wellness observations" };
    }

    const progressPct = Math.min(100, Math.round((totalLoggedDays / milestone.target) * 100));

    return {
      weekDays,
      loggedThisWeek,
      currentStreak,
      totalLoggedDays,
      milestone,
      progressPct
    };
  };

  // Calendar Helper Logic
  const getDaysInMonth = (year, month) => new Date(year, month + 1, 0).getDate();
  const getFirstDayOfMonth = (year, month) => new Date(year, month, 1).getDay();

  const handlePrevMonth = () => {
    if (calendarMonth === 0) {
      setCalendarMonth(11);
      setCalendarYear(calendarYear - 1);
    } else {
      setCalendarMonth(calendarMonth - 1);
    }
  };

  const handleNextMonth = () => {
    if (calendarMonth === 11) {
      setCalendarMonth(0);
      setCalendarYear(calendarYear + 1);
    } else {
      setCalendarMonth(calendarMonth + 1);
    }
  };

  const renderCalendarDays = () => {
    const daysInMonth = getDaysInMonth(calendarYear, calendarMonth);
    const firstDay = getFirstDayOfMonth(calendarYear, calendarMonth);
    
    // Map dates to cycle highlights
    const cycleMap = {};
    cycles.forEach(c => {
      const start = new Date(c.start_date);
      const periodLen = c.period_length || 5;
      
      for (let i = 0; i < periodLen; i++) {
        const curDate = new Date(start);
        curDate.setDate(start.getDate() + i);
        if (curDate.getFullYear() === calendarYear && curDate.getMonth() === calendarMonth) {
          cycleMap[curDate.getDate()] = 'period';
        }
      }
    });

    // Map predicted dates
    if (prediction && prediction.predicted_date) {
      const predDate = new Date(prediction.predicted_date);
      if (predDate.getFullYear() === calendarYear && predDate.getMonth() === calendarMonth) {
        cycleMap[predDate.getDate()] = 'prediction';
      }
    }

    const cells = [];
    // Empty cells for alignment
    for (let i = 0; i < firstDay; i++) {
      cells.push(<div key={`empty-${i}`} className="w-10 h-10"></div>);
    }

    for (let day = 1; day <= daysInMonth; day++) {
      const isPeriod = cycleMap[day] === 'period';
      const isPred = cycleMap[day] === 'prediction';
      const isToday = new Date().getDate() === day && new Date().getMonth() === calendarMonth && new Date().getFullYear() === calendarYear;
      
      let cellClass = "w-10 h-10 flex items-center justify-center rounded-full text-sm font-medium transition-all cursor-pointer relative ";
      if (isPeriod) {
        cellClass += "bg-gradient-to-tr from-pink-400 to-rose-300 text-white shadow-sm scale-105 ";
      } else if (isPred) {
        cellClass += "border-2 border-dashed border-primary text-primary bg-primary/5 ";
      } else if (isToday) {
        cellClass += "bg-primary text-white shadow-md ";
      } else {
        cellClass += "hover:bg-purple-100 text-textPrimary ";
      }

      cells.push(
        <div 
          key={`day-${day}`} 
          className={cellClass}
          onClick={() => {
            const formattedDate = `${calendarYear}-${String(calendarMonth + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
            setLogDate(formattedDate);
            setCycleStartDate(formattedDate);
            triggerToast(`Selected date: ${formattedDate}`);
          }}
        >
          {day}
          {isPeriod && <span className="absolute bottom-1 w-1.5 h-1.5 bg-white rounded-full"></span>}
          {isPred && <span className="absolute bottom-1 w-1.5 h-1.5 bg-primary rounded-full"></span>}
        </div>
      );
    }
    return cells;
  };

  const monthNames = [
    "January", "February", "March", "April", "May", "June", 
    "July", "August", "September", "October", "November", "December"
  ];

  // Render Login page if not authorized
  if (!user) {
    return (
      <div className="min-h-screen bg-gradient-to-tr from-purple-100 via-pink-50 to-indigo-100 flex flex-col justify-between p-6">
        {/* Header Title */}
        <div className="flex items-center justify-center space-x-2 pt-6">
          <div className="bg-primary p-2 rounded-2xl text-white shadow-premium">
            <Heart size={28} className="fill-white" />
          </div>
          <span className="text-2xl font-bold tracking-tight text-textPrimary">OvaCare</span>
        </div>

        {/* Floating Auth Panel */}
        <div className="w-full max-w-md mx-auto glass-panel rounded-3xl p-8 shadow-premium mt-8">
          <h2 className="text-2xl font-semibold text-center text-textPrimary mb-2">
            {authMode === 'login' ? 'Welcome Back' : 'Create Wellness Space'}
          </h2>
          <p className="text-center text-textSecondary text-sm mb-6">
            {authMode === 'login' ? 'Let\'s reconnect with your body\'s cycles' : 'Start your personalized tracking companion'}
          </p>

          <form onSubmit={authMode === 'login' ? handleLogin : handleRegister} className="space-y-4">
            {authMode === 'register' && (
              <div>
                <label className="block text-xs font-semibold text-textSecondary uppercase tracking-wider mb-1">Username</label>
                <input
                  type="text"
                  placeholder="e.g. Priya"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="w-full px-4 py-3 rounded-2xl border border-purple-200 focus:ring-2 focus:ring-primary focus:border-transparent outline-none text-sm transition"
                />
              </div>
            )}
            
            <div>
              <label className="block text-xs font-semibold text-textSecondary uppercase tracking-wider mb-1">Email</label>
              <input
                type="email"
                placeholder="yourname@gmail.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-3 rounded-2xl border border-purple-200 focus:ring-2 focus:ring-primary focus:border-transparent outline-none text-sm transition"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-textSecondary uppercase tracking-wider mb-1">Password</label>
              <input
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-3 rounded-2xl border border-purple-200 focus:ring-2 focus:ring-primary focus:border-transparent outline-none text-sm transition"
                required
              />
            </div>

            {authMode === 'register' && (
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-textSecondary uppercase tracking-wider mb-1">Age</label>
                  <input
                    type="number"
                    placeholder="25"
                    value={age}
                    onChange={(e) => setAge(e.target.value)}
                    className="w-full px-4 py-3 rounded-2xl border border-purple-200 focus:ring-2 focus:ring-primary focus:border-transparent outline-none text-sm transition"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-textSecondary uppercase tracking-wider mb-1">Lifestyle</label>
                  <select
                    value={lifestyle}
                    onChange={(e) => setLifestyle(e.target.value)}
                    className="w-full px-4 py-3 rounded-2xl border border-purple-200 focus:ring-2 focus:ring-primary focus:border-transparent outline-none text-sm transition"
                  >
                    <option value="Sedentary">Sedentary</option>
                    <option value="Moderate">Moderate</option>
                    <option value="Active">Active</option>
                  </select>
                </div>
              </div>
            )}

            {authMode === 'register' && (
              <div className="flex items-center space-x-2 pt-2">
                <input
                  type="checkbox"
                  id="hasPcosCheck"
                  checked={hasPcos}
                  onChange={(e) => setHasPcos(e.target.checked)}
                  className="rounded text-primary focus:ring-primary h-4 w-4"
                />
                <label htmlFor="hasPcosCheck" className="text-xs text-textSecondary select-none">
                  I track irregular cycle / PCOS patterns
                </label>
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-primary hover:bg-primary-dark text-white py-3 rounded-2xl font-medium shadow-premium transition text-sm flex items-center justify-center space-x-2 mt-6"
            >
              <span>{loading ? 'Validating...' : (authMode === 'login' ? 'Login' : 'Get Started')}</span>
              <ArrowRight size={16} />
            </button>
          </form>

          {/* Demo Mode Button */}
          <div className="relative flex py-4 items-center">
            <div className="flex-grow border-t border-purple-200"></div>
            <span className="flex-shrink mx-4 text-xs font-medium text-textLight uppercase tracking-wider">or</span>
            <div className="flex-grow border-t border-purple-200"></div>
          </div>

          <button
            onClick={handleDemoMode}
            disabled={loading}
            className="w-full border-2 border-primary/20 hover:border-primary text-primary py-3 rounded-2xl font-semibold bg-white/50 hover:bg-primary/5 transition text-sm flex items-center justify-center space-x-2"
          >
            <Sparkles size={16} className="fill-primary/10" />
            <span>{loading ? 'Initializing Demo...' : 'Sign in Demo Mode (Seed Data)'}</span>
          </button>

          <div className="mt-6 text-center">
            <button
              onClick={() => setAuthMode(authMode === 'login' ? 'register' : 'login')}
              className="text-xs text-primary font-semibold hover:underline"
            >
              {authMode === 'login' ? 'Don\'t have an account? Sign up' : 'Already have an account? Log in'}
            </button>
          </div>
        </div>

        {/* Footer */}
        <div className="text-center text-xs text-textLight pt-12 pb-2">
          Secure Wellness Space • OvaCare HIPAA Compliant Synthetic Research
        </div>

        {/* Global Notifications */}
        {error && (
          <div className="fixed bottom-4 left-4 right-4 bg-rose-50 border border-rose-200 p-4 rounded-2xl flex items-center space-x-2 shadow-lg">
            <AlertCircle className="text-rose-500 flex-shrink-0" size={18} />
            <span className="text-xs text-rose-800 font-medium">{error}</span>
          </div>
        )}
        {successMsg && (
          <div className="fixed bottom-4 left-4 right-4 bg-emerald-50 border border-emerald-200 p-4 rounded-2xl flex items-center space-x-2 shadow-lg">
            <Check className="text-emerald-500 flex-shrink-0" size={18} />
            <span className="text-xs text-emerald-800 font-medium">{successMsg}</span>
          </div>
        )}
      </div>
    );
  }

  // Active User is Authenticated. Render main application view.
  const phaseInfo = getCyclePhaseDetails();

  return (
    <div className="min-h-screen bg-[#F5F3FF] pb-44 pt-4 px-4 sm:px-8">
      {/* Top Header */}
      <header className={`${(activeTab === 'community' || activeTab === 'companion') ? 'max-w-5xl' : 'max-w-4xl'} mx-auto flex justify-between items-center mb-6 pt-2 transition-all`}>
        <div className="flex items-center space-x-2">
          <div className="bg-primary p-1.5 rounded-xl text-white shadow-soft">
            <Heart size={20} className="fill-white" />
          </div>
          <span className="text-lg font-bold text-textPrimary tracking-tight">OvaCare</span>
          {user.has_pcos && (
            <span className="bg-amber-100 text-amber-700 text-[10px] px-2 py-0.5 rounded-full font-semibold border border-amber-200 flex items-center space-x-0.5">
              <span>PCOS Mode</span>
            </span>
          )}
        </div>
        
        {/* Quick Admin/LogOut Access */}
        <div className="flex items-center space-x-3">
          <button 
            onClick={() => setActiveTab(activeTab === 'admin' ? 'dashboard' : 'admin')} 
            className={`p-2 rounded-xl text-textSecondary transition ${activeTab === 'admin' ? 'bg-primary text-white shadow-md' : 'glass-panel hover:bg-purple-100'}`}
            title="System Admin Portal"
          >
            <Users size={16} />
          </button>
          
          <button 
            onClick={handleLogout} 
            className="p-2 rounded-xl glass-panel text-rose-600 hover:bg-rose-50 transition" 
            title="Log Out"
          >
            <LogOut size={16} />
          </button>
        </div>
      </header>

      {/* Main Tab Panels */}
      <main className={`${(activeTab === 'community' || activeTab === 'companion') ? 'max-w-5xl' : 'max-w-4xl'} mx-auto transition-all`}>
        {loading && (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-primary border-t-transparent mb-2"></div>
            <p className="text-xs text-textSecondary">Syncing wellness charts...</p>
          </div>
        )}

        {!loading && (
          <>
            {/* ==========================================
                TAB: DASHBOARD
                ========================================== */}
            {activeTab === 'dashboard' && (
              <div className="space-y-5 sm:space-y-6">
                {/* Welcome Card */}
                <div className={`p-5 sm:p-6 rounded-2xl bg-gradient-to-tr ${phaseInfo.color} text-white shadow-premium relative overflow-hidden`}>
                  <div className="relative z-10">
                    <span className="text-xs font-semibold bg-white/20 px-3 py-1 rounded-full uppercase tracking-wider">
                      {phaseInfo.phase}
                    </span>
                    <h1 className="text-xl sm:text-2xl font-bold mt-2">
                      Good Day, {user.username}
                    </h1>
                    <p className="text-xs sm:text-sm font-medium mt-1 opacity-90 max-w-lg leading-relaxed">
                      {phaseInfo.message}
                    </p>
                  </div>
                  {/* Decorative glowing backdrops */}
                  <div className="absolute right-0 top-0 w-48 h-48 bg-white/10 rounded-full blur-3xl -mr-16 -mt-16"></div>
                </div>

                {/* Main Prediction Metrics Row */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {/* Predicted Next Period Widget */}
                  <div className="glass-panel p-5 sm:p-6 rounded-2xl relative overflow-hidden flex flex-col justify-between">
                    <div>
                      <div className="flex justify-between items-start">
                        <span className="text-xs font-semibold text-textSecondary uppercase tracking-wider">Period Prediction</span>
                        {prediction && (
                          <div>
                            {prediction.prediction_confidence === 'high' && (
                              <span className="text-[10px] px-2 py-0.5 rounded-full font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200">
                                High Confidence
                              </span>
                            )}
                            {prediction.prediction_confidence === 'moderate' && (
                              <span className="text-[10px] px-2 py-0.5 rounded-full font-semibold bg-blue-100 text-blue-800 border border-blue-200">
                                Moderate Confidence
                              </span>
                            )}
                            {prediction.prediction_confidence === 'low' && (
                              <span className="text-[10px] px-2 py-0.5 rounded-full font-semibold bg-amber-100 text-amber-800 border border-amber-200">
                                Low Confidence
                              </span>
                            )}
                            {prediction.prediction_confidence === 'uncertain' && (
                              <span className="text-[10px] px-2 py-0.5 rounded-full font-semibold bg-purple-100 text-purple-800 border border-purple-200">
                                Uncertain Variation
                              </span>
                            )}
                            {!['high', 'moderate', 'low', 'uncertain'].includes(prediction.prediction_confidence) && (
                              <span className="text-[10px] px-2 py-0.5 rounded-full font-semibold bg-purple-50 text-purple-700 border border-purple-200">
                                Calculated Estimate
                              </span>
                            )}
                          </div>
                        )}
                      </div>
                      <div className="mt-3.5">
                        {prediction ? (
                          <>
                            <h3 className="text-2xl sm:text-3xl font-bold text-textPrimary tracking-tight">
                              {prediction.delayed_days > 0 
                                ? `${prediction.delayed_days} Days Delayed` 
                                : new Date(prediction.predicted_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
                              }
                            </h3>
                            <p className="text-xs text-textSecondary mt-1">
                              {prediction.message}
                            </p>
                            {prediction.confidence_reason && (
                              <p className="text-[11px] text-textSecondary mt-1 flex items-start gap-1">
                                <Info size={12} className="inline flex-shrink-0 text-primary mt-0.5" />
                                <span>{prediction.confidence_reason}</span>
                              </p>
                            )}

                            {/* Tracking Gap Clarification Alert */}
                            {prediction.has_unresolved_gaps && (
                              <div className="mt-3 p-3 rounded-xl bg-amber-50/90 border border-amber-200/80 text-xs">
                                <div className="flex items-start justify-between gap-2">
                                  <div className="flex items-start gap-1.5">
                                    <AlertCircle size={14} className="text-amber-600 flex-shrink-0 mt-0.5" />
                                    <div>
                                      <p className="font-semibold text-amber-900 text-[11px]">Tracking gap detected (&gt;45 days)</p>
                                      <p className="text-[10px] text-amber-800 mt-0.5">
                                        {prediction.clarification_prompt || "One or more intervals between recorded cycles exceed 45 days. You can clarify whether this was a forgotten log, a missed period, or a longer cycle."}
                                      </p>
                                    </div>
                                  </div>
                                  {prediction.excluded_intervals?.find(e => e.requires_clarification) && (
                                    <button
                                      onClick={() => handleOpenClarifyModal(prediction.excluded_intervals.find(e => e.requires_clarification).cycle_id)}
                                      className="px-2.5 py-1 rounded-xl bg-amber-600 hover:bg-amber-700 text-white text-[10px] font-semibold whitespace-nowrap transition shadow-xs"
                                    >
                                      Clarify
                                    </button>
                                  )}
                                </div>
                              </div>
                            )}

                            {/* Explainable Calculation Accordion */}
                            <div className="mt-3 pt-2 border-t border-purple-100/60">
                              <button
                                type="button"
                                onClick={() => setShowExplainableDetails(!showExplainableDetails)}
                                className="w-full flex items-center justify-between text-[11px] font-semibold text-primary hover:text-primary/80 transition"
                              >
                                <span className="flex items-center gap-1">
                                  <HelpCircle size={12} />
                                  <span>How this estimate was calculated</span>
                                </span>
                                {showExplainableDetails ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                              </button>

                              {showExplainableDetails && (
                                <div className="mt-2.5 p-3 rounded-xl bg-purple-50/50 border border-purple-100/70 text-[11px] text-textSecondary space-y-2">
                                  <div>
                                    <span className="font-semibold text-textPrimary block">History Quality:</span>
                                    <span>
                                      {prediction.history_quality === 'insufficient' && 'Not enough history yet'}
                                      {prediction.history_quality === 'limited' && 'Limited history (1 completed interval)'}
                                      {prediction.history_quality === 'needs_clarification' && 'History needs clarification'}
                                      {prediction.history_quality === 'adequate' && 'Adequate recorded history'}
                                      {prediction.history_quality === 'established' && 'Sufficient history for personal estimate'}
                                      {!['insufficient', 'limited', 'needs_clarification', 'adequate', 'established'].includes(prediction.history_quality) && (prediction.history_quality || 'Baseline')}
                                    </span>
                                    {prediction.history_quality_description && (
                                      <p className="text-[10px] text-textSecondary mt-0.5 italic">{prediction.history_quality_description}</p>
                                    )}
                                  </div>

                                  <div>
                                    <span className="font-semibold text-textPrimary block">Contributing Completed Cycles:</span>
                                    {prediction.usable_intervals && prediction.usable_intervals.length > 0 ? (
                                      <p className="text-[10px]">
                                        Recorded lengths: <strong>{prediction.usable_intervals.join('d, ')}d</strong> (average: {prediction.average_cycle_length} days{prediction.cycle_length_std_dev !== null ? `, variability: ±${prediction.cycle_length_std_dev}d` : ''})
                                      </p>
                                    ) : (
                                      <p className="text-[10px]">
                                        Using standard 28-day baseline because completed cycle intervals have not yet been established.
                                      </p>
                                    )}
                                  </div>

                                  {prediction.excluded_intervals && prediction.excluded_intervals.length > 0 && (
                                    <div className="pt-1 border-t border-purple-100/50">
                                      <span className="font-semibold text-textPrimary block">Excluded / Unresolved Intervals:</span>
                                      <div className="space-y-1 mt-1">
                                        {prediction.excluded_intervals.map((exc, idx) => (
                                          <div key={idx} className="flex items-start justify-between gap-1 text-[10px] bg-white/70 p-1.5 rounded-lg border border-purple-100/40">
                                            <div>
                                              <span className="font-medium text-textPrimary">{exc.start_date} ({exc.interval_days}d): </span>
                                              <span className="text-textSecondary">{exc.reason}</span>
                                            </div>
                                            {exc.requires_clarification && (
                                              <button
                                                onClick={() => handleOpenClarifyModal(exc.cycle_id)}
                                                className="text-primary hover:underline font-semibold ml-1 whitespace-nowrap"
                                              >
                                                Clarify
                                              </button>
                                            )}
                                          </div>
                                        ))}
                                      </div>
                                    </div>
                                  )}

                                  <p className="text-[9px] text-textLight border-t border-purple-100/40 pt-1.5">
                                    Note: This is an empirical estimate calculated from your personal tracking logs and standard baselines, not a confirmed medical diagnosis.
                                  </p>
                                </div>
                              )}
                            </div>
                          </>
                        ) : (
                          <h3 className="text-lg font-medium text-textLight">No cycle logged yet</h3>
                        )}
                      </div>
                    </div>
                    {prediction && (
                      <div className="mt-4 border-t border-purple-100 pt-3 flex flex-wrap justify-between gap-2 text-xs text-textSecondary">
                        <span>Avg Cycle: <strong>{prediction.average_cycle_length} Days</strong></span>
                        <span>Avg Period: <strong>{prediction.average_period_length} Days</strong></span>
                        <span>Contributing: <strong>{prediction.usable_intervals?.length || 0}</strong></span>
                      </div>
                    )}
                  </div>

                  {/* Wellness State Card */}
                  <div className="glass-panel p-5 sm:p-6 rounded-2xl flex flex-col justify-between">
                    <div>
                      <div className="flex justify-between items-start">
                        <span className="text-xs font-semibold text-textSecondary uppercase tracking-wider">Current Cycle Status</span>
                        <Sparkles size={18} className="text-pink-500 fill-pink-100" />
                      </div>
                      <div className="mt-3.5">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="text-2xl sm:text-3xl font-bold tracking-tight text-textPrimary">
                            {cycles.length > 0 ? (
                              prediction?.delayed_days > 0 
                                ? `${prediction.delayed_days} Days Delayed` 
                                : `Day ${(Math.round(Math.abs(new Date() - new Date(cycles[0].start_date)) / (1000 * 60 * 60 * 24)) % (prediction?.average_cycle_length || 28)) || 1}`
                            ) : 'Not Started'}
                          </span>
                          {(!prediction || !prediction.can_classify_regularity || prediction.regularity_assessment === 'insufficient_data') ? (
                            <span className="text-xs px-2.5 py-0.5 rounded-full font-semibold bg-purple-100/70 text-purple-700 border border-purple-200">
                              Not enough data to assess regularity
                            </span>
                          ) : (prediction.regularity_assessment === 'irregular' || prediction.irregular) ? (
                            <span className="text-xs px-2.5 py-0.5 rounded-full font-semibold bg-rose-100 text-rose-700 border border-rose-200">
                              Irregular Cycle Pattern
                            </span>
                          ) : (
                            <span className="text-xs px-2.5 py-0.5 rounded-full font-semibold bg-emerald-100 text-emerald-700 border border-emerald-200">
                              Consistent Cycle Pattern
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-textSecondary mt-1.5">
                          {prediction?.regularity_message || (user.has_pcos ? 'Tracking optimized for hormonal variance (PCOS).' : 'Cycle tracking following standard parameters.')}
                        </p>
                      </div>
                    </div>
                    
                    <button 
                      onClick={() => setShowCycleModal(true)} 
                      className="w-full mt-4 bg-primary/10 hover:bg-primary text-primary hover:text-white py-2.5 rounded-xl text-xs font-semibold transition"
                    >
                      Log New Cycle Start
                    </button>
                  </div>
                </div>

                {/* Milestone 3, Phase B.4 Gamification: Weekly Rhythm & Milestones Card */}
                {(() => {
                  const rhythm = getWeeklyRhythmAndStreak();
                  return (
                    <div className="glass-panel p-4 sm:p-5 rounded-2xl border border-purple-100/80">
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                        {/* Left: Rhythm & Streak Status */}
                        <div className="flex items-center space-x-3">
                          <div className="w-10 h-10 rounded-xl bg-purple-50 flex items-center justify-center text-primary border border-purple-200/60 flex-shrink-0">
                            {rhythm.currentStreak > 0 ? (
                              <Flame size={20} className="text-amber-500 fill-amber-100" />
                            ) : (
                              <Activity size={20} className="text-primary" />
                            )}
                          </div>
                          <div>
                            <div className="flex items-center space-x-2">
                              <h3 className="text-sm font-semibold text-textPrimary">
                                {rhythm.currentStreak > 0 ? `${rhythm.currentStreak}-Day Active Rhythm` : 'Weekly Tracking Rhythm'}
                              </h3>
                              {rhythm.currentStreak > 0 && (
                                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200/60">
                                  Active
                                </span>
                              )}
                            </div>
                            <p className="text-[11px] text-textSecondary mt-0.5">
                              {rhythm.loggedThisWeek} of 7 days logged this week ({rhythm.totalLoggedDays} total entry {rhythm.totalLoggedDays === 1 ? 'day' : 'days'})
                            </p>
                          </div>
                        </div>

                        {/* Right: 7-Day Rhythm Segmented Dots */}
                        <div className="flex items-center space-x-1.5 self-start sm:self-auto">
                          {rhythm.weekDays.map((d, i) => (
                            <div key={i} className="flex flex-col items-center">
                              <span className={`text-[9px] font-medium mb-1 ${d.isToday ? 'text-primary font-bold' : 'text-textLight'}`}>
                                {d.dayName.slice(0, 1)}
                              </span>
                              <div
                                title={`${d.dayName} (${d.dateStr}): ${d.isLogged ? 'Logged' : 'Not logged'}`}
                                className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] transition ${
                                  d.isLogged
                                    ? 'bg-primary text-white shadow-xs'
                                    : d.isToday
                                    ? 'border-2 border-dashed border-primary/50 text-primary bg-primary/5'
                                    : 'bg-purple-50 text-textLight border border-purple-100'
                                }`}
                              >
                                {d.isLogged ? <Check size={12} strokeWidth={3} /> : (d.isToday ? '·' : '')}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Milestone Progress Bar */}
                      <div className="mt-3 pt-3 border-t border-purple-100/60 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
                        <div className="flex items-center space-x-2">
                          <Award size={14} className="text-primary flex-shrink-0" />
                          <span className="text-[11px] font-medium text-textPrimary">
                            Milestone: <strong className="text-primary">{rhythm.milestone.label}</strong>
                          </span>
                          <span className="text-[10px] text-textSecondary">
                            ({rhythm.totalLoggedDays}/{rhythm.milestone.target} days tracked)
                          </span>
                        </div>

                        <div className="flex items-center space-x-2 w-full sm:w-44">
                          <div className="w-full bg-purple-100 rounded-full h-1.5 overflow-hidden">
                            <div
                              className="bg-primary h-1.5 rounded-full transition-all duration-500"
                              style={{ width: `${rhythm.progressPct}%` }}
                            ></div>
                          </div>
                          <span className="text-[10px] font-semibold text-textSecondary whitespace-nowrap">
                            {rhythm.progressPct}%
                          </span>
                        </div>
                      </div>
                    </div>
                  );
                })()}

                {/* Quick Log Form */}
                <div id="wellness-log-form" className="glass-panel p-5 sm:p-6 rounded-2xl">
                  <div className="flex justify-between items-start mb-1">
                    <div>
                      <h3 className="text-base sm:text-lg font-semibold text-textPrimary">Quick Wellness Log</h3>
                      <p className="text-xs text-textSecondary">Record logs for daily symptoms, energy, and notes</p>
                    </div>
                    {editingLogId && (
                      <span className="text-[10px] font-semibold px-2.5 py-0.5 rounded-full bg-purple-100 text-primary border border-purple-200">
                        Editing Log
                      </span>
                    )}
                  </div>

                  {editingLogId && (
                    <div className="mt-2 mb-3 px-3 py-2 rounded-xl bg-purple-50/80 border border-purple-200/60 flex items-center justify-between text-xs">
                      <span className="text-primary font-medium flex items-center gap-1">
                        <Edit3 size={12} className="inline flex-shrink-0" />
                        <span>Loaded saved log for {logDate}.</span>
                      </span>
                      <button
                        type="button"
                        onClick={() => handleDeleteLog(editingLogId)}
                        className="text-rose-600 hover:text-rose-700 text-xs font-semibold flex items-center space-x-1 transition"
                      >
                        <Trash2 size={13} />
                        <span>Delete Log</span>
                      </button>
                    </div>
                  )}

                  <form onSubmit={handleSaveLog} className="space-y-4 mt-3">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
                      <div>
                        <label className="block text-[10px] font-semibold text-textSecondary uppercase mb-1">Log Date</label>
                        <input
                          type="date"
                          value={logDate}
                          onChange={(e) => populateFormForDate(e.target.value)}
                          className="w-full px-3 py-2 rounded-xl border border-purple-100 text-xs focus:ring-1 focus:ring-primary outline-none"
                        />
                      </div>
                      <div>
                        <label className="block text-[10px] font-semibold text-textSecondary uppercase mb-1">Daily Mood</label>
                        <select
                          value={logMood}
                          onChange={(e) => setLogMood(e.target.value)}
                          className="w-full px-3 py-2 rounded-xl border border-purple-100 text-xs focus:ring-1 focus:ring-primary outline-none"
                        >
                          <option value="Happy">Happy</option>
                          <option value="Calm">Calm</option>
                          <option value="Emotional">Emotional</option>
                          <option value="Irritated">Irritated</option>
                          <option value="Tired">Tired</option>
                          <option value="Anxious">Anxious</option>
                        </select>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-2">
                      <div>
                        <label className="block text-[10px] font-semibold text-textSecondary uppercase mb-1">Cramps</label>
                        <select
                          value={logCramps}
                          onChange={(e) => setLogCramps(e.target.value)}
                          className="w-full px-2.5 py-2 rounded-xl border border-purple-100 text-xs focus:ring-1 focus:ring-primary outline-none"
                        >
                          <option value="">Untracked / Skip</option>
                          <option value="None">None (No cramps)</option>
                          <option value="Mild">Mild</option>
                          <option value="Moderate">Moderate</option>
                          <option value="Severe">Severe</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-[10px] font-semibold text-textSecondary uppercase mb-1">Fatigue</label>
                        <select
                          value={logFatigue}
                          onChange={(e) => setLogFatigue(e.target.value)}
                          className="w-full px-2.5 py-2 rounded-xl border border-purple-100 text-xs focus:ring-1 focus:ring-primary outline-none"
                        >
                          <option value="">Untracked / Skip</option>
                          <option value="None">None (No fatigue)</option>
                          <option value="Mild">Mild</option>
                          <option value="Moderate">Moderate</option>
                          <option value="Severe">Severe</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-[10px] font-semibold text-textSecondary uppercase mb-1">Flow</label>
                        <select
                          value={logFlow}
                          onChange={(e) => setLogFlow(e.target.value)}
                          className="w-full px-2.5 py-2 rounded-xl border border-purple-100 text-xs focus:ring-1 focus:ring-primary outline-none"
                        >
                          <option value="">Untracked / Skip</option>
                          <option value="None">None (No bleeding)</option>
                          <option value="Light">Light</option>
                          <option value="Medium">Medium</option>
                          <option value="Heavy">Heavy</option>
                        </select>
                      </div>
                    </div>

                    {/* Supportive safety callout for severe cramps or heavy flow */}
                    {(logCramps === 'Severe' || logFlow === 'Heavy') && (
                      <div className="p-3 rounded-xl bg-purple-50/90 border border-purple-200/80 text-[11px] text-purple-900 flex items-start space-x-2">
                        <Sparkles size={14} className="text-primary mt-0.5 flex-shrink-0" />
                        <div className="leading-relaxed">
                          <span className="font-semibold text-primary">Care & Safety Note: </span>
                          {logCramps === 'Severe' && logFlow === 'Heavy'
                            ? "You've logged severe cramps and heavy flow. Rest and gentle heat can help soothe tension. If pain or bleeding is unusually sudden, intense, or soaking through pads rapidly, consider reaching out to your healthcare provider."
                            : logCramps === 'Severe'
                            ? "You've reported severe cramps today. Rest and soothing warmth can offer relief. If pain is sudden, debilitating, or persists, please consult your doctor for personalized evaluation."
                            : "You've logged heavy menstrual flow. Remember to stay hydrated. If flow is unusually heavy (soaking through pads/tampons every hour), consult a medical professional."}
                        </div>
                      </div>
                    )}

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
                      <div>
                        <label className="block text-[10px] font-semibold text-textSecondary uppercase mb-1">Stress Level ({logStress})</label>
                        <select
                          value={logStress}
                          onChange={(e) => setLogStress(e.target.value)}
                          className="w-full px-3 py-2 rounded-xl border border-purple-100 text-xs focus:ring-1 focus:ring-primary outline-none"
                        >
                          <option value="Low">Low</option>
                          <option value="Medium">Medium</option>
                          <option value="High">High</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-[10px] font-semibold text-textSecondary uppercase mb-1">Sleep ({logSleep} hrs)</label>
                        <input
                          type="range"
                          min="4"
                          max="11"
                          step="0.5"
                          value={logSleep}
                          onChange={(e) => setLogSleep(e.target.value)}
                          className="w-full accent-primary h-2 bg-purple-100 rounded-lg cursor-pointer mt-2"
                        />
                      </div>
                    </div>

                    {/* Energy Level Selector (Optional) */}
                    <div>
                      <label className="block text-[10px] font-semibold text-textSecondary uppercase mb-1">Energy Level (Optional)</label>
                      <select
                        value={logEnergy}
                        onChange={(e) => setLogEnergy(e.target.value)}
                        className="w-full px-3 py-2 rounded-xl border border-purple-100 text-xs focus:ring-1 focus:ring-primary outline-none"
                      >
                        <option value="">Untracked / Skip</option>
                        <option value="High">High</option>
                        <option value="Moderate">Moderate</option>
                        <option value="Low">Low</option>
                        <option value="Very Low">Very Low</option>
                      </select>
                    </div>

                    {/* Daily Notes (Optional) */}
                    <div>
                      <label className="block text-[10px] font-semibold text-textSecondary uppercase mb-1">Daily Notes (Optional)</label>
                      <textarea
                        rows="2"
                        value={logNotes}
                        onChange={(e) => setLogNotes(e.target.value)}
                        placeholder="Personal reflections, activities, or notes for today..."
                        className="w-full px-3 py-2 rounded-xl border border-purple-100 text-xs focus:ring-1 focus:ring-primary outline-none resize-none"
                      />
                    </div>

                    <button
                      type="submit"
                      disabled={logSaving}
                      className={`w-full ${logSaving ? 'bg-primary/70 cursor-not-allowed' : 'bg-primary hover:bg-primary-dark'} text-white py-2.5 rounded-xl text-xs font-semibold shadow-soft hover:shadow-md transition`}
                    >
                      {logSaving ? 'Saving Daily Log...' : (editingLogId ? 'Update Daily Log' : 'Save Daily Log')}
                    </button>
                  </form>
                </div>
              </div>
            )}

            {/* ==========================================
                TAB: CALENDAR
                ========================================== */}
            {activeTab === 'calendar' && (
              <div className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  {/* Left: Custom Calendar Grid */}
                  <div className="md:col-span-2 glass-panel p-6 rounded-3xl">
                    <div className="flex justify-between items-center mb-6">
                      <h3 className="text-lg font-semibold text-textPrimary">
                        {monthNames[calendarMonth]} {calendarYear}
                      </h3>
                      <div className="flex space-x-2">
                        <button 
                          onClick={handlePrevMonth} 
                          className="p-1.5 rounded-xl hover:bg-purple-100 text-textSecondary border border-purple-100 text-sm font-semibold transition"
                        >
                          &lt;
                        </button>
                        <button 
                          onClick={handleNextMonth} 
                          className="p-1.5 rounded-xl hover:bg-purple-100 text-textSecondary border border-purple-100 text-sm font-semibold transition"
                        >
                          &gt;
                        </button>
                      </div>
                    </div>

                    {/* Week Header */}
                    <div className="grid grid-cols-7 gap-1 text-center mb-2">
                      {['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'].map(day => (
                        <div key={day} className="text-xs font-semibold text-textLight uppercase">{day}</div>
                      ))}
                    </div>

                    {/* Calendar cells */}
                    <div className="grid grid-cols-7 gap-1 text-center">
                      {renderCalendarDays()}
                    </div>

                    {/* Legend */}
                    <div className="mt-6 flex items-center justify-center space-x-6 text-[10px] font-semibold text-textSecondary border-t border-purple-500/10 pt-4">
                      <div className="flex items-center space-x-1.5">
                        <span className="w-3 h-3 bg-gradient-to-tr from-pink-400 to-rose-300 rounded-full"></span>
                        <span>Logged Period</span>
                      </div>
                      <div className="flex items-center space-x-1.5">
                        <span className="w-3 h-3 border-2 border-dashed border-primary bg-primary/5 rounded-full"></span>
                        <span>Predicted Start</span>
                      </div>
                      <div className="flex items-center space-x-1.5">
                        <span className="w-3 h-3 bg-primary rounded-full"></span>
                        <span>Today</span>
                      </div>
                    </div>
                  </div>

                  {/* Right: Cycle Logs list */}
                  <div className="glass-panel p-6 rounded-3xl flex flex-col justify-between">
                    <div>
                      <h3 className="text-base font-semibold text-textPrimary mb-3">Cycle Logs Timeline</h3>
                      {cycles.length === 0 ? (
                        <p className="text-xs text-textSecondary italic">No cycles recorded yet. Enter a cycle start date.</p>
                      ) : (
                        <div className="space-y-3 max-h-80 overflow-y-auto pr-1 scrollbar-hide">
                          {cycles.map((c) => {
                            const isUnclarifiedGap = c.gap_type === 'unclarified_gap' || (!c.gap_type && c.cycle_length > 45);
                            return (
                              <div key={c.cycle_id} className="p-3 rounded-2xl bg-white/60 border border-purple-100/50 flex justify-between items-center text-xs">
                                <div>
                                  <p className="font-semibold text-textPrimary">
                                    {new Date(c.start_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                                  </p>
                                  <p className="text-[10px] text-textSecondary">
                                    {c.end_date ? `End: ${new Date(c.end_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}` : 'Ongoing'}
                                    {c.cycle_length && ` • Cycle: ${c.cycle_length}d`}
                                  </p>
                                  {/* Interval Gap / Clarification Status */}
                                  <div className="mt-1.5 flex items-center gap-1.5 flex-wrap">
                                    {isUnclarifiedGap && (
                                      <>
                                        <span className="text-[9px] px-2 py-0.5 rounded-full font-medium bg-amber-50 text-amber-800 border border-amber-200">
                                          Tracking Gap (&gt;45d)
                                        </span>
                                        <button
                                          type="button"
                                          onClick={() => handleOpenClarifyModal(c.cycle_id)}
                                          className="text-[9px] px-2 py-0.5 rounded-md font-semibold bg-amber-600 text-white hover:bg-amber-700 transition"
                                        >
                                          Clarify
                                        </button>
                                      </>
                                    )}
                                    {c.gap_type === 'forgotten_entry' && (
                                      <>
                                        <span className="text-[9px] px-2 py-0.5 rounded-full font-medium bg-sky-50 text-sky-800 border border-sky-200">
                                          Reported Forgotten Log
                                        </span>
                                        <button
                                          type="button"
                                          onClick={() => handleOpenClarifyModal(c.cycle_id)}
                                          className="text-[9px] text-textLight hover:text-primary underline"
                                        >
                                          Edit
                                        </button>
                                      </>
                                    )}
                                    {c.gap_type === 'missed_period' && (
                                      <>
                                        <span className="text-[9px] px-2 py-0.5 rounded-full font-medium bg-purple-50 text-purple-800 border border-purple-200">
                                          Reported Missed Period
                                        </span>
                                        <button
                                          type="button"
                                          onClick={() => handleOpenClarifyModal(c.cycle_id)}
                                          className="text-[9px] text-textLight hover:text-primary underline"
                                        >
                                          Edit
                                        </button>
                                      </>
                                    )}
                                    {c.gap_type === 'confirmed_long_cycle' && (
                                      <>
                                        <span className="text-[9px] px-2 py-0.5 rounded-full font-medium bg-rose-50 text-rose-800 border border-rose-200">
                                          Reported Long Cycle
                                        </span>
                                        <button
                                          type="button"
                                          onClick={() => handleOpenClarifyModal(c.cycle_id)}
                                          className="text-[9px] text-textLight hover:text-primary underline"
                                        >
                                          Edit
                                        </button>
                                      </>
                                    )}
                                  </div>
                                </div>
                                <button
                                  type="button"
                                  onClick={() => handleDeleteCycle(c.cycle_id)}
                                  className="text-rose-500 p-1.5 rounded-lg hover:bg-rose-50 transition"
                                >
                                  <Trash2 size={14} />
                                </button>
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>

                    <button 
                      onClick={() => setShowCycleModal(true)} 
                      className="w-full mt-4 bg-primary text-white py-2.5 rounded-2xl text-xs font-semibold shadow-soft hover:shadow-md transition flex items-center justify-center space-x-1"
                    >
                      <Plus size={14} />
                      <span>Log Cycle Dates</span>
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* ==========================================
                TAB: LOGS (Timeline of Daily Entries)
                ========================================== */}
            {activeTab === 'logs' && (
              <div className="space-y-5 sm:space-y-6">
                <div className="glass-panel p-5 sm:p-6 rounded-2xl">
                  <h3 className="text-base sm:text-lg font-semibold text-textPrimary mb-1">Wellness Logs History</h3>
                  <p className="text-xs text-textSecondary mb-5">List of recorded symptoms and daily statuses</p>
                  
                  {logs.length === 0 ? (
                    <div className="text-center py-12 text-textLight italic text-xs">
                      No logs recorded yet. Complete the dashboard entry to see it here!
                    </div>
                  ) : (
                    <div className="space-y-3.5 max-h-[500px] overflow-y-auto pr-1 scrollbar-hide">
                      {logs.map((log) => (
                        <div key={log.log_id} className="p-4 rounded-2xl bg-white/80 border border-purple-100 flex flex-col sm:flex-row justify-between items-start sm:items-center space-y-3 sm:space-y-0 shadow-xs">
                          <div className="space-y-1">
                            <span className="text-[10px] font-bold text-primary bg-primary/10 px-2 py-0.5 rounded-full uppercase tracking-wider">
                              Cycle Day {log.cycle_day || '?'}
                            </span>
                            <h4 className="font-bold text-sm text-textPrimary mt-1">
                              {new Date(log.date).toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' })}
                            </h4>
                            <div className="flex flex-wrap gap-1.5 mt-2">
                              {log.mood && <span className="bg-purple-50 text-primary border border-purple-200/50 text-[10px] px-2 py-0.5 rounded-full">Mood: {log.mood}</span>}
                              {log.stress && <span className="bg-amber-50 text-amber-700 border border-amber-200/50 text-[10px] px-2 py-0.5 rounded-full">Stress: {log.stress}</span>}
                              {log.sleep_hours !== null && log.sleep_hours !== undefined && (
                                <span className="bg-blue-50 text-blue-700 border border-blue-200/50 text-[10px] px-2 py-0.5 rounded-full">Sleep: {log.sleep_hours} hrs</span>
                              )}
                              {log.energy_level && (
                                <span className="bg-emerald-50 text-emerald-700 border border-emerald-200/50 text-[10px] px-2 py-0.5 rounded-full font-medium inline-flex items-center">
                                  <Zap size={10} className="inline mr-1 text-emerald-600" />
                                  Energy: {log.energy_level}
                                </span>
                              )}
                            </div>

                            {/* Physiological symptoms: clearly distinguish None from untracked */}
                            <div className="flex flex-wrap gap-1 mt-2">
                              {log.cramps === 'None' && <span className="bg-slate-100 text-slate-600 text-[10px] px-2 py-0.5 rounded-lg">Cramps: None</span>}
                              {log.cramps && log.cramps !== 'None' && <span className="bg-rose-100 text-rose-700 text-[10px] px-2 py-0.5 rounded-lg font-semibold">Cramps: {log.cramps}</span>}

                              {log.fatigue === 'None' && <span className="bg-slate-100 text-slate-600 text-[10px] px-2 py-0.5 rounded-lg">Fatigue: None</span>}
                              {log.fatigue && log.fatigue !== 'None' && <span className="bg-orange-100 text-orange-700 text-[10px] px-2 py-0.5 rounded-lg font-semibold">Fatigue: {log.fatigue}</span>}

                              {log.flow === 'None' && <span className="bg-slate-100 text-slate-600 text-[10px] px-2 py-0.5 rounded-lg">Flow: None</span>}
                              {log.flow && log.flow !== 'None' && <span className="bg-pink-100 text-pink-700 text-[10px] px-2 py-0.5 rounded-lg font-semibold">Flow: {log.flow}</span>}

                              {!log.cramps && !log.fatigue && !log.flow && (
                                <span className="text-textLight text-xs italic">No physiological symptoms tracked</span>
                              )}
                            </div>

                            {/* Notes display if present */}
                            {log.notes && (
                              <div className="text-xs text-textSecondary bg-purple-50/50 p-2.5 rounded-xl mt-2 italic border border-purple-100/50 max-w-lg flex items-start gap-1.5">
                                <FileText size={12} className="text-purple-600 flex-shrink-0 mt-0.5" />
                                <span>{log.notes}</span>
                              </div>
                            )}
                          </div>

                          {/* Actions: Edit & Delete */}
                          <div className="flex items-center space-x-2 pt-2 sm:pt-0 self-end sm:self-center">
                            <button
                              onClick={() => handleEditLog(log)}
                              className="px-3 py-1.5 rounded-xl bg-purple-50 hover:bg-primary text-primary hover:text-white border border-purple-200/60 text-xs font-semibold transition flex items-center gap-1"
                            >
                              <Edit3 size={11} />
                              <span>Edit</span>
                            </button>
                            <button
                              onClick={() => handleDeleteLog(log.log_id)}
                              className="p-1.5 rounded-xl text-textLight hover:text-rose-600 hover:bg-rose-50 border border-transparent hover:border-rose-100 transition"
                              title="Delete this log"
                            >
                              <Trash2 size={15} />
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* ==========================================
                TAB: ANALYTICS
                ========================================== */}
            {activeTab === 'analytics' && (
              <div className="space-y-5 sm:space-y-6">
                {/* 1. Analytics Page Heading & Concise Summary */}
                <div className="glass-panel p-5 sm:p-6 rounded-2xl">
                  <div className="flex items-center space-x-3">
                    <div className="p-2 rounded-xl bg-primary/10 text-primary flex-shrink-0">
                      <BarChart2 size={20} />
                    </div>
                    <div>
                      <h3 className="text-base sm:text-lg font-semibold text-textPrimary">Cycle & Wellbeing Analytics</h3>
                      <p className="text-xs text-textSecondary mt-0.5">
                        Visual trends, recurring wellbeing patterns, and clinical insights across your logged history
                      </p>
                    </div>
                  </div>
                </div>

                {/* 2. Existing Charts: Cycle Length Trend, Mood Breakdown, Symptom Severity Frequency */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-5 sm:gap-6">
                  {/* Chart 1: Cycle Length Trend */}
                  <div className="glass-panel p-5 sm:p-6 rounded-2xl min-w-0 overflow-hidden flex flex-col justify-between">
                    <div>
                      <h3 className="text-sm font-semibold text-textPrimary mb-1">Cycle Length History (Days)</h3>
                      <p className="text-[11px] text-textSecondary mb-4">Past recorded menstrual cycle durations</p>
                    </div>
                    {analytics?.cycle_history.length > 0 ? (
                      <div className="h-60 sm:h-64 relative min-w-0 w-full">
                        <Bar
                          data={{
                            labels: analytics.cycle_history.map(c => new Date(c.start_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })),
                            datasets: [{
                              label: 'Cycle Duration',
                              data: analytics.cycle_history.map(c => c.cycle_length || 28),
                              backgroundColor: '#C4B5FD',
                              hoverBackgroundColor: '#8B5CF6',
                              borderRadius: 6
                            }]
                          }}
                          options={{
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: { legend: { display: false } },
                            scales: { y: { min: 20, max: 45 } }
                          }}
                        />
                      </div>
                    ) : (
                      <p className="text-xs text-textLight italic text-center py-12">Log multiple cycles to populate trend analytics.</p>
                    )}
                  </div>

                  {/* Chart 2: Mood Distribution */}
                  <div className="glass-panel p-5 sm:p-6 rounded-2xl min-w-0 overflow-hidden flex flex-col justify-between">
                    <div>
                      <h3 className="text-sm font-semibold text-textPrimary mb-1">Mood Frequency Breakdown</h3>
                      <p className="text-[11px] text-textSecondary mb-4">Distribution of self-reported emotional states</p>
                    </div>
                    {analytics?.mood_frequencies.length > 0 ? (
                      <div className="h-60 sm:h-64 flex justify-center relative min-w-0 w-full">
                        <Doughnut
                          data={{
                            labels: analytics.mood_frequencies.map(m => m.mood),
                            datasets: [{
                              data: analytics.mood_frequencies.map(m => m.count),
                              backgroundColor: ['#8B5CF6', '#C4B5FD', '#FBCFE8', '#93C5FD', '#FDE68A', '#FDA4AF'],
                              borderWidth: 1
                            }]
                          }}
                          options={{
                            responsive: true,
                            maintainAspectRatio: false,
                          }}
                        />
                      </div>
                    ) : (
                      <p className="text-xs text-textLight italic text-center py-12">Log daily moods to view emotional patterns.</p>
                    )}
                  </div>

                  {/* Chart 3: Symptoms severity analysis */}
                  <div className="glass-panel p-5 sm:p-6 rounded-2xl col-span-1 md:col-span-2 min-w-0 overflow-hidden">
                    <div>
                      <h3 className="text-sm font-semibold text-textPrimary mb-1">Symptom Severity Frequency</h3>
                      <p className="text-[11px] text-textSecondary mb-4">Incidents of physiological symptoms reported across active logs</p>
                    </div>
                    {analytics && Object.values(analytics.symptoms_frequencies).some(c => c > 0) ? (
                      <div className="h-60 sm:h-64 relative min-w-0 w-full">
                        <Bar
                          data={{
                            labels: Object.keys(analytics.symptoms_frequencies),
                            datasets: [{
                              label: 'Incidents Logged',
                              data: Object.values(analytics.symptoms_frequencies),
                              backgroundColor: '#FDA4AF',
                              hoverBackgroundColor: '#F43F5E',
                              borderRadius: 6
                            }]
                          }}
                          options={{
                            responsive: true,
                            maintainAspectRatio: false,
                            indexAxis: 'y',
                            plugins: { legend: { display: false } }
                          }}
                        />
                      </div>
                    ) : (
                      <p className="text-xs text-textLight italic text-center py-12">Physiological symptoms are currently all cleared.</p>
                    )}
                  </div>
                </div>

                {/* 3. Physical & Emotional Wellbeing Intelligence Pattern Cards */}
                {analytics?.wellbeing_patterns && (
                  <div className="glass-panel p-5 sm:p-6 rounded-2xl">
                    <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 mb-4">
                      <div className="flex items-center space-x-2.5">
                        <div className="p-1.5 rounded-xl bg-primary/10 text-primary flex-shrink-0">
                          <Sparkles size={18} />
                        </div>
                        <div>
                          <h3 className="text-base font-semibold text-textPrimary">Wellbeing Intelligence</h3>
                          <p className="text-xs text-textSecondary">Evidence-based pattern observations across your recorded cycles</p>
                        </div>
                      </div>
                      {analytics.wellbeing_patterns.status === 'supported' && (
                        <span className="text-[10px] font-bold px-2.5 py-1 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-200 flex items-center space-x-1">
                          <CheckCircle2 size={12} className="text-emerald-700" />
                          <span>Patterns Supported</span>
                        </span>
                      )}
                    </div>

                    {/* Insufficient Data State */}
                    {analytics.wellbeing_patterns.status === 'insufficient_data' && (!analytics.wellbeing_patterns.patterns || analytics.wellbeing_patterns.patterns.length === 0) && (
                      <div className="p-5 rounded-xl bg-purple-50/60 border border-purple-100/80 space-y-3">
                        <div className="flex items-start space-x-3">
                          <div className="p-2 rounded-xl bg-purple-100 text-primary mt-0.5 flex-shrink-0">
                            <Clock size={16} />
                          </div>
                          <div>
                            <h4 className="text-sm font-semibold text-textPrimary">Still Learning Your Personal Rhythm</h4>
                            <p className="text-xs text-textSecondary mt-1 leading-relaxed">
                              Wellbeing pattern detection requires multiple recorded cycles and consistent daily logs to identify genuine recurring rhythms without making assumptions.
                            </p>
                          </div>
                        </div>

                        {analytics.wellbeing_patterns.insufficient_data_reasons && analytics.wellbeing_patterns.insufficient_data_reasons.length > 0 && (
                          <div className="pt-2 border-t border-purple-200/50 space-y-1.5">
                            <span className="text-[10px] font-bold text-textLight uppercase tracking-wider">Tracking Milestones Ahead:</span>
                            {analytics.wellbeing_patterns.insufficient_data_reasons.map((reason, idx) => (
                              <div key={idx} className="flex items-center space-x-2 text-xs text-textSecondary">
                                <span className="w-1.5 h-1.5 rounded-full bg-primary/60 flex-shrink-0"></span>
                                <span>{reason}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Unreliable History State */}
                    {analytics.wellbeing_patterns.status === 'unreliable_history' && (
                      <div className="p-4 rounded-xl bg-amber-50/70 border border-amber-200/70 flex items-start space-x-3 mb-4">
                        <AlertCircle size={18} className="text-amber-700 mt-0.5 flex-shrink-0" />
                        <div>
                          <h4 className="text-sm font-semibold text-amber-900">Cycle History Clarification Recommended</h4>
                          <p className="text-xs text-amber-800 mt-1 leading-relaxed">
                            Your cycle history contains unclarified date gaps. Clarifying those intervals in your cycle history helps ensure pattern detection is based on reliable timelines.
                          </p>
                        </div>
                      </div>
                    )}

                    {/* Patterns Grid */}
                    {analytics.wellbeing_patterns.patterns && analytics.wellbeing_patterns.patterns.length > 0 && (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {analytics.wellbeing_patterns.patterns.map((p) => {
                          let badge = null;
                          if (p.evidence_status === 'supported') {
                            badge = (
                              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-200 flex items-center space-x-1">
                                <CheckCircle2 size={11} className="text-emerald-700" />
                                <span>Supported Pattern</span>
                              </span>
                            );
                          } else if (p.evidence_status === 'insufficient_data') {
                            badge = (
                              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-purple-100 text-purple-800 border border-purple-200 flex items-center space-x-1">
                                <Clock size={11} className="text-purple-700" />
                                <span>Collecting Evidence</span>
                              </span>
                            );
                          } else if (p.evidence_status === 'non_recurring') {
                            badge = (
                              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200 flex items-center space-x-1">
                                <HelpCircle size={11} className="text-slate-600" />
                                <span>Varied Across Cycles</span>
                              </span>
                            );
                          } else if (p.evidence_status === 'unreliable_history') {
                            badge = (
                              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 border border-amber-200 flex items-center space-x-1">
                                <AlertCircle size={11} className="text-amber-700" />
                                <span>History Unverified</span>
                              </span>
                            );
                          }

                          return (
                            <div key={p.pattern_id} className="p-4 rounded-2xl bg-white/70 border border-purple-100/80 flex flex-col justify-between">
                              <div>
                                <div className="flex justify-between items-start">
                                  <span className="text-[10px] font-semibold text-textLight uppercase tracking-wider">
                                    {p.metric} observation
                                  </span>
                                  {badge}
                                </div>

                                <h4 className="font-bold text-sm text-textPrimary mt-1.5">{p.title}</h4>
                                <p className="text-xs text-textSecondary mt-1 leading-relaxed">{p.observation}</p>

                                {/* Evidence Metrics */}
                                <div className="flex flex-wrap gap-1.5 mt-3">
                                  <span className="bg-purple-50 text-purple-700 border border-purple-200/50 text-[10px] px-2 py-0.5 rounded-md font-medium">
                                    Window: {p.cycle_window} {p.window_is_estimated ? '(Estimated)' : ''}
                                  </span>
                                  {p.distinct_cycles_observed !== null && p.distinct_cycles_observed !== undefined && (
                                    <span className="bg-purple-50 text-purple-700 border border-purple-200/50 text-[10px] px-2 py-0.5 rounded-md font-medium">
                                      {p.distinct_cycles_observed} cycle{p.distinct_cycles_observed === 1 ? '' : 's'} tracked
                                    </span>
                                  )}
                                  {p.recurrence_count !== null && p.recurrence_count !== undefined && p.recurrence_denominator !== null && p.recurrence_denominator !== undefined && (
                                    <span className="bg-purple-50 text-purple-700 border border-purple-200/50 text-[10px] px-2 py-0.5 rounded-md font-medium">
                                      Present in {p.recurrence_count} of {p.recurrence_denominator} cycles
                                    </span>
                                  )}
                                  {p.relevant_logged_days !== null && p.relevant_logged_days !== undefined && (
                                    <span className="bg-purple-50 text-purple-700 border border-purple-200/50 text-[10px] px-2 py-0.5 rounded-md font-medium">
                                      {p.relevant_logged_days} logged day{p.relevant_logged_days === 1 ? '' : 's'}
                                    </span>
                                  )}
                                </div>
                              </div>

                              {/* Supportive Care Tip */}
                              {p.supportive_recommendation && (
                                <div className="mt-3.5 p-3 rounded-xl bg-purple-50/70 border border-purple-100/70 flex items-start space-x-2 text-xs text-purple-900">
                                  <Sparkles size={14} className="text-primary mt-0.5 flex-shrink-0" />
                                  <div className="leading-relaxed">
                                    <span className="font-semibold text-primary">Supportive Care Tip: </span>
                                    <span>{p.supportive_recommendation}</span>
                                  </div>
                                </div>
                              )}

                              <div className="mt-2 text-[10px] text-textLight italic">
                                * Observational trend based on your self-reported logs. Not a medical diagnosis.
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                )}

                {/* 4. Existing Written Insights and Supporting Explanations */}
                <div className="glass-panel p-5 sm:p-6 rounded-2xl bg-gradient-to-tr from-purple-100/50 to-pink-100/50 border border-white/60">
                  <div className="flex items-center space-x-2 mb-3">
                    <Sparkles className="text-primary fill-primary/10" size={18} />
                    <h3 className="text-sm sm:text-base font-semibold text-textPrimary">Summary Health Insights</h3>
                  </div>
                  <ul className="space-y-2 text-xs text-textSecondary pl-1">
                    {analytics?.insights.map((ins, idx) => (
                      <li key={idx} className="flex items-start space-x-2">
                        <span className="text-primary mt-0.5">•</span>
                        <span>{ins}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                {/* 5. Doctor-Visit Clinical Export Card */}
                <div className="glass-panel p-5 sm:p-6 rounded-2xl bg-gradient-to-r from-purple-50 via-white to-pink-50 border border-purple-200/70 shadow-xs">
                  <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                    <div className="flex items-start space-x-3.5">
                      <div className="p-2.5 rounded-2xl bg-primary/10 text-primary flex-shrink-0 mt-0.5">
                        <FileText size={22} />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="text-sm sm:text-base font-bold text-textPrimary">Doctor-Visit Clinical Summary</h3>
                          <span className="text-[10px] font-semibold bg-primary/10 text-primary px-2 py-0.5 rounded-full">
                            Clinician Ready
                          </span>
                        </div>
                        <p className="text-xs text-textSecondary mt-1 max-w-xl leading-relaxed">
                          Prepare for your next medical appointment with an organized, evidence-based summary. Strictly separates your recorded cycle facts, statistical estimates, and self-reported symptoms.
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 w-full sm:w-auto">
                      <button
                        onClick={handleOpenDoctorSummary}
                        className="flex-1 sm:flex-initial px-4 py-2.5 rounded-xl bg-primary hover:bg-primary-dark text-white text-xs font-semibold shadow-soft hover:shadow-md transition flex items-center justify-center gap-1.5"
                      >
                        <FileText size={14} />
                        <span>View Summary</span>
                      </button>
                      <button
                        onClick={handlePrintDoctorSummary}
                        className="px-3.5 py-2.5 rounded-xl bg-white hover:bg-purple-50 text-primary border border-purple-200 text-xs font-semibold shadow-xs transition flex items-center justify-center gap-1.5"
                        title="Print or Save PDF report"
                      >
                        <Printer size={14} />
                        <span>Print PDF</span>
                      </button>
                    </div>
                  </div>
                </div>

                {/* 6. Clinical Safety Guidance & Red-Flag Warnings */}
                <div className="glass-panel p-5 sm:p-6 rounded-2xl bg-amber-50/50 border border-amber-200/60">
                  <div className="flex items-start space-x-3">
                    <div className="p-2 rounded-xl bg-amber-100 text-amber-800 flex-shrink-0 mt-0.5">
                      <AlertCircle size={18} />
                    </div>
                    <div className="space-y-1.5">
                      <h4 className="text-sm font-bold text-amber-950">Clinical Safety Guidance & When to Consult a Doctor</h4>
                      <p className="text-xs text-amber-900 leading-relaxed">
                        OvaCare AI tracks personal wellness trends and algorithmic estimates to support your self-care. It does not provide medical diagnoses or replace physician care. Please consult a licensed healthcare professional if you experience:
                      </p>
                      <ul className="text-xs text-amber-900/90 list-disc list-inside space-y-1 pt-1">
                        <li><strong>Severe or Acute Pain:</strong> Pelvic or abdominal pain that is sudden, debilitating, or accompanied by fever/vomiting.</li>
                        <li><strong>Abnormal Bleeding:</strong> Bleeding soaking through a pad or tampon every 1–2 hours for multiple consecutive hours.</li>
                        <li><strong>Cycle Irregularities:</strong> Cycles persistently shorter than 21 days, longer than 35 days, or absent for over 90 days.</li>
                        <li><strong>Bleeding Between Periods:</strong> Unexpected spotting or bleeding between menstrual cycles or after intercourse.</li>
                      </ul>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* ==========================================
                TAB: REMINDERS & PROFILE
                ========================================== */}
            {activeTab === 'profile' && (
              <div className="space-y-5 sm:space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-5 sm:gap-6">
                  {/* Reminders List & Manager */}
                  <div className="glass-panel p-5 sm:p-6 rounded-2xl">
                    <h3 className="text-base font-semibold text-textPrimary mb-1">Smart Reminders</h3>
                    <p className="text-xs text-textSecondary mb-4">Manage medicine and hydration alerts</p>

                    <form onSubmit={handleAddReminder} className="flex gap-2 mb-4">
                      <select
                        value={reminderType}
                        onChange={(e) => setReminderType(e.target.value)}
                        className="flex-grow px-2 py-2 rounded-xl border border-purple-100 text-xs focus:ring-1 focus:ring-primary outline-none"
                      >
                        <option value="Hydration">Hydration Alert</option>
                        <option value="Medicine">Medicine Dose</option>
                        <option value="Period">Period Prediction</option>
                        <option value="Self-Care">Self-Care Reminder</option>
                      </select>
                      <input
                        type="date"
                        value={reminderDate}
                        onChange={(e) => setReminderDate(e.target.value)}
                        className="px-2 py-2 rounded-xl border border-purple-100 text-xs focus:ring-1 focus:ring-primary outline-none w-32"
                      >
                      </input>
                      <button 
                        type="submit" 
                        className="bg-primary text-white px-3 rounded-xl hover:bg-primary-dark transition text-xs font-semibold"
                      >
                        Add
                      </button>
                    </form>

                    <div className="space-y-2.5 max-h-60 overflow-y-auto pr-1 scrollbar-hide">
                      {reminders.length === 0 ? (
                        <p className="text-xs text-textSecondary italic py-4">No reminders scheduled.</p>
                      ) : (
                        reminders.map(rem => (
                          <div key={rem.reminder_id} className="p-3 rounded-xl bg-white/70 border border-purple-100 flex justify-between items-center text-xs">
                            <div className="flex items-center space-x-3">
                              <input
                                type="checkbox"
                                checked={rem.completed}
                                onChange={() => handleToggleReminder(rem.reminder_id)}
                                className="rounded text-primary focus:ring-primary h-4 w-4 cursor-pointer"
                              />
                              <div>
                                <div className="flex items-center space-x-1.5">
                                  {rem.reminder_type === 'Hydration' && <Droplets size={14} className="text-blue-500 flex-shrink-0" />}
                                  {rem.reminder_type === 'Medicine' && <Activity size={14} className="text-emerald-500 flex-shrink-0" />}
                                  {rem.reminder_type === 'Period' && <CalendarIcon size={14} className="text-primary flex-shrink-0" />}
                                  {rem.reminder_type === 'Self-Care' && <Heart size={14} className="text-pink-500 flex-shrink-0" />}
                                  {!['Hydration', 'Medicine', 'Period', 'Self-Care'].includes(rem.reminder_type) && <Bell size={14} className="text-primary flex-shrink-0" />}
                                  <span className={rem.completed ? 'line-through text-textLight' : 'font-medium text-textPrimary'}>
                                    {rem.reminder_type}
                                  </span>
                                </div>
                                <span className="block text-[10px] text-textSecondary mt-0.5">
                                  {new Date(rem.reminder_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                                </span>
                              </div>
                            </div>
                            <button 
                              onClick={() => handleDeleteReminder(rem.reminder_id)} 
                              className="text-rose-400 p-1.5 rounded-lg hover:bg-rose-50 transition"
                              title="Delete reminder"
                            >
                              <Trash2 size={13} />
                            </button>
                          </div>
                        ))
                      )}
                    </div>
                  </div>

                  {/* Profile Settings */}
                  <div className="glass-panel p-5 sm:p-6 rounded-2xl flex flex-col justify-between">
                    <div>
                      <h3 className="text-base font-semibold text-textPrimary mb-1">User Settings</h3>
                      <p className="text-xs text-textSecondary mb-4">Edit profile and custom medical metrics</p>

                      <div className="space-y-4">
                        <div>
                          <label className="block text-[10px] font-semibold text-textSecondary uppercase tracking-wider mb-1">Username</label>
                          <div className="text-sm font-semibold text-textPrimary px-3 py-2 bg-white/40 border border-purple-100 rounded-xl">
                            {user.username}
                          </div>
                        </div>
                        <div>
                          <label className="block text-[10px] font-semibold text-textSecondary uppercase tracking-wider mb-1">Email Address</label>
                          <div className="text-sm text-textSecondary px-3 py-2 bg-white/40 border border-purple-100 rounded-xl">
                            {user.email}
                          </div>
                        </div>
                        
                        <div className="flex items-center space-x-2 pt-2">
                          <input
                            type="checkbox"
                            id="profilePcosToggle"
                            checked={user.has_pcos}
                            onChange={(e) => handleUpdateProfilePcos(e.target.checked)}
                            className="rounded text-primary focus:ring-primary h-4 w-4 cursor-pointer"
                          />
                          <label htmlFor="profilePcosToggle" className="text-xs text-textPrimary font-medium select-none cursor-pointer">
                            Active PCOS / Hormonal irregularities log
                          </label>
                        </div>
                      </div>
                    </div>

                    <div className="mt-8 border-t border-purple-100 pt-4 text-center">
                      <p className="text-[10px] text-textLight">HIPAA Compliant User Records System</p>
                      <button 
                        onClick={handleLogout} 
                        className="mt-2 text-xs text-rose-500 font-semibold hover:underline"
                      >
                        Sign Out of Account
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* ==========================================
                TAB: ADMIN PORTAL
                ========================================== */}
            {activeTab === 'admin' && (
              <div className="space-y-6">
                <div className="glass-panel p-6 rounded-3xl">
                  <h3 className="text-lg font-semibold text-textPrimary mb-1">Admin Database Dashboard</h3>
                  <p className="text-xs text-textSecondary mb-6">Database statistics overview and synthetic records audit</p>
                  
                  {adminStats ? (
                    <div className="space-y-6">
                      {/* Aggregate Metrics Grid */}
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div className="p-4 rounded-2xl bg-purple-50 border border-purple-100 text-center">
                          <span className="text-[10px] text-textSecondary font-semibold uppercase">Total Users</span>
                          <h4 className="text-2xl font-bold text-primary mt-1">{adminStats.total_users}</h4>
                        </div>
                        <div className="p-4 rounded-2xl bg-fuchsia-50 border border-fuchsia-100 text-center">
                          <span className="text-[10px] text-textSecondary font-semibold uppercase">Cycles Seeded</span>
                          <h4 className="text-2xl font-bold text-fuchsia-600 mt-1">{adminStats.total_cycles}</h4>
                        </div>
                        <div className="p-4 rounded-2xl bg-pink-50 border border-pink-100 text-center">
                          <span className="text-[10px] text-textSecondary font-semibold uppercase">Wellness Logs</span>
                          <h4 className="text-2xl font-bold text-rose-500 mt-1">{adminStats.total_logs}</h4>
                        </div>
                        <div className="p-4 rounded-2xl bg-blue-50 border border-blue-100 text-center">
                          <span className="text-[10px] text-textSecondary font-semibold uppercase">PCOS Rate</span>
                          <h4 className="text-2xl font-bold text-blue-600 mt-1">{adminStats.pcos_ratio_percentage}%</h4>
                        </div>
                      </div>

                      {/* PCOS vs Cycle Length Analysis */}
                      <div className="p-4 rounded-2xl bg-white/50 border border-purple-100/50">
                        <h4 className="text-xs font-semibold text-textPrimary mb-3 uppercase tracking-wider">Hormonal Profile Analysis</h4>
                        <table className="w-full text-xs text-left">
                          <thead>
                            <tr className="border-b border-purple-100 text-textSecondary pb-2">
                              <th className="py-2">PCOS Profile</th>
                              <th className="py-2">Avg Cycle Length</th>
                              <th className="py-2">Avg Period Length</th>
                              <th className="py-2">Cycles Audited</th>
                            </tr>
                          </thead>
                          <tbody>
                            {adminStats.pcos_cycle_analysis.map((row, idx) => (
                              <tr key={idx} className="border-b border-purple-50 text-textPrimary">
                                <td className="py-2.5 font-medium">{row.has_pcos ? 'Yes (Hormonal Irregularity)' : 'No (Standard Regular)'}</td>
                                <td className="py-2.5">{round(row.avg_cycle, 1)} Days</td>
                                <td className="py-2.5">{round(row.avg_period, 1)} Days</td>
                                <td className="py-2.5">{row.cycle_count} logs</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>

                      {/* Aggregate Lifestyle Cohorts Activity */}
                      <div>
                        <h4 className="text-xs font-semibold text-textPrimary mb-3 uppercase tracking-wider">Lifestyle Cohorts Activity (De-identified)</h4>
                        <div className="overflow-x-auto">
                          <table className="w-full text-xs text-left border-collapse">
                            <thead>
                              <tr className="border-b border-purple-100 text-textSecondary text-[10px] uppercase font-bold">
                                <th className="py-2 pb-1">Lifestyle Cohort</th>
                                <th className="py-2 pb-1">Enrolled Patients</th>
                                <th className="py-2 pb-1">Total Logs Tracked</th>
                                <th className="py-2 pb-1 text-right">Data Privacy Status</th>
                              </tr>
                            </thead>
                            <tbody>
                              {adminStats.activity_cohorts && adminStats.activity_cohorts.length > 0 ? (
                                adminStats.activity_cohorts.map((c, idx) => (
                                  <tr key={idx} className="border-b border-purple-50 hover:bg-purple-50/30 text-textPrimary transition">
                                    <td className="py-2.5 font-medium">{c.lifestyle}</td>
                                    <td className="py-2.5">{c.user_count} Patients</td>
                                    <td className="py-2.5 font-bold text-primary">{c.total_logs}</td>
                                    <td className="py-2.5 text-right">
                                      <span className="text-[9px] bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded-full font-semibold">
                                        De-identified
                                      </span>
                                    </td>
                                  </tr>
                                ))
                              ) : (
                                <tr>
                                  <td colSpan={4} className="py-4 text-center text-textLight italic">No cohort statistics available.</td>
                                </tr>
                              )}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <p className="text-xs text-textLight italic text-center py-6">Connecting database admin metrics...</p>
                  )}
                </div>
              </div>
            )}

            {/* Community Module Tab */}
            {activeTab === 'community' && (
              <Community user={user} token={token} apiBase={API_BASE} />
            )}

            {/* 3D AI Companion Module Tab */}
            {activeTab === 'companion' && (
              <Companion user={user} token={token} apiBase={API_BASE} />
            )}
          </>
        )}
      </main>

      {/* Floating Bottom Nav Bar */}
      <nav
        aria-label="Main Navigation"
        className="fixed bottom-4 sm:bottom-6 left-1/2 transform -translate-x-1/2 glass-panel rounded-full px-3 sm:px-6 py-2 sm:py-3 flex space-x-3 sm:space-x-7 items-center shadow-lg border border-white/60 z-50 max-w-[calc(100vw-1.5rem)] overflow-x-auto scrollbar-hide"
      >
        {[
          { tab: 'dashboard', icon: Home, label: 'Home' },
          { tab: 'companion', icon: Sparkles, label: 'Companion' },
          { tab: 'community', icon: MessageSquare, label: 'Community' },
          { tab: 'calendar', icon: CalendarIcon, label: 'Calendar' },
          { tab: 'logs', icon: Heart, label: 'Logs' },
          { tab: 'analytics', icon: BarChart2, label: 'Charts' },
          { tab: 'profile', icon: User, label: 'Settings' }
        ].map(({ tab, icon: Icon, label }) => {
          const isActive = activeTab === tab;
          return (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              aria-label={label}
              className="flex flex-col items-center justify-center relative transition group focus:outline-none"
            >
              <Icon 
                size={20}
                className={`transition-colors duration-200 ${isActive ? 'text-primary' : 'text-textLight hover:text-textSecondary'}`}
              />
              <span className={`text-[9px] font-medium mt-0.5 transition-colors duration-200 ${isActive ? 'text-primary font-bold' : 'text-textLight'}`}>
                {label}
              </span>
              {isActive && (
                <span className="absolute -top-1 w-1.5 h-1.5 bg-primary rounded-full animate-pulse"></span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Cycle Logging Modal Dialog */}
      {showCycleModal && (
        <div className="fixed inset-0 bg-purple-950/20 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="glass-panel w-full max-w-sm rounded-2xl p-5 sm:p-6 shadow-premium relative max-h-[90vh] overflow-y-auto">
            <h3 className="text-base font-semibold text-textPrimary mb-1">Add Cycle Dates</h3>
            <p className="text-xs text-textSecondary mb-4">Record a new menstrual start event</p>
            
            <form onSubmit={handleAddCycle} className="space-y-4">
              <div>
                <label className="block text-[10px] font-semibold text-textSecondary uppercase tracking-wider mb-1">Start Date</label>
                <input
                  type="date"
                  value={cycleStartDate}
                  onChange={(e) => setCycleStartDate(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl border border-purple-100 text-xs focus:ring-1 focus:ring-primary outline-none"
                  required
                />
              </div>

              <div>
                <label className="block text-[10px] font-semibold text-textSecondary uppercase tracking-wider mb-1">End Date (Optional)</label>
                <input
                  type="date"
                  value={cycleEndDate}
                  onChange={(e) => setCycleEndDate(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl border border-purple-100 text-xs focus:ring-1 focus:ring-primary outline-none"
                />
              </div>

              <div className="flex space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowCycleModal(false)}
                  className="w-1/2 border border-purple-100 text-textSecondary py-2 rounded-xl text-xs font-semibold hover:bg-purple-50 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="w-1/2 bg-primary text-white py-2 rounded-xl text-xs font-semibold shadow-soft hover:bg-primary-dark transition"
                >
                  Save Cycle
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Cycle Clarification Modal Dialog */}
      {showClarifyModal && (
        <div className="fixed inset-0 bg-purple-950/20 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="glass-panel w-full max-w-md rounded-2xl p-5 sm:p-6 shadow-premium relative bg-white/95 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-start mb-3">
              <div>
                <h3 className="text-base font-semibold text-textPrimary">Clarify Cycle Interval</h3>
                <p className="text-xs text-textSecondary mt-0.5">
                  Help OvaCare understand this interval with your reported experience
                </p>
              </div>
              <button
                type="button"
                onClick={() => setShowClarifyModal(false)}
                className="text-textLight hover:text-textPrimary p-1 rounded-lg text-sm"
                disabled={clarifyingLoading}
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleClarifySubmit} className="space-y-4">
              <div className="space-y-2.5">
                <label className="text-[10px] font-semibold text-textSecondary uppercase tracking-wider block mb-1">
                  Select the explanation that best matches your experience:
                </label>

                <label className={`flex items-start p-3 rounded-2xl border transition cursor-pointer ${clarifyOption === 'forgotten_entry' ? 'border-primary bg-primary/5 ring-1 ring-primary' : 'border-purple-100/60 bg-white hover:bg-purple-50/30'}`}>
                  <input
                    type="radio"
                    name="clarifyOption"
                    value="forgotten_entry"
                    checked={clarifyOption === 'forgotten_entry'}
                    onChange={(e) => setClarifyOption(e.target.value)}
                    className="mt-0.5 text-primary focus:ring-primary h-4 w-4"
                  />
                  <div className="ml-3">
                    <span className="text-xs font-semibold text-textPrimary block">I forgot to log a period.</span>
                    <span className="text-[11px] text-textSecondary">You had bleeding during this interval but did not record it in the app. This interval will be excluded from cycle length averages.</span>
                  </div>
                </label>

                <label className={`flex items-start p-3 rounded-2xl border transition cursor-pointer ${clarifyOption === 'missed_period' ? 'border-primary bg-primary/5 ring-1 ring-primary' : 'border-purple-100/60 bg-white hover:bg-purple-50/30'}`}>
                  <input
                    type="radio"
                    name="clarifyOption"
                    value="missed_period"
                    checked={clarifyOption === 'missed_period'}
                    onChange={(e) => setClarifyOption(e.target.value)}
                    className="mt-0.5 text-primary focus:ring-primary h-4 w-4"
                  />
                  <div className="ml-3">
                    <span className="text-xs font-semibold text-textPrimary block">I did not have a period during this interval.</span>
                    <span className="text-[11px] text-textSecondary">You did not experience menstrual bleeding during this time. Treated as your reported experience, not a clinical diagnosis.</span>
                  </div>
                </label>

                <label className={`flex items-start p-3 rounded-2xl border transition cursor-pointer ${clarifyOption === 'confirmed_long_cycle' ? 'border-primary bg-primary/5 ring-1 ring-primary' : 'border-purple-100/60 bg-white hover:bg-purple-50/30'}`}>
                  <input
                    type="radio"
                    name="clarifyOption"
                    value="confirmed_long_cycle"
                    checked={clarifyOption === 'confirmed_long_cycle'}
                    onChange={(e) => setClarifyOption(e.target.value)}
                    className="mt-0.5 text-primary focus:ring-primary h-4 w-4"
                  />
                  <div className="ml-3">
                    <span className="text-xs font-semibold text-textPrimary block">This was a genuinely long cycle.</span>
                    <span className="text-[11px] text-textSecondary">This was a single extended cycle for you. Contributes to your cycle irregularity assessment.</span>
                  </div>
                </label>
              </div>

              <div className="bg-purple-50/60 rounded-xl p-3 border border-purple-100/50 text-[10px] text-textSecondary leading-relaxed">
                <Info size={12} className="inline mr-1 text-primary -mt-0.5" />
                This clarification updates only your personal cycle history, recalculates contributing intervals, and refreshes your prediction without diagnosing any medical condition.
              </div>

              <div className="flex space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowClarifyModal(false)}
                  disabled={clarifyingLoading}
                  className="w-1/2 border border-purple-100 text-textSecondary py-2.5 rounded-xl text-xs font-semibold hover:bg-purple-50 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={clarifyingLoading || !clarifyOption}
                  className="w-1/2 bg-primary hover:bg-primary-dark text-white py-2.5 rounded-xl text-xs font-semibold shadow-soft hover:shadow-md transition disabled:opacity-50"
                >
                  {clarifyingLoading ? 'Updating...' : 'Save Clarification'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ==========================================
          MODAL: DOCTOR-VISIT CLINICAL SUMMARY
          ========================================== */}
      {showDoctorModal && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-fadeIn">
          <div className="bg-white rounded-3xl p-6 sm:p-7 max-w-3xl w-full border border-purple-100 shadow-2xl space-y-5 max-h-[88vh] overflow-y-auto">
            {/* Modal Header */}
            <div className="flex justify-between items-start pb-3 border-b border-purple-100/80">
              <div className="flex items-center space-x-3">
                <div className="p-2.5 rounded-2xl bg-primary/10 text-primary">
                  <FileText size={22} />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-base sm:text-lg font-bold text-textPrimary">Doctor-Visit Clinical Summary</h3>
                    <span className="text-[10px] font-bold bg-primary/10 text-primary px-2.5 py-0.5 rounded-full">
                      Clinician Review
                    </span>
                  </div>
                  <p className="text-xs text-textSecondary mt-0.5">
                    Separating Recorded Facts, Statistical Estimates, and User-Reported Symptoms
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setShowDoctorModal(false)}
                className="text-textLight hover:text-textPrimary p-1.5 rounded-xl hover:bg-slate-100 transition text-sm"
              >
                ✕
              </button>
            </div>

            {doctorSummaryLoading ? (
              <div className="text-center py-16 space-y-3">
                <div className="inline-block animate-spin rounded-full h-8 w-8 border-3 border-primary border-t-transparent"></div>
                <p className="text-xs text-textSecondary">Compiling clinical categories and verifying boundaries...</p>
              </div>
            ) : doctorSummaryData ? (
              <div className="space-y-5">
                {/* Patient Context & Non-Diagnostic Notice */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 p-3.5 bg-slate-50 rounded-2xl border border-slate-200/70 text-xs">
                  <div>
                    <span className="text-[10px] uppercase font-bold text-slate-500 block">Patient</span>
                    <span className="font-semibold text-textPrimary">{doctorSummaryData.patient_context?.username || user?.username}</span>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase font-bold text-slate-500 block">Age</span>
                    <span className="font-semibold text-textPrimary">{doctorSummaryData.patient_context?.age || 'Unspecified'}</span>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase font-bold text-slate-500 block">Lifestyle</span>
                    <span className="font-semibold text-textPrimary">{doctorSummaryData.patient_context?.lifestyle || 'Moderate'}</span>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase font-bold text-slate-500 block">PCOS Reported</span>
                    <span className="font-semibold text-textPrimary">{doctorSummaryData.patient_context?.has_pcos_reported ? 'Yes' : 'No'}</span>
                  </div>
                </div>

                <div className="p-3 bg-amber-50/80 rounded-xl border border-amber-200/80 text-[11px] text-amber-900 leading-relaxed flex items-start space-x-2">
                  <Info size={14} className="text-amber-700 flex-shrink-0 mt-0.5" />
                  <div>
                    <strong>Clinical Notice: </strong>
                    {doctorSummaryData.clinical_disclaimer}
                  </div>
                </div>

                {/* Category 1: Recorded Facts */}
                <div className="rounded-2xl border border-emerald-200 bg-emerald-50/30 overflow-hidden">
                  <div className="px-4 py-2.5 bg-emerald-100/70 text-emerald-900 flex justify-between items-center">
                    <span className="font-bold text-xs uppercase tracking-wider">Category 1 — Recorded Facts</span>
                    <span className="text-[11px] font-semibold bg-emerald-200/70 px-2 py-0.5 rounded-full">
                      {doctorSummaryData.category_1_recorded_facts?.total_cycles_recorded || 0} cycles logged
                    </span>
                  </div>
                  <div className="p-4 space-y-3">
                    <p className="text-[11px] text-emerald-950 leading-relaxed">
                      {doctorSummaryData.category_1_recorded_facts?.description}
                    </p>
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-xs">
                        <thead>
                          <tr className="border-b border-emerald-200 text-[10px] uppercase text-emerald-800">
                            <th className="pb-1.5 font-bold">Start Date</th>
                            <th className="pb-1.5 font-bold">End Date</th>
                            <th className="pb-1.5 font-bold">Cycle Length</th>
                            <th className="pb-1.5 font-bold">Period Length</th>
                            <th className="pb-1.5 font-bold">Status</th>
                            <th className="pb-1.5 font-bold">Gap Clarification</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-emerald-100 text-slate-700">
                          {(doctorSummaryData.category_1_recorded_facts?.cycles || []).map((c, idx) => (
                            <tr key={idx}>
                              <td className="py-1.5">{c.start_date || '—'}</td>
                              <td className="py-1.5">{c.end_date || '—'}</td>
                              <td className="py-1.5 font-semibold text-emerald-900">{c.recorded_cycle_length ? `${c.recorded_cycle_length}d` : '—'}</td>
                              <td className="py-1.5">{c.recorded_period_length ? `${c.recorded_period_length}d` : '—'}</td>
                              <td className="py-1.5">{c.is_irregular ? 'Irregular' : 'Regular'}</td>
                              <td className="py-1.5 text-[10px] text-slate-500">{c.gap_clarification}</td>
                            </tr>
                          ))}
                          {(!doctorSummaryData.category_1_recorded_facts?.cycles || doctorSummaryData.category_1_recorded_facts.cycles.length === 0) && (
                            <tr>
                              <td colSpan="6" className="py-3 text-center text-slate-400 italic">No cycle onset dates recorded yet.</td>
                            </tr>
                          )}
                        </tbody>
                      </table>
                    </div>

                    {/* Flow distribution */}
                    <div className="pt-2 border-t border-emerald-200/50 flex flex-wrap items-center gap-1.5">
                      <span className="text-[10px] font-bold text-emerald-900 uppercase mr-1">Flow Days Logged:</span>
                      {Object.entries(doctorSummaryData.category_1_recorded_facts?.menstrual_flow_records?.flow_distribution || {}).map(([k, v]) => (
                        <span key={k} className="text-[10px] font-medium bg-white px-2 py-0.5 rounded-md border border-emerald-200 text-slate-700">
                          <strong>{k}:</strong> {v}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Category 2: Statistical Estimates */}
                <div className="rounded-2xl border border-purple-200 bg-purple-50/30 overflow-hidden">
                  <div className="px-4 py-2.5 bg-purple-100/70 text-purple-900 flex justify-between items-center">
                    <span className="font-bold text-xs uppercase tracking-wider">Category 2 — Statistical Estimates & Predictions</span>
                    <span className="text-[11px] font-semibold bg-purple-200/70 px-2 py-0.5 rounded-full">Algorithmic Model</span>
                  </div>
                  <div className="p-4 space-y-3">
                    <p className="text-[11px] text-purple-950 leading-relaxed">
                      {doctorSummaryData.category_2_statistical_estimates?.description}
                    </p>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                      <div className="p-3 bg-white rounded-xl border border-purple-100 shadow-2xs">
                        <span className="text-[10px] text-slate-500 block">Average Cycle Length</span>
                        <span className="text-base font-bold text-primary">{doctorSummaryData.category_2_statistical_estimates?.average_cycle_length_days} days</span>
                      </div>
                      <div className="p-3 bg-white rounded-xl border border-purple-100 shadow-2xs">
                        <span className="text-[10px] text-slate-500 block">Average Period Length</span>
                        <span className="text-base font-bold text-primary">{doctorSummaryData.category_2_statistical_estimates?.average_period_length_days} days</span>
                      </div>
                      <div className="p-3 bg-white rounded-xl border border-purple-100 shadow-2xs">
                        <span className="text-[10px] text-slate-500 block">Next Estimated Period</span>
                        <span className="text-base font-bold text-primary">
                          {doctorSummaryData.category_2_statistical_estimates?.predicted_next_cycle?.estimated_next_start_date || 'Pending'}
                        </span>
                      </div>
                    </div>
                    <div className="text-xs text-slate-700">
                      <strong>Regularity Assessment: </strong>
                      {doctorSummaryData.category_2_statistical_estimates?.regularity_assessment}
                    </div>
                    <div className="text-[10px] text-slate-500 italic">
                      * {doctorSummaryData.category_2_statistical_estimates?.methodology_note}
                    </div>
                  </div>
                </div>

                {/* Category 3: User-Reported Symptoms */}
                <div className="rounded-2xl border border-rose-200 bg-rose-50/30 overflow-hidden">
                  <div className="px-4 py-2.5 bg-rose-100/70 text-rose-900 flex justify-between items-center">
                    <span className="font-bold text-xs uppercase tracking-wider">Category 3 — User-Reported Symptoms & Notes</span>
                    <span className="text-[11px] font-semibold bg-rose-200/70 px-2 py-0.5 rounded-full">
                      {doctorSummaryData.category_3_user_reported_symptoms?.total_days_logged || 0} days logged
                    </span>
                  </div>
                  <div className="p-4 space-y-3">
                    <p className="text-[11px] text-rose-950 leading-relaxed">
                      {doctorSummaryData.category_3_user_reported_symptoms?.description}
                    </p>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                      <div className="p-2.5 bg-white rounded-xl border border-rose-100">
                        <strong className="text-[11px] text-rose-950 block mb-1">Cramps Reported:</strong>
                        <div className="flex flex-wrap gap-1 text-[10px] text-slate-600">
                          {Object.entries(doctorSummaryData.category_3_user_reported_symptoms?.symptom_frequency_breakdown?.cramps || {}).map(([k, v]) => (
                            <span key={k} className="bg-slate-100 px-1.5 py-0.5 rounded">{k}: {v}</span>
                          ))}
                        </div>
                      </div>
                      <div className="p-2.5 bg-white rounded-xl border border-rose-100">
                        <strong className="text-[11px] text-rose-950 block mb-1">Fatigue Reported:</strong>
                        <div className="flex flex-wrap gap-1 text-[10px] text-slate-600">
                          {Object.entries(doctorSummaryData.category_3_user_reported_symptoms?.symptom_frequency_breakdown?.fatigue || {}).map(([k, v]) => (
                            <span key={k} className="bg-slate-100 px-1.5 py-0.5 rounded">{k}: {v}</span>
                          ))}
                        </div>
                      </div>
                      <div className="p-2.5 bg-white rounded-xl border border-rose-100">
                        <strong className="text-[11px] text-rose-950 block mb-1">Energy Levels Reported:</strong>
                        <div className="flex flex-wrap gap-1 text-[10px] text-slate-600">
                          {Object.entries(doctorSummaryData.category_3_user_reported_symptoms?.symptom_frequency_breakdown?.energy_levels || {}).map(([k, v]) => (
                            <span key={k} className="bg-slate-100 px-1.5 py-0.5 rounded">{k}: {v}</span>
                          ))}
                        </div>
                      </div>
                      <div className="p-2.5 bg-white rounded-xl border border-rose-100">
                        <strong className="text-[11px] text-rose-950 block mb-1">Sleep Average:</strong>
                        <div className="text-[11px] text-slate-700">
                          {doctorSummaryData.category_3_user_reported_symptoms?.symptom_frequency_breakdown?.sleep_hours_summary?.average_hours_per_night
                            ? `${doctorSummaryData.category_3_user_reported_symptoms.symptom_frequency_breakdown.sleep_hours_summary.average_hours_per_night} hrs/night`
                            : 'Untracked'}
                        </div>
                      </div>
                    </div>

                    {/* Evidence-supported longitudinal patterns */}
                    {doctorSummaryData.category_3_user_reported_symptoms?.observed_longitudinal_patterns?.length > 0 && (
                      <div className="space-y-1.5 pt-2 border-t border-rose-100">
                        <span className="text-[10px] font-bold text-rose-900 uppercase block">Evidence-Supported Patterns:</span>
                        {doctorSummaryData.category_3_user_reported_symptoms.observed_longitudinal_patterns.map((p, idx) => (
                          <div key={idx} className="p-2.5 bg-white rounded-xl border border-rose-100 text-xs">
                            <span className="font-bold text-primary">{p.pattern_title}: </span>
                            <span className="text-slate-700">{p.observation}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

                {/* Safety Guidance */}
                <div className="p-3.5 bg-amber-50 rounded-2xl border border-amber-200 text-xs text-amber-900 space-y-1.5">
                  <span className="font-bold text-amber-950 uppercase tracking-wider text-[10px] block">
                    Clinical Safety Guidance & Red-Flag Warnings:
                  </span>
                  <ul className="list-disc list-inside space-y-1 text-[11px]">
                    {(doctorSummaryData.safety_guidance || []).map((s, idx) => (
                      <li key={idx}>{s}</li>
                    ))}
                  </ul>
                </div>
              </div>
            ) : null}

            {/* Modal Actions */}
            <div className="flex flex-col sm:flex-row justify-between items-center gap-3 pt-3 border-t border-purple-100">
              <div className="flex items-center gap-2 w-full sm:w-auto">
                <button
                  type="button"
                  onClick={handlePrintDoctorSummary}
                  className="flex-1 sm:flex-initial px-4 py-2.5 rounded-xl bg-primary hover:bg-primary-dark text-white text-xs font-semibold shadow-soft hover:shadow-md transition flex items-center justify-center gap-1.5"
                >
                  <Printer size={13} />
                  <span>Print / Save PDF</span>
                </button>
                <button
                  type="button"
                  onClick={handleDownloadDoctorJson}
                  disabled={!doctorSummaryData}
                  className="flex-1 sm:flex-initial px-3.5 py-2.5 rounded-xl bg-white hover:bg-purple-50 text-slate-700 border border-slate-200 text-xs font-semibold shadow-xs transition flex items-center justify-center gap-1.5"
                >
                  <Download size={13} />
                  <span>Download JSON</span>
                </button>
              </div>
              <button
                type="button"
                onClick={() => setShowDoctorModal(false)}
                className="w-full sm:w-auto px-5 py-2.5 rounded-xl border border-purple-100 text-textSecondary text-xs font-semibold hover:bg-purple-50 transition"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Global Notifications */}
      {error && (
        <div className="fixed top-4 left-4 right-4 bg-rose-50 border border-rose-200 p-4 rounded-2xl flex items-center space-x-2 shadow-lg z-50 animate-bounce">
          <AlertCircle className="text-rose-500 flex-shrink-0" size={18} />
          <span className="text-xs text-rose-800 font-medium">{error}</span>
        </div>
      )}
      {successMsg && (
        <div className="fixed top-4 left-4 right-4 bg-emerald-50 border border-emerald-200 p-4 rounded-2xl flex items-center space-x-2 shadow-lg z-50">
          <Check className="text-emerald-500 flex-shrink-0" size={18} />
          <span className="text-xs text-emerald-800 font-medium">{successMsg}</span>
        </div>
      )}
    </div>
  );
}

// Simple rounding helper for rendering
function round(value, precision) {
  if (value === null || value === undefined) return 0;
  const multiplier = Math.pow(10, precision || 0);
  return Math.round(value * multiplier) / multiplier;
}

export default App;
