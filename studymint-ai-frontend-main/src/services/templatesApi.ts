import type { Template } from "../types";
import { apiRequest } from "./apiClient";

export async function listTemplates(): Promise<Template[]> {
  return apiRequest<Template[]>("/templates");
}
