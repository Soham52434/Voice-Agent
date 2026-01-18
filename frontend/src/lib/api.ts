const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

class ApiClient {
  private token: string | null = null;

  setToken(token: string | null) {
    this.token = token;
    if (token) localStorage.setItem('token', token);
    else localStorage.removeItem('token');
  }

  getToken(): string | null {
    if (!this.token && typeof window !== 'undefined') {
      this.token = localStorage.getItem('token');
    }
    return this.token;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const token = this.getToken();
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
      ...options.headers,
    };

    const response = await fetch(`${API_URL}${endpoint}`, { ...options, headers });
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Request failed' }));
      throw new Error(error.detail || 'Request failed');
    }
    
    return response.json();
  }

  // Auth
  async loginUser(phone: string, name: string) {
    const data = await this.request<{ token: string; user: any }>('/api/auth/user/login', {
      method: 'POST',
      body: JSON.stringify({ phone, name }),
    });
    this.setToken(data.token);
    return data;
  }

  async loginMentor(email: string, password: string) {
    const data = await this.request<{ token: string; user: any }>('/api/auth/mentor/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    this.setToken(data.token);
    return data;
  }

  async loginAdmin(email: string, password: string) {
    const data = await this.request<{ token: string; user: any }>('/api/auth/admin/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    this.setToken(data.token);
    return data;
  }

  async getMe() {
    return this.request<{ type: string; user: any }>('/api/auth/me');
  }

  // LiveKit
  async getLiveKitToken() {
    return this.request<{ token: string; room_name: string; livekit_url: string }>('/api/livekit/token');
  }

  // Users
  async getUsers() {
    return this.request<any[]>('/api/users');
  }

  async getUserSessions(phone: string) {
    return this.request<any[]>(`/api/users/${phone}/sessions`);
  }

  async getUserAppointments(phone: string) {
    return this.request<any[]>(`/api/users/${phone}/appointments`);
  }

  // Mentors
  async getMentors() {
    return this.request<any[]>('/api/mentors');
  }

  async getMentorAvailability(mentorId: string, startDate?: string, endDate?: string) {
    const params = new URLSearchParams();
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    return this.request<any[]>(`/api/mentors/${mentorId}/availability?${params}`);
  }

  async addMentorAvailability(mentorId: string, data: { date: string; start_time: string; end_time: string; slot_duration_minutes?: number }) {
    return this.request<any>(`/api/mentors/${mentorId}/availability`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getMentorSlots(mentorId: string, date: string) {
    return this.request<any[]>(`/api/mentors/${mentorId}/slots?date=${date}`);
  }

  async getMentorAppointments(mentorId: string, status?: string, startDate?: string, endDate?: string) {
    const params = new URLSearchParams();
    if (status) params.append('status', status);
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    return this.request<any[]>(`/api/mentors/${mentorId}/appointments?${params}`);
  }

  // Appointments
  async getAppointments() {
    return this.request<any[]>('/api/appointments');
  }

  async getAppointmentCalendar(mentorId: string, month: number, year: number) {
    return this.request<any>(`/api/appointments/calendar?mentor_id=${mentorId}&month=${month}&year=${year}`);
  }

  async updateAppointment(id: string, data: { status?: string; mentor_notes?: string }) {
    return this.request<any>(`/api/appointments/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  // Sessions
  async getSessions() {
    return this.request<any[]>('/api/sessions');
  }

  async getSession(id: string) {
    return this.request<{ session: any; messages: any[] }>(`/api/sessions/${id}`);
  }

  // Admin
  async getAdminStats() {
    return this.request<any>('/api/admin/stats');
  }

  async getCostReport() {
    return this.request<any[]>('/api/admin/costs');
  }

  async getSessionCosts() {
    return this.request<any[]>('/api/admin/costs/sessions');
  }

  logout() {
    this.setToken(null);
  }
}

export const api = new ApiClient();

