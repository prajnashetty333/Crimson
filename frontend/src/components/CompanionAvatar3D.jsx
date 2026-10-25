import React from 'react';
import { Volume2, Sparkles, Mic, AlertCircle, RefreshCw, Heart } from 'lucide-react';

/**
 * OvaCare AI Companion Avatar
 * Displays the exact character portrait preserving authentic identity:
 * - Beautiful stylized female companion with warm wavy brown hair, friendly smile, and lavender top
 * - Preserves exact facial features, smile, skin tone, hair, and proportions (object-fit: contain, no distortion)
 * - Zero fake mouth overlays, duplicated lips, or lower-face warping transforms
 * - Reactive visual states (soft glow halo & bottom waveform equalizer) for listening, thinking, speaking, and idle
 * - Audio-reactive lifecycle: active when speaking, cleanly resting when stopped or idle
 */
export default function CompanionAvatar3D({
  avatarState = 'idle', // 'greeting' | 'listening' | 'thinking' | 'empathy' | 'reassurance' | 'speaking' | 'idle' | 'error'
  isSpeaking = false,
  isListening = false,
  isThinking = false
}) {
  // Determine effective expression state
  const effectiveState = isSpeaking
    ? 'speaking'
    : isListening
    ? 'listening'
    : isThinking
    ? 'thinking'
    : avatarState;

  return (
    <div className="relative w-full h-[380px] sm:h-[450px] lg:h-[500px] rounded-3xl overflow-hidden bg-gradient-to-b from-[#FAF8FC] via-[#F4EFFE] to-[#F8F5FD] border border-purple-100/90 shadow-soft flex flex-col justify-between select-none">
      {/* Top Status & State Pill */}
      <div className="absolute top-3.5 left-3.5 right-3.5 z-20 flex items-center justify-between pointer-events-none">
        <div className="flex items-center space-x-2 bg-white/95 backdrop-blur-md px-3 py-1.5 rounded-full border border-purple-100/80 shadow-2xs pointer-events-auto">
          <span className="relative flex h-2.5 w-2.5">
            <span
              className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
                effectiveState === 'speaking'
                  ? 'bg-teal-500'
                  : effectiveState === 'listening'
                  ? 'bg-rose-500'
                  : effectiveState === 'thinking'
                  ? 'bg-indigo-500'
                  : effectiveState === 'empathy'
                  ? 'bg-pink-500'
                  : 'bg-emerald-500'
              }`}
            ></span>
            <span
              className={`relative inline-flex rounded-full h-2.5 w-2.5 ${
                effectiveState === 'speaking'
                  ? 'bg-teal-600'
                  : effectiveState === 'listening'
                  ? 'bg-rose-600'
                  : effectiveState === 'thinking'
                  ? 'bg-indigo-600'
                  : effectiveState === 'empathy'
                  ? 'bg-pink-600'
                  : 'bg-emerald-600'
              }`}
            ></span>
          </span>
          <span className="text-[11px] font-semibold text-textPrimary capitalize">
            {effectiveState === 'speaking'
              ? 'Speaking response...'
              : effectiveState === 'listening'
              ? 'Listening attentively...'
              : effectiveState === 'thinking'
              ? 'Consulting care knowledge...'
              : effectiveState === 'empathy'
              ? 'Empathizing with you...'
              : effectiveState === 'reassurance'
              ? 'Reassuring support'
              : 'Attentive & Caring'}
          </span>
        </div>

        <div className="flex items-center space-x-1.5 bg-white/90 backdrop-blur-md px-2.5 py-1 rounded-full border border-purple-100/70 shadow-2xs text-[10px] text-textSecondary pointer-events-auto">
          <Sparkles size={11} className="text-teal-700" />
          <span>AI Companion</span>
        </div>
      </div>

      {/* Main Avatar Stage: Prominently displaying the exact girl image with stable authentic portrait */}
      <div className="relative flex-1 w-full flex items-center justify-center p-4 sm:p-5 pt-12 pb-14 overflow-hidden">
        {/* Soft Reactive Ambient Glow Halo behind the girl */}
        <div
          className={`absolute inset-8 rounded-full blur-3xl transition-all duration-700 pointer-events-none opacity-70 ${
            effectiveState === 'speaking'
              ? 'bg-gradient-to-tr from-teal-400/40 via-emerald-300/30 to-purple-300/25 scale-110 animate-pulse'
              : effectiveState === 'listening'
              ? 'bg-gradient-to-tr from-rose-400/40 via-pink-300/30 to-purple-300/25 scale-110 animate-pulse'
              : effectiveState === 'thinking'
              ? 'bg-gradient-to-tr from-indigo-400/35 via-purple-400/30 to-pink-300/25 scale-105 animate-pulse'
              : 'bg-gradient-to-tr from-purple-200/25 via-pink-100/25 to-teal-100/20 scale-100'
          }`}
        />

        {/* Pulsing state ring on active voice interaction */}
        {(isSpeaking || isListening) && (
          <div
            className={`absolute inset-10 rounded-full border-2 pointer-events-none transition-all duration-700 animate-ping opacity-25 ${
              isSpeaking ? 'border-teal-500' : 'border-rose-500'
            }`}
          />
        )}

        {/* The Exact Reference Girl Image — Pristine, Unaltered, Beautiful */}
        <div className={`relative z-10 w-full h-full flex items-center justify-center transition-transform duration-500 ${
          isSpeaking ? 'scale-[1.01]' : 'scale-100'
        }`}>
          <img
            src="/images/ovacare-girl.png"
            alt="OvaCare AI Wellness Companion"
            className="w-full h-full max-h-[380px] sm:max-h-[420px] object-contain drop-shadow-lg select-none pointer-events-none"
            style={{ objectFit: 'contain' }}
            loading="eager"
          />
        </div>
      </div>

      {/* Bottom State Visualizer Bar with Reactive Audio Waveforms */}
      <div className="absolute bottom-3 left-3.5 right-3.5 z-20 flex items-center justify-between text-[11px] text-textLight bg-white/90 backdrop-blur-md px-3.5 py-2 rounded-2xl border border-purple-100/70 shadow-2xs">
        <div className="flex items-center space-x-2">
          {effectiveState === 'speaking' && (
            <div className="flex items-center space-x-1.5 text-teal-700">
              <Volume2 size={13} className="animate-pulse" />
              <span className="font-medium text-[11px]">Speaking response</span>
              {/* Subtle Audio Waveform Bars */}
              <div className="flex items-center space-x-0.5 ml-1">
                <span className="w-0.5 h-2.5 bg-teal-600 rounded-full animate-bounce [animation-delay:0.0s]"></span>
                <span className="w-0.5 h-4 bg-teal-600 rounded-full animate-bounce [animation-delay:0.15s]"></span>
                <span className="w-0.5 h-2 bg-teal-600 rounded-full animate-bounce [animation-delay:0.3s]"></span>
                <span className="w-0.5 h-3.5 bg-teal-600 rounded-full animate-bounce [animation-delay:0.1s]"></span>
                <span className="w-0.5 h-2 bg-teal-600 rounded-full animate-bounce [animation-delay:0.25s]"></span>
              </div>
            </div>
          )}

          {effectiveState === 'listening' && (
            <div className="flex items-center space-x-1.5 text-rose-600">
              <Mic size={13} className="animate-pulse" />
              <span className="font-medium text-[11px]">Listening closely</span>
              {/* Subtle Microphone Waveform Bars */}
              <div className="flex items-center space-x-0.5 ml-1">
                <span className="w-0.5 h-2.5 bg-rose-500 rounded-full animate-pulse [animation-delay:0.0s]"></span>
                <span className="w-0.5 h-4 bg-rose-500 rounded-full animate-pulse [animation-delay:0.12s]"></span>
                <span className="w-0.5 h-3 bg-rose-500 rounded-full animate-pulse [animation-delay:0.24s]"></span>
                <span className="w-0.5 h-4.5 bg-rose-500 rounded-full animate-pulse [animation-delay:0.18s]"></span>
              </div>
            </div>
          )}

          {effectiveState === 'thinking' && (
            <div className="flex items-center space-x-1.5 text-indigo-600">
              <RefreshCw size={13} className="animate-spin" />
              <span className="font-medium text-[11px]">Formulating advice...</span>
            </div>
          )}

          {effectiveState === 'empathy' && (
            <div className="flex items-center space-x-1.5 text-pink-600">
              <Heart size={13} className="fill-pink-200" />
              <span className="font-medium text-[11px]">Here with you</span>
            </div>
          )}

          {effectiveState === 'reassurance' && (
            <div className="flex items-center space-x-1.5 text-emerald-700">
              <Sparkles size={13} />
              <span className="font-medium text-[11px]">You are not alone</span>
            </div>
          )}

          {effectiveState === 'idle' && (
            <span className="text-textSecondary flex items-center space-x-1">
              <span>Ready to listen and support</span>
            </span>
          )}

          {effectiveState === 'error' && (
            <span className="text-amber-700 flex items-center space-x-1">
              <AlertCircle size={13} />
              <span>Here to support you</span>
            </span>
          )}
        </div>

        <div className="hidden sm:flex items-center space-x-1 text-[10px] text-textLight">
          <span>Reactive Voice Aura</span>
        </div>
      </div>
    </div>
  );
}
