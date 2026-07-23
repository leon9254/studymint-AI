import { ArrowLeft, CheckCircle2, KeyRound, XCircle } from "lucide-react";
import { FormEvent, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Button } from "../components/ui/Button";
import { PasswordInput } from "../components/ui/PasswordInput";
import { resetPassword } from "../services/authApi";

export function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") ?? "";
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState("");

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");

    if (!token) {
      setError("Password reset link is missing a token.");
      return;
    }

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setIsSubmitting(true);
    try {
      await resetPassword(token, password);
      setPassword("");
      setConfirmPassword("");
      setSuccess(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to reset password");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen overflow-x-hidden bg-[#f2f5f1] px-4 py-6 text-ink-950 sm:px-6 lg:px-8">
      <main className="mx-auto grid min-h-[calc(100vh-3rem)] w-full min-w-0 max-w-5xl grid-cols-1 items-center gap-6 lg:grid-cols-[minmax(0,1fr)_27rem]">
        <section className="w-full min-w-0 max-w-[22rem] justify-self-start rounded-lg border border-ink-200 bg-white p-5 shadow-panel sm:max-w-full sm:p-8">
          <Link
            to="/login"
            className="inline-flex items-center gap-2 text-sm font-semibold text-ink-700 transition hover:text-mint-800"
          >
            <ArrowLeft size={16} />
            Back to login
          </Link>

          <div className="mt-8 flex h-12 w-12 items-center justify-center rounded-lg bg-mint-700 text-white shadow-lg shadow-mint-900/15">
            <KeyRound size={22} />
          </div>

          <div className="mt-6">
            <span className="inline-flex rounded-full border border-mint-200 bg-mint-50 px-3 py-1 text-xs font-bold uppercase tracking-[0.16em] text-mint-800">
              New password
            </span>
            <h1 className="mt-4 max-w-full break-words text-3xl font-semibold leading-tight tracking-normal text-ink-950 sm:max-w-xl sm:text-4xl">
              Create a fresh password for StudyMint AI.
            </h1>
            <p className="mt-4 max-w-full break-words text-base leading-7 text-ink-700 sm:max-w-xl">
              Once your password is updated, you can sign in and continue
              generating, reviewing, and exporting study documents.
            </p>
          </div>
        </section>

        <form
          onSubmit={onSubmit}
          className="w-full min-w-0 max-w-[22rem] justify-self-start rounded-lg border border-ink-200 bg-white p-5 shadow-panel sm:max-w-full sm:p-7"
        >
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-ink-950 text-white shadow-lg shadow-ink-900/15">
              <KeyRound size={19} />
            </div>
            <div className="min-w-0">
              <h2 className="text-2xl font-semibold tracking-normal text-ink-950">
                Reset password
              </h2>
              <p className="text-sm font-medium text-ink-600">
                Use at least 8 characters.
              </p>
            </div>
          </div>

          {success ? (
            <div className="mt-6 rounded-lg border border-mint-200 bg-mint-50 p-4 text-sm text-mint-900">
              <div className="flex items-center gap-2 font-semibold">
                <CheckCircle2 size={17} />
                Password updated
              </div>
              <p className="mt-2 leading-6 text-mint-800">
                Your password has been reset. Sign in with your new password to
                continue.
              </p>
              <Link
                className="mt-3 inline-flex font-semibold text-mint-800 transition hover:text-mint-700"
                to="/login"
              >
                Go to sign in
              </Link>
            </div>
          ) : (
            <>
              <div className="mt-6 space-y-4">
                <PasswordInput
                  label="New password"
                  autoComplete="new-password"
                  minLength={8}
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  required
                />
                <PasswordInput
                  label="Confirm password"
                  autoComplete="new-password"
                  minLength={8}
                  value={confirmPassword}
                  onChange={(event) => setConfirmPassword(event.target.value)}
                  required
                />
              </div>

              {error && (
                <p className="mt-4 flex items-start gap-2 rounded-lg border border-red-300 bg-red-50 px-3 py-2.5 text-sm leading-6 text-red-800">
                  <XCircle size={16} className="mt-0.5 shrink-0" />
                  <span>{error}</span>
                </p>
              )}

              <Button className="mt-6 w-full" size="lg" disabled={isSubmitting}>
                {isSubmitting ? "Updating password..." : "Update password"}
              </Button>
            </>
          )}
        </form>
      </main>
    </div>
  );
}
