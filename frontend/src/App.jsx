import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { GuestProvider } from './context/GuestContext';
import { WebSocketProvider } from './context/WebSocketContext';
import ProtectedRoute from './components/ProtectedRoute';
import AdminLayout from './components/layout/AdminLayout';
import PreviewBanner from './components/ui/PreviewBanner';

import Dashboard from './pages/admin/Dashboard';
import Inventory from './pages/admin/Inventory';
import Chatbot from './pages/admin/Chatbot';
import Requisitions from './pages/admin/Requisitions';
import UserManagement from './pages/admin/UserManagement';
import SupplierManagement from './pages/admin/SupplierManagement';
import Reports from './pages/admin/Reports';
import OrganizationSettings from './pages/admin/OrganizationSettings';
import BillingCounter from './pages/staff/BillingCounter';

import StaffRequisition from './pages/staff/StaffRequisition';
import DataEntry from './pages/vendor/DataEntry';
import Landing from './pages/Landing';
import { LightSignIn } from './components/ui/sign-in';
import { LightSignUp } from './components/ui/sign-up';
import ForgotPassword from './pages/auth/ForgotPassword';
import ResetPassword from './pages/auth/ResetPassword';
import VerifyEmail from './pages/auth/VerifyEmail';
import PreviewDashboard from './pages/preview/PreviewDashboard';
import OnboardingWizard from './components/ui/OnboardingWizard';

/**
 * Role → home-page map.
 */
const ROLE_HOME = {
  admin:       '/admin/dashboard',
  manager:     '/admin/dashboard',
  staff:       '/staff',
  vendor:      '/vendor',
};

/** Redirect authenticated users to their correct home page, and guests to standalone preview. */
function RoleRedirect() {
  const { user } = useAuth();
  const home = user ? (ROLE_HOME[user.role] || '/admin/dashboard') : '/preview';
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
        {/* Step-by-step onboarding wizard for newly registered users */}
        <OnboardingWizard />


        <Routes>
          {/* ── Public pages ──────────────────────────────────────── */}
          <Route path="/"               element={<Landing />} />
          <Route path="/preview"        element={<PreviewDashboard />} />
          <Route path="/demo"           element={<PreviewDashboard />} />
          <Route path="/signin"         element={<LightSignIn />} />
          <Route path="/signup"         element={<LightSignUp />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/reset-password" element={<ResetPassword />} />
          <Route path="/verify-email"   element={<VerifyEmail />} />
          <Route path="/dashboard"      element={<RoleRedirect />} />

          {/* ── Vendor (auth required) ────────────────────────────── */}
          <Route element={<ProtectedRoute requiredRole="vendor" />}>
            <Route element={<AdminLayout />}>
              <Route path="/vendor" element={<DataEntry />} />
            </Route>
          </Route>

          {/* ── Staff (auth required) ─────────────────────────────── */}
          <Route element={<ProtectedRoute requiredRole="staff" />}>
            <Route path="/staff"         element={<StaffRequisition />} />
            <Route path="/staff/chat"    element={<Chatbot />} />
            <Route path="/staff/billing" element={<BillingCounter />} />
            <Route path="/billing"       element={<BillingCounter />} />
          </Route>

          {/*
            ── Admin / Guest Demo Mode ────────────────────────────────
            /admin layout is open to unauthenticated visitors.
            Guests can browse read-only pages freely.
            Any interactive action (approve, submit, chat) calls
            showAuthModal() in useGuest() which navigates to /signin.

            Management pages (suppliers, users, audit-logs, reports) remain
            behind a nested ProtectedRoute — guests can't reach them.
          */}
          <Route path="/admin" element={<AdminLayout />}>
            <Route index element={<Navigate to="/admin/dashboard" replace />} />
            {/* Guest-accessible read-only pages */}
            <Route path="dashboard"         element={<Dashboard />} />
            <Route path="billing"           element={<BillingCounter />} />
            <Route path="inventory"         element={<Inventory />} />
            <Route path="stock-acquisition" element={<DataEntry />} />
            <Route path="chat"              element={<Chatbot />} />
            <Route path="requisitions"      element={<Requisitions />} />
            <Route path="organization"      element={<OrganizationSettings />} />
            {/* Auth-required management pages */}
            <Route element={<ProtectedRoute requiredRole="admin" />}>
              <Route path="suppliers"       element={<SupplierManagement />} />
              <Route path="users"           element={<UserManagement />} />
              <Route path="reports"         element={<Reports />} />
            </Route>
          </Route>





          {/* ── Catch-all: guests land on demo, not /signin ────────── */}
          <Route path="*" element={<Navigate to="/admin/dashboard" replace />} />
        </Routes>
      </WebSocketProvider>
    </GuestProvider>
  );
}

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }
  componentDidCatch(error, errorInfo) {
    console.error('App Caught Error:', error, errorInfo);
  }
  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-[#FAFAFA] text-slate-900 flex flex-col items-center justify-center p-6 text-center">
          <img src="/logo.png" alt="InvIQ Logo" className="w-16 h-16 object-contain mb-4" />
          <h2 className="text-2xl font-bold mb-2">InvIQ Smart Inventory</h2>
          <p className="text-slate-500 text-sm max-w-md mb-6">
            An unexpected error occurred. Click below to return to the home page.
          </p>
          <button
            onClick={() => { localStorage.clear(); window.location.href = '/'; }}
            className="px-6 py-2.5 bg-blue-600 text-white font-semibold rounded-xl hover:bg-blue-700 shadow-md shadow-blue-500/20 transition-all"
          >
            Reload Home Page
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <BrowserRouter>
          <AppContent />
        </BrowserRouter>
      </AuthProvider>
    </ErrorBoundary>
  );
}

export default App;