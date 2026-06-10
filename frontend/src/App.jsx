import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { GuestProvider } from './context/GuestContext';
import { WebSocketProvider } from './context/WebSocketContext';
import ProtectedRoute from './components/ProtectedRoute';
import AdminLayout from './components/layout/AdminLayout';
import ManagerLayout from './components/layout/ManagerLayout';
import PreviewBanner from './components/ui/PreviewBanner';

import Dashboard from './pages/admin/Dashboard';
import Inventory from './pages/admin/Inventory';
import Chatbot from './pages/admin/Chatbot';
import Requisitions from './pages/admin/Requisitions';
import UserManagement from './pages/admin/UserManagement';
import AuditLogs from './pages/admin/AuditLogs';
import Reports from './pages/admin/Reports';

import ManagerDashboard from './pages/manager/ManagerDashboard';
import ManagerInventory from './pages/manager/ManagerInventory';
import ManagerChatbot from './pages/manager/ManagerChatbot';
import ManagerRequisitions from './pages/manager/ManagerRequisitions';

import StaffRequisition from './pages/staff/StaffRequisition';
import DataEntry from './pages/vendor/DataEntry';
import Landing from './pages/Landing';
import { LightSignIn } from './components/ui/sign-in';
import { LightSignUp } from './components/ui/sign-up';
import ForgotPassword from './pages/auth/ForgotPassword';
import ResetPassword from './pages/auth/ResetPassword';
import VerifyEmail from './pages/auth/VerifyEmail';

/**
 * Role → home-page map. Viewer role removed — guests access /admin/* freely.
 */
const ROLE_HOME = {
  super_admin: '/superadmin/dashboard',
  admin:       '/admin/dashboard',
  manager:     '/manager/dashboard',
  staff:       '/staff',
  vendor:      '/vendor',
};

/** Redirect authenticated users to their correct home page. */
function RoleRedirect() {
  const { user } = useAuth();
  const home = user ? (ROLE_HOME[user.role] || '/admin/dashboard') : '/admin/dashboard';
  return <Navigate to={home} replace />;
}

/**
 * AppContent — all router-dependent providers and routes live here,
 * inside <BrowserRouter>, so hooks like useNavigate() work correctly.
 */
function AppContent() {
  return (
    <GuestProvider>
      <WebSocketProvider>
        {/* PreviewBanner sits outside layouts — always visible to guests */}
        <PreviewBanner />

        <Routes>
          {/* ── Public pages ──────────────────────────────────────── */}
          <Route path="/"               element={<Landing />} />
          <Route path="/signin"         element={<LightSignIn />} />
          <Route path="/signup"         element={<LightSignUp />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/reset-password" element={<ResetPassword />} />
          <Route path="/verify-email"   element={<VerifyEmail />} />
          <Route path="/dashboard"      element={<RoleRedirect />} />

          {/* ── Vendor (auth required) ────────────────────────────── */}
          <Route element={<ProtectedRoute requiredRole="vendor" />}>
            <Route path="/vendor" element={<DataEntry />} />
          </Route>

          {/* ── Staff (auth required) ─────────────────────────────── */}
          <Route element={<ProtectedRoute requiredRole="staff" />}>
            <Route path="/staff"      element={<StaffRequisition />} />
            <Route path="/staff/chat" element={<Chatbot />} />
          </Route>

          {/* ── Manager (auth required) ───────────────────────────── */}
          <Route element={<ProtectedRoute requiredRole="manager" />}>
            <Route path="/manager" element={<ManagerLayout />}>
              <Route index element={<Navigate to="/manager/dashboard" replace />} />
              <Route path="dashboard"    element={<ManagerDashboard />} />
              <Route path="inventory"    element={<ManagerInventory />} />
              <Route path="requisitions" element={<ManagerRequisitions />} />
              <Route path="chat"         element={<ManagerChatbot />} />
            </Route>
          </Route>

          {/*
            ── Admin / Guest Demo Mode ────────────────────────────────
            /admin layout is open to unauthenticated visitors.
            Guests can browse read-only pages freely.
            Any interactive action (approve, submit, chat) calls
            showAuthModal() in useGuest() which navigates to /signin.

            Management pages (users, audit-logs, reports) remain
            behind a nested ProtectedRoute — guests can't reach them.
          */}
          <Route path="/admin" element={<AdminLayout />}>
            <Route index element={<Navigate to="/admin/dashboard" replace />} />
            {/* Guest-accessible read-only pages */}
            <Route path="dashboard"    element={<Dashboard />} />
            <Route path="inventory"    element={<Inventory />} />
            <Route path="chat"         element={<Chatbot />} />
            <Route path="requisitions" element={<Requisitions />} />
            {/* Auth-required management pages */}
            <Route element={<ProtectedRoute requiredRole="admin" />}>
              <Route path="users"      element={<UserManagement />} />
              <Route path="audit-logs" element={<AuditLogs />} />
              <Route path="reports"    element={<Reports />} />
            </Route>
          </Route>

          {/* ── Super Admin (auth required) ───────────────────────── */}
          <Route element={<ProtectedRoute requiredRole="super_admin" />}>
            <Route path="/superadmin" element={<AdminLayout />}>
              <Route index element={<Navigate to="/superadmin/dashboard" replace />} />
              <Route path="dashboard" element={<Dashboard />} />
              <Route path="organizations" element={
                <div className="p-8">
                  <h2 className="text-2xl font-bold">Organizations</h2>
                  <p className="text-slate-500 mt-2">Manage organizations (coming soon)</p>
                </div>
              } />
              <Route path="users" element={
                <div className="p-8">
                  <h2 className="text-2xl font-bold">User Management</h2>
                  <p className="text-slate-500 mt-2">Manage all users (coming soon)</p>
                </div>
              } />
              <Route path="chat" element={<Chatbot />} />
            </Route>
          </Route>

          {/* ── Catch-all: guests land on demo, not /signin ────────── */}
          <Route path="*" element={<Navigate to="/admin/dashboard" replace />} />
        </Routes>
      </WebSocketProvider>
    </GuestProvider>
  );
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppContent />
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;