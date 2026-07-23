import { CheckCircle2, Loader2, MailCheck, XCircle } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

export function VerifyEmailPage() {
  const { user, verifyEmail } = useAuth();
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");
  const navigate = useNavigate();
  const [status, setStatus] = useState<"loading" | "success" | "failed">("loading");
  const [message, setMessage] = useState("Verifying your email address...");

  useEffect(() => {
    if (!token) {
      setStatus("failed");
      setMessage("Verification link is missing a token.");
      return;
    }

    let cancelled = false;
    verifyEmail(token)
      .then(() => {
        if (cancelled) return;
        setStatus("success");
        setMessage("Email verified. Redirecting to your dashboard...");
        window.setTimeout(() => navigate("/dashboard", { replace: true }), 900);
      })
      .catch((err) => {
        if (cancelled) return;
        setStatus("failed");
        setMessage(err instanceof Error ? err.message : "Unable to verify your email.");
      });

    return () => {
      cancelled = true;
    };
  }, [navigate, token]);

  if (user && status !== "loading") {
    return <Navigate to="/dashboard" replace />;
  }

  const Icon = status === "success" ? CheckCircle2 : status === "failed" ? XCircle : Loader2;

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#f2f5f1] px-4 py-8 text-ink-950">
      <main className="w-full max-w-md rounded-lg border border-ink-200 bg-white p-6 shadow-panel">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-mint-700 text-white shadow-lg shadow-mint-900/15">
            <MailCheck size={19} />
          </div>
          <div>
            <h1 className="text-2xl font-semibold tracking-normal">
              Email verification
            </h1>
            <p className="text-sm font-medium text-ink-600">
              StudyMint AI account security
            </p>
          </div>
        </div>

        <div className="mt-6 rounded-lg border border-ink-200 bg-ink-50 p-4">
          <div className="flex items-center gap-3">
            <Icon
              size={20}
              className={
                status === "success"
                  ? "text-mint-700"
                  : status === "failed"
                    ? "text-red-700"
                    : "animate-spin text-iris-700"
              }
            />
            <p className="text-sm font-semibold text-ink-900">{message}</p>
          </div>
        </div>

        {status === "failed" && (
          <div className="mt-5 flex gap-3">
            <Link
              className="inline-flex h-10 flex-1 items-center justify-center rounded-md border border-mint-700 bg-mint-700 px-4 text-sm font-semibold text-white shadow-sm shadow-mint-900/10 transition hover:border-mint-800 hover:bg-mint-800 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-mint-200"
              to="/login"
            >
              Back to sign in
            </Link>
          </div>
        )}
      </main>
    </div>
  );
}
