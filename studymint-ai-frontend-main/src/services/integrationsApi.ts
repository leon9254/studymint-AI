import type { IntegrationCard, StuviaIntegrationConfig, StuviaIntegrationConfigUpdate } from "../types";
import { apiRequest } from "./apiClient";

export async function listIntegrations(): Promise<IntegrationCard[]> {
  return apiRequest<IntegrationCard[]>("/integrations");
}

export async function getStuviaIntegration(): Promise<StuviaIntegrationConfig> {
  return apiRequest<StuviaIntegrationConfig>("/integrations/stuvia");
}

export async function updateStuviaIntegration(input: StuviaIntegrationConfigUpdate): Promise<StuviaIntegrationConfig> {
  return apiRequest<StuviaIntegrationConfig>("/integrations/stuvia", {
    method: "PUT",
    body: JSON.stringify(input)
  });
}
