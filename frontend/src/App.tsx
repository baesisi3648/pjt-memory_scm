import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import './index.css';

function LoginPage() {
  return <div className="flex items-center justify-center min-h-screen bg-background">Login Page (P1-S1-T1)</div>;
}

function DashboardPage() {
  return <div className="min-h-screen bg-background">Dashboard Page (P3-S1-T1)</div>;
}

function AlertSettingsPage() {
  return <div className="min-h-screen bg-background">Alert Settings Page (P5-S1-T1)</div>;
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/settings/alerts" element={<AlertSettingsPage />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
