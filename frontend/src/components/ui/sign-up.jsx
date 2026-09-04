import React, { useState, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { auth } from "../../services/api";
import { AlertCircle, Loader2, ArrowLeft } from "lucide-react";

export const LightSignUp = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, loginWithGoogle, isAuthenticated } = useAuth();
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);
  const [error, setError] = useState("");
  const [formData, setFormData] = useState({
    full_name: "",
    email: "",
    username: "",
    password: "",
    role: "admin"
  });

  const from = "/dashboard";

  useEffect(() => {
    if (window.location.hash) {
      const hashParams = new URLSearchParams(window.location.hash.substring(1));
      const token = hashParams.get("access_token") || hashParams.get("id_token");
      if (token) {
        window.history.replaceState(null, "", window.location.pathname);
        setGoogleLoading(true);
        loginWithGoogle(token)
          .then((userData) => {
            // Route based on role returned from backend
            const role = userData?.role || "admin";
            if (role === "staff" || role === "vendor") {
              navigate("/staff", { replace: true });
            } else {
              navigate("/admin/dashboard", { replace: true });
            }
          })
          .catch((err) => {
            const msg =
              err?.response?.data?.detail ||
              err?.response?.data?.error?.message ||
              err?.response?.data?.message ||
              "Google sign-up failed. Please try again.";
            setError(msg);
            setGoogleLoading(false);
          });
      }
    }
  }, [loginWithGoogle, navigate]);

  useEffect(() => {
    if (isAuthenticated) {
      navigate(from, { replace: true });
    }
  }, [isAuthenticated, navigate]);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const cleanData = {
        full_name: (formData.full_name || formData.fullName || "").trim(),
        email: formData.email.trim().toLowerCase(),
        username: formData.username.trim(),
        password: formData.password,
        role: "admin",
      };
      await auth.register(cleanData);
      // Automatically sign in upon successful registration using email
      await login(cleanData.email, cleanData.password);
      navigate(from, { replace: true });
    } catch (err) {
      const status = err?.response?.status;
      const msg =
        err?.response?.data?.error?.message ||
        err?.response?.data?.detail ||
        err?.response?.data?.message;
      
      if (status === 403) {
        setError("Self-registration is disabled. Please sign up using Google or contact your administrator.");
      } else if (status === 409 || (msg && msg.toLowerCase().includes("already exists"))) {
        setError("This email address is already registered. Please Sign In with your credentials.");
      } else {
        setError(msg || "Registration failed. Please check your details and try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleLogin = () => {
    const clientId = "232640553692-bk12l0dqojirdv31gsr8geag0aju75jf.apps.googleusercontent.com";
    const redirectUri = window.location.origin + window.location.pathname;
    const authUrl = `https://accounts.google.com/o/oauth2/v2/auth?client_id=${encodeURIComponent(clientId)}&redirect_uri=${encodeURIComponent(redirectUri)}&response_type=token&scope=openid%20email%20profile&prompt=select_account`;
    window.location.href = authUrl;
  };


  return (
    <div className="min-h-screen flex items-center justify-center bg-background relative overflow-hidden p-4">
      {/* Clean Subtle Grid Lines & Warm Ambient Glow */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[50vw] h-[50vw] bg-[#F26A4B]/5 rounded-full blur-[120px]" />
        <div className="absolute top-[20%] right-[-10%] w-[60vw] h-[60vw] bg-[#2E2E2E]/5 rounded-full blur-[140px]" />
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#00000008_1px,transparent_1px),linear-gradient(to_bottom,#00000008_1px,transparent_1px)] bg-[size:40px_40px]" />
      </div>

      <button
        onClick={() => navigate('/')}
        className="absolute top-6 left-6 z-20 flex items-center gap-2 text-xs font-semibold text-foreground bg-card/90 hover:bg-card backdrop-blur-md px-4 py-2 rounded-full border border-border shadow-xs transition-all cursor-pointer"
      >
        <ArrowLeft size={14} />
        <span>Back to Home</span>
      </button>

      <div className="w-full max-w-[420px] bg-card rounded-2xl shadow-lg border border-border overflow-hidden relative z-10 p-8 sm:p-9">
        <div className="flex flex-col items-center mb-6">
          <div className="flex items-center gap-2.5 mb-3">
            <img src="/logo.png" alt="InvIQ Logo" className="w-9 h-9 object-contain" />
            <span className="font-sans font-bold text-2xl tracking-tight text-foreground">InvIQ</span>
          </div>
          <h2 className="text-2xl font-sans font-bold text-foreground text-center">
            Create Account
          </h2>
          <p className="text-center text-muted-foreground text-xs sm:text-sm mt-1">
            Sign up or continue with Google
          </p>
        </div>

        {error && (
          <div className="mb-5 flex items-center gap-2 bg-destructive/10 border border-destructive/30 text-destructive text-xs sm:text-sm rounded-xl px-4 py-3 shadow-xs">
            <AlertCircle size={16} className="shrink-0 text-destructive" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-foreground uppercase tracking-wider">
              Full Name
            </label>
            <input
              type="text"
              name="full_name"
              required
              value={formData.full_name}
              onChange={handleChange}
              className="w-full px-3.5 py-2.5 bg-background border border-border rounded-xl text-sm text-foreground placeholder:text-muted-foreground focus:bg-card focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 transition-all"
              placeholder="Enter your full name"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-bold text-foreground uppercase tracking-wider">
              Email
            </label>
            <input
              type="email"
              name="email"
              required
              value={formData.email}
              onChange={handleChange}
              className="w-full px-3.5 py-2.5 bg-background border border-border rounded-xl text-sm text-foreground placeholder:text-muted-foreground focus:bg-card focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 transition-all"
              placeholder="Enter your email"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-bold text-foreground uppercase tracking-wider">
              Username
            </label>
            <input
              type="text"
              name="username"
              required
              value={formData.username}
              onChange={handleChange}
              className="w-full px-3.5 py-2.5 bg-background border border-border rounded-xl text-sm text-foreground placeholder:text-muted-foreground focus:bg-card focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 transition-all"
              placeholder="Choose a username"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-bold text-foreground uppercase tracking-wider">
              Password
            </label>
            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                name="password"
                required
                minLength={8}
                value={formData.password}
                onChange={handleChange}
                className="w-full px-3.5 py-2.5 pr-12 bg-background border border-border rounded-xl text-sm text-foreground placeholder:text-muted-foreground focus:bg-card focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 transition-all"
                placeholder="••••••••"
              />
              <button
                type="button"
                className="absolute right-2 top-1/2 -translate-y-1/2 text-xs font-semibold text-muted-foreground hover:text-foreground px-2 py-1 rounded transition-colors cursor-pointer"
                onClick={() => setShowPassword(!showPassword)}
              >
                {showPassword ? "Hide" : "Show"}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 bg-primary hover:bg-black text-primary-foreground font-bold text-sm rounded-xl transition-all shadow-md active:scale-[0.99] flex items-center justify-center disabled:opacity-60 disabled:pointer-events-none cursor-pointer"
          >
            {loading ? (
              <>
                <Loader2 size={16} className="animate-spin mr-2" />
                <span>Creating account…</span>
              </>
            ) : (
              "Sign Up"
            )}
          </button>

          <div className="flex items-center my-4">
            <div className="flex-1 h-px bg-border" />
            <span className="px-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
              or continue with
            </span>
            <div className="flex-1 h-px bg-border" />
          </div>

          <button 
            type="button"
            onClick={handleGoogleLogin}
            disabled={googleLoading}
            className="w-full h-11 bg-background hover:bg-accent/40 border border-border text-foreground rounded-xl flex items-center justify-center gap-2.5 text-sm font-semibold transition-all shadow-2xs disabled:opacity-50 cursor-pointer"
          >
            {googleLoading ? (
              <Loader2 size={16} className="animate-spin text-primary" />
            ) : (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
                <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
                <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" fill="#FBBC05" />
                <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
              </svg>
            )}
            <span>{googleLoading ? "Signing up with Google..." : "Continue with Google"}</span>
          </button>

          <p className="text-xs text-center text-muted-foreground pt-3">
            Already have an account?{" "}
            <a href="/signin" className="text-[#F26A4B] font-bold hover:underline">
              Sign in
            </a>
          </p>
        </form>
      </div>
    </div>
  );
};
