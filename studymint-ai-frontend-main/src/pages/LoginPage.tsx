import {
  ArrowRight,
  CheckCircle2,
  FileText,
  LockKeyhole,
  Sparkles,
} from "lucide-react";
import { FormEvent, useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { PasswordInput } from "../components/ui/PasswordInput";
import { useAuth } from "../contexts/AuthContext";

const capabilities = [
  "Generate structured study guides from raw notes",
  "Apply PDF-ready templates without manual formatting",
  "Review, refine, and export documents from one workspace",
];

export function LoginPage() {
  const { user, login, isLoading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  if (user) {
    return <Navigate to="/dashboard" replace />;
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");

    try {
      await login(email, password);
      const target =
        (location.state as { from?: { pathname?: string } } | null)?.from
          ?.pathname ?? "/dashboard";
      navigate(target, { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to log in");
    }
  }

  return (
    <div className="min-h-screen overflow-x-hidden bg-[#f2f5f1] px-4 py-6 text-ink-950 sm:px-6 lg:px-8">
      <main className="mx-auto grid min-h-[calc(100vh-3rem)] w-full min-w-0 max-w-6xl grid-cols-1 items-center gap-6 lg:grid-cols-[minmax(0,1fr)_28rem]">
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
              Continue creating
            </span>
            <h1 className="mt-4 max-w-full break-words text-3xl font-semibold leading-tight tracking-normal text-ink-950 sm:max-w-2xl sm:text-5xl">
              Pick up your study document workflow exactly where you left it.
            </h1>
            <p className="mt-4 max-w-full break-words text-base leading-7 text-ink-700 sm:max-w-2xl">
              Draft stronger learning materials, preview professional PDF
              layouts, and move from idea to export with less formatting work.
            </p>
          </div>

          <div className="mt-7 grid gap-3 sm:grid-cols-3">
            {capabilities.map((item) => (
              <div
                key={item}
                className="min-w-0 rounded-lg border border-ink-200 bg-ink-50 p-4"
              >
                <CheckCircle2 size={18} className="text-mint-700" />
                <p className="mt-3 break-words text-sm font-semibold leading-5 text-ink-900">
                  {item}
                </p>
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
                Sign in
              </h2>
              <p className="text-sm font-medium text-ink-600">
                Continue building study documents.
              </p>
            </div>
          </div>

          <div className="mt-6 space-y-4">
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
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
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
            disabled={isLoading}
            icon={<ArrowRight size={17} />}
          >
            {isLoading ? "Signing in..." : "Sign in"}
          </Button>

          <div className="mt-5 flex flex-wrap items-center justify-between gap-3 text-sm">
            <Link
              className="font-semibold text-mint-800 transition hover:text-mint-700"
              to="/register"
            >
              Create account
            </Link>
            <Link
              className="inline-flex items-center gap-1.5 font-semibold text-ink-700 transition hover:text-ink-950"
              to="/forgot-password"
            >
              <LockKeyhole size={15} />
              Forgot password
            </Link>
          </div>
        </form>
      </main>
    </div>
  );
}
