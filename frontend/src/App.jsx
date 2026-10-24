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
  MessageSquare
} from 'lucide-react';
import Community from './components/Community';
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
  const [logCramps, setLogCramps] = useState('None');
  const [logFatigue, setLogFatigue] = useState('None');
  const [logFlow, setLogFlow] = useState('None');

  // Cycle Modal/Form States
  const [cycleStartDate, setCycleStartDate] = useState(new Date().toISOString().split('T')[0]);
  const [cycleEndDate, setCycleEndDate] = useState('');
  const [showCycleModal, setShowCycleModal] = useState(false);

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
        triggerToast(`Welcome back, ${data.user.username}! 💜`);
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
        triggerToast("Account created successfully! 💜");
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
        triggerToast(`Demo Mode active as ${data.user.username}! 💜`);
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
    triggerToast("Logged out successfully");
  };

  // Save Log Handler
  const handleSaveLog = async (e) => {
    e.preventDefault();
    if (!user) return;
    try {
      const res = await authFetch(`${API_BASE}/logs`, {
        method: 'POST',
        body: JSON.stringify({
          date: logDate,
          mood: logMood,
          stress: logStress,
          sleep_hours: parseFloat(logSleep),
          cramps: logCramps,
          fatigue: logFatigue,
          flow: logFlow
        })
      });
      const data = await res.json();
      if (res.ok) {
        triggerToast("Daily wellness log saved successfully! 💜");
        fetchUserData();
      } else {
        triggerToast(data.error || "Failed to save log", true);
      }
    } catch (err) {
      triggerToast("Network error saving log.", true);
    }
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
        triggerToast("Cycle start recorded! 🌸");
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
        triggerToast("Reminder set successfully! ⏰");
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
        triggerToast(`PCOS tracking settings updated (${pcosVal ? 'Active' : 'Off'}). 💜`);
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
        message: "Log your first cycle date below to begin generating personalized predictions and tracking your wellness phases 💜",
        color: "from-purple-400 to-fuchsia-400"
      };
    }
    
    // Cycle Day calculations from last start
    if (cycles.length === 0) return { phase: "Unknown", message: "Log a cycle to start", color: "from-purple-400 to-fuchsia-400" };
    
    const lastStart = new Date(cycles[0].start_date);
    const today = new Date();
    const diffTime = Math.abs(today - lastStart);
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    const cycleDay = (diffDays % (prediction.average_cycle_length || 28)) || 1;
    
    const periodLen = prediction.average_period_length || 5;
    
    if (cycleDay <= periodLen) {
      return {
        phase: "Menstrual Phase",
        message: "Your body is working hard today. Prioritize gentle sleep, heat relief, and nourishing hydration 💜",
        color: "from-rose-400 to-pink-400"
      };
    } else if (cycleDay <= periodLen + 6) {
      return {
        phase: "Follicular Phase",
        message: "Estrogen is rising! You may feel a gentle lift in physical energy and creative focus ✨",
        color: "from-violet-400 to-indigo-400"
      };
    } else if (cycleDay <= periodLen + 11) {
      return {
        phase: "Ovulatory Phase",
        message: "A peak time for vital energy! Excellent for active exercises and social connection 🌟",
        color: "from-emerald-400 to-teal-400"
      };
    } else {
      return {
        phase: "Luteal Phase",
        message: "Progesterone is high. You might need some quiet self-care. Be kind to your mood today 🌸",
        color: "from-amber-400 to-orange-400"
      };
    }
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
      <header className={`${activeTab === 'community' ? 'max-w-5xl' : 'max-w-4xl'} mx-auto flex justify-between items-center mb-6 pt-2 transition-all`}>
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
      <main className={`${activeTab === 'community' ? 'max-w-5xl' : 'max-w-4xl'} mx-auto transition-all`}>
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
              <div className="space-y-6">
                {/* Welcome Card */}
                <div className={`p-6 rounded-3xl bg-gradient-to-tr ${phaseInfo.color} text-white shadow-premium relative overflow-hidden`}>
                  <div className="relative z-10">
                    <span className="text-xs font-semibold bg-white/20 px-3 py-1 rounded-full uppercase tracking-wider">
                      {phaseInfo.phase}
                    </span>
                    <h1 className="text-2xl font-bold mt-2">
                      Good Day, {user.username} 💜
                    </h1>
                    <p className="text-sm font-medium mt-1 opacity-90 max-w-lg leading-relaxed">
                      {phaseInfo.message}
                    </p>
                  </div>
                  {/* Decorative glowing backdrops */}
                  <div className="absolute right-0 top-0 w-48 h-48 bg-white/10 rounded-full blur-3xl -mr-16 -mt-16"></div>
                </div>

                {/* Main Prediction Metrics Row */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {/* Predicted Next Period Widget */}
                  <div className="glass-panel p-6 rounded-3xl relative overflow-hidden flex flex-col justify-between">
                    <div>
                      <div className="flex justify-between items-start">
                        <span className="text-xs font-semibold text-textSecondary uppercase tracking-wider">Period Prediction</span>
                        <CalendarIcon size={18} className="text-primary" />
                      </div>
                      <div className="mt-4">
                        {prediction ? (
                          <>
                            <h3 className="text-3xl font-bold text-textPrimary tracking-tight">
                              {prediction.delayed_days > 0 
                                ? `${prediction.delayed_days} Days Delayed` 
                                : new Date(prediction.predicted_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
                              }
                            </h3>
                            <p className="text-xs text-textSecondary mt-1">
                              {prediction.message}
                            </p>
                          </>
                        ) : (
                          <h3 className="text-xl font-medium text-textLight">No cycle logged yet</h3>
                        )}
                      </div>
                    </div>
                    {prediction && (
                      <div className="mt-4 border-t border-purple-100 pt-3 flex justify-between text-xs text-textSecondary">
                        <span>Avg Cycle: <strong>{prediction.average_cycle_length} Days</strong></span>
                        <span>Avg Period: <strong>{prediction.average_period_length} Days</strong></span>
                      </div>
                    )}
                  </div>

                  {/* Wellness State Card */}
                  <div className="glass-panel p-6 rounded-3xl flex flex-col justify-between">
                    <div>
                      <div className="flex justify-between items-start">
                        <span className="text-xs font-semibold text-textSecondary uppercase tracking-wider">Current Cycle Status</span>
                        <Sparkles size={18} className="text-pink-500 fill-pink-100" />
                      </div>
                      <div className="mt-4">
                        <div className="flex items-center space-x-2">
                          <span className="text-3xl font-bold tracking-tight text-textPrimary">
                            {cycles.length > 0 ? (
                              prediction?.delayed_days > 0 
                                ? `${prediction.delayed_days} Days Delayed` 
                                : `Day ${(Math.round(Math.abs(new Date() - new Date(cycles[0].start_date)) / (1000 * 60 * 60 * 24)) % (prediction?.average_cycle_length || 28)) || 1}`
                            ) : 'Not Started'}
                          </span>
                          <span className={`text-xs px-2 py-0.5 rounded-full font-semibold ${prediction?.irregular ? 'bg-rose-100 text-rose-700 border border-rose-200' : 'bg-emerald-100 text-emerald-700 border border-emerald-200'}`}>
                            {prediction?.irregular ? 'Irregular Cycle' : 'Regular Cycle'}
                          </span>
                        </div>
                        <p className="text-xs text-textSecondary mt-1">
                          {user.has_pcos ? 'Tracking optimized for hormonal variance (PCOS).' : 'Cycle tracking following standard parameters.'}
                        </p>
                      </div>
                    </div>
                    
                    <button 
                      onClick={() => setShowCycleModal(true)} 
                      className="w-full mt-4 bg-primary/10 hover:bg-primary text-primary hover:text-white py-2 rounded-2xl text-xs font-semibold transition"
                    >
                      Log New Cycle Start
                    </button>
                  </div>
                </div>

                {/* Quick Log Form */}
                <div className="glass-panel p-6 rounded-3xl">
                  <h3 className="text-lg font-semibold text-textPrimary mb-1">Quick Wellness Log</h3>
                  <p className="text-xs text-textSecondary mb-4">Record logs for daily symptoms and emotional states</p>
                  
                  <form onSubmit={handleSaveLog} className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-[10px] font-semibold text-textSecondary uppercase mb-1">Log Date</label>
                        <input
                          type="date"
                          value={logDate}
                          onChange={(e) => setLogDate(e.target.value)}
                          className="w-full px-3 py-2 rounded-xl border border-purple-100 text-xs focus:ring-1 focus:ring-primary outline-none"
                        />
                      </div>
                      <div>
                        <label className="block text-[10px] font-semibold text-textSecondary uppercase mb-1">Mood Emoji State</label>
                        <select
                          value={logMood}
                          onChange={(e) => setLogMood(e.target.value)}
                          className="w-full px-3 py-2 rounded-xl border border-purple-100 text-xs focus:ring-1 focus:ring-primary outline-none"
                        >
                          <option value="Happy">😊 Happy</option>
                          <option value="Calm">😌 Calm</option>
                          <option value="Emotional">😢 Emotional</option>
                          <option value="Irritated">😠 Irritated</option>
                          <option value="Tired">😴 Tired</option>
                          <option value="Anxious">😟 Anxious</option>
                        </select>
                      </div>
                    </div>

                    <div className="grid grid-cols-3 gap-2">
                      <div>
                        <label className="block text-[10px] font-semibold text-textSecondary uppercase mb-1">Cramps</label>
                        <select
                          value={logCramps}
                          onChange={(e) => setLogCramps(e.target.value)}
                          className="w-full px-2 py-2 rounded-xl border border-purple-100 text-xs focus:ring-1 focus:ring-primary outline-none"
                        >
                          <option value="None">None</option>
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
                          className="w-full px-2 py-2 rounded-xl border border-purple-100 text-xs focus:ring-1 focus:ring-primary outline-none"
                        >
                          <option value="None">None</option>
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
                          className="w-full px-2 py-2 rounded-xl border border-purple-100 text-xs focus:ring-1 focus:ring-primary outline-none"
                        >
                          <option value="None">None</option>
                          <option value="Light">Light</option>
                          <option value="Medium">Medium</option>
                          <option value="Heavy">Heavy</option>
                        </select>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
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

                    <button
                      type="submit"
                      className="w-full bg-primary hover:bg-primary-dark text-white py-2.5 rounded-2xl text-xs font-semibold shadow-soft hover:shadow-md transition"
                    >
                      Save Daily Log
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
                          {cycles.map((c) => (
                            <div key={c.cycle_id} className="p-3 rounded-2xl bg-white/60 border border-purple-100/50 flex justify-between items-center text-xs">
                              <div>
                                <p className="font-semibold text-textPrimary">
                                  {new Date(c.start_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                                </p>
                                <p className="text-[10px] text-textSecondary">
                                  {c.end_date ? `End: ${new Date(c.end_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}` : 'Ongoing'}
                                  {c.cycle_length && ` • Cycle: ${c.cycle_length}d`}
                                </p>
                              </div>
                              <button 
                                onClick={() => handleDeleteCycle(c.cycle_id)} 
                                className="text-rose-500 p-1.5 rounded-lg hover:bg-rose-50 transition"
                              >
                                <Trash2 size={14} />
                              </button>
                            </div>
                          ))}
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
              <div className="space-y-6">
                <div className="glass-panel p-6 rounded-3xl">
                  <h3 className="text-lg font-semibold text-textPrimary mb-1">Wellness Logs History</h3>
                  <p className="text-xs text-textSecondary mb-6">List of recorded symptoms and daily statuses</p>
                  
                  {logs.length === 0 ? (
                    <div className="text-center py-12 text-textLight italic text-xs">
                      No logs logged yet. Complete the dashboard entry to see it here!
                    </div>
                  ) : (
                    <div className="space-y-4 max-h-[500px] overflow-y-auto pr-2 scrollbar-hide">
                      {logs.map((log) => (
                        <div key={log.log_id} className="p-4 rounded-2xl bg-white/70 border border-purple-100 flex flex-col sm:flex-row justify-between items-start sm:items-center space-y-3 sm:space-y-0">
                          <div>
                            <span className="text-[10px] font-bold text-primary bg-primary/10 px-2 py-0.5 rounded-full uppercase tracking-wider">
                              Cycle Day {log.cycle_day || '?'}
                            </span>
                            <h4 className="font-bold text-sm text-textPrimary mt-1">
                              {new Date(log.date).toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' })}
                            </h4>
                            <div className="flex flex-wrap gap-1.5 mt-2">
                              {log.mood && <span className="bg-purple-50 text-primary border border-purple-200/50 text-[10px] px-2 py-0.5 rounded-full">Mood: {log.mood}</span>}
                              {log.stress && <span className="bg-amber-50 text-amber-700 border border-amber-200/50 text-[10px] px-2 py-0.5 rounded-full">Stress: {log.stress}</span>}
                              {log.sleep_hours && <span className="bg-blue-50 text-blue-700 border border-blue-200/50 text-[10px] px-2 py-0.5 rounded-full">Sleep: {log.sleep_hours} hrs</span>}
                            </div>
                          </div>
                          
                          <div className="flex flex-wrap gap-1">
                            {log.cramps !== 'None' && <span className="bg-rose-100 text-rose-700 text-[10px] px-2 py-1 rounded-lg font-semibold">Cramps: {log.cramps}</span>}
                            {log.fatigue !== 'None' && <span className="bg-orange-100 text-orange-700 text-[10px] px-2 py-1 rounded-lg font-semibold">Fatigue: {log.fatigue}</span>}
                            {log.flow !== 'None' && <span className="bg-pink-100 text-pink-700 text-[10px] px-2 py-1 rounded-lg font-semibold">Flow: {log.flow}</span>}
                            {log.cramps === 'None' && log.fatigue === 'None' && log.flow === 'None' && (
                              <span className="text-textLight text-xs italic">No physiological symptoms logged</span>
                            )}
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
              <div className="space-y-6">
                {/* Insights Panel */}
                <div className="glass-panel p-6 rounded-3xl bg-gradient-to-tr from-purple-100/50 to-pink-100/50 border border-white/60">
                  <div className="flex items-center space-x-2 mb-3">
                    <Sparkles className="text-primary fill-primary/10" size={18} />
                    <h3 className="text-base font-semibold text-textPrimary">Wellness Insights</h3>
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

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Chart 1: Cycle Length Trend */}
                  <div className="glass-panel p-6 rounded-3xl">
                    <h3 className="text-sm font-semibold text-textPrimary mb-4">Cycle Lengths (Days)</h3>
                    {analytics?.cycle_history.length > 0 ? (
                      <div className="h-64">
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
                  <div className="glass-panel p-6 rounded-3xl">
                    <h3 className="text-sm font-semibold text-textPrimary mb-4">Mood Frequency Breakdown</h3>
                    {analytics?.mood_frequencies.length > 0 ? (
                      <div className="h-64 flex justify-center">
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
                  <div className="glass-panel p-6 rounded-3xl col-span-1 md:col-span-2">
                    <h3 className="text-sm font-semibold text-textPrimary mb-4">Symptom Severity Frequency</h3>
                    {analytics && Object.values(analytics.symptoms_frequencies).some(c => c > 0) ? (
                      <div className="h-64">
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
              </div>
            )}

            {/* ==========================================
                TAB: REMINDERS & PROFILE
                ========================================== */}
            {activeTab === 'profile' && (
              <div className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Reminders List & Manager */}
                  <div className="glass-panel p-6 rounded-3xl">
                    <h3 className="text-base font-semibold text-textPrimary mb-1">Smart Reminders</h3>
                    <p className="text-xs text-textSecondary mb-4">Manage medicine and hydration alerts</p>

                    <form onSubmit={handleAddReminder} className="flex gap-2 mb-4">
                      <select
                        value={reminderType}
                        onChange={(e) => setReminderType(e.target.value)}
                        className="flex-grow px-2 py-2 rounded-xl border border-purple-100 text-xs focus:ring-1 focus:ring-primary outline-none"
                      >
                        <option value="Hydration">💧 Hydration Alert</option>
                        <option value="Medicine">💊 Medicine Dose</option>
                        <option value="Period">🌸 Period Prediction</option>
                        <option value="Self-Care">🧘 Self-Care reminder</option>
                      </select>
                      <input
                        type="date"
                        value={reminderDate}
                        onChange={(e) => setReminderDate(e.target.value)}
                        className="px-2 py-2 rounded-xl border border-purple-100 text-xs focus:ring-1 focus:ring-primary outline-none w-32"
                      />
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
                          <div key={rem.reminder_id} className="p-3 rounded-2xl bg-white/50 border border-purple-100 flex justify-between items-center text-xs">
                            <div className="flex items-center space-x-3">
                              <input
                                type="checkbox"
                                checked={rem.completed}
                                onChange={() => handleToggleReminder(rem.reminder_id)}
                                className="rounded text-primary focus:ring-primary h-4 w-4 cursor-pointer"
                              />
                              <span className={rem.completed ? 'line-through text-textLight' : 'font-medium text-textPrimary'}>
                                {rem.reminder_type === 'Hydration' ? '💧' : rem.reminder_type === 'Medicine' ? '💊' : '🌸'} {rem.reminder_type}
                                <span className="block text-[10px] text-textSecondary">{new Date(rem.reminder_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</span>
                              </span>
                            </div>
                            <button 
                              onClick={() => handleDeleteReminder(rem.reminder_id)} 
                              className="text-rose-400 p-1.5 rounded-lg hover:bg-rose-50 transition"
                            >
                              <Trash2 size={13} />
                            </button>
                          </div>
                        ))
                      )}
                    </div>
                  </div>

                  {/* Profile Settings */}
                  <div className="glass-panel p-6 rounded-3xl flex flex-col justify-between">
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
          </>
        )}
      </main>

      {/* Floating Bottom Nav Bar */}
      <nav className="fixed bottom-6 left-1/2 transform -translate-x-1/2 glass-panel rounded-full px-5 py-3 flex space-x-6 sm:space-x-8 items-center shadow-lg border border-white/60 z-50">
        {[
          { tab: 'dashboard', icon: Home, label: 'Home' },
          { tab: 'calendar', icon: CalendarIcon, label: 'Calendar' },
          { tab: 'community', icon: MessageSquare, label: 'Community' },
          { tab: 'logs', icon: Heart, label: 'Logs' },
          { tab: 'analytics', icon: BarChart2, label: 'Charts' },
          { tab: 'profile', icon: User, label: 'Settings' }
        ].map(({ tab, icon: Icon, label }) => {
          const isActive = activeTab === tab;
          return (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className="flex flex-col items-center justify-center relative transition group focus:outline-none"
            >
              <Icon 
                size={22} 
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
          <div className="glass-panel w-full max-w-sm rounded-3xl p-6 shadow-premium relative">
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
