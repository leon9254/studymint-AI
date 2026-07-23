import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowLeft,
  CheckCircle2,
  KeyRound,
  Mail,
} from "lucide-react";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { requestPasswordReset } from "../services/authApi";

const recoverySteps = [
  "Enter the email on your StudyMint AI account",
  "Open the secure reset link from your inbox",
  "Create a new password and continue your work",
];

export function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setSent(false);
    setIsSubmitting(true);

    try {
      await requestPasswordReset(email);
      setSent(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to send reset link");
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
              Account access
            </span>
            <h1 className="mt-4 max-w-full break-words text-3xl font-semibold leading-tight tracking-normal text-ink-950 sm:max-w-xl sm:text-4xl">
              Reset your password and get back to your documents.
            </h1>
            <p className="mt-4 max-w-full break-words text-base leading-7 text-ink-700 sm:max-w-xl">
              We will send a secure link you can use to create a new password
              and return to your study document workflow.
            </p>
          </div>

          <div className="mt-7 grid gap-3">
            {recoverySteps.map((step, index) => (
              <div
                key={step}
                className="flex min-w-0 items-center gap-3 rounded-lg border border-ink-200 bg-ink-50 p-3"
              >
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-white text-sm font-semibold text-mint-800 ring-1 ring-mint-200">
                  {index + 1}
                </div>
                <span className="min-w-0 break-words text-sm font-semibold text-ink-900">
                  {step}
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
              <Mail size={19} />
            </div>
            <div className="min-w-0">
              <h2 className="text-2xl font-semibold tracking-normal text-ink-950">
                Password recovery
              </h2>
              <p className="text-sm font-medium text-ink-600">
                Request a secure reset link.
              </p>
            </div>
          </div>

          <div className="mt-6">
            <Input
              label="Email"
              type="email"
              autoComplete="email"
              placeholder="you@example.com"
              value={email}
              onChange={(event) => {
                setEmail(event.target.value);
                setSent(false);
              }}
              required
            />
          </div>

          {error && (
            <p className="mt-4 rounded-lg border border-red-300 bg-red-50 px-3 py-2.5 text-sm leading-6 text-red-800">
              {error}
            </p>
          )}

          <Button className="mt-6 w-full" size="lg" disabled={isSubmitting}>
            {isSubmitting ? "Sending reset link..." : "Send reset link"}
          </Button>

          <div className="mt-5 rounded-lg border border-ink-200 bg-ink-50 px-3.5 py-3">
            <div className="flex items-center gap-2 text-sm font-semibold text-ink-950">
              <CheckCircle2 size={15} className="text-mint-700" />
              {sent ? "Check your inbox" : "Reset link delivery"}
            </div>
            <p className="mt-1 text-sm leading-6 text-ink-700">
              {sent
                ? "If an account exists for that email, a secure reset link has been sent."
                : "For account privacy, we show the same confirmation whether or not the email is registered."}
            </p>
          </div>
        </form>
      </main>
    </div>
  );
}
