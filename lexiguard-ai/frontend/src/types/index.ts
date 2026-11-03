export type RiskSeverity = 'low' | 'medium' | 'high' | 'critical';
export type DocumentStatus = 'uploading' | 'processing' | 'ready' | 'error' | 'demo';
export type AIMode = 'demo' | 'ai';

export interface PageText {
  page_number: number;
  text: string;
  word_count: number;
  char_count: number;
}

export interface Document {
  id: string;
  filename: string;
  uploadedAt: string;
  status: DocumentStatus;
  page_count: number;
  word_count: number;
  char_count: number;
  has_text: boolean;
  scanned_warning: boolean;
  demo_mode: boolean;
  pages?: PageText[];
}

export interface Clause {
  id: string;
  heading: string;
  original_heading?: string;
  predicted_category?: string;
  type: string;
  text: string;
  page?: number;
  page_start?: number;
  page_end?: number;
  page_span?: string;
  demo?: boolean;
}

export interface RiskPriorityBreakdown {
  priority_score: number;
  priority_tier: 'URGENT' | 'HIGH' | 'MODERATE' | 'LOW';
  factors: {
    severity: { weight: number; score: number; rating: string };
    financial_exposure: { weight: number; score: number; rationale: string };
    obligation_asymmetry: { weight: number; score: number; rationale: string };
    evidence_confidence: { multiplier: number; rationale: string };
  };
  formula: string;
}

export type FindingCategory = 'contractual_defect' | 'negotiation_point' | 'informational';

export interface Risk {
  id: string;
  severity: RiskSeverity;
  finding_category?: FindingCategory;
  title: string;
  clause?: string;
  explanation: string;
  relevantText?: string;
  page?: number;
  page_start?: number;
  page_end?: number;
  page_span?: string;
  impact?: string;
  suggestion?: string;
  demo?: boolean;
  evidence_unverified?: boolean;
  priority_score?: number;
  priority_tier?: 'URGENT' | 'HIGH' | 'MODERATE' | 'LOW';
  priority_breakdown?: RiskPriorityBreakdown;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: { page: number; excerpt: string }[];
  timestamp: string;
  demo?: boolean;
  error?: boolean;
}

export interface AnalysisData {
  document_id: string;
  demo_mode: boolean;
  disclaimer?: string;
  summary: {
    overview: string;
    contract_type: string;
    parties: string[];
    effective_date: string;
    duration: string;
    key_obligations: string[];
  };
  clauses: Clause[];
  risks: Risk[];
}

export interface UploadResponse {
  document_id: string;
  filename: string;
  page_count: number;
  word_count: number;
  char_count: number;
  status: string;
  has_text: boolean;
  scanned_warning: boolean;
  demo_mode: boolean;
  message: string;
}
