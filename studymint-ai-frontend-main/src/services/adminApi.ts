import { apiRequest } from "./apiClient";
import type { User } from "../types";

export interface AdminOverview {
  users: number;
  active_users: number;
  unverified_users: number;
  admin_users: number;
  super_admins: number;
  tenants: number;
  generated_documents: number;
  ai_usage_events: number;
  audit_events: number;
  recent_users: User[];
}

export async function getAdminOverview(): Promise<AdminOverview> {
  return apiRequest<AdminOverview>("/admin/overview");
}
