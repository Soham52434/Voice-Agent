"use client";

import { useState, useEffect } from "react";

interface CallingLoaderProps {
  isConnecting: boolean;
}

const funMessages = [
  "Preparing your AI assistant...",
  "Almost there! Setting up the connection...",
  "Just a moment, we're getting ready...",
  "Connecting to the future of voice AI...",
  "Hang tight! Your avatar is waking up...",
  "Great things take time... almost ready!",
  "Polishing the experience for you...",
  "We're making it perfect, just a sec...",
];

export default function CallingLoader({ isConnecting }: CallingLoaderProps) {
  const [currentMessage, setCurrentMessage] = useState(0);
  const [audioContext, setAudioContext] = useState<AudioContext | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);

  useEffect(() => {
    if (isConnecting && !isPlaying) {
      // Play calling tune
      const playCallingTune = async () => {
        try {
          const ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
          setAudioContext(ctx);
          
          // Create a pleasant calling tone (two-tone sequence)
          const playTone = (frequency: number, duration: number, startTime: number) => {
            const oscillator = ctx.createOscillator();
            const gainNode = ctx.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(ctx.destination);
            
            oscillator.frequency.value = frequency;
            oscillator.type = 'sine';
            
            gainNode.gain.setValueAtTime(0.3, startTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, startTime + duration);
            
            oscillator.start(startTime);
            oscillator.stop(startTime + duration);
          };
          
          // Play two-tone sequence repeatedly
          const playSequence = () => {
            const now = ctx.currentTime;
            playTone(440, 0.2, now); // A4
            playTone(523.25, 0.2, now + 0.3); // C5
          };
          
          setIsPlaying(true);
          playSequence();
          
          // Repeat every 2 seconds
          const interval = setInterval(() => {
            if (isConnecting) {
              playSequence();
            } else {
              clearInterval(interval);
              setIsPlaying(false);
            }
          }, 2000);
          
          return () => {
            clearInterval(interval);
            if (ctx.state !== 'closed') {
              ctx.close();
            }
          };
        } catch (err) {
          console.error("Failed to play calling tune:", err);
        }
      };
      
      playCallingTune();
    } else if (!isConnecting && audioContext) {
      // Stop audio when connection is established
      if (audioContext.state !== 'closed') {
        audioContext.close();
      }
      setIsPlaying(false);
    }
  }, [isConnecting, isPlaying, audioContext]);

  useEffect(() => {
    if (isConnecting) {
      // Rotate messages every 2 seconds
      const interval = setInterval(() => {
        setCurrentMessage((prev) => (prev + 1) % funMessages.length);
      }, 2000);
      
      return () => clearInterval(interval);
    }
  }, [isConnecting]);

  if (!isConnecting) return null;

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50">
      <div className="text-center">
        {/* Animated Loader */}
        <div className="relative w-32 h-32 mx-auto mb-8">
          <div className="absolute inset-0 border-4 border-blue-500/30 rounded-full"></div>
          <div className="absolute inset-0 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
          <div className="absolute inset-4 border-4 border-indigo-500/30 rounded-full"></div>
          <div className="absolute inset-4 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin" style={{ animationDirection: 'reverse', animationDuration: '1.5s' }}></div>
          
          {/* Pulsing center circle */}
          <div className="absolute inset-1/2 -translate-x-1/2 -translate-y-1/2 w-16 h-16 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-full animate-pulse"></div>
        </div>

        {/* Message */}
        <div className="space-y-4">
          <h3 className="text-2xl font-semibold text-white mb-2">
            Connecting...
          </h3>
          <p className="text-lg text-gray-300 animate-pulse">
            {funMessages[currentMessage]}
          </p>
          
          {/* Dots animation */}
          <div className="flex justify-center space-x-2 mt-4">
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                className="w-3 h-3 bg-blue-500 rounded-full animate-bounce"
                style={{ animationDelay: `${i * 0.2}s` }}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
