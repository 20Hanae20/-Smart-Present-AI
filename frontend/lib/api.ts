import axios, { AxiosInstance } from 'axios';
import { getApiBase } from './config';

/**
 * Centralized API client with typed error handling and request utilities.
 * All API calls should go through this module for consistency.
 */

// Types
export interface User {
  id: number;
  email: string;
  full_name: string;
  role: 'admin' | 'trainer' | 'student';
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_at: string;
}

export interface Student {
  id: number;
  user_id: number;
  student_code: string;
  first_name: string;
  last_name: string;
  email: string;
  class_name: string;
  attendance_rate: number;
}

export interface Trainer {
  id: number;
  user_id: number;
  first_name: string;
  last_name: string;
  email: string;
}

export interface Session {
  id: number;
  class_name: string;
  subject: string;
  date: string;
  start_time: string;
  end_time: string;
  trainer_id: number;
  status: string;
}

/**
 * Standard API error structure
 */
export interface APIError {
  message: string;
  statusCode?: number;
  detail?: unknown;
}

/**
 * Parse errors into a consistent APIError format.
 * Handles Axios errors, native Error objects, and unknown error types.
 * @param error - The error to parse (can be AxiosError, Error, or unknown)
 * @returns {APIError} Normalized error object with message, statusCode, and detail
 */
export function parseAPIError(error: unknown): APIError {
  if (axios.isAxiosError(error)) {
    const axiosError = error as any;
    return {
      message:
        axiosError.response?.data?.detail ||
        axiosError.response?.data?.message ||
        axiosError.message ||
        'Request failed',
      statusCode: axiosError.response?.status,
      detail: axiosError.response?.data,
    };
  }

  if (error instanceof Error) {
    return {
      message: error.message,
    };
  }

  return {
    message: 'Unknown error occurred',
  };
}

export interface AttendanceRecord {
  id: number;
  session_id: number;
  student_id: number;
  status: 'present' | 'absent' | 'late' | 'excused';
  marked_via: string;
  facial_confidence?: number;
  marked_at: string;
  late_minutes: number;
  justification?: string;
}

export interface AttendanceSummary {
  student_id: number;
  total_sessions: number;
  present: number;
  absent: number;
  late: number;
  excused: number;
  attendance_rate: number;
  period_days: number;
}

export interface ClassStats {
  class: string;
  total_records: number;
  present_count: number;
  average_attendance_rate: number;
  period_days: number;
}

export interface Notification {
  id: number;
  user_id: number;
  title?: string;
  message: string;
  type: string;
  read: boolean;
  created_at: string;
}

// API Client
const TOKEN_KEY = 'spa_access_token';

class ApiClient {
  private client: AxiosInstance;
  private token: string | null = null;

  constructor() {
    const apiUrl = getApiBase();
    this.client = axios.create({
      baseURL: `${apiUrl}/api`,
    });

    this.loadToken();
    this.setupInterceptors();
  }

  private loadToken() {
    if (typeof window !== 'undefined') {
      this.token = localStorage.getItem(TOKEN_KEY);
    }
  }

  private setupInterceptors() {
    this.client.interceptors.request.use((config) => {
      if (this.token) {
        config.headers.Authorization = `Bearer ${this.token}`;
      }
      return config;
    });
  }

  setToken(token: string) {
    this.token = token;
    localStorage.setItem(TOKEN_KEY, token);
    this.setupInterceptors();
  }

  clearToken() {
    this.token = null;
    localStorage.removeItem(TOKEN_KEY);
  }

  // Auth endpoints
  async login(email: string, password: string): Promise<LoginResponse> {
    const response = await this.client.post<LoginResponse>('/auth/login', { email, password });
    return response.data;
  }

  async getCurrentUser(): Promise<User> {
    const response = await this.client.get<User>('/users/me');
    return response.data;
  }

  // User endpoints
  async listStudents(): Promise<Student[]> {
    const response = await this.client.get<any[]>('/users/');
    if (!Array.isArray(response.data)) return [];

    return response.data
      .filter((u) => u.role === 'student')
      .map((u) => ({
        id: u.id,
        user_id: u.id,
        student_code: u.username,
        first_name: u.email.split('@')[0],
        last_name: u.username,
        email: u.email,
        class_name: `DEV101`,
        attendance_rate: 100,
      }));
  }

  async listTrainers(): Promise<Trainer[]> {
    const response = await this.client.get<any[]>('/users/');
    if (!Array.isArray(response.data)) return [];

    return response.data
      .filter((u) => u.role === 'trainer')
      .map((u) => ({
        id: u.id,
        user_id: u.id,
        trainer_code: u.username,
        first_name: u.email.split('@')[0],
        last_name: u.username,
        email: u.email,
        specialization: 'Web Development',
      }));
  }

  async getUser(userId: number): Promise<User> {
    const response = await this.client.get<User>(`/users/${userId}`);
    return response.data;
  }

  // Session endpoints
  async listSessions(): Promise<Session[]> {
    const response = await this.client.get<any[]>('/sessions/');
    if (!Array.isArray(response.data)) return [];

    return response.data.map((s) => ({
      ...s,
      subject: s.topic,
      date: s.session_date,
      class_name: `Class ${s.classroom_id}`,
    }));
  }

  async getSession(sessionId: number): Promise<Session> {
    const response = await this.client.get<any>(`/sessions/${sessionId}`);
    return {
      ...response.data,
      subject: response.data.topic,
      date: response.data.session_date,
      class_name: `Class ${response.data.classroom_id}`,
    };
  }

  async createSession(session: Partial<Session>): Promise<Session> {
    const response = await this.client.post<Session>('/sessions/', session);
    return response.data;
  }

  // Attendance endpoints
  async markAttendance(
    sessionId: number,
    studentId: number,
    status: string,
  ): Promise<AttendanceRecord> {
    const response = await this.client.post<AttendanceRecord>('/attendance', {
      session_id: sessionId,
      student_id: studentId,
      status,
    });
    return response.data;
  }

  async getStudentSummary(studentId: number, days: number = 30): Promise<AttendanceSummary> {
    const response = await this.client.get<AttendanceSummary>(
      `/attendance/student/${studentId}/summary?days=${days}`,
    );
    return response.data;
  }

  async getSessionAttendance(sessionId: number): Promise<AttendanceRecord[]> {
    const response = await this.client.get<{ records: AttendanceRecord[] }>(
      `/attendance/session/${sessionId}/all`,
    );
    return response.data.records || [];
  }

  async getClassStats(className: string, days: number = 30): Promise<ClassStats> {
    const response = await this.client.get<ClassStats>(
      `/attendance/class/${className}/stats?days=${days}`,
    );
    return response.data;
  }

  // Notification endpoints
  async getPendingNotifications(): Promise<Notification[]> {
    try {
      const response = await this.client.get<any>('/notifications/me/');
      return response.data.notifications || [];
    } catch (err) {
      return [];
    }
  }

  async markNotificationRead(notificationId: number): Promise<void> {
    await this.client.put(`/notifications/${notificationId}/read`);
  }

  // Report endpoints
  async exportReport(format: 'csv' | 'excel' | 'pdf', type: string): Promise<Blob> {
    const response = await this.client.get(
      `/reports/attendance/summary?format=${format}&type=${type}`,
      { responseType: 'blob' },
    );
    return response.data;
  }

  // Chatbot endpoints removed
}

export const api = new ApiClient();
