export type DocumentStatus = 'pending' | 'processing' | 'done' | 'failed';
export type DocumentRole = 'question_paper' | 'answer_key' | 'unknown';
export type QuestionStatus = 'extracted' | 'partial' | 'needs_review' | 'approved' | 'rejected';

export interface User {
  id: string;
  email: string;
  created_at?: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
}

export interface Document {
  id: string;
  filename: string;
  file_type: string;
  status: DocumentStatus;
  doc_role: DocumentRole;
  group_id?: string | null;
  created_at: string;
  pages_count?: number;
  questions_count?: number;
}

export interface Page {
  id: string;
  document_id: string;
  page_number: number;
  raw_text?: string;
  image_path?: string;
  image_url?: string;
  created_at?: string;
}

export interface Question {
  id: string;
  document_id: string;
  question_number?: number | null;
  question_text: string;
  options?: Record<string, string> | string[] | null;
  question_type?: string;
  source_pages?: number[];
  confidence_score: number;
  status: QuestionStatus;
  created_at?: string;
}

export interface Answer {
  id: string;
  question_id?: string | null;
  raw_answer_text: string;
  matched: boolean;
  confidence_score: number;
  source_document_id?: string | null;
  created_at?: string;
}

export interface DocumentGroup {
  id: string;
  owner_id: string;
  name: string;
  created_at: string;
  documents?: Document[];
}

export interface ReviewItems {
  document_id: string;
  review_questions: Question[];
  unmatched_answers: Answer[];
  total_review_items: number;
}

export interface QuestionUpdateRequest {
  question_number?: number;
  question_text?: string;
  options?: Record<string, string> | string[];
  question_type?: string;
  status?: QuestionStatus;
}
