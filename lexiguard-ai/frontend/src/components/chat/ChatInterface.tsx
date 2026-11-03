import React, { useState } from 'react';
import type { ChatMessage, PageText } from '../../types';
import { Send, Bot, User, HelpCircle, FileText, AlertCircle } from 'lucide-react';
import { SUGGESTED_QUESTIONS } from '../../data/sampleData';
import { Badge } from '../ui/Badge';
import { api } from '../../services/api';

interface ChatInterfaceProps {
  documentId?: string;
  pages?: PageText[];
  pageCount?: number;
  onNavigateToSource?: (page: number) => void;
}

export function ChatInterface({ documentId, pages, pageCount, onNavigateToSource }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'm1',
      role: 'assistant',
      content: documentId
        ? 'Hello. I can answer questions grounded in the extracted text of this agreement. What would you like to verify?'
        : 'No document is loaded. Please upload a document first to ask questions about it.',
      timestamp: new Date().toISOString(),
    },
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);

  const handleSend = async (textToSend?: string) => {
    const q = textToSend || input;
    if (!q.trim()) return;

    const userMsg: ChatMessage = {
      id: String(Date.now()),
      role: 'user',
      content: q,
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMsg]);
    if (!textToSend) setInput('');
    setIsTyping(true);

    // If no document is loaded, show an error
    if (!documentId) {
      const errorMsg: ChatMessage = {
        id: String(Date.now() + 1),
        role: 'assistant',
        content: 'No document is loaded. Please navigate to an uploaded document to ask questions.',
        timestamp: new Date().toISOString(),
      };
      setMessages(prev => [...prev, errorMsg]);
      setIsTyping(false);
      return;
    }

    try {
      const result = await api.chatWithDocument(documentId, q);

      // Validate sources: only include pages that exist in the document
      const maxPage = pageCount || (pages ? pages.length : 0);
      const validSources = (result.sources || []).filter(
        (s) => s.page >= 1 && s.page <= maxPage
      );

      const botMsg: ChatMessage = {
        id: String(Date.now() + 1),
        role: 'assistant',
        content: result.answer,
        timestamp: new Date().toISOString(),
        demo: result.demo_mode === true,
        sources: validSources,
      };
      setMessages(prev => [...prev, botMsg]);
    } catch (err: any) {
      const errorMessage = err instanceof Error ? err.message : 'An unexpected error occurred';
      const errorMsg: ChatMessage = {
        id: String(Date.now() + 1),
        role: 'assistant',
        content: `⚠️ Failed to get an answer: ${errorMessage}\n\nPlease check that the AI backend is running and try again.`,
        timestamp: new Date().toISOString(),
        error: true,
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className="flex flex-col h-[600px] bg-white rounded-2xl border border-gray-200 overflow-hidden">
      <div className="flex-1 p-4 sm:p-6 overflow-y-auto space-y-4">
        {messages.map((m) => (
          <div
            key={m.id}
            className={`flex items-start gap-3 ${m.role === 'user' ? 'flex-row-reverse' : ''}`}
          >
            <div
              className={`w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 ${
                m.role === 'user' ? 'bg-blue-600 text-white' : (m as any).error ? 'bg-red-500 text-white' : 'bg-gray-900 text-white'
              }`}
            >
              {m.role === 'user' ? <User className="w-4 h-4" /> : (m as any).error ? <AlertCircle className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
            </div>

            <div
              className={`max-w-[80%] rounded-2xl p-4 text-sm ${
                m.role === 'user'
                  ? 'bg-blue-600 text-white rounded-tr-none'
                  : (m as any).error
                    ? 'bg-red-50 text-red-800 border border-red-200 rounded-tl-none'
                    : 'bg-gray-50 text-gray-800 border border-gray-100 rounded-tl-none'
              }`}
            >
              <div className="flex items-center justify-between gap-4 mb-1">
                <span className="text-[10px] opacity-70">
                  {new Date(m.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
                {m.demo && <Badge variant="demo">Demo Mode</Badge>}
                {(m as any).error && <Badge variant="error">Error</Badge>}
              </div>

              <p className="leading-relaxed whitespace-pre-wrap">{m.content}</p>

              {m.sources && m.sources.length > 0 && (
                <div className="mt-3 pt-3 border-t border-gray-200/50 space-y-2">
                  <span className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider block">
                    Citations & Evidence
                  </span>
                  {m.sources.map((ref, idx) => (
                    <div
                      key={idx}
                      className="p-2 bg-white/70 rounded-lg text-xs text-gray-700 border border-gray-200/60"
                    >
                      <div className="flex items-center justify-between text-blue-600 font-medium mb-0.5">
                        <span className="flex items-center gap-1">
                          <FileText className="w-3 h-3" /> Page {ref.page}
                        </span>
                        {onNavigateToSource && (
                          <button
                            onClick={() => onNavigateToSource(ref.page)}
                            className="hover:underline text-[11px]"
                          >
                            Jump to page
                          </button>
                        )}
                      </div>
                      <p className="italic text-gray-500 text-[11px]">"{ref.excerpt}"</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}

        {isTyping && (
          <div className="flex items-center gap-2 text-xs text-gray-400 italic pl-11">
            <span className="inline-block w-2 h-2 rounded-full bg-gray-400 animate-pulse" />
            LexiGuard is analyzing document context...
          </div>
        )}
      </div>

      <div className="p-3 bg-gray-50/60 border-t border-gray-100 flex items-center gap-2 overflow-x-auto">
        <HelpCircle className="w-4 h-4 text-gray-400 flex-shrink-0" />
        <span className="text-xs text-gray-400 whitespace-nowrap">Suggested:</span>
        {SUGGESTED_QUESTIONS.slice(0, 3).map((sq, i) => (
          <button
            key={i}
            onClick={() => handleSend(sq)}
            disabled={isTyping}
            className="px-2.5 py-1 bg-white border border-gray-200 rounded-lg text-xs text-gray-600 hover:bg-gray-100 whitespace-nowrap transition-colors disabled:opacity-50"
          >
            {sq}
          </button>
        ))}
      </div>

      <div className="p-3 bg-white border-t border-gray-200 flex items-center gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && !isTyping && handleSend()}
          placeholder="Ask a question about this contract..."
          className="flex-1 px-4 py-2.5 rounded-xl border border-gray-200 text-sm focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
          disabled={isTyping}
        />
        <button
          onClick={() => handleSend()}
          disabled={!input.trim() || isTyping}
          className="p-2.5 bg-gray-900 text-white rounded-xl hover:bg-gray-800 disabled:opacity-40 transition-colors"
        >
          <Send className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
