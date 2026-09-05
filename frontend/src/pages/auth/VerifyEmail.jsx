import React, { useState, useEffect } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { auth } from "../../services/api";
import { AlertCircle, Loader2, CheckCircle } from "lucide-react";

const VerifyEmail = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get("token");

  const [status, setStatus] = useState("loading"); // loading, success, error
  const [message, setMessage] = useState("");

  useEffect(() => {
    const verifyEmail = async () => {
      if (!token) {
        setStatus("error");
        setMessage("Invalid verification link");
        return;
      }

      try {
        await auth.verifyEmail({ token });
        setStatus("success");
        setMessage("Email verified successfully!");
      } catch (err) {
        setStatus("error");
        setMessage(err?.response?.data?.message || "Verification failed");
      }
    };

    verifyEmail();
  }, [token]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <div className="w-full max-w-[400px] bg-card rounded-none shadow-lg p-7 border border-border">
        <div className="flex flex-col items-center">
          {status === "loading" && (
            <>
              <Loader2 size={48} className="text-[#F26A4B] animate-spin mb-4" />
              <h2 className="text-2xl font-sans font-bold text-foreground">Verifying...</h2>
              <p className="text-center text-muted-foreground mt-2 text-sm">
                Please wait while we verify your email.
              </p>
            </>
          )}

          {status === "success" && (
            <>
              <CheckCircle size={48} className="text-[#F26A4B] mb-4" />
              <h2 className="text-2xl font-sans font-bold text-foreground">Email Verified!</h2>
              <p className="text-center text-muted-foreground mt-2 text-sm">{message}</p>
              <button
                onClick={() => navigate("/signin")}
                className="mt-6 bg-primary text-primary-foreground px-6 py-2.5 rounded-xl hover:bg-black font-semibold text-sm cursor-pointer"
              >
                Sign In
              </button>
            </>
          )}

          {status === "error" && (
            <>
              <AlertCircle size={48} className="text-destructive mb-4" />
              <h2 className="text-2xl font-sans font-bold text-foreground">Verification Failed</h2>
              <p className="text-center text-muted-foreground mt-2 text-sm">{message}</p>
              <button
                onClick={() => navigate("/signin")}
                className="mt-6 text-[#F26A4B] hover:underline font-semibold text-sm cursor-pointer"
              >
                Back to Sign In
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default VerifyEmail;