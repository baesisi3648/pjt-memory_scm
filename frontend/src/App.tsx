// @TASK P1-S0-T1 - App routing with AuthGuard and TopBar
// @TASK P3-S1-T3 - Wired real DashboardPage
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import './index.css';

// import { AuthGuard } from './components/layout/AuthGuard';
import { TopBar } from './components/layout/TopBar';
// import { LoginPage } from './pages/LoginPage';
import { AlertSettingsPage } from './pages/AlertSettingsPage';
import { DashboardPage } from './pages/DashboardPage';
import { ToastContainer } from './components/ui/Toast';

// Layout wrapper — renders fixed TopBar + page content.
function AuthenticatedLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <TopBar />
      {children}
    </>
  );
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* DEV MODE: Auth bypassed — all routes accessible without login */}
        {/* <Route path="/login" element={<LoginPage />} /> */}

        <Route
          path="/dashboard"
          element={
            <AuthenticatedLayout>
              <DashboardPage />
            </AuthenticatedLayout>
          }
        />
        <Route
          path="/settings/alerts"
          element={
            <AuthenticatedLayout>
              <AlertSettingsPage />
            </AuthenticatedLayout>
          }
        />

        {/* Fallback → dashboard */}
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>

      {/* Global toast notifications — fixed overlay, renders above all routes */}
      <ToastContainer />
    </BrowserRouter>
  );
}

export default App;
