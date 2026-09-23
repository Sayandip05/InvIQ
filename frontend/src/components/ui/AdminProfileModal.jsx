import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { auth } from '../../services/api';
import {
    User,
    Mail,
    Lock,
    KeyRound,
    X,
    Check,
    AlertCircle,
    Loader2,
    Shield,
} from 'lucide-react';

export default function AdminProfileModal({ isOpen, onClose }) {
    const { user, updateUser } = useAuth();

    const [fullName, setFullName] = useState('');
    const [email, setEmail] = useState('');

    // Password change fields
    const [showPasswordSection, setShowPasswordSection] = useState(false);
    const [currentPassword, setCurrentPassword] = useState('');
    const [newPassword, setNewPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');

    const [loading, setLoading] = useState(false);
    const [passwordLoading, setPasswordLoading] = useState(false);
    const [error, setError] = useState('');
    const [successMessage, setSuccessMessage] = useState('');
    const [passwordSuccess, setPasswordSuccess] = useState('');

    useEffect(() => {
        if (isOpen) {
            // Preload from context
            if (user) {
                setFullName(user.full_name || user.username || '');
                setEmail(user.email || '');
            }
            // Also fetch latest fresh data from backend
            auth.me()
                .then((res) => {
                    if (res?.data?.data) {
                        const u = res.data.data;
                        setFullName(u.full_name || u.username || '');
                        setEmail(u.email || '');
                        updateUser({
                            full_name: u.full_name,
                            email: u.email,
                            username: u.username,
                            organization_name: u.organization_name,
                        });
                    }
                })
                .catch(() => {});

            setError('');
            setSuccessMessage('');
            setPasswordSuccess('');
        }
    }, [isOpen]);

    if (!isOpen || !user) return null;

    const handleSaveProfile = async (e) => {
        e.preventDefault();
        setError('');
        setSuccessMessage('');

        if (!fullName.trim()) {
            setError('Full Name is mandatory.');
            return;
        }

        setLoading(true);
        try {
            const res = await auth.updateProfile({
                full_name: fullName.trim(),
                email: email.trim().toLowerCase(),
            });

            if (res.data?.success) {
                const updated = res.data.data;
                updateUser({
                    full_name: updated.full_name,
                    email: updated.email,
                    username: updated.username,
                });
                setSuccessMessage('Profile details saved successfully!');
                setTimeout(() => {
                    setSuccessMessage('');
                }, 3000);
            }
        } catch (err) {
            const msg =
                err?.response?.data?.detail ||
                err?.response?.data?.error?.message ||
                err?.response?.data?.message ||
                'Failed to update profile. Please try again.';
            setError(msg);
        } finally {
            setLoading(false);
        }
    };

    const handleChangePassword = async (e) => {
        e.preventDefault();
        setError('');
        setPasswordSuccess('');

        if (!currentPassword) {
            setError('Please enter your current password.');
            return;
        }
        if (newPassword.length < 8) {
            setError('New password must be at least 8 characters long.');
            return;
        }
        if (newPassword !== confirmPassword) {
            setError('New passwords do not match.');
            return;
        }

        setPasswordLoading(true);
        try {
            const res = await auth.changePassword({
                old_password: currentPassword,
                new_password: newPassword,
            });

            if (res.data?.success) {
                setPasswordSuccess('Password changed successfully!');
                setCurrentPassword('');
                setNewPassword('');
                setConfirmPassword('');
                setShowPasswordSection(false);
                setTimeout(() => setPasswordSuccess(''), 3000);
            }
        } catch (err) {
            const msg =
                err?.response?.data?.detail ||
                err?.response?.data?.error?.message ||
                err?.response?.data?.message ||
                'Failed to change password. Please verify your current password.';
            setError(msg);
        } finally {
            setPasswordLoading(false);
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-xs animate-in fade-in duration-150">
            <div className="bg-card border border-border text-card-foreground w-full max-w-lg shadow-2xl rounded-none flex flex-col max-h-[90vh] overflow-hidden">
                
                {/* ── Modal Header ────────────────────────────────────────── */}
                <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-muted/20">
                    <div className="flex items-center gap-2.5">
                        <div className="w-8 h-8 bg-primary text-primary-foreground flex items-center justify-center font-bold text-xs rounded-none">
                            <User size={16} />
                        </div>
                        <div>
                            <h3 className="text-sm font-bold text-foreground">Administrator Profile</h3>
                            <p className="text-xs text-muted-foreground">Update your name and security credentials</p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-1 text-muted-foreground hover:text-foreground hover:bg-accent/50 transition cursor-pointer rounded-none"
                    >
                        <X size={18} />
                    </button>
                </div>

                {/* ── Modal Body ──────────────────────────────────────────── */}
                <div className="p-6 overflow-y-auto space-y-5">
                    
                    {error && (
                        <div className="p-3 bg-destructive/10 border border-destructive/20 text-destructive text-xs flex items-center gap-2 rounded-none">
                            <AlertCircle size={15} className="shrink-0 text-destructive" />
                            <span>{error}</span>
                        </div>
                    )}

                    {successMessage && (
                        <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 text-emerald-800 dark:text-emerald-300 text-xs flex items-center gap-2 rounded-none">
                            <Check size={15} className="shrink-0 text-emerald-600" />
                            <span>{successMessage}</span>
                        </div>
                    )}

                    {passwordSuccess && (
                        <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 text-emerald-800 dark:text-emerald-300 text-xs flex items-center gap-2 rounded-none">
                            <Check size={15} className="shrink-0 text-emerald-600" />
                            <span>{passwordSuccess}</span>
                        </div>
                    )}

                    {/* Profile Information Form */}
                    <form onSubmit={handleSaveProfile} className="space-y-4">
                        <div>
                            <label className="block text-xs font-semibold text-foreground uppercase tracking-wider mb-1">
                                Full Name <span className="text-destructive">*</span>
                            </label>
                            <input
                                type="text"
                                required
                                value={fullName}
                                onChange={(e) => setFullName(e.target.value)}
                                placeholder="Enter your full name"
                                className="w-full px-3 py-2 bg-background border border-border rounded-none text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-ring focus:border-ring placeholder:text-muted-foreground"
                            />
                            <p className="text-[11px] text-muted-foreground mt-0.5">This name is used across the dashboard and the InvIQ AI assistant.</p>
                        </div>

                        <div>
                            <label className="block text-xs font-semibold text-foreground uppercase tracking-wider mb-1">
                                Email Address <span className="text-destructive">*</span>
                            </label>
                            <input
                                type="email"
                                required
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                placeholder="admin@pharmacy.com"
                                className="w-full px-3 py-2 bg-background border border-border rounded-none text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-ring focus:border-ring placeholder:text-muted-foreground"
                            />
                            <p className="text-[11px] text-muted-foreground mt-0.5">Used for authentication and important pharmacy alerts.</p>
                        </div>

                        <div className="pt-2 flex items-center justify-between">
                            <button
                                type="button"
                                onClick={() => setShowPasswordSection(!showPasswordSection)}
                                className="text-xs text-muted-foreground hover:text-foreground font-semibold flex items-center gap-1.5 cursor-pointer"
                            >
                                <KeyRound size={13} />
                                <span>{showPasswordSection ? 'Hide Password Change' : 'Change Password'}</span>
                            </button>

                            <button
                                type="submit"
                                disabled={loading}
                                className="px-5 py-2 bg-primary text-primary-foreground text-xs font-bold rounded-none hover:opacity-90 transition disabled:opacity-50 flex items-center gap-2 cursor-pointer"
                            >
                                {loading && <Loader2 size={13} className="animate-spin" />}
                                <span>Save Profile Changes</span>
                            </button>
                        </div>
                    </form>

                    {/* Change Password Section */}
                    {showPasswordSection && (
                        <div className="pt-4 border-t border-border bg-muted/15 p-4 space-y-3 rounded-none">
                            <div className="flex items-center gap-2">
                                <Shield size={14} className="text-foreground" />
                                <h4 className="text-xs font-bold text-foreground uppercase tracking-wider">Update Account Password</h4>
                            </div>

                            <form onSubmit={handleChangePassword} className="space-y-3">
                                <div>
                                    <label className="block text-[11px] font-semibold text-muted-foreground mb-1">
                                        Current Password
                                    </label>
                                    <input
                                        type="password"
                                        required
                                        value={currentPassword}
                                        onChange={(e) => setCurrentPassword(e.target.value)}
                                        placeholder="••••••••"
                                        className="w-full px-3 py-1.5 bg-background border border-border rounded-none text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-ring focus:border-ring"
                                    />
                                </div>

                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                    <div>
                                        <label className="block text-[11px] font-semibold text-muted-foreground mb-1">
                                            New Password
                                        </label>
                                        <input
                                            type="password"
                                            required
                                            value={newPassword}
                                            onChange={(e) => setNewPassword(e.target.value)}
                                            placeholder="Min 8 characters"
                                            className="w-full px-3 py-1.5 bg-background border border-border rounded-none text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-ring focus:border-ring"
                                        />
                                    </div>

                                    <div>
                                        <label className="block text-[11px] font-semibold text-muted-foreground mb-1">
                                            Confirm New Password
                                        </label>
                                        <input
                                            type="password"
                                            required
                                            value={confirmPassword}
                                            onChange={(e) => setConfirmPassword(e.target.value)}
                                            placeholder="Repeat new password"
                                            className="w-full px-3 py-1.5 bg-background border border-border rounded-none text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-ring focus:border-ring"
                                        />
                                    </div>
                                </div>

                                <div className="flex justify-end pt-1">
                                    <button
                                        type="submit"
                                        disabled={passwordLoading}
                                        className="px-4 py-1.5 bg-primary text-primary-foreground text-xs font-semibold rounded-none hover:opacity-90 transition disabled:opacity-50 flex items-center gap-1.5 cursor-pointer"
                                    >
                                        {passwordLoading && <Loader2 size={12} className="animate-spin" />}
                                        <span>Update Password</span>
                                    </button>
                                </div>
                            </form>
                        </div>
                    )}
                </div>

                {/* ── Modal Footer ────────────────────────────────────────── */}
                <div className="px-6 py-3 border-t border-border bg-muted/20 flex justify-end">
                    <button
                        type="button"
                        onClick={onClose}
                        className="px-4 py-1.5 bg-background border border-border text-foreground text-xs font-semibold hover:bg-accent transition rounded-none cursor-pointer"
                    >
                        Close
                    </button>
                </div>

            </div>
        </div>
    );
}

