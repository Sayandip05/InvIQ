import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import AdminLayout from './components/layout/AdminLayout';

// ── Admin Pages ───────────────────────────────────────────────
import Dashboard from './pages/admin/Dashboard';
import Inventory from './pages/admin/Inventory';
import Chatbot from './pages/admin/Chatbot';
import Requisitions from './pages/admin/Requisitions';

// ── Staff Pages ───────────────────────────────────────────────
import StaffRequisition from './pages/staff/StaffRequisition';

// ── Vendor Pages ──────────────────────────────────────────────
import DataEntry from './pages/vendor/DataEntry';

// ── Landing Page ────────────────────────────────────────────────
import Landing from './pages/Landing';

// ── Login ─────────────────────────────────────────────────────
import Login from './pages/Login';

/**
 * Role → default landing page mapping.
 * After login, users are redirected to their portal.
 */
const ROLE_HOME = {
  super_admin: '/admin/dashboard',
  admin: '/admin/dashboard',
  manager: '/admin/dashboard',
  staff: '/staff',
  vendor: '/vendor',
  viewer: '/admin/dashboard',
};

function RoleRedirect() {
  const { user } = useAuth();
  const home = user ? (ROLE_HOME[user.role] || '/admin/dashboard') : '/login';
  return <Navigate to={home} replace />;
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* ── Public ──────────────────────────────────────────── */}
          <Route path="/" element={<Landing />} />
          <Route path="/login" element={<Login />} />

          {/* Root → redirect based on role */}
          <Route path="/dashboard" element={<RoleRedirect />} />

          {/* ── Vendor Portal (vendor+) ───────────────────────── */}
          <Route element={<ProtectedRoute requiredRole="vendor" />}>
            <Route path="/vendor" element={<DataEntry />} />
          </Route>

          {/* ── Staff Portal (staff+) ─────────────────────────── */}
          <Route element={<ProtectedRoute requiredRole="staff" />}>
            <Route path="/staff" element={<StaffRequisition />} />
            <Route path="/staff/chat" element={<Chatbot />} />
          </Route>

          {/* ── Admin/Manager/Viewer Portal (viewer+, shared layout) */}
          <Route element={<ProtectedRoute requiredRole="viewer" />}>
            <Route path="/admin" element={<AdminLayout />}>
              <Route index element={<Navigate to="/admin/dashboard" replace />} />
              <Route path="dashboard" element={<Dashboard />} />
              <Route path="inventory" element={<Inventory />} />
              <Route path="requisitions" element={<Requisitions />} />
              <Route path="chat" element={<Chatbot />} />
            </Route>
          </Route>

          {/* Catch-all */}
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
