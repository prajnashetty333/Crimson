import React, { useState, useEffect, useRef } from 'react';
import {
  Send,
  Mic,
  MicOff,
  Volume2,
  VolumeX,
  Square,
  Trash2,
  Sparkles,
  Info,
  AlertTriangle,
  Heart,
  HelpCircle,
  RefreshCw,
  PhoneCall,
  X,
  MessageCircle,
  MessageSquare,
  ChevronUp,
  ChevronDown,
  Minimize2,
  Maximize2,
  BookOpen,
  ExternalLink
} from 'lucide-react';
import CompanionAvatar3D from './CompanionAvatar3D';

const INITIAL_MESSAGE = {
  id: 'init_welcome',
  role: 'assistant',
  content: "Hey there! I'm here to chat about whatever is on your mind—how your day went, what you're up to, or any health and wellness questions whenever you want to explore them. How are you doing today?",
  timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
};

const SUGGESTED_TOPICS = [
  "☕ How's your day going?",
  "🎬 Suggest a cozy movie to watch",
  "🌸 Can PCOS affect menstrual cycle length?",
  "💧 Gentle remedies for easing painful cramps"
];

export default function Companion({ user, token, apiBase }) {
  // Conversation panel state: CLOSED by default as required
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [chatMode, setChatMode] = useState('text'); // 'voice' | 'text'

  // Chat state
  const [messages, setMessages] = useState([INITIAL_MESSAGE]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);

  // Avatar and Voice State
  const [avatarState, setAvatarState] = useState('idle'); // 'idle' | 'listening' | 'thinking' | 'empathy' | 'reassurance' | 'speaking' | 'error'
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [voiceOutputEnabled, setVoiceOutputEnabled] = useState(true);

  // Speech Recognition State
  const [isListening, setIsListening] = useState(false);
  const [voiceTranscript, setVoiceTranscript] = useState('');
  const [speechSupported, setSpeechSupported] = useState(true);
  const recognitionRef = useRef(null);
  const transcriptRef = useRef('');
  const handleSendMessageRef = useRef(null);
  const isLoadingRef = useRef(false);
  const messagesRef = useRef(messages);

  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);

  useEffect(() => {
    isLoadingRef.current = isLoading;
  }, [isLoading]);

  // Disclaimer / Emergency modal state
  const [showDisclaimer, setShowDisclaimer] = useState(false);
  const [showEmergencyHelp, setShowEmergencyHelp] = useState(false);
  const [expandedSources, setExpandedSources] = useState({});

  const toggleSources = (msgId) => {
    setExpandedSources(prev => ({
      ...prev,
      [msgId]: !prev[msgId]
    }));
  };

  // DOM ref for auto-scrolling
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Initial warm greeting animation on mount
  useEffect(() => {
    setAvatarState('greeting');
    const timer = setTimeout(() => {
      setAvatarState(curr => (curr === 'greeting' ? 'idle' : curr));
    }, 3800);
    return () => clearTimeout(timer);
  }, []);

  // Auto-scroll to bottom of conversation
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading, voiceTranscript]);

  // Initialize Speech Recognition
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setSpeechSupported(false);
      return;
    }

    const recognizer = new SpeechRecognition();
    recognizer.continuous = false;
    recognizer.interimResults = true;
    recognizer.lang = 'en-US';

    recognizer.onstart = () => {
      setIsListening(true);
      setAvatarState('listening');
      setErrorMsg(null);
    };

    recognizer.onresult = (event) => {
      let interim = '';
      let finalTranscript = '';
      for (let i = event.resultIndex; i < event.results.length; ++i) {
        if (event.results[i].isFinal) {
          finalTranscript += event.results[i][0].transcript;
        } else {
          interim += event.results[i][0].transcript;
        }
      }
      const current = (finalTranscript || interim).trim();
      transcriptRef.current = current;
      setVoiceTranscript(current);
      setInputText(current);
    };

    recognizer.onerror = (event) => {
      console.warn('Speech recognition error:', event.error);
      setIsListening(false);
      setAvatarState('idle');
      transcriptRef.current = '';
      if (event.error === 'not-allowed') {
        setErrorMsg('Microphone permission was denied. Please allow microphone access in your browser to talk with your companion.');
      } else if (event.error === 'no-speech') {
        setErrorMsg(null);
      } else if (event.error !== 'aborted') {
        setErrorMsg(`Speech recognition issue: ${event.error}`);
      }
    };

    recognizer.onend = () => {
      setIsListening(false);
      const textToSend = transcriptRef.current?.trim();
      transcriptRef.current = '';
      setVoiceTranscript('');

      if (textToSend && !isLoadingRef.current) {
        handleSendMessageRef.current?.(textToSend);
      } else {
        setAvatarState('idle');
      }
    };

    recognitionRef.current = recognizer;

    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch (e) {}
      }
      window.speechSynthesis?.cancel();
    };
  }, []);

  // Text-To-Speech Output
  const speakText = (text, forceSpeak = false) => {
    if ((!voiceOutputEnabled && !forceSpeak) || !('speechSynthesis' in window)) return;

    window.speechSynthesis.cancel(); // Stop any pending speech

    // Clean text of emojis / symbols for natural TTS pronunciation
    const cleanText = text
      .replace(/[\u{1F600}-\u{1F64F}\u{1F300}-\u{1F5FF}\u{1F680}-\u{1F6FF}\u{1F1E0}-\u{1F1FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]/gu, '')
      .replace(/\*/g, '')
      .trim();

    if (!cleanText) return;

    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.rate = 0.96;
    utterance.pitch = 1.05;

    // Select natural female voice
    const voices = window.speechSynthesis.getVoices();
    const femaleVoice = voices.find(v =>
      (v.name.includes('Female') || v.name.includes('Samantha') || v.name.includes('Karen') ||
       v.name.includes('Victoria') || v.name.includes('Zira') || v.name.includes('Google UK English Female')) &&
      v.lang.startsWith('en')
    ) || voices.find(v => v.lang.startsWith('en'));

    if (femaleVoice) {
      utterance.voice = femaleVoice;
    }

    utterance.onstart = () => {
      setIsSpeaking(true);
      setAvatarState('speaking');
    };

    utterance.onend = () => {
      setIsSpeaking(false);
      setAvatarState('reassurance');
      setTimeout(() => {
        setAvatarState((curr) => (curr === 'reassurance' ? 'idle' : curr));
      }, 2600);
    };

    utterance.onerror = () => {
      setIsSpeaking(false);
      setAvatarState('idle');
    };

    window.speechSynthesis.speak(utterance);
  };

  const handleStopSpeaking = () => {
    window.speechSynthesis?.cancel();
    setIsSpeaking(false);
    setAvatarState('idle');
  };

  const handleToggleVoiceInput = () => {
    if (!speechSupported) {
      setErrorMsg('Voice input is not supported in this browser. Please use Chrome, Edge, or Safari.');
      return;
    }

    if (isListening) {
      recognitionRef.current?.stop();
    } else {
      handleStopSpeaking();
      setVoiceTranscript('');
      try {
        recognitionRef.current?.start();
      } catch (err) {
        console.warn('Speech recognition start failed:', err);
      }
    }
  };

  // Option A — Voice Conversation starter (Voice-first: does NOT open conversation window)
  const handleStartVoiceChat = () => {
    // If companion is speaking aloud, tapping voice button halts speech
    if (isSpeaking) {
      handleStopSpeaking();
      return;
    }

    // If currently listening, tapping voice button stops recording and submits transcription
    if (isListening) {
      recognitionRef.current?.stop();
      return;
    }

    // If companion is currently thinking/processing, guard against duplicate requests
    if (isLoading) {
      return;
    }

    // Voice mode enabled, keeping conversation window CLOSED on the main screen
    setChatMode('voice');
    setVoiceOutputEnabled(true);
    setVoiceTranscript('');
    setErrorMsg(null);

    if (!speechSupported) {
      setErrorMsg('Voice input is not supported in this browser. Please use Chrome, Edge, or Safari, or click "Chat by text".');
      return;
    }

    try {
      if (recognitionRef.current) {
        recognitionRef.current.start();
      }
    } catch (err) {
      console.warn('Speech recognition start failed or already active:', err);
    }
  };

  // Option B — Text Conversation starter (Opens conversation window with text input)
  const handleStartTextChat = () => {
    handleStopSpeaking();
    if (isListening) {
      transcriptRef.current = ''; // Discard partial transcript so it doesn't auto-send
      recognitionRef.current?.stop();
      setIsListening(false);
    }
    setIsChatOpen(true);
    setChatMode('text');
    setVoiceOutputEnabled(false); // Do not play audio automatically in text mode
    setErrorMsg(null);
    setTimeout(() => {
      inputRef.current?.focus();
    }, 150);
  };

  // Close Conversation Handler (Preserves chat history, stops audio & microphone)
  const handleCloseChat = () => {
    handleStopSpeaking();
    if (isListening) {
      transcriptRef.current = '';
      recognitionRef.current?.stop();
      setIsListening(false);
    }
    setIsChatOpen(false);
    setAvatarState('idle');
  };

  // Determine explicit reactive application state
  const effectiveState = isSpeaking
    ? 'speaking'
    : isListening
    ? 'listening'
    : isLoading
    ? 'thinking'
    : errorMsg
    ? 'error'
    : avatarState;

  // Check crisis keywords to prioritize urgent human safety
  const checkSafetyKeywords = (text) => {
    const crisisTriggers = ['suicide', 'kill myself', 'end my life', 'self-harm', 'emergency', 'heart attack', 'unconscious'];
    const lower = text.toLowerCase();
    return crisisTriggers.some(t => lower.includes(t));
  };

  // Check empathy triggers (pain, emotional strain, menstrual distress)
  const checkEmpathyKeywords = (text) => {
    const triggers = ['pain', 'cramp', 'hurt', 'sad', 'crying', 'anxious', 'stress', 'tired', 'exhausted', 'flare', 'bleed', 'scared', 'worried', 'struggling', 'hard day'];
    const lower = text.toLowerCase();
    return triggers.some(t => lower.includes(t));
  };

  const handleSendMessage = async (textToSend = null) => {
    const rawContent = textToSend || inputText;
    const trimmed = rawContent.trim();
    if (!trimmed || isLoading) return;

    // Check crisis keywords
    if (checkSafetyKeywords(trimmed)) {
      setShowEmergencyHelp(true);
    }

    handleStopSpeaking();
    if (isListening) {
      transcriptRef.current = '';
      recognitionRef.current?.stop();
    }

    const userMessage = {
      id: `usr_${Date.now()}`,
      role: 'user',
      content: trimmed,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages(prev => [...prev, userMessage]);
    setInputText('');
    setVoiceTranscript('');
    setIsLoading(true);

    // Responsive Avatar reaction: empathy for distress, otherwise thinking
    if (checkEmpathyKeywords(trimmed)) {
      setAvatarState('empathy');
      setTimeout(() => {
        setAvatarState((curr) => (curr === 'empathy' ? 'thinking' : curr));
      }, 1600);
    } else {
      setAvatarState('thinking');
    }
    setErrorMsg(null);

    // Format bounded conversation history for server from freshest ref
    const historyPayload = messagesRef.current
      .filter(m => m.id !== 'init_welcome')
      .slice(-8)
      .map(m => ({ role: m.role, content: m.content }));

    const authToken = token || localStorage.getItem('ovacare_token');

    try {
      const res = await fetch(`${apiBase}/companion/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(authToken ? { 'Authorization': `Bearer ${authToken}` } : {})
        },
        body: JSON.stringify({
          message: trimmed,
          history: historyPayload
        })
      });

      let data = {};
      try {
        data = await res.json();
      } catch (jsonErr) {
        data = { error: `Server response error (${res.status}). Please try again in a moment.` };
      }

      if (!res.ok) {
        throw new Error(data.error || 'Failed to receive reply from companion.');
      }

      const structured = data.structured || {};
      const answerContent = structured.answer || data.response;

      const assistantMessage = {
        id: `asst_${Date.now()}`,
        role: 'assistant',
        content: answerContent,
        confidence: structured.confidence || 'moderate',
        medicalTopic: structured.medical_topic,
        sources: structured.sources || [],
        needsProfessionalCare: structured.needs_professional_care || false,
        urgency: structured.urgency || 'routine',
        emotion: structured.emotion || 'warm',
        model: data.model,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };

      setMessages(prev => [...prev, assistantMessage]);
      setIsLoading(false);

      // Trigger Voice TTS playback only in voice mode when voice output is enabled
      // Spoken voice speaks ONLY conversational answer text (never URLs or citations)
      if (voiceOutputEnabled && chatMode === 'voice') {
        speakText(answerContent);
      } else {
        setAvatarState('idle');
      }
    } catch (err) {
      console.error('Companion request error:', err);
      setIsLoading(false);
      setAvatarState('error');
      setErrorMsg(err.message || 'The companion could not connect right now.');
      setTimeout(() => {
        if (avatarState === 'error') setAvatarState('idle');
      }, 4000);
    }
  };

  // Keep fresh reference for speech recognition callback
  handleSendMessageRef.current = handleSendMessage;

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleClearConversation = () => {
    handleStopSpeaking();
    if (isListening) recognitionRef.current?.stop();
    setMessages([INITIAL_MESSAGE]);
    setInputText('');
    setVoiceTranscript('');
    setErrorMsg(null);
    setAvatarState('idle');
  };

  return (
    <div className="space-y-4 animate-fade-in pb-32 sm:pb-24 w-full max-w-full overflow-x-hidden">
      {/* Top Companion Header Bar */}
      <div className="bg-white/80 backdrop-blur-md rounded-2xl p-4 border border-purple-100/80 shadow-2xs flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-purple-500 to-pink-400 flex items-center justify-center text-white shadow-soft">
            <Sparkles size={20} className="fill-white" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-lg font-bold text-textPrimary tracking-tight">OvaCare AI Companion</h1>
            </div>
            <p className="text-xs text-textSecondary">
              Your conversational friend for daily life, listening, and evidence-grounded health answers
            </p>
          </div>
        </div>

        {/* Action Controls: Audio toggle, Clear, Disclaimer, and Close (if open) */}
        <div className="flex items-center space-x-2 shrink-0 self-end sm:self-auto">
          {isChatOpen && (
            <button
              onClick={handleCloseChat}
              className="bg-purple-50 hover:bg-purple-100 text-textPrimary px-3 py-1.5 rounded-xl border border-purple-200 text-xs font-semibold flex items-center space-x-1 cursor-pointer transition shadow-2xs"
              title="Close conversation window"
            >
              <X size={14} />
              <span>Close Chat</span>
            </button>
          )}



          <button
            onClick={() => {
              if (voiceOutputEnabled) handleStopSpeaking();
              setVoiceOutputEnabled(!voiceOutputEnabled);
            }}
            className={`p-2 rounded-xl text-xs font-medium border transition flex items-center space-x-1.5 cursor-pointer ${
              voiceOutputEnabled
                ? 'bg-purple-50 text-primary border-purple-200 hover:bg-purple-100'
                : 'bg-white text-textLight border-purple-100 hover:text-textSecondary'
            }`}
            title={voiceOutputEnabled ? 'Voice output is active' : 'Voice output is muted'}
          >
            {voiceOutputEnabled ? <Volume2 size={16} /> : <VolumeX size={16} />}
            <span className="hidden md:inline text-xs">{voiceOutputEnabled ? 'Voice On' : 'Voice Off'}</span>
          </button>

          <button
            onClick={handleClearConversation}
            className="p-2 rounded-xl text-textLight hover:text-rose-600 hover:bg-rose-50 border border-purple-100/70 transition cursor-pointer"
            title="Clear current session chat"
          >
            <Trash2 size={16} />
          </button>

          <button
            onClick={() => setShowDisclaimer(true)}
            className="p-2 rounded-xl text-textLight hover:text-primary hover:bg-purple-50 border border-purple-100/70 transition cursor-pointer"
            title="Healthcare Disclaimer & Ethics Pledge"
          >
            <Info size={16} />
          </button>
        </div>
      </div>

      {/* ======================================================== */}
      {/* INTERACTION SECTION: DEFAULT CLOSED VIEW OR EXPANDED    */}
      {/* ======================================================== */}
      {!isChatOpen ? (
        /* Default Screen: Avatar Prominently Displayed with Compact Controls Directly Below */
        <div className="max-w-md mx-auto space-y-3.5 animate-fade-in">
          {/* Prominent Girl Avatar */}
          <CompanionAvatar3D
            avatarState={avatarState}
            isSpeaking={isSpeaking}
            isListening={isListening}
            isThinking={isLoading}
          />

          {/* Compact Interaction Controls directly below the avatar */}
          <div className="bg-white/95 backdrop-blur-md rounded-3xl p-4 border border-purple-100 shadow-soft space-y-3">
            {/* Status Line */}
            <div className="flex items-center justify-between px-1">
              <div className="flex items-center space-x-2">
                <span className="relative flex h-2.5 w-2.5">
                  <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
                    effectiveState === 'speaking' ? 'bg-teal-500' :
                    effectiveState === 'listening' ? 'bg-rose-500' :
                    effectiveState === 'thinking' ? 'bg-indigo-500' :
                    'bg-emerald-500'
                  }`}></span>
                  <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${
                    effectiveState === 'speaking' ? 'bg-teal-600' :
                    effectiveState === 'listening' ? 'bg-rose-600' :
                    effectiveState === 'thinking' ? 'bg-indigo-600' :
                    'bg-emerald-600'
                  }`}></span>
                </span>
                <span className="text-xs font-semibold text-textPrimary">
                  {effectiveState === 'speaking' ? 'Speaking response...' :
                   effectiveState === 'listening' ? 'Listening…' :
                   effectiveState === 'thinking' ? 'Thinking…' :
                   effectiveState === 'error' ? 'Connection issue' :
                   'Ready to listen and support'}
                </span>
              </div>


            </div>

            {/* Subtle live voice transcript when listening */}
            {isListening && voiceTranscript && (
              <div className="text-xs italic text-teal-900 bg-teal-50/80 border border-teal-200/80 rounded-xl px-3 py-1.5 text-center animate-fade-in">
                "{voiceTranscript}"
              </div>
            )}

            {/* Subtle thinking indicator */}
            {isLoading && (
              <div className="text-xs text-purple-800 bg-purple-50/80 border border-purple-200/80 rounded-xl px-3 py-1.5 text-center animate-pulse flex items-center justify-center space-x-2">
                <Sparkles size={13} className="animate-spin text-purple-600" />
                <span>Thinking…</span>
              </div>
            )}



            {/* Error notice */}
            {errorMsg && (
              <div className="text-xs text-rose-800 bg-rose-50 border border-rose-200 rounded-xl px-3 py-2 flex items-start justify-between gap-2 animate-fade-in">
                <span className="leading-snug">{errorMsg}</span>
                <button
                  onClick={() => setErrorMsg(null)}
                  className="text-rose-500 hover:text-rose-800 shrink-0 p-0.5 cursor-pointer"
                  title="Dismiss"
                >
                  <X size={13} />
                </button>
              </div>
            )}

            {/* Two Visible Interaction Controls: Option A (Voice) & Option B (Text) */}
            <div className="grid grid-cols-2 gap-3 pt-0.5">
              {/* Option A: Voice Conversation (Voice-first without opening transcript window) */}
              <button
                type="button"
                onClick={handleStartVoiceChat}
                disabled={isLoading}
                className={`h-12 px-4 rounded-2xl text-xs font-semibold flex items-center justify-center space-x-2 transition cursor-pointer shadow-soft active:scale-[0.98] ${
                  isListening
                    ? 'bg-rose-600 hover:bg-rose-700 text-white shadow-rose-200 ring-2 ring-rose-300 animate-pulse'
                    : isSpeaking
                    ? 'bg-amber-600 hover:bg-amber-700 text-white shadow-soft'
                    : isLoading
                    ? 'bg-purple-200 text-purple-700 cursor-not-allowed opacity-80'
                    : 'bg-teal-700 hover:bg-teal-800 text-white shadow-soft'
                }`}
                title={
                  isListening ? 'Stop listening and send' :
                  isSpeaking ? 'Stop speaking' :
                  isLoading ? 'Formulating response...' :
                  'Talk to companion using your voice'
                }
              >
                {isListening ? (
                  <>
                    <Square size={16} className="fill-white" />
                    <span>Stop listening</span>
                  </>
                ) : isSpeaking ? (
                  <>
                    <Square size={16} className="fill-white" />
                    <span>Stop speaking</span>
                  </>
                ) : isLoading ? (
                  <>
                    <Sparkles size={16} className="animate-spin text-purple-700" />
                    <span>Thinking…</span>
                  </>
                ) : (
                  <>
                    <Mic size={18} />
                    <span>Talk to me</span>
                  </>
                )}
              </button>

              {/* Option B: Text Conversation (Opens conversation window) */}
              <button
                type="button"
                onClick={handleStartTextChat}
                className="h-12 px-4 rounded-2xl text-xs font-semibold flex items-center justify-center space-x-2 transition cursor-pointer border border-purple-200/90 bg-[#FAF8FC] hover:bg-purple-100/70 text-textPrimary hover:text-teal-900 shadow-2xs active:scale-[0.98]"
                title="Open text conversation window"
              >
                <MessageSquare size={18} className="text-teal-700" />
                <span>Chat by text</span>
              </button>
            </div>
          </div>

          {/* Compassionate Care Focus card */}
          <div className="bg-white/80 rounded-2xl p-3.5 border border-purple-100/70 shadow-2xs space-y-1 text-center">
            <div className="flex items-center justify-center space-x-1.5 text-xs font-semibold text-textPrimary">
              <Heart size={13} className="text-primary fill-purple-100" />
              <span>Compassionate Care Focus</span>
            </div>
            <p className="text-[11px] text-textSecondary leading-relaxed">
              Trained on holistic hormonal wellness, cycle phases, nutrition, and everyday lifestyle coping strategies. Like talking with a caring, knowledgeable friend.
            </p>
          </div>
        </div>
      ) : (
        /* Expanded View: Two-column Desktop Layout (Avatar on left, Chat on right) / Stacked on Mobile */
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start animate-fade-in">
          {/* Left Column: Avatar & Controls (~5 cols) */}
          <div className="lg:col-span-5 lg:sticky lg:top-4 space-y-3.5">
            <CompanionAvatar3D
              avatarState={avatarState}
              isSpeaking={isSpeaking}
              isListening={isListening}
              isThinking={isLoading}
            />

            {/* Compact Interaction Controls (allows switching mode or toggling mic) */}
            <div className="bg-white/95 backdrop-blur-md rounded-2xl p-3 border border-purple-100 shadow-2xs space-y-2.5">
              <div className="flex items-center justify-between px-1">
                <div className="flex items-center space-x-2">
                  <span className="relative flex h-2 w-2">
                    <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
                      effectiveState === 'speaking' ? 'bg-teal-500' :
                      effectiveState === 'listening' ? 'bg-rose-500' :
                      effectiveState === 'thinking' ? 'bg-indigo-500' :
                      'bg-emerald-500'
                    }`}></span>
                    <span className={`relative inline-flex rounded-full h-2 w-2 ${
                      effectiveState === 'speaking' ? 'bg-teal-600' :
                      effectiveState === 'listening' ? 'bg-rose-600' :
                      effectiveState === 'thinking' ? 'bg-indigo-600' :
                      'bg-emerald-600'
                    }`}></span>
                  </span>
                  <span className="text-[11px] font-medium text-textSecondary">
                    {effectiveState === 'speaking' ? 'Speaking response...' :
                     effectiveState === 'listening' ? 'Listening to your voice...' :
                     effectiveState === 'thinking' ? 'Formulating guidance...' :
                     effectiveState === 'error' ? 'Connection issue' :
                     'Ready to listen and support'}
                  </span>
                </div>


              </div>

              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={handleStartVoiceChat}
                  className={`h-10 px-3 rounded-xl text-xs font-semibold flex items-center justify-center space-x-1.5 transition cursor-pointer shadow-2xs active:scale-[0.98] ${
                    chatMode === 'voice' && isListening
                      ? 'bg-rose-600 text-white shadow-rose-200 ring-2 ring-rose-300 animate-pulse'
                      : isSpeaking
                      ? 'bg-amber-600 hover:bg-amber-700 text-white shadow-soft'
                      : chatMode === 'voice'
                      ? 'bg-teal-700 text-white ring-2 ring-teal-500/30 shadow-soft'
                      : 'bg-teal-50 hover:bg-teal-100 text-teal-800 border border-teal-200/80'
                  }`}
                  title={isSpeaking ? 'Stop speaking' : 'Switch to voice mode'}
                >
                  {isSpeaking ? (
                    <>
                      <Square size={13} className="fill-white" />
                      <span>Stop speaking</span>
                    </>
                  ) : (
                    <>
                      <Mic size={15} />
                      <span>Talk to me</span>
                    </>
                  )}
                </button>

                <button
                  type="button"
                  onClick={handleStartTextChat}
                  className={`h-10 px-3 rounded-xl text-xs font-semibold flex items-center justify-center space-x-1.5 transition cursor-pointer shadow-2xs active:scale-[0.98] border ${
                    chatMode === 'text'
                      ? 'bg-purple-100 text-primary border-purple-300 ring-2 ring-purple-300/40'
                      : 'bg-[#FAF8FC] hover:bg-purple-50 text-textPrimary border-purple-200/80'
                  }`}
                  title="Switch to text mode"
                >
                  <MessageSquare size={15} className="text-teal-700" />
                  <span>Chat by text</span>
                </button>
              </div>
            </div>

            {/* Quick Guidance Card beneath Avatar */}
            <div className="bg-white rounded-2xl p-3.5 border border-purple-100/80 shadow-2xs space-y-1.5">
              <div className="flex items-center space-x-2 text-xs font-semibold text-textPrimary">
                <Heart size={14} className="text-primary fill-purple-100" />
                <span>Compassionate Care Focus</span>
              </div>
              <p className="text-[11px] text-textSecondary leading-relaxed">
                Trained on holistic hormonal wellness, cycle phases, nutrition, and everyday lifestyle coping strategies. Responses are non-judgmental and personalized to your journey.
              </p>
            </div>
          </div>

          {/* Right Column: Chat Stream & Interactive Voice Bar (~7 cols) */}
          <div className="lg:col-span-7 flex flex-col bg-white rounded-3xl border border-purple-100/80 shadow-soft h-[580px] sm:h-[620px] overflow-hidden">
            {/* Chat Panel Top Control Bar */}
            <div className="px-4 py-2.5 bg-purple-50/60 border-b border-purple-100 flex items-center justify-between shrink-0">
              <div className="flex items-center space-x-2">
                <span className={`text-[10px] font-semibold px-2.5 py-0.5 rounded-full border ${
                  chatMode === 'voice'
                    ? 'bg-teal-100 text-teal-800 border-teal-200'
                    : 'bg-purple-100 text-primary border-purple-200'
                }`}>
                  {chatMode === 'voice' ? '🎙️ Voice Mode' : '💬 Text Mode'}
                </span>
                <span className="text-xs font-bold text-textPrimary hidden sm:inline">
                  Conversation
                </span>
              </div>

              {/* Action Buttons: Stop, Voice Toggle, Clear, Close */}
              <div className="flex items-center space-x-1.5">
                {isSpeaking && (
                  <button
                    onClick={handleStopSpeaking}
                    className="bg-rose-50 hover:bg-rose-100 text-rose-700 text-[11px] font-semibold px-2.5 py-1 rounded-lg border border-rose-200 transition flex items-center space-x-1 cursor-pointer animate-pulse"
                    title="Stop speech playback"
                  >
                    <Square size={11} className="fill-rose-700" />
                    <span>Stop</span>
                  </button>
                )}

                <button
                  onClick={() => {
                    if (voiceOutputEnabled) handleStopSpeaking();
                    setVoiceOutputEnabled(!voiceOutputEnabled);
                  }}
                  className={`p-1.5 rounded-lg text-xs border transition cursor-pointer ${
                    voiceOutputEnabled
                      ? 'bg-purple-50 text-primary border-purple-200'
                      : 'bg-white text-textLight border-purple-100'
                  }`}
                  title={voiceOutputEnabled ? 'Voice reply enabled' : 'Voice reply muted'}
                >
                  {voiceOutputEnabled ? <Volume2 size={14} /> : <VolumeX size={14} />}
                </button>

                <button
                  onClick={handleClearConversation}
                  className="p-1.5 rounded-lg text-textLight hover:text-rose-600 hover:bg-rose-50 border border-purple-100/70 transition cursor-pointer"
                  title="Clear chat"
                >
                  <Trash2 size={14} />
                </button>

                {/* Close Button: closes conversation panel without losing messages */}
                <button
                  onClick={handleCloseChat}
                  className="bg-purple-100 hover:bg-purple-200 text-textPrimary hover:text-rose-700 text-xs font-semibold px-2.5 py-1 rounded-lg border border-purple-200 transition flex items-center space-x-1 cursor-pointer shadow-2xs ml-1"
                  title="Close conversation window"
                >
                  <X size={14} />
                  <span>Close</span>
                </button>
              </div>
            </div>

            {/* Chat Messages Scroll Container */}
            <div className="flex-1 min-h-0 overflow-y-auto p-4 sm:p-5 space-y-4">
            {messages.map((msg) => {
              const isUser = msg.role === 'user';
              return (
                <div
                  key={msg.id}
                  className={`flex items-start space-x-2.5 ${isUser ? 'flex-row-reverse space-x-reverse' : 'flex-row'}`}
                >
                  {/* Avatar Icon */}
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 shadow-2xs overflow-hidden border ${
                    isUser
                      ? 'bg-primary text-white text-xs font-semibold border-primary/20'
                      : 'border-purple-200 bg-purple-50'
                  }`}>
                    {isUser ? (
                      'You'
                    ) : (
                      <img
                        src="/images/ovacare-girl.png"
                        alt="OvaCare Companion"
                        className="w-full h-full object-cover"
                      />
                    )}
                  </div>

                  {/* Message Bubble */}
                  <div className={`max-w-[82%] sm:max-w-[76%] rounded-2xl px-4 py-3 text-xs leading-relaxed space-y-1.5 shadow-2xs ${
                    isUser
                      ? 'bg-primary text-white rounded-tr-none'
                      : 'bg-purple-50/60 border border-purple-100 text-textPrimary rounded-tl-none'
                  }`}>
                    <div className="whitespace-pre-wrap">{msg.content}</div>

                    {/* Emergency Red-Flag Advisory Box */}
                    {msg.urgency === 'emergency' && (
                      <div className="mt-2 p-2.5 rounded-xl bg-rose-50 border border-rose-300 text-rose-900 text-[11px] space-y-1">
                        <div className="font-bold flex items-center gap-1.5 text-rose-700">
                          <AlertTriangle size={13} className="shrink-0" />
                          <span>Emergency Medical Advisory</span>
                        </div>
                        <p className="leading-snug">
                          If you are experiencing sudden severe pain, heavy hemorrhaging, or fainting, please contact local emergency services (911 / 999 / 112) or go to the nearest emergency department immediately.
                        </p>
                      </div>
                    )}

                    {/* Limited Evidence / Emerging Research Badge */}
                    {msg.confidence === 'limited' && (
                      <div className="mt-1.5 inline-flex items-center space-x-1 text-[9px] font-medium text-amber-800 bg-amber-50 px-2 py-0.5 rounded-md border border-amber-200">
                        <Info size={10} className="shrink-0" />
                        <span>Evidence status: Emerging research / Low certainty</span>
                      </div>
                    )}

                    {/* Expandable Evidence Sources Section */}
                    {msg.sources && msg.sources.length > 0 && (
                      <div className="mt-2 pt-1 border-t border-purple-100/80">
                        <button
                          type="button"
                          onClick={() => toggleSources(msg.id)}
                          className="flex items-center space-x-1.5 text-[10px] font-semibold text-teal-800 hover:text-teal-900 bg-teal-50 hover:bg-teal-100/80 px-2.5 py-1 rounded-lg border border-teal-200/80 transition cursor-pointer"
                        >
                          <BookOpen size={11} className="text-teal-700" />
                          <span>
                            {expandedSources[msg.id] ? 'Hide Clinical Sources' : `Verified Evidence Sources (${msg.sources.length})`}
                          </span>
                          <ChevronDown
                            size={11}
                            className={`transition-transform duration-200 ${expandedSources[msg.id] ? 'rotate-180' : ''}`}
                          />
                        </button>

                        {expandedSources[msg.id] && (
                          <div className="mt-2 space-y-1.5 animate-fade-in">
                            {msg.sources.map((src, sIdx) => (
                              <div
                                key={sIdx}
                                className="bg-white/95 rounded-xl p-2.5 border border-purple-100 text-[10px] space-y-1 shadow-2xs"
                              >
                                <div className="flex items-center justify-between text-textLight">
                                  <span className="font-bold text-teal-800">{src.organization}</span>
                                  <span>{src.date}</span>
                                </div>
                                <div className="font-medium text-textPrimary leading-snug">
                                  {src.title}
                                </div>
                                {src.evidence_level && (
                                  <div className="text-[9px] text-purple-700 italic">
                                    {src.evidence_level}
                                  </div>
                                )}
                                {src.url && (
                                  <div className="pt-0.5">
                                    <a
                                      href={src.url}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="inline-flex items-center space-x-1 text-primary hover:underline font-semibold"
                                    >
                                      <span>View clinical guidance</span>
                                      <ExternalLink size={10} />
                                    </a>
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Metadata & Audio Replay */}
                    <div className={`flex items-center justify-between text-[10px] pt-1 ${isUser ? 'text-purple-200' : 'text-textLight'}`}>
                      <span>{msg.timestamp}</span>
                      {!isUser && (
                        <button
                          onClick={() => speakText(msg.content, true)}
                          className="hover:text-primary transition flex items-center space-x-1 cursor-pointer ml-3"
                          title="Read this response aloud"
                        >
                          <Volume2 size={12} />
                          <span className="text-[10px]">Listen</span>
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}

            {/* Thinking / Typing indicator */}
            {isLoading && (
              <div className="flex items-start space-x-2.5">
                <div className="w-8 h-8 rounded-full overflow-hidden border border-purple-200 bg-purple-50 shrink-0 shadow-2xs">
                  <img
                    src="/images/ovacare-girl.png"
                    alt="OvaCare Companion"
                    className="w-full h-full object-cover"
                  />
                </div>
                <div className="bg-purple-50/60 border border-purple-100 rounded-2xl rounded-tl-none px-4 py-3 text-xs text-textSecondary flex items-center space-x-2 shadow-2xs animate-pulse">
                  <div className="flex space-x-1">
                    <div className="w-1.5 h-1.5 bg-primary rounded-full animate-bounce"></div>
                    <div className="w-1.5 h-1.5 bg-primary rounded-full animate-bounce [animation-delay:0.2s]"></div>
                    <div className="w-1.5 h-1.5 bg-primary rounded-full animate-bounce [animation-delay:0.4s]"></div>
                  </div>
                  <span className="text-[11px] font-medium text-textSecondary">OvaCare Companion is formulating guidance...</span>
                </div>
              </div>
            )}

            {/* Error Banner */}
            {errorMsg && (
              <div className="bg-rose-50 border border-rose-200 text-rose-800 px-3.5 py-2.5 rounded-xl text-xs flex items-center justify-between animate-fade-in">
                <div className="flex items-center space-x-2">
                  <AlertTriangle size={15} className="text-rose-500 shrink-0" />
                  <span className="font-medium">{errorMsg}</span>
                </div>
                <button
                  onClick={() => setErrorMsg(null)}
                  className="text-rose-600 hover:text-rose-900 cursor-pointer ml-2"
                >
                  <X size={14} />
                </button>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Quick Suggestion Chips (shown when few messages) */}
          {messages.length <= 4 && !isLoading && (
            <div className="px-4 py-2.5 bg-purple-50/40 border-t border-purple-100/70 flex flex-wrap items-center gap-2">
              <span className="text-[10px] font-bold text-textLight uppercase tracking-wider shrink-0 mr-1 flex items-center gap-1">
                <Sparkles size={11} className="text-teal-700" /> Suggestions:
              </span>
              {SUGGESTED_TOPICS.map((topic, i) => (
                <button
                  key={i}
                  onClick={() => handleSendMessage(topic)}
                  className="px-3 py-1 rounded-full bg-white hover:bg-purple-100/80 text-textSecondary hover:text-teal-800 text-[11px] font-medium border border-purple-100/90 transition cursor-pointer shadow-2xs hover:shadow-xs"
                >
                  {topic}
                </button>
              ))}
            </div>
          )}

          {/* Live Voice Transcript Floating Box */}
          {isListening && (
            <div className="px-4 py-2.5 bg-rose-50 border-t border-rose-200 text-rose-900 text-xs flex items-center justify-between animate-fade-in">
              <div className="flex items-center space-x-2 truncate">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-rose-500"></span>
                </span>
                <span className="font-semibold text-[11px] shrink-0">Hearing:</span>
                <span className="truncate italic text-rose-700">{voiceTranscript || 'Speak into your microphone...'}</span>
              </div>
              <button
                onClick={() => handleSendMessage()}
                disabled={!voiceTranscript.trim()}
                className="bg-rose-600 hover:bg-rose-700 disabled:opacity-50 text-white text-[11px] font-semibold px-3 py-1 rounded-lg transition cursor-pointer shrink-0 ml-2 shadow-2xs"
              >
                Send Words
              </button>
            </div>
          )}

          {/* Input & Voice Controls Footer */}
          <div className="p-3.5 sm:p-4 border-t border-purple-100 bg-white/95 shrink-0">
            <div className="flex items-center space-x-2.5">
              {/* Voice Input Microphone Button */}
              <button
                type="button"
                onClick={handleToggleVoiceInput}
                className={`h-11 w-11 rounded-2xl transition cursor-pointer flex items-center justify-center shrink-0 shadow-2xs ${
                  isListening
                    ? 'bg-rose-600 text-white shadow-rose-200 animate-pulse ring-2 ring-rose-300'
                    : 'bg-teal-50 hover:bg-teal-100 text-teal-800 border border-teal-200/80'
                }`}
                title={isListening ? 'Stop listening' : 'Start voice input (speech-to-text)'}
              >
                {isListening ? <MicOff size={19} /> : <Mic size={19} />}
              </button>

              {/* Text Input */}
              <div className="flex-1 relative flex items-center">
                <input
                  ref={inputRef}
                  type="text"
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder={isListening ? "Listening to your voice..." : "Ask your companion anything (Enter to send)..."}
                  disabled={isLoading}
                  maxLength={1000}
                  className="w-full h-11 pl-4 pr-10 text-xs rounded-2xl border border-purple-100/90 focus:outline-none focus:ring-1.5 focus:ring-teal-700 focus:border-teal-700 bg-purple-50/20 text-textPrimary placeholder:text-textLight transition shadow-2xs"
                />
                {inputText.length > 800 && (
                  <span className="absolute right-3 text-[10px] text-textLight font-mono">
                    {1000 - inputText.length}
                  </span>
                )}
              </div>

              {/* Send Button */}
              <button
                type="button"
                onClick={() => handleSendMessage()}
                disabled={!inputText.trim() || isLoading}
                className="h-11 w-11 bg-teal-700 hover:bg-teal-800 disabled:opacity-40 text-white rounded-2xl transition cursor-pointer shadow-soft flex items-center justify-center shrink-0"
                title="Send message"
              >
                <Send size={17} />
              </button>
            </div>

            {/* Micro Safe Health Footer */}
            <div className="flex items-center justify-between mt-2 px-1 text-[10px] text-textLight">
              <span>OvaCare AI provides general wellness support • Not clinical advice</span>
              <button
                onClick={() => setShowDisclaimer(true)}
                className="text-teal-700 hover:underline font-medium cursor-pointer"
              >
                Disclaimer
              </button>
            </div>
          </div>
        </div>
      </div>
      )}

      {/* ======================================================== */}
      {/* MODAL: Medical & Privacy Disclaimer */}
      {/* ======================================================== */}
      {showDisclaimer && (
        <div className="fixed inset-0 bg-purple-950/20 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-fade-in">
          <div className="bg-white w-full max-w-md rounded-3xl p-6 shadow-xl border border-purple-100 relative space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-purple-100">
              <div className="flex items-center space-x-2">
                <div className="p-1.5 bg-primary/10 text-primary rounded-xl">
                  <Heart size={18} />
                </div>
                <h3 className="text-base font-bold text-textPrimary">Companion Care & Ethics</h3>
              </div>
              <button
                onClick={() => setShowDisclaimer(false)}
                className="text-textLight hover:text-textPrimary cursor-pointer p-1 rounded-lg hover:bg-purple-50"
              >
                <X size={18} />
              </button>
            </div>

            <div className="space-y-3 text-xs text-textSecondary leading-relaxed">
              <div className="p-3 rounded-2xl bg-purple-50/70 border border-purple-100 space-y-1">
                <span className="font-semibold text-textPrimary">Non-Medical Wellness Information</span>
                <p>
                  OvaCare Companion is an AI wellness assistant. It does not provide medical diagnosis, write prescriptions, or replace formal care from a licensed gynecologist or physician.
                </p>
              </div>

              <div className="p-3 rounded-2xl bg-purple-50/70 border border-purple-100 space-y-1">
                <span className="font-semibold text-textPrimary">Confidentiality & Privacy</span>
                <p>
                  Conversations are processed in memory and are not logged or sold. We recommend avoiding typing identifying details such as social security or full private medical records.
                </p>
              </div>

              <div className="p-3 rounded-2xl bg-amber-50 border border-amber-200 text-amber-900 space-y-1">
                <span className="font-semibold">Concerning or Acute Symptoms</span>
                <p>
                  If you experience sudden severe abdominal pain, persistent heavy hemorrhaging, or fainting, seek urgent professional medical assistance immediately.
                </p>
              </div>
            </div>

            <div className="flex justify-end pt-2 border-t border-purple-100">
              <button
                onClick={() => setShowDisclaimer(false)}
                className="bg-primary hover:bg-primary-dark text-white text-xs font-semibold px-4 py-2 rounded-xl transition cursor-pointer shadow-2xs"
              >
                Understood
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ======================================================== */}
      {/* MODAL: Emergency Crisis Support Banner */}
      {/* ======================================================== */}
      {showEmergencyHelp && (
        <div className="fixed inset-0 bg-rose-950/25 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fade-in">
          <div className="bg-white w-full max-w-md rounded-3xl p-6 shadow-xl border border-rose-200 relative space-y-4">
            <div className="flex items-center space-x-2 text-rose-600 pb-2 border-b border-rose-100">
              <PhoneCall size={20} />
              <h3 className="text-base font-bold text-textPrimary">Support Resources Available Now</h3>
            </div>

            <p className="text-xs text-textSecondary leading-relaxed">
              Your safety and life are precious. If you are experiencing overwhelming distress, severe crisis, or need someone to talk to right now, please reach out to compassionate professionals:
            </p>

            <div className="space-y-2 text-xs">
              <div className="p-3 rounded-2xl bg-rose-50 border border-rose-200">
                <div className="font-bold text-rose-900">988 Suicide & Crisis Lifeline</div>
                <div className="text-rose-700 text-[11px]">Free, confidential, available 24/7 in US & Canada. Call or text 988.</div>
              </div>
              <div className="p-3 rounded-2xl bg-purple-50 border border-purple-200">
                <div className="font-bold text-purple-900">Crisis Text Line</div>
                <div className="text-purple-700 text-[11px]">Text HOME to 741741 to connect with a crisis counselor 24/7.</div>
              </div>
              <div className="p-3 rounded-2xl bg-slate-50 border border-slate-200">
                <div className="font-bold text-slate-800">International Emergency Services</div>
                <div className="text-slate-600 text-[11px]">Dial 911 (US), 112 (EU/UK), 999 (UK), or 000 (AU) for immediate physical emergencies.</div>
              </div>
            </div>

            <div className="flex justify-end pt-2 border-t border-rose-100">
              <button
                onClick={() => setShowEmergencyHelp(false)}
                className="bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold px-4 py-2 rounded-xl transition cursor-pointer shadow-2xs"
              >
                Close Support Notice
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
