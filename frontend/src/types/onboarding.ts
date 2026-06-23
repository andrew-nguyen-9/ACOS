export type ConfidenceLevel = "verified" | "strong_inference" | "weak_inference";

export interface OnboardingSkill {
  label: string;
  confidence: ConfidenceLevel;
}

export interface CareerVoice {
  tone_descriptors: string[];
  structure_patterns: string[];
  sample_sentences: string[];
  /** true when this is the default template, not derived from the user's writing. */
  synthetic: boolean;
}

export interface OnboardingSummary {
  skills: OnboardingSkill[];
  documents: { count: number };
  career_voice: CareerVoice;
}

export type IngestStatus = "queued" | "processing" | "done" | "failed";

export interface IngestJob {
  job_id: string;
  status: IngestStatus;
  filename?: string;
  error?: string;
}
