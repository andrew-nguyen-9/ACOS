export type ConfidenceLevel = "verified" | "strong_inference" | "weak_inference";

export interface HealthResponse {
  status: string;
  db: string;
  version: string;
}

export interface ResumeBullet {
  text: string;
  evidence_id: string;
  confidence: ConfidenceLevel;
}

export interface ResumeExperience {
  title: string;
  company: string;
  dates: string;
  bullets: ResumeBullet[];
}

export interface ResumeContent {
  experiences: ResumeExperience[];
  skills: string[];
  projects: Array<{ name: string; description?: string; tech?: string }>;
  education: Array<{ degree: string; school: string; dates?: string }>;
}

export interface ResumeGenerateRequest {
  job_description: string;
  template_name?: string;
  application_id?: string;
}

export interface ResumeGenerateResponse {
  resume_id: string;
  content_json: ResumeContent;
  ats_score: {
    overall_score: number;
    keyword_score: number;
    skill_score: number;
    matched_keywords: string[];
    missing_keywords: string[];
  };
  weak_inference_count: number;
  requires_approval: boolean;
}

export interface Application {
  id: string;
  company: string;
  role: string;
  status: string;
  date_applied: string | null;
  notes: string | null;
  job_description: string | null;
  created_at: string;
  updated_at: string;
}

export interface ApplicationCreate {
  company: string;
  role: string;
  status?: string;
  date_applied?: string;
  notes?: string;
  job_description?: string;
}

export interface CopilotChatRequest {
  message: string;
  conversation_history?: Array<{ role: string; content: string }>;
}

export interface CopilotChatResponse {
  response: string;
  intent: string;
  confidence: ConfidenceLevel;
  citations: Array<{
    source: string;
    text: string;
    confidence: ConfidenceLevel;
    similarity: number;
  }>;
  evidence_count: number;
}

export interface LearningOutcome {
  question_id: string;
  application_id: string;
  outcome: "correct" | "incorrect" | "skipped";
  time_spent_seconds?: number;
}

export interface GeneratedQuestion {
  id: string;
  question_text: string;
  question_type: string;
  difficulty: string;
  application_id: string;
  created_at: string;
}
