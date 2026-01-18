"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuth, useChat } from "@/lib/store";
import LiveKitRoom from "@/components/LiveKitRoom";

export default function ChatPage() {
  const router = useRouter();
  const { user, logout } = useAuth();
  const { sessions, setSessions, toolCalls, transcript, summary, setSummary, clearChat } = useChat();
  
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [roomInfo, setRoomInfo] = useState<{ token: string; room_name: string; livekit_url: string } | null>(null);
  const [audioStream, setAudioStream] = useState<MediaStream | null>(null);
  const [avatarVideo, setAvatarVideo] = useState<HTMLVideoElement | null>(null);
  
  const avatarContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!user) {
      router.push("/");
      return;
    }
    loadSessions();
  }, [user, router]);

  // Attach avatar video to container when available
  useEffect(() => {
    if (avatarVideo && avatarContainerRef.current) {
      // Clear existing content
      avatarContainerRef.current.innerHTML = "";
      avatarContainerRef.current.appendChild(avatarVideo);
    }
    
    return () => {
      if (avatarVideo && avatarVideo.parentNode) {
        avatarVideo.parentNode.removeChild(avatarVideo);
      }
    };
  }, [avatarVideo]);

  const loadSessions = async () => {
    if (!user?.phone) return;
    try {
      const data = await api.getUserSessions(user.phone);
      setSessions(data);
    } catch {
      setSessions([]);
    }
  };

  const startCall = async () => {
    try {
      clearChat();
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      setAudioStream(stream);
      const data = await api.getLiveKitToken();
      setRoomInfo(data);
      setIsConnected(true);
    } catch (err: any) {
      console.error("Failed to start call:", err);
      alert(err.message || "Failed to start call. Check microphone permissions.");
    }
  };

  const endCall = useCallback(() => {
    if (audioStream) {
      audioStream.getTracks().forEach(track => track.stop());
      setAudioStream(null);
    }
    setAvatarVideo(null);
    setIsConnected(false);
    setRoomInfo(null);
    setIsSpeaking(false);
    loadSessions();
  }, [audioStream]);

  const handleSpeakingChange = useCallback((speaking: boolean) => {
    setIsSpeaking(speaking);
  }, []);

  const handleAvatarVideo = useCallback((videoEl: HTMLVideoElement | null) => {
    setAvatarVideo(videoEl);
  }, []);

  const handleLogout = () => {
    api.logout();
    logout();
    router.push("/");
  };

  if (!user) return null;

  return (
    <div className="h-screen flex bg-slate-900">
      {/* Sidebar */}
      <div className={`fixed inset-y-0 left-0 z-50 w-72 bg-slate-800 shadow-xl transform transition-transform lg:relative lg:translate-x-0 ${sidebarOpen ? "translate-x-0" : "-translate-x-full"}`}>
        <div className="h-full flex flex-col">
          <div className="p-4 border-b border-slate-700 flex items-center justify-between">
            <h2 className="font-semibold text-white">Your Chats</h2>
            <button onClick={() => setSidebarOpen(false)} className="lg:hidden text-slate-400 hover:text-white">✕</button>
          </div>

          <div className="flex-1 overflow-y-auto p-2">
            {sessions.map((session: any) => (
              <div key={session.id} className="p-3 mb-2 bg-slate-700/50 rounded-lg hover:bg-slate-700">
                <div className="flex justify-between items-start mb-1">
                  <span className="text-sm font-medium text-white">
                    {new Date(session.started_at).toLocaleDateString()}
                  </span>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${session.status === "active" ? "bg-green-500/20 text-green-400" : "bg-slate-600 text-slate-300"}`}>
                    {session.status}
                  </span>
                </div>
                <p className="text-xs text-slate-400 truncate">{session.summary || "No summary"}</p>
              </div>
            ))}
            {sessions.length === 0 && (
              <p className="text-center text-slate-500 text-sm py-8">No previous chats</p>
            )}
          </div>

          <div className="p-4 border-t border-slate-700 bg-slate-800/50">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium text-white">{user.name}</p>
                <p className="text-xs text-slate-400">{user.phone}</p>
              </div>
              <button onClick={handleLogout} className="text-slate-400 hover:text-red-400">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content - Full Screen Avatar */}
      <div className="flex-1 flex flex-col relative">
        {/* Top Bar */}
        <div className="absolute top-0 left-0 right-0 z-20 bg-gradient-to-b from-slate-900/90 to-transparent p-4 flex items-center justify-between">
          <button onClick={() => setSidebarOpen(true)} className="lg:hidden text-white/70 hover:text-white">
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <h1 className="text-lg font-semibold text-white">SuperBryn Assistant</h1>
          <div className="w-6" />
        </div>

        {/* Avatar Container - Full Screen */}
        <div className="flex-1 relative bg-gradient-to-br from-slate-800 to-slate-900">
          {/* Avatar Video */}
          <div 
            ref={avatarContainerRef}
            className="absolute inset-0 flex items-center justify-center"
            style={{ backgroundColor: '#1a1a2e' }}
          >
            {/* Placeholder when no avatar video */}
            {!avatarVideo && (
              <div className="flex flex-col items-center justify-center text-white/60">
                <div className={`w-48 h-48 rounded-full bg-gradient-to-br from-indigo-600 to-purple-700 flex items-center justify-center mb-6 ${isSpeaking ? 'animate-pulse' : ''}`}>
                  <svg className="w-24 h-24 text-white/80" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                  </svg>
                </div>
                {isConnected ? (
                  <p className="text-sm">Connecting to avatar...</p>
                ) : (
                  <p className="text-sm">Start a call to see the avatar</p>
                )}
              </div>
            )}
          </div>

          {/* Speaking Indicator */}
          {isSpeaking && (
            <div className="absolute bottom-32 left-1/2 -translate-x-1/2 flex items-center space-x-1 bg-black/50 px-4 py-2 rounded-full">
              {[0,1,2,3,4].map(i => (
                <div 
                  key={i} 
                  className="w-1 bg-green-400 rounded-full animate-pulse"
                  style={{ height: `${12 + Math.random() * 16}px`, animationDelay: `${i * 0.1}s` }} 
                />
              ))}
              <span className="ml-2 text-white text-sm">Speaking...</span>
            </div>
          )}

          {/* Overlay UI - Transcript & Tool Calls */}
          <div className="absolute bottom-28 left-0 right-0 px-4 max-h-48 overflow-y-auto">
            <div className="max-w-2xl mx-auto space-y-2">
              {transcript.slice(-3).map((entry, i) => (
                <div key={i} className={`flex ${entry.role === "user" ? "justify-end" : "justify-start"}`}>
                  <span className={`inline-block px-4 py-2 rounded-2xl text-sm max-w-[80%] ${
                    entry.role === "user" 
                      ? "bg-indigo-600 text-white" 
                      : "bg-slate-700/90 text-white"
                  }`}>
                    {entry.text}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Tool Calls Indicator */}
          {toolCalls.length > 0 && (
            <div className="absolute top-20 right-4 bg-slate-800/90 rounded-xl p-3 max-w-xs">
              <h3 className="text-xs font-medium text-slate-400 mb-2">Actions</h3>
              <div className="space-y-1">
                {toolCalls.slice(-3).map((call, i) => (
                  <div key={i} className="flex items-center text-sm text-white">
                    <span className={`w-2 h-2 rounded-full mr-2 ${call.result?.success ? "bg-green-500" : "bg-yellow-500"}`} />
                    <span className="truncate">{call.tool.replace(/_/g, " ")}</span>
                    {call.result?.success && <span className="ml-auto text-green-400">✓</span>}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Bottom Controls */}
        <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-slate-900 to-transparent pt-16 pb-6 px-4">
          <div className="flex justify-center">
            {!isConnected ? (
              <button
                onClick={startCall}
                className="px-8 py-4 bg-indigo-600 text-white rounded-full font-medium hover:bg-indigo-500 transition flex items-center shadow-lg shadow-indigo-500/30"
              >
                <svg className="w-6 h-6 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                </svg>
                Start Voice Chat
              </button>
            ) : (
              <button
                onClick={endCall}
                className="px-8 py-4 bg-red-600 text-white rounded-full font-medium hover:bg-red-500 transition flex items-center shadow-lg shadow-red-500/30"
              >
                <svg className="w-6 h-6 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
                End Call
              </button>
            )}
          </div>
        </div>

        {/* LiveKit Room Connection */}
        {isConnected && roomInfo && (
          <LiveKitRoom
            token={roomInfo.token}
            serverUrl={roomInfo.livekit_url}
            roomName={roomInfo.room_name}
            onDisconnect={endCall}
            onSpeakingChange={handleSpeakingChange}
            onAvatarVideo={handleAvatarVideo}
            audioStream={audioStream || undefined}
          />
        )}

        {/* Summary Modal */}
        {summary && (
          <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
            <div className="bg-slate-800 rounded-2xl max-w-md w-full p-6 border border-slate-700">
              <h2 className="text-xl font-bold text-white mb-4">Call Summary</h2>
              
              {summary.actions?.length > 0 && (
                <div className="mb-4">
                  <h3 className="text-sm font-medium text-slate-400 mb-2">Actions:</h3>
                  <ul className="space-y-1">
                    {summary.actions.map((action: string, i: number) => (
                      <li key={i} className="text-sm text-white flex items-center">
                        <span className="w-1.5 h-1.5 bg-green-500 rounded-full mr-2" />
                        {action}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {summary.upcoming_appointments?.length > 0 && (
                <div className="mb-4">
                  <h3 className="text-sm font-medium text-slate-400 mb-2">Upcoming:</h3>
                  {summary.upcoming_appointments.map((apt: any, i: number) => (
                    <p key={i} className="text-sm text-white">📅 {apt.date} at {apt.time}</p>
                  ))}
                </div>
              )}

              {summary.cost_breakdown && (
                <div className="mb-4 p-3 bg-slate-700/50 rounded-lg">
                  <h3 className="text-sm font-medium text-slate-400 mb-1">Cost</h3>
                  <p className="text-2xl font-bold text-indigo-400">${summary.cost_breakdown.total?.toFixed(4)}</p>
                </div>
              )}

              <button
                onClick={() => setSummary(null)}
                className="w-full py-3 bg-indigo-600 text-white rounded-xl font-medium hover:bg-indigo-500"
              >
                Done
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
