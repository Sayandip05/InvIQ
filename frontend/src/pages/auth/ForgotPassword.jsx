import React, { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { auth } from "../../services/api";
import { AlertCircle, Loader2, CheckCircle } from "lucide-react";

const ForgotPassword = () => {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      await auth.requestPasswordReset({ email });
      setSuccess(true);
    } catch (err) {
      const msg = err?.response?.data?.message || "Failed to send reset link";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background p-4">
        <div className="w-full max-w-[400px] bg-card rounded-none shadow-lg p-7 border border-border">
          <div className="flex flex-col items-center">
            <CheckCircle size={48} className="text-[#F26A4B] mb-4" />
            <h2 className="text-2xl font-sans font-bold text-foreground">Check your email</h2>
            <p className="text-center text-muted-foreground mt-2 text-sm">
              If an account exists with {email}, we've sent a password reset link.
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

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <div className="w-full max-w-[400px] bg-card rounded-none shadow-lg p-7 border border-border">
        <div className="flex flex-col items-center mb-6">
          <h2 className="text-2xl font-sans font-bold text-foreground">Forgot Password?</h2>
          <p className="text-center text-muted-foreground text-sm mt-2">
            Enter your email and we'll send you a reset link
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
            <label className="text-xs font-bold text-foreground uppercase tracking-wider">Email</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 w-full px-3.5 py-2.5 bg-background border border-border rounded-xl text-sm text-foreground placeholder:text-muted-foreground focus:bg-card focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 transition-all"
              placeholder="Enter your email"
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
                Sending...
              </>
            ) : (
              "Send Reset Link"
            )}
          </button>

          <button
            type="button"
            onClick={() => navigate("/signin")}
            className="w-full text-center text-muted-foreground hover:text-foreground text-sm pt-1 cursor-pointer"
          >
            Back to Sign In
          </button>
        </form>
      </div>
    </div>
  );
};

export default ForgotPassword;