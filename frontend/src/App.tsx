// @TASK P1-S0-T1 - App routing with AuthGuard and TopBar
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import './index.css';

import { AuthGuard } from './components/layout/AuthGuard';
import { TopBar } from './components/layout/TopBar';
import { LoginPage } from './pages/LoginPage';

function DashboardPage() {
  return <div className="min-h-screen bg-background">Dashboard Page (P3-S1-T1)</div>;
}

function AlertSettingsPage() {
  return <div className="min-h-screen bg-background">Alert Settings Page (P5-S1-T1)</div>;
}

// Layout wrapper for authenticated pages — renders TopBar + page content
function AuthenticatedLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <TopBar />
      {/* Offset content below fixed TopBar (h-14 = 56px) */}
      <div className="pt-14">{children}</div>
    </>
  );
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public */}
        <Route path="/login" element={<LoginPage />} />

        {/* Protected */}
        <Route
          path="/dashboard"
          element={
            <AuthGuard>
              <AuthenticatedLayout>
                <DashboardPage />
              </AuthenticatedLayout>
            </AuthGuard>
          }
        />
        <Route
          path="/settings/alerts"
          element={
            <AuthGuard>
              <AuthenticatedLayout>
                <AlertSettingsPage />
              </AuthenticatedLayout>
            </AuthGuard>
          }
        />

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
