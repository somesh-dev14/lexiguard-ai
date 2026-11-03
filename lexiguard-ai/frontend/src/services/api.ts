import type { Document, AnalysisData, UploadResponse } from '../types';

const API_BASE = '/api';

export const api = {
  async health(): Promise<{ status: string; version: string; ai_mode: string; message: string }> {
    const res = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(3000) });
    if (!res.ok) throw new Error('Health check failed');
    const data = await res.json();
    return {
      status: data.status,
      version: data.version,
      ai_mode: data.ai_mode,
      message: `LexiGuard AI API v${data.version} online`,
    };
  },

  async uploadDocument(
    file: File,
    onProgress?: (pct: number) => void
  ): Promise<UploadResponse> {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      const formData = new FormData();
      formData.append('file', file);

      xhr.upload.onprogress = (evt) => {
        if (evt.lengthComputable && onProgress) {
          const percent = Math.round((evt.loaded / evt.total) * 100);
          onProgress(percent);
        }
      };

      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            const data = JSON.parse(xhr.responseText);
            resolve({
              document_id: data.id,
              filename: data.filename,
              page_count: data.page_count,
              word_count: data.word_count,
              char_count: data.word_count * 6,
              status: data.status,
              has_text: data.word_count > 0,
              scanned_warning: data.word_count === 0,
              demo_mode: data.demo_mode,
              message: 'Processed successfully',
            });
          } catch (e) {
            reject(new Error('Invalid JSON response from server'));
          }
        } else {
          try {
            const err = JSON.parse(xhr.responseText);
            reject(new Error(err.detail || 'Upload failed'));
          } catch {
            reject(new Error(`Server error: ${xhr.statusText || xhr.status}`));
          }
        }
      };

      xhr.onerror = () => reject(new Error('Network error during upload'));
      xhr.ontimeout = () => reject(new Error('Upload timed out'));

      xhr.open('POST', `${API_BASE}/documents/upload`);
      xhr.send(formData);
    });
  },

  async getDocument(id: string): Promise<Document> {
    const res = await fetch(`${API_BASE}/documents/${id}`);
    if (!res.ok) throw new Error('Failed to fetch document');
    const data = await res.json();
    return {
      id: data.id,
      filename: data.filename,
      uploadedAt: data.uploadedAt,
      status: data.status,
      page_count: data.page_count,
      word_count: data.word_count,
      char_count: data.word_count * 6,
      has_text: data.word_count > 0,
      scanned_warning: data.word_count === 0,
      demo_mode: data.demo_mode,
      pages: data.pages,
    };
  },

  async getDocumentPages(id: string): Promise<{ pages: any[] }> {
    const doc = await this.getDocument(id);
    return { pages: doc.pages || [] };
  },

  async getDocumentAnalysis(id: string): Promise<AnalysisData> {
    const res = await fetch(`${API_BASE}/documents/${id}/analysis`);
    if (!res.ok) {
      let detail = '';
      try {
        const errJson = await res.json();
        detail = errJson.detail || '';
      } catch {}
      throw new Error(detail || `Failed to fetch analysis (HTTP ${res.status})`);
    }
    return res.json();
  },

  async deleteDocument(id: string): Promise<{ success: boolean }> {
    const res = await fetch(`${API_BASE}/documents/${id}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('Failed to delete document');
    return res.json();
  },

  async chatWithDocument(
    docId: string,
    question: string
  ): Promise<{ answer: string; sources: { page: number; excerpt: string; excerpt_verified?: boolean }[]; demo_mode: boolean; error?: boolean }> {
    const res = await fetch(`${API_BASE}/documents/${docId}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
    });
    if (!res.ok) {
      let detail = '';
      try {
        const errJson = await res.json();
        detail = errJson.detail || '';
      } catch {}
      throw new Error(detail || `Chat request failed (HTTP ${res.status})`);
    }
    return res.json();
  },
};
