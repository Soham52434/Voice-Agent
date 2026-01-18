"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/store";

export default function MentorDashboard() {
  const router = useRouter();
  const { user, logout } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [viewMode, setViewMode] = useState<"day" | "week" | "month">("day");
  const [currentDate, setCurrentDate] = useState(new Date());
  const [appointments, setAppointments] = useState<any[]>([]);
  const [availability, setAvailability] = useState<any[]>([]);
  const [showAddModal, setShowAddModal] = useState(false);
  const [newAvail, setNewAvail] = useState({ date: "", start_time: "09:00", end_time: "17:00" });

  useEffect(() => {
    if (!user || user.type !== "mentor") {
      router.push("/mentor/login");
      return;
    }
    loadAppointments();
    loadAvailability();
  }, [user, router, currentDate]);

  const loadAppointments = async () => {
    try {
      const startDate = new Date(currentDate);
      startDate.setDate(1);
      const endDate = new Date(currentDate);
      endDate.setMonth(endDate.getMonth() + 1);
      const data = await api.getMentorAppointments(user!.id, undefined, startDate.toISOString().split('T')[0], endDate.toISOString().split('T')[0]);
      setAppointments(data);
    } catch (err) {
      console.error("Failed to load appointments:", err);
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

  const getTimeSlots = () => {
    const slots = [];
    for (let hour = 0; hour < 24; hour++) {
      slots.push(`${hour.toString().padStart(2, "0")}:00`);
      if (hour < 23) {
        slots.push(`${hour.toString().padStart(2, "0")}:30`);
      }
    }
    return slots;
  };

  const getAppointmentsForDay = (date: Date) => {
    const dateStr = date.toISOString().split('T')[0];
    return appointments.filter(apt => apt.date === dateStr);
  };

  const getAppointmentPosition = (time: string) => {
    const [hours, minutes] = time.split(':').map(Number);
    return (hours * 60 + minutes) * 2; // 2px per minute
  };

  const getAppointmentHeight = (duration: number = 60) => {
    return duration * 2; // 2px per minute
  };

  const formatTime = (time: string) => {
    const [hours, minutes] = time.split(':');
    const hour = parseInt(hours);
    const ampm = hour >= 12 ? 'PM' : 'AM';
    const displayHour = hour % 12 || 12;
    return `${displayHour}:${minutes} ${ampm}`;
  };

  const navigateDate = (direction: "prev" | "next" | "today") => {
    const newDate = new Date(currentDate);
    if (direction === "today") {
      setCurrentDate(new Date());
    } else if (direction === "prev") {
      newDate.setDate(newDate.getDate() - 1);
      setCurrentDate(newDate);
    } else {
      newDate.setDate(newDate.getDate() + 1);
      setCurrentDate(newDate);
    }
  };

  const dayAppointments = getAppointmentsForDay(currentDate);

  if (!user) return null;

  return (
    <div className="h-screen flex bg-gray-50">
      {/* Sidebar */}
      <div className={`fixed inset-y-0 left-0 z-50 w-72 bg-white shadow-xl transform transition-transform lg:relative lg:translate-x-0 ${sidebarOpen ? "translate-x-0" : "-translate-x-full"}`}>
        <div className="h-full flex flex-col">
          <div className="p-4 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <h2 className="font-semibold text-gray-900">Availability</h2>
              <button onClick={() => setSidebarOpen(false)} className="lg:hidden text-gray-500 hover:text-gray-700">✕</button>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-4">
            <button
              onClick={() => setShowAddModal(true)}
              className="w-full mb-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium"
            >
              + Add Availability
            </button>

            {availability.length === 0 ? (
              <p className="text-sm text-gray-500 text-center py-4">No availability set</p>
            ) : (
              availability.map((a: any) => (
                <div key={a.id} className="p-3 mb-2 bg-gray-50 rounded-lg border border-gray-200">
                  <p className="font-medium text-gray-900">{a.date}</p>
                  <p className="text-sm text-gray-600">{a.start_time} - {a.end_time}</p>
                </div>
              ))
            )}
          </div>

          <div className="p-4 border-t border-gray-200 bg-gray-50">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium text-gray-900">{user.name}</p>
                <p className="text-xs text-gray-600">{user.email}</p>
              </div>
              <button onClick={handleLogout} className="text-gray-500 hover:text-red-600">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content - Outlook Style */}
      <div className="flex-1 flex flex-col overflow-hidden bg-white">
        {/* Top Toolbar */}
        <div className="bg-white border-b border-gray-200 px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <button onClick={() => setSidebarOpen(true)} className="lg:hidden p-2 hover:bg-gray-100 rounded">
                <svg className="w-5 h-5 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              </button>
              <button className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 font-medium text-sm">
                New event
              </button>
              <div className="flex items-center space-x-1 border border-gray-300 rounded">
                <button
                  onClick={() => setViewMode("day")}
                  className={`px-3 py-1 text-sm ${viewMode === "day" ? "bg-blue-50 text-blue-700" : "text-gray-700 hover:bg-gray-50"}`}
                >
                  Day
                </button>
                <button
                  onClick={() => setViewMode("week")}
                  className={`px-3 py-1 text-sm ${viewMode === "week" ? "bg-blue-50 text-blue-700" : "text-gray-700 hover:bg-gray-50"}`}
                >
                  Week
                </button>
                <button
                  onClick={() => setViewMode("month")}
                  className={`px-3 py-1 text-sm ${viewMode === "month" ? "bg-blue-50 text-blue-700" : "text-gray-700 hover:bg-gray-50"}`}
                >
                  Month
                </button>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <button onClick={() => navigateDate("prev")} className="p-2 hover:bg-gray-100 rounded">
                <svg className="w-5 h-5 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </button>
              <button onClick={() => navigateDate("today")} className="px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded font-medium">
                Today
              </button>
              <button onClick={() => navigateDate("next")} className="p-2 hover:bg-gray-100 rounded">
                <svg className="w-5 h-5 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </button>
              <div className="ml-4 px-3 py-1 text-sm font-medium text-gray-900">
                {currentDate.toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric", year: "numeric" })}
              </div>
            </div>
          </div>
        </div>

        {/* Calendar Day View - Outlook Style */}
        <div className="flex-1 overflow-auto bg-white">
          <div className="flex h-full">
            {/* Time Column */}
            <div className="w-20 border-r border-gray-200 bg-gray-50">
              <div className="h-12 border-b border-gray-200"></div>
              {getTimeSlots().map((time, i) => {
                const [hours] = time.split(':');
                const hour = parseInt(hours);
                if (hour >= 12 && hour < 24) {
                  return (
                    <div key={i} className="h-8 border-b border-gray-100 flex items-start justify-end pr-2">
                      {i % 2 === 0 && (
                        <span className="text-xs text-gray-600 mt-0.5">
                          {hour === 12 ? '12 PM' : hour > 12 ? `${hour - 12} PM` : `${hour} AM`}
                        </span>
                      )}
                    </div>
                  );
                }
                return null;
              })}
            </div>

            {/* Calendar Content */}
            <div className="flex-1 relative">
              <div className="absolute inset-0">
                {/* Time Grid Lines */}
                {getTimeSlots().map((time, i) => {
                  const [hours] = time.split(':');
                  const hour = parseInt(hours);
                  if (hour >= 12 && hour < 24) {
                    return (
                      <div
                        key={i}
                        className={`absolute left-0 right-0 border-b ${i % 2 === 0 ? 'border-gray-200' : 'border-gray-100'}`}
                        style={{ top: `${i * 8}px` }}
                      />
                    );
                  }
                  return null;
                })}

                {/* Appointments */}
                {dayAppointments.map((apt: any, idx: number) => {
                  const position = getAppointmentPosition(apt.time);
                  const height = getAppointmentHeight(apt.duration_minutes || 60);
                  const top = position - (12 * 60 * 2); // Offset for 12 PM start
                  
                  return (
                    <div
                      key={apt.id || idx}
                      className="absolute left-2 right-2 bg-blue-100 border-l-4 border-blue-500 rounded shadow-sm hover:shadow-md transition-shadow"
                      style={{
                        top: `${Math.max(0, top)}px`,
                        height: `${height}px`,
                        minHeight: '40px'
                      }}
                    >
                      <div className="p-2 h-full flex flex-col">
                        <div className="font-medium text-sm text-gray-900">
                          {formatTime(apt.time)}
                        </div>
                        <div className="text-sm text-gray-700 mt-1">
                          {apt.users?.name || apt.contact_number || 'Unknown User'}
                        </div>
                        {apt.notes && (
                          <div className="text-xs text-gray-600 mt-1 truncate">
                            {apt.notes}
                          </div>
                        )}
                        <div className="mt-auto text-xs text-gray-500">
                          {apt.status === 'confirmed' ? '✓ Confirmed' : apt.status === 'pending' ? '⏳ Pending' : apt.status}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Add Availability Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-md w-full p-6 shadow-xl">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Add Availability</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Date</label>
                <input
                  type="date"
                  value={newAvail.date}
                  onChange={(e) => setNewAvail({ ...newAvail, date: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Start Time</label>
                  <input
                    type="time"
                    value={newAvail.start_time}
                    onChange={(e) => setNewAvail({ ...newAvail, start_time: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">End Time</label>
                  <input
                    type="time"
                    value={newAvail.end_time}
                    onChange={(e) => setNewAvail({ ...newAvail, end_time: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
              </div>
            </div>
            <div className="flex space-x-3 mt-6">
              <button
                onClick={() => setShowAddModal(false)}
                className="flex-1 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 font-medium"
              >
                Cancel
              </button>
              <button
                onClick={addAvailability}
                className="flex-1 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium"
              >
                Add
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
