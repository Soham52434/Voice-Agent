"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Github } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/store";

type Tab = "overview" | "users" | "mentors" | "sessions" | "costs";

export default function AdminDashboard() {
  const router = useRouter();
  const { user, logout } = useAuth();
  const [tab, setTab] = useState<Tab>("overview");
  const [stats, setStats] = useState<any>(null);
  const [users, setUsers] = useState<any[]>([]);
  const [mentors, setMentors] = useState<any[]>([]);
  const [sessions, setSessions] = useState<any[]>([]);
  const [costs, setCosts] = useState<any[]>([]);
  const [selectedSession, setSelectedSession] = useState<any>(null);
  const [showMentorModal, setShowMentorModal] = useState(false);
  const [newMentor, setNewMentor] = useState({
    name: "",
    email: "",
    password: "",
    specialty: "",
    bio: "",
    phone: "",
  });

  useEffect(() => {
    if (!user || user.type !== "admin") {
      router.push("/admin/login");
      return;
    }
    loadData();
  }, [user, router, tab]);

  const loadData = async () => {
    try {
      if (tab === "overview") {
        const data = await api.getAdminStats();
        setStats(data);
      } else if (tab === "users") {
        const data = await api.getUsers();
        setUsers(data);
      } else if (tab === "mentors") {
        const data = await api.getMentors();
        setMentors(data);
      } else if (tab === "sessions") {
        const data = await api.getSessions();
        setSessions(data);
      } else if (tab === "costs") {
        const data = await api.getSessionCosts();
        setCosts(data);
      }
    } catch (err) {
      console.error("Failed to load data:", err);
    }
  };

  const viewSession = async (id: string) => {
    try {
      const data = await api.getSession(id);
      setSelectedSession(data);
    } catch (err) {
      console.error("Failed to load session:", err);
    }
  };

  const handleLogout = () => {
    api.logout();
    logout();
    router.push("/admin/login");
  };

  const createMentor = async () => {
    try {
      await api.createMentor(newMentor);
      setShowMentorModal(false);
      setNewMentor({ name: "", email: "", password: "", specialty: "", bio: "", phone: "" });
      loadData();
    } catch (err: any) {
      alert(err.message || "Failed to create mentor");
    }
  };

  if (!user) return null;

  const tabs: { id: Tab; label: string }[] = [
    { id: "overview", label: "Overview" },
    { id: "users", label: "Users" },
    { id: "mentors", label: "Mentors" },
    { id: "sessions", label: "Sessions" },
    { id: "costs", label: "Costs" },
  ];

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <div className="bg-slate-800 text-white">
        <div className="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
          <h1 className="text-xl font-bold">Admin Dashboard</h1>
          <div className="flex items-center space-x-4">
            <a
              href="https://github.com/Soham52434/Voice-Agent/blob/main/README.md"
              target="_blank"
              rel="noopener noreferrer"
              className="relative w-10 h-10 rounded-full bg-white/10 hover:bg-white/20 flex items-center justify-center transition-all duration-300 animate-pulse-scale"
              title="View README for setup instructions and credentials"
            >
              <Github className="w-5 h-5 text-white relative z-10" />
              <span className="absolute inset-0 rounded-full animate-ping opacity-20 bg-white"></span>
              <span className="absolute inset-0 rounded-full animate-pulse bg-white/10"></span>
            </a>
            <span className="text-sm text-slate-300">{user.email}</span>
            <button onClick={handleLogout} className="text-slate-300 hover:text-white">Logout</button>
          </div>
        </div>
        <div className="max-w-7xl mx-auto px-4">
          <div className="flex space-x-1">
            {tabs.map((t) => (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={`px-4 py-2 text-sm font-medium rounded-t-lg ${tab === t.id ? "bg-gray-100 text-slate-800" : "text-slate-300 hover:text-white"}`}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-4 py-6">
        {/* Overview Tab */}
        {tab === "overview" && stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-white p-6 rounded-xl shadow">
              <p className="text-sm text-gray-500">Total Users</p>
              <p className="text-3xl font-bold text-slate-800">{stats.total_users || 0}</p>
            </div>
            <div className="bg-white p-6 rounded-xl shadow">
              <p className="text-sm text-gray-500">Total Mentors</p>
              <p className="text-3xl font-bold text-emerald-600">{stats.total_mentors || 0}</p>
            </div>
            <div className="bg-white p-6 rounded-xl shadow">
              <p className="text-sm text-gray-500">Total Sessions</p>
              <p className="text-3xl font-bold text-indigo-600">{stats.total_sessions || 0}</p>
            </div>
            <div className="bg-white p-6 rounded-xl shadow">
              <p className="text-sm text-gray-500">Total Cost</p>
              <p className="text-3xl font-bold text-amber-600">${(stats.total_cost || 0).toFixed(2)}</p>
            </div>
            <div className="bg-white p-6 rounded-xl shadow">
              <p className="text-sm text-gray-500">Total Appointments</p>
              <p className="text-3xl font-bold text-gray-900">{stats.total_appointments || 0}</p>
            </div>
            <div className="bg-white p-6 rounded-xl shadow">
              <p className="text-sm text-gray-500">Pending</p>
              <p className="text-3xl font-bold text-yellow-600">{stats.pending_appointments || 0}</p>
            </div>
            <div className="bg-white p-6 rounded-xl shadow">
              <p className="text-sm text-gray-500">Booked</p>
              <p className="text-3xl font-bold text-blue-600">{stats.booked_appointments || 0}</p>
            </div>
            <div className="bg-white p-6 rounded-xl shadow">
              <p className="text-sm text-gray-500">Completed</p>
              <p className="text-3xl font-bold text-green-600">{stats.completed_appointments || 0}</p>
            </div>
          </div>
        )}

        {/* Users Tab */}
        {tab === "users" && (
          <div className="bg-white rounded-xl shadow overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Name</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Phone</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Created</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {users.map((u) => (
                  <tr key={u.id}>
                    <td className="px-4 py-3 text-gray-900">{u.name}</td>
                    <td className="px-4 py-3 text-gray-700">{u.contact_number}</td>
                    <td className="px-4 py-3 text-gray-600 text-sm">{new Date(u.created_at).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Mentors Tab */}
        {tab === "mentors" && (
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <h2 className="text-lg font-semibold text-gray-900">Mentors</h2>
              <button
                onClick={() => setShowMentorModal(true)}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium"
              >
                + Add Mentor
              </button>
            </div>
            <div className="bg-white rounded-xl shadow overflow-hidden">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Name</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Email</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Specialty</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {mentors.map((m) => (
                    <tr key={m.id}>
                      <td className="px-4 py-3 font-medium text-gray-900">{m.name}</td>
                      <td className="px-4 py-3 text-gray-700">{m.email}</td>
                      <td className="px-4 py-3 text-gray-700">{m.specialty}</td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-1 text-xs rounded-full ${m.is_active ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>
                          {m.is_active ? "Active" : "Inactive"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Sessions Tab */}
        {tab === "sessions" && (
          <div className="bg-white rounded-xl shadow overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">User</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Started</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Duration</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Status</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {sessions.map((s) => (
                  <tr key={s.id}>
                    <td className="px-4 py-3 text-gray-900">{s.users?.name || s.contact_number || "Unknown"}</td>
                    <td className="px-4 py-3 text-sm text-gray-700">{new Date(s.started_at).toLocaleString()}</td>
                    <td className="px-4 py-3 text-sm text-gray-900">{s.duration_seconds ? `${Math.round(s.duration_seconds / 60)}m` : "-"}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 text-xs rounded-full ${s.status === "completed" ? "bg-green-100 text-green-700" : s.status === "active" ? "bg-blue-100 text-blue-700" : "bg-gray-100 text-gray-700"}`}>
                        {s.status}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <button onClick={() => viewSession(s.id)} className="text-indigo-600 hover:underline text-sm">View</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Costs Tab */}
        {tab === "costs" && (
          <div className="bg-white rounded-xl shadow overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Session</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">User</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">STT</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">TTS</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">LLM</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Total</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {costs.map((c) => (
                  <tr key={c.id}>
                    <td className="px-4 py-3 text-sm font-mono text-gray-900">{c.id?.slice(0, 8)}...</td>
                    <td className="px-4 py-3 text-gray-900">{c.users?.name || c.contact_number || "-"}</td>
                    <td className="px-4 py-3 text-sm text-gray-900">${(c.cost_breakdown?.stt || 0).toFixed(4)}</td>
                    <td className="px-4 py-3 text-sm text-gray-900">${(c.cost_breakdown?.tts || 0).toFixed(4)}</td>
                    <td className="px-4 py-3 text-sm text-gray-900">${(c.cost_breakdown?.llm || 0).toFixed(4)}</td>
                    <td className="px-4 py-3 font-medium text-gray-900">${(c.cost_breakdown?.total || 0).toFixed(4)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Session Detail Modal */}
      {selectedSession && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl max-w-2xl w-full max-h-[80vh] overflow-hidden">
            <div className="p-4 border-b flex justify-between items-center">
              <h2 className="font-bold text-gray-900">Session Details</h2>
              <button onClick={() => setSelectedSession(null)} className="text-gray-500 hover:text-gray-700">✕</button>
            </div>
            <div className="p-4 overflow-y-auto max-h-[60vh]">
              <p className="text-sm text-gray-700 mb-4">
                Started: {new Date(selectedSession.session.started_at).toLocaleString()}
                {selectedSession.session.summary && ` • Summary: ${selectedSession.session.summary}`}
              </p>
              <div className="space-y-2">
                {selectedSession.messages.map((m: any, i: number) => (
                  <div key={i} className={`p-2 rounded ${m.role === "user" ? "bg-blue-50 ml-8" : m.role === "tool" ? "bg-yellow-50" : "bg-gray-50 mr-8"}`}>
                    <p className="text-xs font-medium text-gray-700 mb-1">{m.role} {m.tool_name && `(${m.tool_name})`}</p>
                    <p className="text-sm text-gray-900">{m.content}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Add Mentor Modal */}
      {showMentorModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold text-gray-900">Add New Mentor</h2>
              <button onClick={() => setShowMentorModal(false)} className="text-gray-500 hover:text-gray-700">✕</button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Name *</label>
                <input
                  type="text"
                  value={newMentor.name}
                  onChange={(e) => setNewMentor({ ...newMentor, name: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Dr. John Doe"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Email *</label>
                <input
                  type="email"
                  value={newMentor.email}
                  onChange={(e) => setNewMentor({ ...newMentor, email: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="mentor@example.com"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Password *</label>
                <input
                  type="password"
                  value={newMentor.password}
                  onChange={(e) => setNewMentor({ ...newMentor, password: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="••••••••"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Specialty</label>
                <input
                  type="text"
                  value={newMentor.specialty}
                  onChange={(e) => setNewMentor({ ...newMentor, specialty: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="General Consultation"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Phone</label>
                <input
                  type="tel"
                  value={newMentor.phone}
                  onChange={(e) => setNewMentor({ ...newMentor, phone: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="+1234567890"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Bio</label>
                <textarea
                  value={newMentor.bio}
                  onChange={(e) => setNewMentor({ ...newMentor, bio: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Brief description..."
                  rows={3}
                />
              </div>
            </div>
            <div className="flex space-x-3 mt-6">
              <button
                onClick={() => setShowMentorModal(false)}
                className="flex-1 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 font-medium"
              >
                Cancel
              </button>
              <button
                onClick={createMentor}
                className="flex-1 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium"
              >
                Create Mentor
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

