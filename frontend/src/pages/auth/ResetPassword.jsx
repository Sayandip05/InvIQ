import React, { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { auth } from "../../services/api";
import { AlertCircle, Loader2, CheckCircle } from "lucide-react";

const ResetPassword = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    if (password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }

    setLoading(true);

    try {
      await auth.resetPassword({ token, new_password: password });
      setSuccess(true);
    } catch (err) {
      const msg = err?.response?.data?.detail || err?.response?.data?.message || "Failed to reset password";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background p-4">
        <div className="w-full max-w-[400px] bg-card rounded-2xl shadow-lg p-7 border border-border">
          <div className="flex flex-col items-center">
            <AlertCircle size={48} className="text-destructive mb-4" />
            <h2 className="text-2xl font-sans font-bold text-foreground">Invalid Link</h2>
            <p className="text-center text-muted-foreground mt-2 text-sm">
              This password reset link is invalid or has expired.
            </p>
            <button
              onClick={() => navigate("/signin")}
              className="mt-6 text-[#F26A4B] hover:underline font-semibold text-sm cursor-pointer"
            >
              Back to Sign In
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background p-4">
        <div className="w-full max-w-[400px] bg-card rounded-2xl shadow-lg p-7 border border-border">
          <div className="flex flex-col items-center">
            <CheckCircle size={48} className="text-[#F26A4B] mb-4" />
            <h2 className="text-2xl font-sans font-bold text-foreground">Password Reset</h2>
            <p className="text-center text-muted-foreground mt-2 text-sm">
              Your password has been reset successfully.
            </p>
            <button
              onClick={() => navigate("/signin")}
              className="mt-6 bg-primary text-primary-foreground px-6 py-2.5 rounded-xl hover:bg-black font-semibold text-sm cursor-pointer"
            >
              Sign In
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <div className="w-full max-w-[400px] bg-card rounded-2xl shadow-lg p-7 border border-border">
        <div className="flex flex-col items-center mb-6">
          <h2 className="text-2xl font-sans font-bold text-foreground">Set New Password</h2>
          <p className="text-center text-muted-foreground mt-2 text-sm">
            Enter your new password below
          </p>
        </div>

        {error && (
          <div className="mb-4 flex items-center gap-2 bg-destructive/10 border border-destructive/30 text-destructive text-sm rounded-xl px-4 py-3">
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="text-xs font-bold text-foreground uppercase tracking-wider">New Password</label>
            <input
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 w-full px-3.5 py-2.5 bg-background border border-border rounded-xl text-sm text-foreground placeholder:text-muted-foreground focus:bg-card focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 transition-all"
              placeholder="••••••••"
            />
          </div>

          <div>
            <label className="text-xs font-bold text-foreground uppercase tracking-wider">Confirm Password</label>
            <input
              type="password"
              required
              minLength={8}
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="mt-1 w-full px-3.5 py-2.5 bg-background border border-border rounded-xl text-sm text-foreground placeholder:text-muted-foreground focus:bg-card focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 transition-all"
              placeholder="••••••••"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full h-11 bg-primary text-primary-foreground font-semibold rounded-xl hover:bg-black transition disabled:opacity-50 flex items-center justify-center cursor-pointer"
          >
            {loading ? (
              <>
                <Loader2 size={16} className="animate-spin mr-2" />
                Resetting...
              </>
            ) : (
              "Reset Password"
            )}
          </button>
        </form>
      </div>
    </div>
  );
};

export default ResetPassword;