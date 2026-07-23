import type { User } from "../types";
import { apiRequest } from "./apiClient";

interface AuthResponse {
  access_token: string;
  token_type: "bearer";
  user: User;
}

export interface RegistrationResponse {
  message: string;
  email: string;
  requires_email_verification: boolean;
}

export async function login(email: string, password: string): Promise<AuthResponse> {
  return apiRequest<AuthResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password })
  });
}

export async function register(payload: { full_name: string; email: string; password: string }): Promise<RegistrationResponse> {
  return apiRequest<RegistrationResponse>("/auth/register", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function verifyEmail(token: string): Promise<AuthResponse> {
  return apiRequest<AuthResponse>("/auth/verify-email", {
    method: "POST",
    body: JSON.stringify({ token })
  });
}

export async function resendVerification(email: string): Promise<void> {
  return apiRequest<void>("/auth/resend-verification", {
    method: "POST",
    body: JSON.stringify({ email })
  });
}

export async function requestPasswordReset(email: string): Promise<void> {
  return apiRequest<void>("/auth/forgot-password", {
    method: "POST",
    body: JSON.stringify({ email })
  });
}

export async function resetPassword(token: string, password: string): Promise<void> {
  return apiRequest<void>("/auth/reset-password", {
    method: "POST",
    body: JSON.stringify({ token, password })
  });
}

export async function getMe(): Promise<User> {
  return apiRequest<User>("/auth/me");
}
