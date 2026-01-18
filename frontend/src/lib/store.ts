import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface User {
  id: string;
  name: string;
  phone?: string;
  email?: string;
  type: 'user' | 'mentor' | 'admin';
}

interface AuthState {
  user: User | null;
  token: string | null;
  setAuth: (user: User, token: string) => void;
  logout: () => void;
}

export const useAuth = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      setAuth: (user, token) => set({ user, token }),
      logout: () => set({ user: null, token: null }),
    }),
    { name: 'auth-storage' }
  )
);

interface ChatState {
  sessions: any[];
  currentSession: any | null;
  toolCalls: any[];
  transcript: { role: string; text: string; timestamp: string }[];
  summary: any | null;
  setSessions: (sessions: any[]) => void;
  setCurrentSession: (session: any) => void;
  addToolCall: (call: any) => void;
  addTranscript: (entry: any) => void;
  setSummary: (summary: any) => void;
  clearChat: () => void;
}

export const useChat = create<ChatState>((set) => ({
  sessions: [],
  currentSession: null,
  toolCalls: [],
  transcript: [],
  summary: null,
  setSessions: (sessions) => set({ sessions }),
  setCurrentSession: (session) => set({ currentSession: session }),
  addToolCall: (call) => set((s) => ({ toolCalls: [...s.toolCalls, call] })),
  addTranscript: (entry) => set((s) => ({ transcript: [...s.transcript, entry] })),
  setSummary: (summary) => set({ summary }),
  clearChat: () => set({ toolCalls: [], transcript: [], summary: null }),
}));
