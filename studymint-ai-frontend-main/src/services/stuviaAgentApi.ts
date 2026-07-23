import type { StuviaAgentRun, StuviaAgentRunInput, StuviaManualPublishResponse } from "../types";
import { apiRequest } from "./apiClient";

export async function startStuviaAgentRun(input: StuviaAgentRunInput): Promise<StuviaAgentRun> {
  return apiRequest<StuviaAgentRun>("/stuvia-agent/runs", {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export async function getStuviaAgentRun(runId: string): Promise<StuviaAgentRun> {
  return apiRequest<StuviaAgentRun>(`/stuvia-agent/runs/${runId}`);
}

export async function publishStuviaDocument(documentId: string): Promise<StuviaManualPublishResponse> {
  return apiRequest<StuviaManualPublishResponse>(`/stuvia-agent/documents/${documentId}/publish`, {
    method: "POST"
  });
}
