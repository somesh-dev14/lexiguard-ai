import { useState, useEffect } from 'react';
import { api } from '../services/api';

export type BackendStatus = 'checking' | 'online' | 'offline';

export function useBackendStatus() {
  const [status, setStatus] = useState<BackendStatus>('checking');
  const [aiMode, setAiMode] = useState<string>('demo');
  const [message, setMessage] = useState('');

  useEffect(() => {
    let cancelled = false;
    const check = async () => {
      try {
        const health = await api.health();
        if (!cancelled) { setStatus('online'); setAiMode(health.ai_mode); setMessage(health.message); }
      } catch {
        if (!cancelled) { setStatus('offline'); setMessage('Backend not reachable. Start the FastAPI server on port 8000.'); }
      }
    };
    check();
    return () => { cancelled = true; };
  }, []);

  return { status, aiMode, message };
}
