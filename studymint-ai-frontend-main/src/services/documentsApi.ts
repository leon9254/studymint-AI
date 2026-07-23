import type { DashboardStats, DocumentCreateInput, GenerationJob, PdfExport, StudyDocument } from "../types";
import { apiRequest } from "./apiClient";

export async function getDashboardStats(): Promise<DashboardStats> {
  return apiRequest<DashboardStats>("/documents/stats");
}

export async function listDocuments(): Promise<StudyDocument[]> {
  return apiRequest<StudyDocument[]>("/documents");
}

export async function getDocument(id: string): Promise<StudyDocument> {
  return apiRequest<StudyDocument>(`/documents/${id}`);
}

export async function createDocument(input: DocumentCreateInput): Promise<StudyDocument> {
  return apiRequest<StudyDocument>("/documents", {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export async function startDocumentGeneration(input: DocumentCreateInput): Promise<GenerationJob> {
  return apiRequest<GenerationJob>("/documents/generation-jobs", {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export async function getGenerationJob(jobId: string): Promise<GenerationJob> {
  return apiRequest<GenerationJob>(`/documents/generation-jobs/${jobId}`);
}

export async function deleteDocument(id: string): Promise<void> {
  return apiRequest<void>(`/documents/${id}`, { method: "DELETE" });
}

export async function createPdfExport(documentId: string): Promise<PdfExport> {
  return apiRequest<PdfExport>(`/pdf-exports/documents/${documentId}`, { method: "POST" });
}
