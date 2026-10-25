import React, { useState } from 'react';
import {
  Heart,
  Calendar,
  Sparkles,
  BarChart2,
  MessageSquare,
  FileText,
  Shield,
  ArrowRight,
  Check,
  CheckCircle2,
  Menu,
  X,
  Droplets,
  Activity,
  Flame,
  Clock,
  AlertCircle,
  HelpCircle,
  Info,
  ChevronDown,
  User,
  LogOut,
  Users
} from 'lucide-react';

export default function LandingPage({
  user,
  onGetStarted,
  onLogin,
  onDemoMode,
  onGoToDashboard,
  onLogout
}) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const scrollToSection = (id) => {
    setMobileMenuOpen(false);
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <div className="w-full min-h-screen bg-[#F5F3FF] text-[#1F2937] antialiased selection:bg-purple-200 selection:text-purple-900 overflow-x-hidden">
      {/* ==================================================================== */}
      {/* Section 1: Navigation Header                                         */}
      {/* ==================================================================== */}
      <header className="sticky top-0 z-50 w-full bg-white/85 backdrop-blur-md border-b border-purple-100/70 shadow-xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-8 lg:px-12 h-20 flex items-center justify-between">
          {/* Brand Logo */}
          <a
            href="#top"
            onClick={(e) => {
              e.preventDefault();
              window.scrollTo({ top: 0, behavior: 'smooth' });
            }}
            className="flex items-center space-x-2.5 group focus:outline-none"
            aria-label="OvaCare AI Home"
          >
            <div className="bg-primary p-2 rounded-2xl text-white shadow-soft group-hover:scale-105 transition-transform duration-200">
              <Heart size={22} className="fill-white" />
            </div>
            <div className="flex items-baseline space-x-1.5">
              <span className="text-xl font-bold tracking-tight text-textPrimary">
                OvaCare<span className="text-primary font-black ml-0.5">AI</span>
              </span>
              <span className="hidden sm:inline-block bg-purple-100 text-purple-800 text-[10px] font-bold px-2 py-0.5 rounded-full border border-purple-200">
                FemTech
              </span>
            </div>
          </a>

          {/* Desktop Navigation Links */}
          <nav className="hidden md:flex items-center space-x-8" aria-label="Main Navigation">
            <button
              onClick={() => scrollToSection('features')}
              className="text-sm font-semibold text-textSecondary hover:text-primary transition-colors cursor-pointer"
            >
              Features
            </button>
            <button
              onClick={() => scrollToSection('how-it-works')}
              className="text-sm font-semibold text-textSecondary hover:text-primary transition-colors cursor-pointer"
            >
              How It Works
            </button>
            <button
              onClick={() => scrollToSection('our-approach')}
              className="text-sm font-semibold text-textSecondary hover:text-primary transition-colors cursor-pointer"
            >
              Our Approach
            </button>
          </nav>

          {/* Header Action Buttons */}
          <div className="hidden md:flex items-center space-x-3.5">
            {user ? (
              <>
                <button
                  type="button"
                  onClick={onGoToDashboard}
                  className="bg-primary hover:bg-primary-dark text-white px-5 py-2.5 rounded-2xl text-xs font-bold shadow-soft hover:shadow-premium transition flex items-center space-x-1.5 cursor-pointer"
                >
                  <span>Go to My Dashboard</span>
                  <ArrowRight size={14} />
                </button>
                {onLogout && (
                  <button
                    type="button"
                    onClick={onLogout}
                    className="p-2.5 rounded-2xl text-rose-600 hover:bg-rose-50 border border-transparent hover:border-rose-100 transition"
                    title="Log Out"
                  >
                    <LogOut size={16} />
                  </button>
                )}
              </>
            ) : (
              <>
                <button
                  type="button"
                  onClick={onLogin}
                  className="text-xs font-bold text-textPrimary hover:text-primary px-3.5 py-2 rounded-xl transition cursor-pointer"
                >
                  Log In
                </button>
                <button
                  type="button"
                  onClick={onGetStarted}
                  className="bg-primary hover:bg-primary-dark text-white px-5 py-2.5 rounded-2xl text-xs font-bold shadow-soft hover:shadow-premium transition flex items-center space-x-1.5 cursor-pointer"
                >
                  <span>Get Started</span>
                  <ArrowRight size={14} />
                </button>
              </>
            )}
          </div>

          {/* Mobile Menu Hamburger */}
          <button
            type="button"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="md:hidden p-2 rounded-xl text-textSecondary hover:text-primary focus:outline-none"
            aria-label="Toggle navigation menu"
          >
            {mobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
          </button>
        </div>

        {/* Mobile Dropdown Drawer */}
        {mobileMenuOpen && (
          <div className="md:hidden bg-white border-b border-purple-100 px-6 py-5 space-y-4 shadow-lg animate-fade-in">
            <button
              onClick={() => scrollToSection('features')}
              className="block w-full text-left text-sm font-semibold text-textSecondary hover:text-primary py-1"
            >
              Features
            </button>
            <button
              onClick={() => scrollToSection('how-it-works')}
              className="block w-full text-left text-sm font-semibold text-textSecondary hover:text-primary py-1"
            >
              How It Works
            </button>
            <button
              onClick={() => scrollToSection('our-approach')}
              className="block w-full text-left text-sm font-semibold text-textSecondary hover:text-primary py-1"
            >
              Our Approach
            </button>
            <div className="pt-3 border-t border-purple-100 flex flex-col space-y-2.5">
              {user ? (
                <button
                  type="button"
                  onClick={() => { setMobileMenuOpen(false); onGoToDashboard(); }}
                  className="w-full bg-primary text-white py-3 rounded-2xl text-xs font-bold shadow-soft text-center"
                >
                  Go to My Dashboard
                </button>
              ) : (
                <>
                  <button
                    type="button"
                    onClick={() => { setMobileMenuOpen(false); onLogin(); }}
                    className="w-full text-center text-xs font-bold text-textPrimary py-2.5 border border-purple-200 rounded-2xl"
                  >
                    Log In
                  </button>
                  <button
                    type="button"
                    onClick={() => { setMobileMenuOpen(false); onGetStarted(); }}
                    className="w-full bg-primary text-white py-3 rounded-2xl text-xs font-bold shadow-soft text-center"
                  >
                    Get Started
                  </button>
                </>
              )}
            </div>
          </div>
        )}
      </header>

      {/* ==================================================================== */}
      {/* Section 2: Hero Section (Desktop Full-Width, Balanced 2-Column)      */}
      {/* ==================================================================== */}
      <section className="relative w-full max-w-7xl mx-auto px-4 sm:px-8 lg:px-12 py-10 sm:py-16 lg:py-20 min-h-[calc(100svh-80px)] flex items-center">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-12 items-center w-full">
          
          {/* Left Column: Headline, Copy, Action Buttons, Trust Statements */}
          <div className="lg:col-span-6 space-y-6 sm:space-y-7 text-left">
            {/* Eyebrow */}
            <div className="inline-flex items-center space-x-2 bg-white/80 border border-purple-200/80 px-3.5 py-1.5 rounded-full shadow-xs">
              <Sparkles size={14} className="text-primary" />
              <span className="text-[11px] font-bold text-primary tracking-wider uppercase">
                Personalized Menstrual Health & Wellbeing
              </span>
            </div>

            {/* Headline */}
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold text-[#0F172A] tracking-tight leading-[1.12]">
              Understand your cycle.<br />
              <span className="bg-gradient-to-r from-primary via-purple-600 to-indigo-600 bg-clip-text text-transparent">
                Understand yourself.
              </span>
            </h1>

            {/* Description */}
            <p className="text-base sm:text-lg text-slate-600 leading-relaxed max-w-xl font-normal">
              Track your cycle, explore your wellbeing patterns, and bring your health observations
              together in one thoughtful, personalized space.
            </p>

            {/* Primary & Secondary Action Buttons */}
            <div className="flex flex-wrap items-center gap-3.5 pt-1">
              <button
                type="button"
                onClick={user ? onGoToDashboard : onGetStarted}
                className="bg-primary hover:bg-primary-dark text-white px-7 py-3.5 rounded-2xl font-bold text-sm shadow-premium hover:shadow-lg transition-all duration-200 flex items-center space-x-2.5 cursor-pointer transform hover:-translate-y-0.5"
              >
                <span>{user ? 'Open My Dashboard' : 'Get Started'}</span>
                <ArrowRight size={17} />
              </button>

              <button
                type="button"
                onClick={() => scrollToSection('features')}
                className="bg-white/80 hover:bg-white text-textPrimary hover:text-primary px-6 py-3.5 rounded-2xl font-bold text-sm border border-purple-200/80 shadow-xs hover:shadow-soft transition-all duration-200 flex items-center space-x-2 cursor-pointer"
              >
                <Sparkles size={16} className="text-primary" />
                <span>Explore Features</span>
              </button>
            </div>

            {/* Instant Demo Sandbox Shortcut */}
            {onDemoMode && !user && (
              <div className="pt-1">
                <button
                  type="button"
                  onClick={() => onDemoMode('maya.demo@example.com')}
                  className="inline-flex items-center space-x-1.5 text-xs font-semibold text-purple-700 hover:text-primary hover:underline transition"
                >
                  <Sparkles size={13} className="text-primary" />
                  <span>Judges / Evaluators: Explore Maya Demo Patient account instantly</span>
                  <ArrowRight size={12} />
                </button>
              </div>
            )}

            {/* Three Concise Product Statements */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-4 border-t border-purple-200/60">
              <div className="flex items-center space-x-2">
                <div className="w-5 h-5 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center flex-shrink-0">
                  <Check size={12} strokeWidth={3} />
                </div>
                <span className="text-xs font-semibold text-slate-700">Personalized cycle estimates</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-5 h-5 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center flex-shrink-0">
                  <Check size={12} strokeWidth={3} />
                </div>
                <span className="text-xs font-semibold text-slate-700">Physical & emotional wellbeing</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-5 h-5 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center flex-shrink-0">
                  <Check size={12} strokeWidth={3} />
                </div>
                <span className="text-xs font-semibold text-slate-700">AI-assisted wellness support</span>
              </div>
            </div>
          </div>

          {/* Right Column: Realistic OvaCare AI Dashboard Window Preview */}
          <div className="lg:col-span-6 relative">
            {/* Subtle background glow */}
            <div className="absolute -inset-4 bg-gradient-to-tr from-purple-300/30 to-pink-300/30 rounded-3xl blur-2xl -z-10" />

            {/* Main Interactive-Style Preview Window */}
            <div className="bg-white/95 backdrop-blur-xl border border-purple-200/90 rounded-3xl p-5 sm:p-6 shadow-2xl relative overflow-hidden space-y-4">
              
              {/* Top Window Bar (Simulates OvaCare App Header) */}
              <div className="flex items-center justify-between pb-3 border-b border-purple-100">
                <div className="flex items-center space-x-2">
                  <div className="bg-primary p-1 rounded-lg text-white shadow-xs">
                    <Heart size={14} className="fill-white" />
                  </div>
                  <span className="text-sm font-bold text-slate-900 tracking-tight">OvaCare</span>
                  <span className="bg-amber-100 text-amber-800 text-[10px] font-bold px-2 py-0.5 rounded-full border border-amber-300">
                    PCOS Mode
                  </span>
                </div>
                <div className="flex items-center space-x-2">
                  <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                  <span className="text-[11px] font-semibold text-slate-500">Live Companion</span>
                  <div className="w-7 h-7 rounded-full bg-purple-100 text-primary font-bold text-xs flex items-center justify-center border border-purple-200">
                    M
                  </div>
                </div>
              </div>

              {/* Banner Card (Matches Good Day Demo Patient in Screenshots) */}
              <div className="bg-gradient-to-r from-pink-400 via-rose-400 to-purple-400 p-4 sm:p-5 rounded-2xl text-white shadow-soft relative overflow-hidden">
                <span className="text-[10px] font-bold bg-white/20 px-2.5 py-0.5 rounded-full uppercase tracking-wider">
                  Follicular Phase · Day 12
                </span>
                <h3 className="text-lg sm:text-xl font-bold mt-1.5">
                  Good Day, Maya
                </h3>
                <p className="text-xs font-medium text-white/90 mt-0.5 line-clamp-2">
                  Prioritize restorative rest, mindful hydration, and comfort as your cycle progresses.
                </p>
              </div>

              {/* Dual Metric Cards (Period Prediction & Current Cycle Status) */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                {/* Card 1: Prediction */}
                <div className="bg-purple-50/50 border border-purple-100 rounded-2xl p-4 flex flex-col justify-between space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                      Period Prediction
                    </span>
                    <span className="text-[9px] font-bold bg-blue-100 text-blue-800 px-2 py-0.5 rounded-full border border-blue-200">
                      Calculated
                    </span>
                  </div>
                  <div>
                    <span className="text-xl sm:text-2xl font-extrabold text-slate-800">
                      Nov 22, 2026
                    </span>
                    <p className="text-[11px] text-slate-500 mt-0.5">
                      Estimated around Nov 22 based on personal cycle history.
                    </p>
                  </div>
                  <div className="bg-amber-50 border border-amber-200/80 rounded-xl p-2 flex items-center justify-between text-[10px] text-amber-900">
                    <div className="flex items-center space-x-1">
                      <AlertCircle size={12} className="text-amber-600 flex-shrink-0" />
                      <span className="font-semibold">Tracking gap &gt;45d</span>
                    </div>
                    <span className="bg-amber-600 text-white font-bold px-2 py-0.5 rounded-lg text-[9px]">
                      Clarify
                    </span>
                  </div>
                </div>

                {/* Card 2: Cycle Status */}
                <div className="bg-purple-50/50 border border-purple-100 rounded-2xl p-4 flex flex-col justify-between space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                      Cycle Overview
                    </span>
                    <Sparkles size={14} className="text-primary" />
                  </div>
                  <div>
                    <div className="flex items-baseline space-x-1.5">
                      <span className="text-xl sm:text-2xl font-extrabold text-slate-800">Day 12</span>
                      <span className="text-xs text-slate-500 font-semibold">of 29 days</span>
                    </div>
                    <p className="text-[11px] text-slate-500 mt-0.5">
                      Average cycle: 29 days · Period: 5 days
                    </p>
                  </div>
                  <div className="flex items-center justify-between text-[11px] pt-1 border-t border-purple-100 text-slate-600">
                    <span>Contributing Cycles: <strong>6</strong></span>
                    <span className="text-primary font-bold">Standard</span>
                  </div>
                </div>
              </div>

              {/* Active Rhythm Row (Matches Screenshot Habit Tracking Bar) */}
              <div className="bg-white border border-purple-100 rounded-2xl p-3.5 flex items-center justify-between">
                <div className="flex items-center space-x-2.5">
                  <div className="w-8 h-8 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center border border-amber-200/60">
                    <Flame size={16} />
                  </div>
                  <div>
                    <div className="flex items-center space-x-1.5">
                      <span className="text-xs font-bold text-slate-800">1-Day Active Rhythm</span>
                      <span className="text-[9px] bg-emerald-100 text-emerald-800 font-bold px-1.5 py-0.2 rounded-full">Active</span>
                    </div>
                    <span className="text-[10px] text-slate-500">60-Day Milestone: Dedicated Rhythm</span>
                  </div>
                </div>
                <div className="hidden sm:flex items-center space-x-1 text-[10px] text-slate-400 font-bold">
                  {['M', 'T', 'W', 'T', 'F', 'S'].map((day, i) => (
                    <span key={i} className="w-5 h-5 rounded-full bg-slate-100 flex items-center justify-center">
                      {day}
                    </span>
                  ))}
                  <span className="w-5 h-5 rounded-full bg-primary text-white flex items-center justify-center">
                    <Check size={10} strokeWidth={3} />
                  </span>
                </div>
              </div>

              {/* Floating Bottom Navigation Simulation */}
              <div className="bg-white/90 backdrop-blur-md border border-purple-200 rounded-full px-5 py-2 flex items-center justify-around shadow-sm text-slate-400 text-xs">
                <span className="text-primary font-bold flex items-center space-x-1">
                  <Heart size={14} className="fill-primary" />
                  <span>Home</span>
                </span>
                <span className="hover:text-primary transition">Calendar</span>
                <span className="hover:text-primary transition">Community</span>
                <span className="hover:text-primary transition">Logs</span>
                <span className="hover:text-primary transition">Report</span>
              </div>
            </div>
          </div>

        </div>
      </section>

      {/* ==================================================================== */}
      {/* Section 3: Product Features                                          */}
      {/* ==================================================================== */}
      <section id="features" className="w-full max-w-7xl mx-auto px-4 sm:px-8 lg:px-12 py-16 sm:py-24">
        <div className="text-center max-w-2xl mx-auto mb-14 space-y-3">
          <div className="inline-flex items-center space-x-1.5 bg-purple-100 text-purple-800 text-xs font-bold px-3 py-1 rounded-full border border-purple-200">
            <Sparkles size={12} className="text-primary" />
            <span>Core Capabilities</span>
          </div>
          <h2 className="text-3xl sm:text-4xl font-extrabold text-[#0F172A] tracking-tight">
            Your wellbeing, all in one place.
          </h2>
          <p className="text-slate-600 text-sm sm:text-base leading-relaxed">
            Bring your cycle history, daily check-ins, and wellbeing observations together to build
            a clearer picture of your personal patterns.
          </p>
        </div>

        {/* 6 Feature Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 sm:gap-8">
          
          {/* Card 1: Cycle Tracking */}
          <div className="bg-white rounded-3xl p-7 border border-purple-100 shadow-soft hover:shadow-premium hover:-translate-y-1 transition duration-200 flex flex-col justify-between">
            <div>
              <div className="w-12 h-12 rounded-2xl bg-purple-100/80 text-primary flex items-center justify-center mb-5 shadow-xs">
                <Calendar size={22} />
              </div>
              <h3 className="text-lg font-bold text-slate-900 mb-2">Cycle Tracking</h3>
              <p className="text-sm text-slate-600 leading-relaxed">
                Record menstrual start and end dates, view historical intervals, review transparent estimates,
                and clarify gaps in your records without guesswork.
              </p>
            </div>
            <div className="pt-5 mt-5 border-t border-purple-50 flex items-center justify-between text-xs font-bold text-primary">
              <span>Period & Gap Logging</span>
              <ArrowRight size={14} />
            </div>
          </div>

          {/* Card 2: Wellbeing Analytics */}
          <div className="bg-white rounded-3xl p-7 border border-purple-100 shadow-soft hover:shadow-premium hover:-translate-y-1 transition duration-200 flex flex-col justify-between">
            <div>
              <div className="w-12 h-12 rounded-2xl bg-pink-100/80 text-pink-700 flex items-center justify-center mb-5 shadow-xs">
                <BarChart2 size={22} />
              </div>
              <h3 className="text-lg font-bold text-slate-900 mb-2">Wellbeing Analytics</h3>
              <p className="text-sm text-slate-600 leading-relaxed">
                Explore visual trends in your recorded mood, sleep hours, stress, energy levels,
                and physical symptoms to discover how you feel across phases.
              </p>
            </div>
            <div className="pt-5 mt-5 border-t border-purple-50 flex items-center justify-between text-xs font-bold text-primary">
              <span>Visual Trend Charts</span>
              <ArrowRight size={14} />
            </div>
          </div>

          {/* Card 3: AI Wellness Companion */}
          <div className="bg-white rounded-3xl p-7 border border-purple-100 shadow-soft hover:shadow-premium hover:-translate-y-1 transition duration-200 flex flex-col justify-between">
            <div>
              <div className="w-12 h-12 rounded-2xl bg-indigo-100/80 text-indigo-700 flex items-center justify-center mb-5 shadow-xs">
                <Sparkles size={22} />
              </div>
              <h3 className="text-lg font-bold text-slate-900 mb-2">AI Wellness Companion</h3>
              <p className="text-sm text-slate-600 leading-relaxed">
                Interact through conversational guidance grounded in verified Monash and WHO clinical
                guidelines, with strict medical safety classifications and disclaimers.
              </p>
            </div>
            <div className="pt-5 mt-5 border-t border-purple-50 flex items-center justify-between text-xs font-bold text-primary">
              <span>Evidence-Ground RAG</span>
              <ArrowRight size={14} />
            </div>
          </div>

          {/* Card 4: My Health Report */}
          <div className="bg-white rounded-3xl p-7 border border-purple-100 shadow-soft hover:shadow-premium hover:-translate-y-1 transition duration-200 flex flex-col justify-between">
            <div>
              <div className="w-12 h-12 rounded-2xl bg-blue-100/80 text-blue-700 flex items-center justify-center mb-5 shadow-xs">
                <FileText size={22} />
              </div>
              <h3 className="text-lg font-bold text-slate-900 mb-2">My Health Report</h3>
              <p className="text-sm text-slate-600 leading-relaxed">
                Synthesize recorded cycle statistics, symptom clusters, and wellbeing patterns into a structured,
                print-friendly summary to support doctor visits.
              </p>
            </div>
            <div className="pt-5 mt-5 border-t border-purple-50 flex items-center justify-between text-xs font-bold text-primary">
              <span>Doctor-Visit Ready</span>
              <ArrowRight size={14} />
            </div>
          </div>

          {/* Card 5: Community */}
          <div className="bg-white rounded-3xl p-7 border border-purple-100 shadow-soft hover:shadow-premium hover:-translate-y-1 transition duration-200 flex flex-col justify-between">
            <div>
              <div className="w-12 h-12 rounded-2xl bg-emerald-100/80 text-emerald-700 flex items-center justify-center mb-5 shadow-xs">
                <Users size={22} />
              </div>
              <h3 className="text-lg font-bold text-slate-900 mb-2">Community Safe Haven</h3>
              <p className="text-sm text-slate-600 leading-relaxed">
                Share lived experiences, ask questions, and support peers across specialized categories
                with anonymous posting and verified healthcare label moderation.
              </p>
            </div>
            <div className="pt-5 mt-5 border-t border-purple-50 flex items-center justify-between text-xs font-bold text-primary">
              <span>Peer Support Forums</span>
              <ArrowRight size={14} />
            </div>
          </div>

          {/* Card 6: PCOS-Aware Tracking */}
          <div className="bg-white rounded-3xl p-7 border border-purple-100 shadow-soft hover:shadow-premium hover:-translate-y-1 transition duration-200 flex flex-col justify-between">
            <div>
              <div className="w-12 h-12 rounded-2xl bg-amber-100/80 text-amber-700 flex items-center justify-center mb-5 shadow-xs">
                <Shield size={22} />
              </div>
              <h3 className="text-lg font-bold text-slate-900 mb-2">PCOS-Aware Tracking</h3>
              <p className="text-sm text-slate-600 leading-relaxed">
                An optional personalization preference adapted for irregular intervals and hormonal
                symptoms. Designed for tracking and lifestyle awareness, not medical diagnosis.
              </p>
            </div>
            <div className="pt-5 mt-5 border-t border-purple-50 flex items-center justify-between text-xs font-bold text-primary">
              <span>Personalized Tracking</span>
              <ArrowRight size={14} />
            </div>
          </div>

        </div>
      </section>

      {/* ==================================================================== */}
      {/* Section 4: How It Works                                              */}
      {/* ==================================================================== */}
      <section id="how-it-works" className="w-full bg-white py-16 sm:py-24 border-y border-purple-100/80">
        <div className="max-w-7xl mx-auto px-4 sm:px-8 lg:px-12">
          <div className="text-center max-w-2xl mx-auto mb-16 space-y-3">
            <div className="inline-flex items-center space-x-1.5 bg-purple-100 text-purple-800 text-xs font-bold px-3 py-1 rounded-full border border-purple-200">
              <Clock size={12} className="text-primary" />
              <span>Simple Workflow</span>
            </div>
            <h2 className="text-3xl sm:text-4xl font-extrabold text-[#0F172A] tracking-tight">
              Start with a check-in. Discover your patterns.
            </h2>
            <p className="text-slate-600 text-sm sm:text-base leading-relaxed">
              OvaCare AI makes recording intuitive and quick, then helps you connect everyday observations
              with long-term cycle health.
            </p>
          </div>

          {/* 3 Steps: Horizontal on Desktop, Vertical on Mobile */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 relative">
            {/* Step 1 */}
            <div className="bg-[#F5F3FF] rounded-3xl p-8 border border-purple-200/80 relative space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-3xl font-black text-primary">01</span>
                <span className="bg-white text-primary text-xs font-bold px-3 py-1 rounded-full border border-purple-100">
                  Daily Habit
                </span>
              </div>
              <h3 className="text-xl font-bold text-slate-900">Track</h3>
              <p className="text-sm text-slate-600 leading-relaxed">
                Record your cycle dates and relevant daily observations—mood, cramps, sleep hours, stress,
                and energy level—in under a minute.
              </p>
            </div>

            {/* Step 2 */}
            <div className="bg-[#F5F3FF] rounded-3xl p-8 border border-purple-200/80 relative space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-3xl font-black text-primary">02</span>
                <span className="bg-white text-primary text-xs font-bold px-3 py-1 rounded-full border border-purple-100">
                  Insights
                </span>
              </div>
              <h3 className="text-xl font-bold text-slate-900">Understand</h3>
              <p className="text-sm text-slate-600 leading-relaxed">
                Review estimates and explore potential patterns identified from your recorded history with
                transparent explanations and confidence indicators.
              </p>
            </div>

            {/* Step 3 */}
            <div className="bg-[#F5F3FF] rounded-3xl p-8 border border-purple-200/80 relative space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-3xl font-black text-primary">03</span>
                <span className="bg-white text-primary text-xs font-bold px-3 py-1 rounded-full border border-purple-100">
                  Clinical Visit
                </span>
              </div>
              <h3 className="text-xl font-bold text-slate-900">Prepare</h3>
              <p className="text-sm text-slate-600 leading-relaxed">
                Generate an organized health report summarizing your recorded symptoms, averages, and notes
                to support informed conversations with your healthcare provider.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ==================================================================== */}
      {/* Section 5: Trust and Responsible Use                                 */}
      {/* ==================================================================== */}
      <section id="our-approach" className="w-full max-w-7xl mx-auto px-4 sm:px-8 lg:px-12 py-16 sm:py-24">
        <div className="max-w-3xl mx-auto text-center space-y-3 mb-14">
          <div className="inline-flex items-center space-x-1.5 bg-purple-100 text-purple-800 text-xs font-bold px-3 py-1 rounded-full border border-purple-200">
            <Shield size={12} className="text-primary" />
            <span>Our Approach</span>
          </div>
          <h2 className="text-3xl sm:text-4xl font-extrabold text-[#0F172A] tracking-tight">
            Personal insights, with care.
          </h2>
          <p className="text-slate-600 text-sm sm:text-base leading-relaxed">
            Health technology should leave you feeling grounded and informed—never anxious, judged, or confused.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="bg-white rounded-3xl p-8 border border-purple-100 shadow-soft space-y-3">
            <div className="w-10 h-10 rounded-2xl bg-purple-50 text-primary flex items-center justify-center font-bold text-sm">
              01
            </div>
            <h3 className="text-lg font-bold text-slate-900">Personalized</h3>
            <p className="text-sm text-slate-600 leading-relaxed">
              Cycle estimates depend on your individual recorded history and natural variance, never an
              arbitrary one-size-fits-all 28-day rule.
            </p>
          </div>

          <div className="bg-white rounded-3xl p-8 border border-purple-100 shadow-soft space-y-3">
            <div className="w-10 h-10 rounded-2xl bg-purple-50 text-primary flex items-center justify-center font-bold text-sm">
              02
            </div>
            <h3 className="text-lg font-bold text-slate-900">Explainable</h3>
            <p className="text-sm text-slate-600 leading-relaxed">
              We present the clear logic, confidence metrics, and interval exclusions behind estimates,
              ensuring your records remain completely transparent.
            </p>
          </div>

          <div className="bg-white rounded-3xl p-8 border border-purple-100 shadow-soft space-y-3">
            <div className="w-10 h-10 rounded-2xl bg-purple-50 text-primary flex items-center justify-center font-bold text-sm">
              03
            </div>
            <h3 className="text-lg font-bold text-slate-900">Supportive</h3>
            <p className="text-sm text-slate-600 leading-relaxed">
              OvaCare AI supports self-awareness and healthcare discussions. It is an informational
              wellness companion, not a replacement for qualified medical diagnosis.
            </p>
          </div>
        </div>
      </section>

      {/* ==================================================================== */}
      {/* Section 6: Final CTA                                                 */}
      {/* ==================================================================== */}
      <section className="w-full max-w-7xl mx-auto px-4 sm:px-8 lg:px-12 pb-16 sm:pb-24">
        <div className="bg-gradient-to-tr from-purple-600 via-indigo-600 to-purple-700 text-white rounded-3xl p-10 sm:p-14 lg:p-16 shadow-premium text-center relative overflow-hidden space-y-6">
          <div className="inline-flex items-center space-x-1.5 bg-white/20 text-white text-xs font-bold px-3.5 py-1 rounded-full backdrop-blur-md">
            <Heart size={12} className="fill-white" />
            <span>Start Your Wellness Space</span>
          </div>

          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight max-w-2xl mx-auto leading-tight">
            Start understanding your personal patterns.
          </h2>

          <p className="text-white/90 text-sm sm:text-base max-w-xl mx-auto leading-relaxed font-normal">
            Bring cycle tracking, wellbeing observations, and helpful insights together with OvaCare AI.
          </p>

          <div className="flex flex-wrap items-center justify-center gap-4 pt-2">
            <button
              type="button"
              onClick={user ? onGoToDashboard : onGetStarted}
              className="bg-white hover:bg-purple-50 text-primary px-8 py-4 rounded-2xl font-bold text-sm shadow-lg transition transform hover:-translate-y-0.5 cursor-pointer"
            >
              <span>{user ? 'Open My Dashboard' : 'Create Your Account'}</span>
            </button>

            {onDemoMode && !user && (
              <button
                type="button"
                onClick={() => onDemoMode('maya.demo@example.com')}
                className="bg-white/15 hover:bg-white/25 text-white border border-white/30 px-6 py-4 rounded-2xl font-bold text-sm backdrop-blur-md transition cursor-pointer"
              >
                <span>Try Maya Demo Account</span>
              </button>
            )}
          </div>

          <p className="text-xs text-white/70 pt-2">
            No credit card required • Local-first privacy • Evidence-based clinical guidelines
          </p>
        </div>
      </section>

      {/* ==================================================================== */}
      {/* Section 7: Footer                                                    */}
      {/* ==================================================================== */}
      <footer className="w-full bg-white border-t border-purple-100/80 py-12 px-4 sm:px-8 lg:px-12 text-xs text-slate-500">
        <div className="max-w-7xl mx-auto space-y-8">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-6">
            <div className="flex items-center space-x-2">
              <div className="bg-primary p-1.5 rounded-xl text-white shadow-soft">
                <Heart size={16} className="fill-white" />
              </div>
              <span className="text-base font-bold text-slate-800">OvaCare AI</span>
            </div>

            <div className="flex flex-wrap items-center gap-6 text-slate-600 font-semibold">
              <button onClick={() => scrollToSection('features')} className="hover:text-primary transition">
                Features
              </button>
              <button onClick={() => scrollToSection('how-it-works')} className="hover:text-primary transition">
                How It Works
              </button>
              <button onClick={() => scrollToSection('our-approach')} className="hover:text-primary transition">
                Our Approach
              </button>
              {user ? (
                <button onClick={onGoToDashboard} className="hover:text-primary transition text-primary font-bold">
                  Dashboard
                </button>
              ) : (
                <>
                  <button onClick={onLogin} className="hover:text-primary transition">
                    Log In
                  </button>
                  <button onClick={onGetStarted} className="hover:text-primary transition text-primary font-bold">
                    Create Account
                  </button>
                </>
              )}
            </div>
          </div>

          {/* Explicit Medical Disclaimer Box */}
          <div className="bg-purple-50/70 border border-purple-100 rounded-2xl p-4 text-[11px] text-slate-600 leading-relaxed">
            <strong className="text-slate-800 font-bold block mb-1">Important Health Notice:</strong>
            OvaCare AI provides informational wellness support and cycle estimates based on user-recorded data. It is not a medical device, does not diagnose medical conditions (including PCOS or cycle irregularities), and does not replace professional medical advice, evaluation, or treatment from a qualified healthcare provider.
          </div>

          <div className="flex flex-col sm:flex-row justify-between items-center text-slate-400 text-[11px] gap-2 pt-2 border-t border-purple-50">
            <span>© {new Date().getFullYear()} OvaCare AI. Built with care for real life.</span>
            <span>Made for thoughtful health journeys ♡</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
