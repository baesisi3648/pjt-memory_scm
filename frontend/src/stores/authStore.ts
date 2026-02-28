// @TASK P1-S0-T1 - Auth Zustand store
import { create } from 'zustand';
import api from '../services/api';

interface User {
  email: string;
  name: string;
  role: string;
}

interface AuthState {
  token: string | null;
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  loadToken: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  user: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,

  loadToken: () => {
    const token = localStorage.getItem('access_token');
    if (token) {
      set({ token, isAuthenticated: true });
    }
  },

  login: async (email: string, password: string) => {
    set({ isLoading: true, error: null });
    try {
      const formData = new URLSearchParams();
      formData.append('username', email);
      formData.append('password', password);

      const response = await api.post<{ access_token: string; token_type: string }>(
        '/auth/login',
        formData.toString(),
        { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
      );

      const { access_token } = response.data;
      localStorage.setItem('access_token', access_token);

      // Decode basic user info from token payload (JWT)
      let user: User = { email, name: email, role: 'viewer' };
      try {
        const payload = JSON.parse(atob(access_token.split('.')[1]));
        user = {
          email: payload.sub ?? email,
          name: payload.name ?? email,
          role: payload.role ?? 'viewer',
        };
      } catch {
        // If decoding fails, use email as fallback
      }

      set({ token: access_token, user, isAuthenticated: true, isLoading: false, error: null });
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        '로그인에 실패했습니다. 이메일과 비밀번호를 확인해주세요.';
      set({ isLoading: false, error: message, isAuthenticated: false });
      throw err;
    }
  },

  logout: () => {
    localStorage.removeItem('access_token');
    set({ token: null, user: null, isAuthenticated: false, error: null });
  },
}));
