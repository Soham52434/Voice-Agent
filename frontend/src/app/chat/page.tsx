"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuth, useChat } from "@/lib/store";

export default function ChatPage() {
  const router = useRouter();
  const { user, logout } = useAuth();
  const { sessions, setSessions, toolCalls, transcript, summary, addToolCall, addTranscript, setSummary, clearChat } = useChat();
  
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [roomInfo, setRoomInfo] = useState<{ token: string; room_name: string; livekit_url: string } | null>(null);
  const dataChannelRef = useRef<any>(null);

  useEffect(() => {
    if (!user) {
      router.push("/");
      return;
    }
    loadSessions();
  }, [user, router]);

  const loadSessions = async () => {
    try {
      if (user?.phone) {
        const data = await api.getUserSessions(user.phone);
        setSessions(data);
      }
    } catch (err) {
      console.error("Failed to load sessions:", err);
    }
  };

  const startCall = async () => {
    try {
      clearChat();
      const data = await api.getLiveKitToken();
      setRoomInfo(data);
      setIsConnected(true);
      // LiveKit connection would be handled here
    } catch (err) {
      console.error("Failed to start call:", err);
    }
  };

  const endCall = () => {
    setIsConnected(false);
    setRoomInfo(null);
    loadSessions();
  };

  const handleLogout = () => {
    api.logout();
    logout();
    router.push("/");
  };

  const getSessionStatus = (session: any) => {
    if (session.status === "active") return { label: "Active", color: "bg-green-100 text-green-700" };
    if (session.summary?.includes("Booked")) return { label: "Booked", color: "bg-blue-100 text-blue-700" };
    return { label: "Completed", color: "bg-gray-100 text-gray-600" };
  };

  if (!user) return null;

  return (
    <div className="h-screen flex bg-gray-100">
      {/* Sidebar */}
      <div className={`fixed inset-y-0 left-0 z-50 w-72 bg-white shadow-xl transform transition-transform lg:relative lg:translate-x-0 ${sidebarOpen ? "translate-x-0" : "-translate-x-full"}`}>
        <div className="h-full flex flex-col">
          {/* Header */}
          <div className="p-4 border-b">
            <div className="flex items-center justify-between">
              <h2 className="font-semibold text-gray-800">Your Chats</h2>
              <button onClick={() => setSidebarOpen(false)} className="lg:hidden text-gray-500">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>

          {/* Sessions List */}
          <div className="flex-1 overflow-y-auto p-2">
            {sessions.map((session: any) => {
              const status = getSessionStatus(session);
              return (
                <div key={session.id} className="p-3 mb-2 bg-gray-50 rounded-lg hover:bg-gray-100 cursor-pointer">
                  <div className="flex justify-between items-start mb-1">
                    <span className="text-sm font-medium text-gray-800 truncate">
                      {new Date(session.started_at).toLocaleDateString()}
                    </span>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${status.color}`}>
                      {status.label}
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 truncate">{session.summary || "No summary"}</p>
                </div>
              );
            })}
            {sessions.length === 0 && (
              <p className="text-center text-gray-400 text-sm py-8">No previous chats</p>
            )}
          </div>

          {/* User Info */}
          <div className="p-4 border-t bg-gray-50">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium text-gray-800">{user.name}</p>
                <p className="text-xs text-gray-500">{user.phone}</p>
              </div>
              <button onClick={handleLogout} className="text-gray-400 hover:text-red-500">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Top Bar */}
        <div className="bg-white shadow-sm p-4 flex items-center justify-between">
          <button onClick={() => setSidebarOpen(true)} className="lg:hidden text-gray-600">
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <h1 className="text-lg font-semibold text-gray-800">Voice Assistant</h1>
          <div className="w-6" />
        </div>

        {/* Avatar & Chat Area */}
        <div className="flex-1 flex flex-col items-center justify-center p-8">
          {/* Avatar Container */}
          <div className={`relative w-64 h-64 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center mb-8 transition-all ${isSpeaking ? "avatar-speaking" : "avatar-glow"}`}>
            {/* Placeholder for Beyond Presence Avatar */}
            <div className="w-56 h-56 rounded-full bg-white/10 flex items-center justify-center">
              <svg className="w-24 h-24 text-white/80" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
            </div>
            {isSpeaking && (
              <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex space-x-1">
                {[...Array(4)].map((_, i) => (
                  <div key={i} className="w-1.5 h-4 bg-white rounded-full animate-pulse" style={{ animationDelay: `${i * 0.1}s` }} />
                ))}
              </div>
            )}
          </div>

          {/* Transcript */}
          {transcript.length > 0 && (
            <div className="w-full max-w-lg bg-white rounded-xl shadow-lg p-4 mb-6 max-h-48 overflow-y-auto">
              {transcript.slice(-5).map((entry, i) => (
                <div key={i} className={`mb-2 ${entry.role === "user" ? "text-right" : ""}`}>
                  <span className={`inline-block px-3 py-2 rounded-lg text-sm ${entry.role === "user" ? "bg-indigo-100 text-indigo-800" : "bg-gray-100 text-gray-800"}`}>
                    {entry.text}
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* Tool Calls Display */}
          {toolCalls.length > 0 && (
            <div className="w-full max-w-lg bg-white rounded-xl shadow-lg p-4 mb-6">
              <h3 className="text-sm font-medium text-gray-700 mb-2">Actions</h3>
              <div className="space-y-2">
                {toolCalls.slice(-3).map((call, i) => (
                  <div key={i} className="flex items-center text-sm">
                    <span className={`w-2 h-2 rounded-full mr-2 ${call.result?.success ? "bg-green-500" : "bg-yellow-500"}`} />
                    <span className="text-gray-600">{call.tool.replace(/_/g, " ")}</span>
                    {call.result?.success && <span className="ml-auto text-green-600">✓</span>}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Call Controls */}
          {!isConnected ? (
            <button
              onClick={startCall}
              className="px-8 py-4 bg-indigo-600 text-white rounded-full font-medium hover:bg-indigo-700 transition flex items-center shadow-lg"
            >
              <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
              </svg>
              Start Voice Chat
            </button>
          ) : (
            <button
              onClick={endCall}
              className="px-8 py-4 bg-red-500 text-white rounded-full font-medium hover:bg-red-600 transition flex items-center shadow-lg"
            >
              <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
              End Call
            </button>
          )}
        </div>

        {/* Summary Modal */}
        {summary && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-2xl max-w-md w-full p-6 animate-fade-in">
              <h2 className="text-xl font-bold text-gray-800 mb-4">Call Summary</h2>
              
              {summary.actions?.length > 0 && (
                <div className="mb-4">
                  <h3 className="text-sm font-medium text-gray-600 mb-2">Actions Taken:</h3>
                  <ul className="space-y-1">
                    {summary.actions.map((action: string, i: number) => (
                      <li key={i} className="text-sm text-gray-800 flex items-center">
                        <span className="w-1.5 h-1.5 bg-green-500 rounded-full mr-2" />
                        {action}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {summary.upcoming_appointments?.length > 0 && (
                <div className="mb-4">
                  <h3 className="text-sm font-medium text-gray-600 mb-2">Upcoming Appointments:</h3>
                  <ul className="space-y-1">
                    {summary.upcoming_appointments.map((apt: any, i: number) => (
                      <li key={i} className="text-sm text-gray-800">📅 {apt.date} at {apt.time}</li>
                    ))}
                  </ul>
                </div>
              )}

              {summary.cost_breakdown && (
                <div className="mb-4 p-3 bg-gray-50 rounded-lg">
                  <h3 className="text-sm font-medium text-gray-600 mb-1">Call Cost</h3>
                  <p className="text-2xl font-bold text-indigo-600">${summary.cost_breakdown.total?.toFixed(4)}</p>
                </div>
              )}

              <button
                onClick={() => setSummary(null)}
                className="w-full py-3 bg-indigo-600 text-white rounded-xl font-medium hover:bg-indigo-700 transition"
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

