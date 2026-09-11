import React, { Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { GuestProvider } from './context/GuestContext';
import { WebSocketProvider } from './context/WebSocketContext';
import ProtectedRoute from './components/ProtectedRoute';
import AdminLayout from './components/layout/AdminLayout';
import PreviewBanner from './components/ui/PreviewBanner';
import RouteLoadingFallback from '@/shared/components/ui/RouteLoadingFallback';
import { getRoleHome } from '@/shared/constants/roles';

// ── Code-split Lazy Route Modules ──────────────────────────────────────────
const Dashboard = lazy(() => import('./pages/admin/Dashboard'));
const Inventory = lazy(() => import('./pages/admin/Inventory'));
const Chatbot = lazy(() => import('./pages/admin/Chatbot'));
const UserManagement = lazy(() => import('./pages/admin/UserManagement'));
const SupplierManagement = lazy(() => import('./pages/admin/SupplierManagement'));
const Reports = lazy(() => import('./pages/admin/Reports'));
const SuppliersAndStaff = lazy(() => import('./pages/admin/SuppliersAndStaff'));
const OrganizationSettings = lazy(() => import('./pages/admin/OrganizationSettings'));
const BillingCounter = lazy(() => import('./pages/staff/BillingCounter'));
const StaffRequisition = lazy(() => import('./pages/staff/StaffRequisition'));
const DataEntry = lazy(() => import('./pages/vendor/DataEntry'));
const Landing = lazy(() => import('./pages/Landing'));
const LightSignIn = lazy(() => import('./components/ui/sign-in').then(m => ({ default: m.LightSignIn })));
const LightSignUp = lazy(() => import('./components/ui/sign-up').then(m => ({ default: m.LightSignUp })));
const ForgotPassword = lazy(() => import('./pages/auth/ForgotPassword'));
const ResetPassword = lazy(() => import('./pages/auth/ResetPassword'));
const VerifyEmail = lazy(() => import('./pages/auth/VerifyEmail'));
const PreviewDashboard = lazy(() => import('./pages/preview/PreviewDashboard'));
const OnboardingWizard = lazy(() => import('./components/ui/OnboardingWizard'));

/** Redirect authenticated users to their correct home page, and guests to standalone preview. */
function RoleRedirect() {
  const { user } = useAuth();
  const home = getRoleHome(user?.role);
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
        <Suspense fallback={null}>
          <OnboardingWizard />
        </Suspense>


        <Suspense fallback={<RouteLoadingFallback />}>
          <Routes>
            {/* ── Public pages ──────────────────────────────────────── */}
            <Route path="/" element={<Landing />} />
            <Route path="/preview" element={<PreviewDashboard />} />
            <Route path="/demo" element={<PreviewDashboard />} />
            <Route path="/signin" element={<LightSignIn />} />
            <Route path="/signup" element={<LightSignUp />} />
            <Route path="/forgot-password" element={<ForgotPassword />} />
            <Route path="/reset-password" element={<ResetPassword />} />
            <Route path="/verify-email" element={<VerifyEmail />} />
            <Route path="/dashboard" element={<RoleRedirect />} />

            {/* ── Vendor (auth required) ────────────────────────────── */}
            <Route element={<ProtectedRoute requiredRole="vendor" />}>
              <Route element={<AdminLayout />}>
                <Route path="/vendor" element={<DataEntry />} />
              </Route>
            </Route>

            {/* ── Staff (auth required) ─────────────────────────────── */}
            <Route element={<ProtectedRoute requiredRole="staff" />}>
              <Route path="/staff" element={<StaffRequisition />} />
              <Route path="/staff/chat" element={<Chatbot />} />
              <Route path="/staff/billing" element={<BillingCounter />} />
              <Route path="/billing" element={<BillingCounter />} />
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
              <Route path="dashboard" element={<Dashboard />} />
              <Route path="billing" element={<BillingCounter />} />
              <Route path="inventory" element={<Inventory />} />
              <Route path="stock-acquisition" element={<DataEntry />} />
              <Route path="chat" element={<Chatbot />} />
              <Route path="requisitions" element={<Navigate to="/admin/stock-acquisition" replace />} />
              <Route path="organization" element={<OrganizationSettings />} />
              {/* Auth-required management pages */}
              <Route element={<ProtectedRoute requiredRole="admin" />}>
                <Route path="suppliers-and-staff" element={<SuppliersAndStaff />} />
                <Route path="suppliers" element={<SuppliersAndStaff initialTab="suppliers" />} />
                <Route path="users" element={<SuppliersAndStaff initialTab="staff" />} />
                <Route path="reports" element={<Reports />} />
              </Route>
            </Route>

            {/* ── Catch-all: guests land on demo, not /signin ────────── */}
            <Route path="*" element={<Navigate to="/admin/dashboard" replace />} />
          </Routes>
        </Suspense>
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
          <p className="text-slate-500 text-sm max-w-md mb-4">
            An unexpected error occurred. Click below to return to the home page.
          </p>
          {this.state.error && (
            <pre className="text-xs text-red-600 bg-red-50 p-3 rounded-lg max-w-lg overflow-auto mb-6 text-left border border-red-200">
              {this.state.error.message || this.state.error.toString()}
            </pre>
          )}
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