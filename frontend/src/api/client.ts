import {
  AuthResponse,
  Document,
  Page,
  Question,
  Answer,
  DocumentGroup,
  ReviewItems,
  QuestionUpdateRequest,
} from '../types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

class ApiClient {
  private token: string | null = null;
  private userEmail: string | null = null;

  constructor() {
    this.token = localStorage.getItem('docintel_token');
    this.userEmail = localStorage.getItem('docintel_user_email');
  }

  public setToken(token: string, email?: string) {
    this.token = token;
    localStorage.setItem('docintel_token', token);
    if (email) {
      this.userEmail = email;
      localStorage.setItem('docintel_user_email', email);
    }
  }

  public clearToken() {
    this.token = null;
    this.userEmail = null;
    localStorage.removeItem('docintel_token');
    localStorage.removeItem('docintel_user_email');
  }

  public getToken(): string | null {
    return this.token;
  }

  public getUserEmail(): string | null {
    return this.userEmail;
  }

  public isAuthenticated(): boolean {
    return !!this.token;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const headers: Record<string, string> = {
      ...(options.headers as Record<string, string>),
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    if (!(options.body instanceof FormData) && !headers['Content-Type']) {
      headers['Content-Type'] = 'application/json';
    }

    const res = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
    });

    if (res.status === 401) {
      this.clearToken();
      window.dispatchEvent(new Event('docintel-auth-logout'));
      throw new Error('Session expired or unauthorized. Please log in again.');
    }

    if (!res.ok) {
      let errMsg = `Request failed: ${res.status} ${res.statusText}`;
      try {
        const errorData = await res.json();
        if (errorData?.detail) {
          errMsg = typeof errorData.detail === 'string' ? errorData.detail : JSON.stringify(errorData.detail);
        }
      } catch {
        // fallback
      }
      throw new Error(errMsg);
    }

    // Return empty object for 204 or void responses
    if (res.status === 204) {
      return {} as T;
    }

    return res.json();
  }

  // --- Auth ---
  async register(email: string, password: string): Promise<{ id: string; email: string }> {
    return this.request('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
  }

  async login(email: string, password: string): Promise<AuthResponse> {
    const res = await this.request<AuthResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    this.setToken(res.access_token, email);
    return res;
  }

  // --- Documents ---
  async getDocuments(): Promise<Document[]> {
    return this.request<Document[]>('/documents');
  }

  async getDocument(id: string): Promise<Document> {
    return this.request<Document>(`/documents/${id}`);
  }

  async uploadDocument(file: File): Promise<{ id: string; status: string }> {
    const formData = new FormData();
    formData.append('file', file);
    return this.request<{ id: string; status: string }>('/documents', {
      method: 'POST',
      body: formData,
    });
  }

  async getDocumentPages(id: string): Promise<Page[]> {
    return this.request<Page[]>(`/documents/${id}/pages`);
  }

  getPageImageUrl(documentId: string, pageNumber: number): string {
    return `${API_BASE}/documents/${documentId}/pages/${pageNumber}/image`;
  }

  async fetchPageImageBlob(documentId: string, pageNumber: number): Promise<string> {
    const res = await fetch(this.getPageImageUrl(documentId, pageNumber), {
      headers: this.token ? { Authorization: `Bearer ${this.token}` } : {},
    });
    if (!res.ok) {
      throw new Error('Failed to load page image');
    }
    const blob = await res.blob();
    return URL.createObjectURL(blob);
  }

  // --- Questions ---
  async getDocumentQuestions(documentId: string): Promise<Question[]> {
    return this.request<Question[]>(`/documents/${documentId}/questions`);
  }

  async getQuestion(id: string): Promise<Question> {
    return this.request<Question>(`/questions/${id}`);
  }

  async updateQuestion(id: string, data: QuestionUpdateRequest): Promise<Question> {
    return this.request<Question>(`/questions/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  // --- Answers ---
  async getQuestionAnswer(questionId: string): Promise<Answer> {
    return this.request<Answer>(`/questions/${questionId}/answer`);
  }

  // --- Review Items ---
  async getDocumentReviewItems(documentId: string): Promise<ReviewItems> {
    return this.request<ReviewItems>(`/documents/${documentId}/review-items`);
  }

  // --- Document Groups ---
  async getGroups(): Promise<DocumentGroup[]> {
    return this.request<DocumentGroup[]>('/document-groups');
  }

  async createGroup(name: string): Promise<DocumentGroup> {
    return this.request<DocumentGroup>('/document-groups', {
      method: 'POST',
      body: JSON.stringify({ name }),
    });
  }

  async addDocumentToGroup(groupId: string, documentId: string): Promise<DocumentGroup> {
    return this.request<DocumentGroup>(`/document-groups/${groupId}/add`, {
      method: 'POST',
      body: JSON.stringify({ document_id: documentId }),
    });
  }
}

export const api = new ApiClient();
