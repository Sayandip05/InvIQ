/**
 * Login Page — JWT authentication entry point.
 *
 * Flow:
 *  1. User submits username + password
 *  2. POST /api/auth/login → receives access_token + refresh_token
 *  3. Tokens stored in localStorage via AuthContext.login()
 *  4. Redirect to originally requested page or /admin/dashboard
 */

import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Package, Lock, User, AlertCircle, Loader2 } from 'lucide-react';

export default function Login() {
    const { login, isAuthenticated } = useAuth();
    const navigate = useNavigate();
    const location = useLocation();

    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const from = location.state?.from?.pathname || '/dashboard';

    // Auto-redirect if already logged in
    React.useEffect(() => {
        if (isAuthenticated) {
            navigate(from, { replace: true });
        }
    }, [isAuthenticated, navigate, from]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setLoading(true);

        try {
            await login(username, password);
            navigate(from, { replace: true });
        } catch (err) {
            const msg =
                err?.response?.data?.detail ||
                err?.response?.data?.message ||
                'Invalid username or password';
            setError(msg);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
            {/* Background gradient blob */}
            <div className="absolute inset-0 overflow-hidden pointer-events-none">
                <div className="absolute -top-40 -right-40 w-80 h-80 bg-blue-600 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-pulse" />
                <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-indigo-600 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-pulse delay-1000" />
            </div>

            <div className="relative w-full max-w-md">
                {/* Card */}
                <div className="bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl p-8">
                    {/* Logo */}
                    <div className="flex flex-col items-center mb-8">
                        <div className="w-14 h-14 bg-blue-600 rounded-xl flex items-center justify-center mb-4 shadow-lg shadow-blue-600/30">
                            <Package className="text-white" size={28} />
                        </div>
                        <h1 className="text-2xl font-bold text-white">Smart Inventory</h1>
                        <p className="text-slate-400 text-sm mt-1">Sign in to your account</p>
                    </div>

                    {/* Error alert */}
                    {error && (
                        <div className="mb-5 flex items-center gap-2 bg-red-950/60 border border-red-800 text-red-400 text-sm rounded-lg px-4 py-3">
                            <AlertCircle size={16} className="shrink-0" />
                            <span>{error}</span>
                        </div>
                    )}

                    {/* Form */}
                    <form onSubmit={handleSubmit} className="space-y-5">
                        {/* Username */}
                        <div>
                            <label className="block text-sm font-medium text-slate-300 mb-1.5">
                                Username
                            </label>
                            <div className="relative">
                                <User
                                    size={16}
                                    className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500"
                                />
                                <input
                                    id="login-username"
                                    type="text"
                                    autoComplete="username"
                                    required
                                    value={username}
                                    onChange={(e) => setUsername(e.target.value)}
                                    placeholder="Enter your username"
                                    className="w-full bg-slate-800 border border-slate-700 text-white rounded-lg pl-10 pr-4 py-2.5 text-sm placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent transition"
                                />
                            </div>
                        </div>

                        {/* Password */}
                        <div>
                            <label className="block text-sm font-medium text-slate-300 mb-1.5">
                                Password
                            </label>
                            <div className="relative">
                                <Lock
                                    size={16}
                                    className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500"
                                />
                                <input
                                    id="login-password"
                                    type="password"
                                    autoComplete="current-password"
                                    required
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    placeholder="Enter your password"
                                    className="w-full bg-slate-800 border border-slate-700 text-white rounded-lg pl-10 pr-4 py-2.5 text-sm placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent transition"
                                />
                            </div>
                        </div>

                        {/* Submit */}
                        <button
                            id="login-submit"
                            type="submit"
                            disabled={loading}
                            className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-60 disabled:cursor-not-allowed text-white font-semibold py-2.5 rounded-lg transition-colors duration-200 shadow-lg shadow-blue-600/20"
                        >
                            {loading ? (
                                <>
                                    <Loader2 size={16} className="animate-spin" />
                                    Signing in…
                                </>
                            ) : (
                                'Sign In'
                            )}
                        </button>
                    </form>

                    {/* Info */}
                    <p className="text-center text-xs text-slate-600 mt-6">
                        Contact your administrator to get access credentials.
                    </p>
                </div>
            </div>
        </div>
    );
}
