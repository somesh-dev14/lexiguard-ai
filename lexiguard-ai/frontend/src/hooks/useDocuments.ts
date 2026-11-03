import { useState, useCallback } from 'react';
import { api } from '../services/api';
import type { Document } from '../types';
import { SAMPLE_DOCUMENTS } from '../data/sampleData';

const STORAGE_KEY = 'lexiguard_documents';

function loadDocuments(): Document[] {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) return JSON.parse(stored);
  } catch {}
  return [...SAMPLE_DOCUMENTS];
}

function saveDocuments(docs: Document[]) {
  try {
    const safe = docs.map(({ pages: _p, ...rest }) => rest);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(safe));
  } catch {}
}

export function useDocuments() {
  const [documents, setDocuments] = useState<Document[]>(loadDocuments);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const uploadDocument = useCallback(async (file: File): Promise<Document> => {
    setUploading(true);
    setUploadProgress(0);
    setError(null);
    try {
      const response = await api.uploadDocument(file, pct => setUploadProgress(pct));
      let pages: any[] = [];
      try {
        const pagesData = await api.getDocumentPages(response.document_id);
        pages = pagesData.pages || [];
      } catch {
        pages = [];
      }

      const doc: Document = {
        id: response.document_id,
        filename: response.filename,
        uploadedAt: new Date().toISOString(),
        status: 'ready',
        page_count: response.page_count,
        word_count: response.word_count,
        char_count: response.char_count,
        has_text: response.has_text,
        scanned_warning: response.scanned_warning,
        demo_mode: response.demo_mode,
        pages,
      };
      setDocuments(prev => {
        const updated = [doc, ...prev];
        saveDocuments(updated);
        return updated;
      });
      return doc;
    } catch (err: any) {
      const message = err instanceof Error ? err.message : 'Upload failed';
      setError(message);
      throw err;
    } finally {
      setUploading(false);
    }
  }, []);

  const deleteDocument = useCallback(async (documentId: string) => {
    try {
      await api.deleteDocument(documentId);
    } catch {}
    setDocuments(prev => {
      const updated = prev.filter(d => d.id !== documentId);
      saveDocuments(updated);
      return updated;
    });
  }, []);

  const getDocumentById = useCallback((id: string) => {
    return documents.find(d => d.id === id);
  }, [documents]);

  const fetchDocumentById = useCallback(async (id: string): Promise<Document | null> => {
    const existing = documents.find(d => d.id === id);
    if (existing) return existing;

    try {
      const fetched = await api.getDocument(id);
      setDocuments(prev => {
        if (prev.some(d => d.id === id)) return prev;
        const updated = [fetched, ...prev];
        saveDocuments(updated);
        return updated;
      });
      return fetched;
    } catch {
      return null;
    }
  }, [documents]);

  return {
    documents,
    uploading,
    isUploading: uploading,
    uploadProgress,
    error,
    uploadDocument,
    deleteDocument,
    getDocumentById,
    fetchDocumentById,
    clearError: () => setError(null),
  };
}
