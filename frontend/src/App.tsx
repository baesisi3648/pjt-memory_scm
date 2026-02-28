// @TASK P1-S0-T1 - App routing with AuthGuard and TopBar
// @TASK P3-S1-T3 - Wired real DashboardPage
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import './index.css';

import { AuthGuard } from './components/layout/AuthGuard';
import { TopBar } from './components/layout/TopBar';
import { LoginPage } from './pages/LoginPage';
import { AlertSettingsPage } from './pages/AlertSettingsPage';
import { DashboardPage } from './pages/DashboardPage';

// Layout wrapper for authenticated pages — renders TopBar + page content.
// DashboardPage is overflow-hidden and self-sized, so no pt-14 padding needed
// on it — it uses dashboard-page-height (calc(100vh - 56px)) directly.
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
