export type Role = "USER" | "TENANT_ADMIN" | "SUPER_ADMIN";

export type DocumentStatus =
  | "DRAFT"
  | "GENERATING"
  | "READY_FOR_REVIEW"
  | "PDF_READY"
  | "MARKETPLACE_READY"
  | "ARCHIVED";

export type DocumentType =
  | "Study Notes"
  | "Summary"
  | "Exam Prep"
  | "Question Bank"
  | "Q&A Guide"
  | "Study Guide"
  | "Flashcard Pack";

export type TargetPlatform = "Stuvia" | "Docsity/DocCity" | "Other";

export type LengthOption = "Short" | "Medium" | "Long";
export type GenerationMode = "SOURCE_GROUNDED" | "GENERAL_KNOWLEDGE_DRAFT";
export type DifficultyMode =
  | "Mixed"
  | "Foundational"
  | "Intermediate"
  | "Advanced";
export type GenerationJobStatus = "QUEUED" | "RUNNING" | "COMPLETED" | "FAILED";
export type StuviaAgentStatus = "QUEUED" | "RUNNING" | "COMPLETED" | "FAILED";
export type StuviaAgentPublishMode =
  | "drafts_only"
  | "n8n_review"
  | "n8n_auto_publish"
  | "manual_publish";

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: Role;
  tenant_id: string;
  email_verified: boolean;
}

export interface Tenant {
  id: string;
  name: string;
  slug: string;
  plan: string;
}

export interface Template {
  id: string;
  name: string;
  description: string;
  page_size: string;
  font_settings: Record<string, unknown>;
  cover_style: string;
  section_style: string;
  footer_settings: Record<string, unknown>;
  is_active: boolean;
}

export interface DocumentSection {
  id: string;
  title: string;
  body: string;
}

export interface QuestionOption {
  label: "A" | "B" | "C" | "D";
  text: string;
}

export interface QuestionItem {
  number: number;
  category: string;
  learning_objective: string;
  difficulty: "foundational" | "intermediate" | "advanced";
  question_type:
    | "conceptual"
    | "application"
    | "clinical_scenario"
    | "case_scenario"
    | "calculation"
    | "definition";
  stem: string;
  options: QuestionOption[];
  correct_option: "A" | "B" | "C" | "D";
  rationale: string;
  source_refs: string[];
  review_flags: string[];
}

export interface QualitySummary {
  requested_question_count?: number;
  generated_question_count?: number;
  duplicate_questions_rejected?: number;
  questions_repaired?: number;
  generation_mode?: GenerationMode;
  review_required?: boolean;
  issue_codes?: string[];
}

export interface DocumentVersion {
  id: string;
  version_number: number;
  content: {
    title_page: string;
    introduction: string;
    sections: DocumentSection[];
    key_points: string[];
    examples: string[];
    study_questions: string[];
    conclusion: string;
    metadata?: {
      display_title?: string;
      topic_label?: string;
      generation_mode?: GenerationMode;
      review_required?: boolean;
      quality_summary?: QualitySummary;
      blueprint?: unknown;
    };
    question_bank?: QuestionItem[];
  };
  created_at: string;
}

export interface StudyDocument {
  id: string;
  title: string;
  subject: string;
  education_level: string;
  document_type: DocumentType;
  target_platform: TargetPlatform;
  output_language: string;
  length: LengthOption;
  status: DocumentStatus;
  template_id?: string;
  tenant_id: string;
  owner_id: string;
  created_at: string;
  updated_at: string;
  latest_version?: DocumentVersion;
  generation_time_seconds?: number | null;
}

export interface DocumentCreateInput {
  title: string;
  subject: string;
  education_level: string;
  document_type: DocumentType;
  target_platform: TargetPlatform;
  output_language: string;
  length: LengthOption;
  template_id?: string;
  question_count?: number;
  generation_mode: GenerationMode;
  user_instructions?: string;
  source_notes?: string;
  difficulty: DifficultyMode;
  speed_mode?: boolean;
}

export interface GenerationJob {
  job_id: string;
  status: GenerationJobStatus;
  stage: string;
  stage_label: string;
  message: string;
  progress: number;
  document_id?: string | null;
  error?: string | null;
  created_at: string;
  updated_at: string;
}

export interface DashboardStats {
  total_documents: number;
  drafts: number;
  pdfs_exported: number;
  marketplace_ready: number;
  ai_credits_used: number;
}

export interface PdfExport {
  id: string;
  document_id: string;
  status: "PENDING" | "COMPLETED" | "FAILED";
  pdf_url: string;
  created_at: string;
}

export interface StuviaAgentRunInput {
  profile_url: string;
  manual_topics: string[];
  max_topics: number;
  question_count: number;
  concurrency: number;
  education_level: string;
  document_type: DocumentType;
  output_language: string;
  length: LengthOption;
  template_id?: string;
  generation_mode: GenerationMode;
  user_instructions?: string;
  source_notes?: string;
  difficulty: DifficultyMode;
  publish_mode: StuviaAgentPublishMode;
  reset_topic_history?: boolean;
}

export interface StuviaAgentTopic {
  title: string;
  topic: string;
  source_url: string;
  score: number;
  reason: string;
}

export interface StuviaAgentListing {
  title: string;
  topic: string;
  document_id?: string | null;
  document_url?: string | null;
  status: string;
  error?: string | null;
  attempts?: number;
  publish_status?: string | null;
  stuvia_url?: string | null;
}

export interface StuviaAgentRun {
  run_id: string;
  status: StuviaAgentStatus;
  stage: string;
  stage_label: string;
  message: string;
  progress: number;
  profile_url: string;
  publish_mode: StuviaAgentPublishMode;
  topics: StuviaAgentTopic[];
  listings: StuviaAgentListing[];
  n8n_status?: string | null;
  error?: string | null;
  created_at: string;
  updated_at: string;
}

export interface StuviaManualPublishResponse {
  document_id: string;
  status: string;
  message: string;
  n8n_status: string;
}

export interface IntegrationCard {
  id: string;
  name: string;
  status: string;
  description: string;
  required_fields: string[];
}

export interface StuviaIntegrationConfig {
  provider: "stuvia";
  status: string;
  connected: boolean;
  automation_ready: boolean;
  stuvia_email: string;
  stuvia_password_configured: boolean;
  n8n_webhook_url: string;
  n8n_app_url: string;
  n8n_webhook_token_configured: boolean;
  stuvia_credential_name: string;
  browser_publisher_url: string;
  auto_publish_enabled: boolean;
  credential_storage: "backend_encrypted" | "n8n";
}

export interface StuviaIntegrationConfigUpdate {
  stuvia_email: string;
  stuvia_password?: string | null;
  n8n_webhook_url?: string | null;
  n8n_app_url?: string | null;
  n8n_webhook_token?: string | null;
  stuvia_credential_name?: string | null;
  browser_publisher_url?: string | null;
  auto_publish_enabled: boolean;
}
