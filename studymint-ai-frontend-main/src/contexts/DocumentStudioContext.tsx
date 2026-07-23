import { createContext, useContext, useMemo, useReducer } from "react";
import type { ReactNode } from "react";
import type { DocumentCreateInput, DocumentSection, StudyDocument } from "../types";

interface StudioState {
  document: StudyDocument | null;
  settings: Partial<DocumentCreateInput>;
  sections: DocumentSection[];
  selectedSectionId: string | null;
  isPreparingPdf: boolean;
}

type StudioAction =
  | { type: "LOAD_DOCUMENT"; document: StudyDocument }
  | { type: "SELECT_SECTION"; sectionId: string }
  | { type: "UPDATE_SECTION"; sectionId: string; body: string }
  | { type: "APPLY_AI_ACTION"; action: string }
  | { type: "SET_PREPARING_PDF"; value: boolean };

interface StudioContextValue extends StudioState {
  loadDocument: (document: StudyDocument) => void;
  selectSection: (sectionId: string) => void;
  updateSection: (sectionId: string, body: string) => void;
  applyAiAction: (action: string) => void;
  setPreparingPdf: (value: boolean) => void;
}

const StudioContext = createContext<StudioContextValue | undefined>(undefined);

function transformBody(body: string, action: string): string {
  const additions: Record<string, string> = {
    "Regenerate section": "\n\nRegenerated draft: Reframe this section with a clearer topic sentence, original explanation, and concise study takeaway.",
    "Make more detailed": "\n\nAdditional detail: Expand this concept with definitions, cause-and-effect links, and a short revision note.",
    "Simplify wording": "\n\nSimplified version: Use shorter sentences and explain specialist terms before applying them.",
    "Add examples": "\n\nExample: Add a practical learner-friendly scenario that shows how the concept is used.",
    "Improve formatting": "\n\nFormatting note: Convert long paragraphs into concise bullets and add a checkpoint question.",
    "Add study questions": "\n\nStudy questions:\n1. What is the main idea in this section?\n2. How would you explain it using a course example?",
    "Prepare for PDF": "\n\nPDF readiness: Check headings, originality, citations, examples, and section flow before export."
  };

  return `${body}${additions[action] ?? ""}`;
}

function studioReducer(state: StudioState, action: StudioAction): StudioState {
  switch (action.type) {
    case "LOAD_DOCUMENT": {
      const sections = action.document.latest_version?.content.sections ?? [];
      return {
        document: action.document,
        settings: {
          title: action.document.title,
          subject: action.document.subject,
          education_level: action.document.education_level,
          document_type: action.document.document_type,
          target_platform: action.document.target_platform,
          output_language: action.document.output_language,
          length: action.document.length,
          template_id: action.document.template_id
        },
        sections,
        selectedSectionId: sections[0]?.id ?? null,
        isPreparingPdf: false
      };
    }
    case "SELECT_SECTION":
      return { ...state, selectedSectionId: action.sectionId };
    case "UPDATE_SECTION":
      return {
        ...state,
        sections: state.sections.map((section) => (section.id === action.sectionId ? { ...section, body: action.body } : section))
      };
    case "APPLY_AI_ACTION":
      if (!state.selectedSectionId) return state;
      return {
        ...state,
        sections: state.sections.map((section) =>
          section.id === state.selectedSectionId ? { ...section, body: transformBody(section.body, action.action) } : section
        ),
        isPreparingPdf: action.action === "Prepare for PDF" ? true : state.isPreparingPdf
      };
    case "SET_PREPARING_PDF":
      return { ...state, isPreparingPdf: action.value };
    default:
      return state;
  }
}

export function DocumentStudioProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(studioReducer, {
    document: null,
    settings: {},
    sections: [],
    selectedSectionId: null,
    isPreparingPdf: false
  });

  const value = useMemo<StudioContextValue>(
    () => ({
      ...state,
      loadDocument(document) {
        dispatch({ type: "LOAD_DOCUMENT", document });
      },
      selectSection(sectionId) {
        dispatch({ type: "SELECT_SECTION", sectionId });
      },
      updateSection(sectionId, body) {
        dispatch({ type: "UPDATE_SECTION", sectionId, body });
      },
      applyAiAction(action) {
        dispatch({ type: "APPLY_AI_ACTION", action });
      },
      setPreparingPdf(value) {
        dispatch({ type: "SET_PREPARING_PDF", value });
      }
    }),
    [state]
  );

  return <StudioContext.Provider value={value}>{children}</StudioContext.Provider>;
}

export function useDocumentStudio() {
  const context = useContext(StudioContext);
  if (!context) {
    throw new Error("useDocumentStudio must be used within DocumentStudioProvider");
  }
  return context;
}
