import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { WebSocketProvider } from './context/WebSocketContext';
import ProtectedRoute from './components/ProtectedRoute';
import AdminLayout from './components/layout/AdminLayout';
import ManagerLayout from './components/layout/ManagerLayout';

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

const ROLE_HOME = {
  super_admin: '/superadmin/dashboard',
  admin: '/admin/dashboard',
  manager: '/manager/dashboard',
  staff: '/staff',
  vendor: '/vendor',
  // Viewers use the same /admin layout — they only see read-only pages
  viewer: '/admin/dashboard',
};

function RoleRedirect() {
  const { user } = useAuth();
  const home = user ? (ROLE_HOME[user.role] || '/admin/dashboard') : '/signin';
  return <Navigate to={home} replace />;
}

function App() {
  return (
    <AuthProvider>
      <WebSocketProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/signin" element={<LightSignIn />} />
            <Route path="/signup" element={<LightSignUp />} />
            <Route path="/forgot-password" element={<ForgotPassword />} />
            <Route path="/reset-password" element={<ResetPassword />} />
            <Route path="/verify-email" element={<VerifyEmail />} />
            <Route path="/dashboard" element={<RoleRedirect />} />

            <Route element={<ProtectedRoute requiredRole="vendor" />}>
              <Route path="/vendor" element={<DataEntry />} />
            </Route>

            <Route element={<ProtectedRoute requiredRole="staff" />}>
              <Route path="/staff" element={<StaffRequisition />} />
              <Route path="/staff/chat" element={<Chatbot />} />
            </Route>

            <Route element={<ProtectedRoute requiredRole="manager" />}>
              <Route path="/manager" element={<ManagerLayout />}>
                <Route index element={<Navigate to={"/manager/dashboard"} replace />} />
                <Route path="dashboard" element={<ManagerDashboard />} />
                <Route path="inventory" element={<ManagerInventory />} />
                <Route path="requisitions" element={<ManagerRequisitions />} />
                <Route path="chat" element={<ManagerChatbot />} />
              </Route>
            </Route>

            {/*
              /admin layout is accessible to viewers and above.
              Admin-only pages (users, audit-logs, reports, requisitions)
              are guarded by a nested ProtectedRoute inside the layout.
            */}
            <Route element={<ProtectedRoute requiredRole="viewer" />}>
              <Route path="/admin" element={<AdminLayout />}>
                <Route index element={<Navigate to={"/admin/dashboard"} replace />} />
                {/* Read-only pages — viewers can access */}
                <Route path="dashboard" element={<Dashboard />} />
                <Route path="inventory" element={<Inventory />} />
                <Route path="chat" element={<Chatbot />} />
                {/* Admin-only pages — nested guard blocks viewer access */}
                <Route element={<ProtectedRoute requiredRole="admin" />}>
                  <Route path="requisitions" element={<Requisitions />} />
                  <Route path="users" element={<UserManagement />} />
                  <Route path="audit-logs" element={<AuditLogs />} />
                  <Route path="reports" element={<Reports />} />
                </Route>
              </Route>
            </Route>

            {/* /viewer/* redirects to /admin/* — viewer users now use the shared admin layout */}
            <Route path="/viewer" element={<Navigate to="/admin/dashboard" replace />} />
            <Route path="/viewer/*" element={<Navigate to="/admin/dashboard" replace />} />

            <Route element={<ProtectedRoute requiredRole="super_admin" />}>
              <Route path="/superadmin" element={<AdminLayout />}>
                <Route index element={<Navigate to={"/superadmin/dashboard"} replace />} />
                <Route path="dashboard" element={<Dashboard />} />
                <Route path="organizations" element={<div className="p-8"><h2 className="text-2xl font-bold">Organizations</h2><p className="text-slate-500 mt-2">Manage organizations (coming soon)</p></div>} />
                <Route path="users" element={<div className="p-8"><h2 className="text-2xl font-bold">User Management</h2><p className="text-slate-500 mt-2">Manage all users (coming soon)</p></div>} />
                <Route path="chat" element={<Chatbot />} />
              </Route>
            </Route>

            <Route path="*" element={<Navigate to="/signin" replace />} />
          </Routes>
        </BrowserRouter>
      </WebSocketProvider>
    </AuthProvider>
  );
}

export default App;