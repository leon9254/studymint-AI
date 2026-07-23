import {
  ArrowRight,
  CheckCircle2,
  FileText,
  MailCheck,
  Sparkles,
} from "lucide-react";
import { FormEvent, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { PasswordInput } from "../components/ui/PasswordInput";
import { useAuth } from "../contexts/AuthContext";

const setupItems = [
  "Turn notes and outlines into structured study documents",
  "Preview clean PDF layouts before exporting",
  "Organize study content in one focused workspace",
];

export function RegisterPage() {
  const { user, register, isLoading } = useAuth();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [verificationEmail, setVerificationEmail] = useState("");
  const [registrationMessage, setRegistrationMessage] = useState("");
  const [requiresVerification, setRequiresVerification] = useState(true);

  if (user) {
    return <Navigate to="/dashboard" replace />;
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    try {
      const result = await register({
        full_name: fullName,
        email,
        password,
      });
      setPassword("");
      setConfirmPassword("");
      setVerificationEmail(result.email);
      setRegistrationMessage(result.message);
      setRequiresVerification(result.requires_email_verification);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create account");
    }
  }

  return (
    <div className="min-h-screen overflow-x-hidden bg-[#f2f5f1] px-4 py-6 text-ink-950 sm:px-6 lg:px-8">
      <main className="mx-auto grid min-h-[calc(100vh-3rem)] w-full min-w-0 max-w-6xl grid-cols-1 items-center gap-6 lg:grid-cols-[minmax(0,1fr)_29rem]">
        <section className="w-full min-w-0 max-w-[22rem] justify-self-start rounded-lg border border-ink-200 bg-white p-5 shadow-panel sm:max-w-full sm:p-8">
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-mint-700 text-white shadow-lg shadow-mint-900/15">
              <Sparkles size={21} />
            </div>
            <div className="min-w-0">
              <p className="text-xl font-semibold tracking-tight">
                StudyMint AI
              </p>
              <p className="text-sm font-medium text-ink-600">
                Study document production
              </p>
            </div>
          </div>

          <div className="mt-10">
            <span className="inline-flex rounded-full border border-mint-200 bg-mint-50 px-3 py-1 text-xs font-bold uppercase tracking-[0.16em] text-mint-800">
              Start creating
            </span>
            <h1 className="mt-4 max-w-full break-words text-3xl font-semibold leading-tight tracking-normal text-ink-950 sm:max-w-2xl sm:text-5xl">
              Build polished study documents faster from the material you already have.
            </h1>
            <p className="mt-4 max-w-full break-words text-base leading-7 text-ink-700 sm:max-w-2xl">
              StudyMint AI helps you draft structured learning content, shape it
              with PDF-ready templates, review the output, and export cleaner
              documents without rebuilding everything by hand.
            </p>
          </div>

          <div className="mt-7 grid gap-3">
            {setupItems.map((item) => (
              <div
                key={item}
                className="flex min-w-0 items-center gap-3 rounded-lg border border-ink-200 bg-ink-50 p-3"
              >
                <CheckCircle2 size={18} className="shrink-0 text-mint-700" />
                <span className="min-w-0 break-words text-sm font-semibold text-ink-900">
                  {item}
                </span>
              </div>
            ))}
          </div>
        </section>

        <form
          onSubmit={onSubmit}
          className="w-full min-w-0 max-w-[22rem] justify-self-start rounded-lg border border-ink-200 bg-white p-5 shadow-panel sm:max-w-full sm:p-7"
        >
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-ink-950 text-white shadow-lg shadow-ink-900/15">
              <FileText size={19} />
            </div>
            <div className="min-w-0">
              <h2 className="text-2xl font-semibold tracking-normal text-ink-950">
                Create your account
              </h2>
              <p className="text-sm font-medium text-ink-600">
                Verify your email, then start your first document.
              </p>
            </div>
          </div>

          <div className="mt-6 rounded-lg border border-mint-200 bg-mint-50 p-3 text-sm leading-6 text-mint-900">
            Create study guides, lesson-ready handouts, practice materials, and
            PDF previews from one focused workspace.
          </div>

          {verificationEmail && (
            <div className="mt-6 rounded-lg border border-mint-200 bg-mint-50 p-4 text-sm text-mint-900">
              <div className="flex items-center gap-2 font-semibold">
                <MailCheck size={17} />
                {requiresVerification ? "Verification email sent" : "Account created"}
              </div>
              <p className="mt-2 leading-6 text-mint-800">
                {registrationMessage ||
                  (requiresVerification
                    ? `Check ${verificationEmail} and open the verification link before signing in.`
                    : "Your account is ready. You can sign in now.")}
              </p>
              <Link
                className="mt-3 inline-flex font-semibold text-mint-800 transition hover:text-mint-700"
                to="/login"
              >
                Go to sign in
              </Link>
            </div>
          )}

          <div className="mt-6 space-y-4">
            <Input
              label="Full name"
              autoComplete="name"
              value={fullName}
              onChange={(event) => setFullName(event.target.value)}
              required
            />
            <Input
              label="Email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
            <PasswordInput
              label="Password"
              autoComplete="new-password"
              minLength={8}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              helperText="Use at least 8 characters."
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
            <p className="mt-4 rounded-lg border border-red-300 bg-red-50 px-3 py-2.5 text-sm leading-6 text-red-800">
              {error}
            </p>
          )}

          <Button
            className="mt-6 w-full"
            size="lg"
            disabled={isLoading || Boolean(verificationEmail)}
            icon={<ArrowRight size={17} />}
          >
            {isLoading ? "Creating account..." : "Create account"}
          </Button>

          <div className="mt-5 flex flex-wrap items-center justify-between gap-3 text-sm">
            <Link
              className="font-semibold text-mint-800 transition hover:text-mint-700"
              to="/login"
            >
              Already have an account
            </Link>
            <span className="font-semibold text-ink-600">
              {requiresVerification ? "Email verification required" : "Local dev auto-verifies"}
            </span>
          </div>
        </form>
      </main>
    </div>
  );
}
