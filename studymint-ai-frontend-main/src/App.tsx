import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import type { ReactNode } from "react";
import { AppShell } from "./components/layout/AppShell";
import { useAuth } from "./contexts/AuthContext";
import { AdminPage } from "./pages/AdminPage";
import { DashboardPage } from "./pages/DashboardPage";
import { DocumentStudioPage } from "./pages/DocumentStudioPage";
import { DocumentsPage } from "./pages/DocumentsPage";
import { ForgotPasswordPage } from "./pages/ForgotPasswordPage";
import { IntegrationsPage } from "./pages/IntegrationsPage";
import { LoginPage } from "./pages/LoginPage";
import { NewDocumentPage } from "./pages/NewDocumentPage";
import { PdfPreviewPage } from "./pages/PdfPreviewPage";
import { RegisterPage } from "./pages/RegisterPage";
import { ResetPasswordPage } from "./pages/ResetPasswordPage";
import { StuviaAgentPage } from "./pages/StuviaAgentPage";
import { TemplatesPage } from "./pages/TemplatesPage";
import { VerifyEmailPage } from "./pages/VerifyEmailPage";

function ProtectedRoute({ children, adminOnly = false }: { children: ReactNode; adminOnly?: boolean }) {
  const { user, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return <div className="flex min-h-screen items-center justify-center bg-[#f2f5f1] text-sm font-semibold text-ink-700">Loading StudyMint AI...</div>;
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (adminOnly && user.role !== "SUPER_ADMIN") {
    return <Navigate to="/dashboard" replace />;
  }

  return <AppShell>{children}</AppShell>;
}

export function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/verify-email" element={<VerifyEmailPage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <DashboardPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/documents"
        element={
          <ProtectedRoute>
            <DocumentsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/documents/new"
        element={
          <ProtectedRoute>
            <NewDocumentPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/documents/:id/studio"
        element={
          <ProtectedRoute>
            <DocumentStudioPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/documents/:id/pdf"
        element={
          <ProtectedRoute>
            <PdfPreviewPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/templates"
        element={
          <ProtectedRoute>
            <TemplatesPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/integrations"
        element={
          <ProtectedRoute>
            <IntegrationsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/agent"
        element={
          <ProtectedRoute>
            <StuviaAgentPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin"
        element={
          <ProtectedRoute adminOnly>
            <AdminPage />
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}
