// @TASK P1-S0-T1 - Auth route guard component
import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';

interface AuthGuardProps {
  children: React.ReactNode;
}

export function AuthGuard({ children }: AuthGuardProps) {
  const { isAuthenticated, loadToken } = useAuthStore();
  const navigate = useNavigate();

  useEffect(() => {
    // Hydrate auth state from localStorage on mount
    loadToken();
  }, [loadToken]);

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      navigate('/login', { replace: true });
    }
  }, [isAuthenticated, navigate]);

  // Check token directly from storage for synchronous guard on first render
  const token = localStorage.getItem('access_token');
  if (!token) {
    return null;
  }

  return <>{children}</>;
}
