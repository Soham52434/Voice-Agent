"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/store";

export default function MentorDashboard() {
  const router = useRouter();
  const { user, logout } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [currentDate, setCurrentDate] = useState(new Date());
  const [calendar, setCalendar] = useState<any>({ days: {} });
  const [availability, setAvailability] = useState<any[]>([]);
  const [showAddModal, setShowAddModal] = useState(false);
  const [newAvail, setNewAvail] = useState({ date: "", start_time: "09:00", end_time: "17:00" });

  useEffect(() => {
    if (!user || user.type !== "mentor") {
      router.push("/mentor/login");
      return;
    }
    loadCalendar();
    loadAvailability();
  }, [user, router, currentDate]);

  const loadCalendar = async () => {
    try {
      const data = await api.getAppointmentCalendar(user!.id, currentDate.getMonth() + 1, currentDate.getFullYear());
      setCalendar(data);
    } catch (err) {
      console.error("Failed to load calendar:", err);
    }
  };

  const loadAvailability = async () => {
    try {
      const data = await api.getMentorAvailability(user!.id);
      setAvailability(data);
    } catch (err) {
      console.error("Failed to load availability:", err);
    }
  };

  const addAvailability = async () => {
    try {
      await api.addMentorAvailability(user!.id, newAvail);
      setShowAddModal(false);
      setNewAvail({ date: "", start_time: "09:00", end_time: "17:00" });
      loadAvailability();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleLogout = () => {
    api.logout();
    logout();
    router.push("/mentor/login");
  };

  const getDaysInMonth = () => {
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();
    const firstDay = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const days = [];
    
    for (let i = 0; i < firstDay; i++) days.push(null);
    for (let i = 1; i <= daysInMonth; i++) days.push(i);
    
    return days;
  };

  const getDateString = (day: number) => {
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth() + 1;
    return `${year}-${month.toString().padStart(2, "0")}-${day.toString().padStart(2, "0")}`;
  };

  if (!user) return null;

  return (
    <div className="h-screen flex bg-gray-100">
      {/* Sidebar */}
      <div className={`fixed inset-y-0 left-0 z-50 w-72 bg-white shadow-xl transform transition-transform lg:relative lg:translate-x-0 ${sidebarOpen ? "translate-x-0" : "-translate-x-full"}`}>
        <div className="h-full flex flex-col">
          <div className="p-4 border-b">
            <div className="flex items-center justify-between">
              <h2 className="font-semibold text-gray-800">Availability</h2>
              <button onClick={() => setSidebarOpen(false)} className="lg:hidden">✕</button>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-4">
            <button
              onClick={() => setShowAddModal(true)}
              className="w-full mb-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700"
            >
              + Add Availability
            </button>

            {availability.map((a: any) => (
              <div key={a.id} className="p-3 mb-2 bg-gray-50 rounded-lg">
                <p className="font-medium text-gray-800">{a.date}</p>
                <p className="text-sm text-gray-500">{a.start_time} - {a.end_time}</p>
              </div>
            ))}
          </div>

          <div className="p-4 border-t bg-gray-50">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium text-gray-800">{user.name}</p>
                <p className="text-xs text-gray-500">{user.email}</p>
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
      <div className="flex-1 flex flex-col overflow-hidden">
        <div className="bg-white shadow-sm p-4 flex items-center justify-between">
          <button onClick={() => setSidebarOpen(true)} className="lg:hidden">☰</button>
          <h1 className="text-lg font-semibold">Calendar</h1>
          <div className="flex items-center space-x-2">
            <button onClick={() => setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() - 1))} className="p-2 hover:bg-gray-100 rounded">←</button>
            <span className="font-medium">{currentDate.toLocaleDateString("en-US", { month: "long", year: "numeric" })}</span>
            <button onClick={() => setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() + 1))} className="p-2 hover:bg-gray-100 rounded">→</button>
          </div>
        </div>

        {/* Calendar Grid */}
        <div className="flex-1 p-4 overflow-auto">
          <div className="bg-white rounded-xl shadow-lg p-4">
            <div className="grid grid-cols-7 gap-1 mb-2">
              {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((d) => (
                <div key={d} className="text-center text-sm font-medium text-gray-500 py-2">{d}</div>
              ))}
            </div>
            <div className="grid grid-cols-7 gap-1">
              {getDaysInMonth().map((day, i) => {
                if (!day) return <div key={i} />;
                const dateStr = getDateString(day);
                const dayData = calendar.days?.[dateStr];
                const hasAppts = dayData?.appointments?.length > 0;
                const hasAvail = dayData?.availability;

                return (
                  <div
                    key={i}
                    className={`min-h-24 p-2 border rounded-lg ${hasAppts ? "bg-blue-50 border-blue-200" : hasAvail ? "bg-green-50 border-green-200" : "bg-gray-50"}`}
                  >
                    <span className="text-sm font-medium">{day}</span>
                    {dayData?.appointments?.map((apt: any, j: number) => (
                      <div key={j} className="mt-1 text-xs p-1 bg-blue-100 rounded truncate">
                        {apt.time} - {apt.users?.name || apt.user_phone}
                      </div>
                    ))}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Add Availability Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6">
            <h2 className="text-xl font-bold mb-4">Add Availability</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Date</label>
                <input type="date" value={newAvail.date} onChange={(e) => setNewAvail({ ...newAvail, date: e.target.value })} className="w-full px-4 py-2 border rounded-lg" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Start Time</label>
                  <input type="time" value={newAvail.start_time} onChange={(e) => setNewAvail({ ...newAvail, start_time: e.target.value })} className="w-full px-4 py-2 border rounded-lg" />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">End Time</label>
                  <input type="time" value={newAvail.end_time} onChange={(e) => setNewAvail({ ...newAvail, end_time: e.target.value })} className="w-full px-4 py-2 border rounded-lg" />
                </div>
              </div>
            </div>
            <div className="flex space-x-3 mt-6">
              <button onClick={() => setShowAddModal(false)} className="flex-1 py-2 border rounded-lg">Cancel</button>
              <button onClick={addAvailability} className="flex-1 py-2 bg-emerald-600 text-white rounded-lg">Add</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

