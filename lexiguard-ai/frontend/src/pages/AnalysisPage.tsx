import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useDocuments } from '../hooks/useDocuments';
import { api } from '../services/api';
import { SAMPLE_ANALYSIS } from '../data/sampleData';
import { SummaryTab } from '../components/analysis/SummaryTab';
import { ClausesTab } from '../components/analysis/ClausesTab';
import { RiskTab } from '../components/analysis/RiskTab';
import { ChatInterface } from '../components/chat/ChatInterface';
import { SourceTab } from '../components/analysis/SourceTab';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { ArrowLeft, Download, FileText, ShieldAlert, AlertTriangle, MessageSquare, BookOpen, Loader2 } from 'lucide-react';
import { cn } from '../utils/cn';
import type { Document, AnalysisData } from '../types';

type ActiveTab = 'summary' | 'clauses' | 'risk' | 'chat' | 'source';

export function AnalysisPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { getDocumentById, fetchDocumentById } = useDocuments();

  const [activeTab, setActiveTab] = useState<ActiveTab>('summary');
  const [sourceTargetPage, setSourceTargetPage] = useState<number>(1);
  const [doc, setDoc] = useState<Document | null | undefined>(id ? getDocumentById(id) : undefined);
  const [analysisData, setAnalysisData] = useState<AnalysisData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [reloadCounter, setReloadCounter] = useState(0);

  useEffect(() => {
    let cancelled = false;

    async function loadData() {
      if (!id) {
        setLoading(false);
        setDoc(null);
        return;
      }

      setLoading(true);
      setAnalysisError(null);

      // 1. Get or fetch document
      let targetDoc = getDocumentById(id);
      if (!targetDoc) {
        targetDoc = await fetchDocumentById(id) || undefined;
      }

      if (cancelled) return;
      setDoc(targetDoc || null);

      // 2. Fetch analysis data if document exists
      if (targetDoc) {
        // If this is an explicit sample document (e.g. sample-001), use SAMPLE_ANALYSIS
        if (targetDoc.id.startsWith('sample-') || targetDoc.status === 'demo') {
          if (!cancelled) {
            setAnalysisData({
              ...SAMPLE_ANALYSIS,
              document_id: id,
              demo_mode: true,
            });
            setLoading(false);
          }
          return;
        }

        try {
          const remoteAnalysis = await api.getDocumentAnalysis(id);
          if (!cancelled) {
            setAnalysisData(remoteAnalysis);
          }
        } catch (err: any) {
          if (!cancelled) {
            setAnalysisError(err.message || 'Failed to generate contract analysis');
            setAnalysisData(null);
          }
        }
      }

      if (!cancelled) setLoading(false);
    }

    loadData();

    return () => {
      cancelled = true;
    };
  }, [id, reloadCounter, getDocumentById, fetchDocumentById]);

  const navigateToSource = (page: number) => {
    setSourceTargetPage(page);
    setActiveTab('source');
  };

  const handleRetry = () => {
    setReloadCounter(prev => prev + 1);
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-24 space-y-4">
        <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
        <p className="text-sm text-gray-500">Loading contract analysis...</p>
      </div>
    );
  }

  if (!doc) {
    return (
      <div className="text-center py-20 space-y-4">
        <h2 className="text-xl font-semibold text-gray-900">Document Not Found</h2>
        <p className="text-sm text-gray-500">The requested contract analysis does not exist or has been removed.</p>
        <Button onClick={() => navigate('/dashboard')}>Return to Dashboard</Button>
      </div>
    );
  }

  if (analysisError) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3 pb-4 border-b border-gray-200">
          <button
            onClick={() => navigate('/dashboard')}
            className="p-2 rounded-xl border border-gray-200 text-gray-500 hover:text-gray-900 hover:bg-gray-50 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <h1 className="text-xl font-bold text-gray-900 tracking-tight">{doc.filename}</h1>
            <p className="text-xs text-gray-400 mt-0.5">
              {doc.page_count} pages &middot; {doc.word_count.toLocaleString()} extracted words
            </p>
          </div>
        </div>

        <div className="bg-red-50 border border-red-200 rounded-2xl p-8 text-center max-w-xl mx-auto space-y-4 my-8">
          <div className="w-12 h-12 bg-red-100 text-red-600 rounded-2xl flex items-center justify-center mx-auto">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-red-900">Analysis Failed</h3>
            <p className="text-sm text-red-700 mt-1">{analysisError}</p>
          </div>
          <div className="flex items-center justify-center gap-3 pt-2">
            <Button variant="secondary" onClick={() => navigate('/dashboard')}>
              Return to Dashboard
            </Button>
            <Button onClick={handleRetry}>
              Retry Analysis
            </Button>
          </div>
        </div>
      </div>
    );
  }

  if (!analysisData) {
    return (
      <div className="text-center py-20 space-y-4">
        <h2 className="text-xl font-semibold text-gray-900">No Analysis Available</h2>
        <p className="text-sm text-gray-500">Analysis has not been processed for this contract yet.</p>
        <Button onClick={handleRetry}>Analyze Contract</Button>
      </div>
    );
  }

  const effectiveAnalysis = analysisData;

  const tabs = [
    { id: 'summary', label: 'Executive Summary', icon: FileText },
    { id: 'clauses', label: 'Key Clauses', icon: ShieldAlert },
    { id: 'risk', label: 'Risk Analysis', icon: AlertTriangle, count: effectiveAnalysis.risks.length },
    { id: 'chat', label: 'Ask Questions', icon: MessageSquare },
    { id: 'source', label: 'Source Document', icon: BookOpen },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 pb-4 border-b border-gray-200">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/dashboard')}
            className="p-2 rounded-xl border border-gray-200 text-gray-500 hover:text-gray-900 hover:bg-gray-50 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold text-gray-900 tracking-tight">{doc.filename}</h1>
              {doc.demo_mode && <Badge variant="demo">Demo Mode</Badge>}
            </div>
            <p className="text-xs text-gray-400 mt-0.5">
              {doc.page_count} pages &middot; {doc.word_count.toLocaleString()} extracted words
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="secondary" size="sm" onClick={() => window.print()}>
            <Download className="w-4 h-4" />
            Export Report
          </Button>
        </div>
      </div>

      <div className="flex items-center gap-2 border-b border-gray-200 overflow-x-auto">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as ActiveTab)}
              className={cn(
                'flex items-center gap-2 py-3 px-4 text-sm font-medium border-b-2 whitespace-nowrap transition-colors',
                isActive
                  ? 'border-gray-900 text-gray-900'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              )}
            >
              <Icon className="w-4 h-4" />
              <span>{tab.label}</span>
              {tab.count !== undefined && (
                <span className="text-[11px] bg-red-100 text-red-700 px-1.5 py-0.2 rounded-full font-bold">
                  {tab.count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      <div className="no-print">
        {activeTab === 'summary' && (
          <SummaryTab
            summary={effectiveAnalysis.summary}
            onNavigateToSource={navigateToSource}
            isDemo={Boolean(effectiveAnalysis.demo_mode)}
          />
        )}
        {activeTab === 'clauses' && (
          <ClausesTab clauses={effectiveAnalysis.clauses} onNavigateToSource={navigateToSource} />
        )}
        {activeTab === 'risk' && (
          <RiskTab risks={effectiveAnalysis.risks} onNavigateToSource={navigateToSource} />
        )}
        {activeTab === 'chat' && (
          <ChatInterface
            documentId={doc.id}
            pages={doc.pages}
            pageCount={doc.page_count}
            onNavigateToSource={navigateToSource}
          />
        )}
        {activeTab === 'source' && (
          <SourceTab
            pages={doc.pages && doc.pages.length > 0 ? doc.pages : [{ page_number: 1, text: 'No text extracted.', word_count: 0, char_count: 0 }]}
            initialPage={sourceTargetPage}
          />
        )}
      </div>

      {/* Complete Printable Report Rendered for Print / Save as PDF */}
      <div className="hidden print:block printable-report space-y-6 p-4">
        <div className="border-b pb-4 mb-4">
          <h1 className="text-2xl font-bold text-gray-900">LexiGuard AI — Legal Analysis Report</h1>
          <p className="text-sm text-gray-600 mt-1">
            Document: <strong>{doc.filename}</strong> &bull; {doc.page_count} Pages &bull; {doc.word_count.toLocaleString()} Words
            {effectiveAnalysis.demo_mode && ' (Demo Analysis)'}
          </p>
        </div>

        <section className="space-y-3">
          <h2 className="text-lg font-bold text-gray-900 border-b pb-1">1. Executive Summary</h2>
          <p className="text-sm text-gray-800 leading-relaxed">{effectiveAnalysis.summary.overview}</p>
          <div className="grid grid-cols-2 gap-4 text-xs mt-2">
            <div>
              <span className="font-semibold text-gray-500">Contract Type:</span>
              <p className="font-medium text-gray-800">{effectiveAnalysis.summary.contract_type || 'Commercial Agreement'}</p>
            </div>
            <div>
              <span className="font-semibold text-gray-500">Identified Parties:</span>
              <p className="font-medium text-gray-800">{effectiveAnalysis.summary.parties.join(', ')}</p>
            </div>
            <div>
              <span className="font-semibold text-gray-500">Effective Date:</span>
              <p className="font-medium text-gray-800">{effectiveAnalysis.summary.effective_date || 'Not explicitly specified'}</p>
            </div>
            <div>
              <span className="font-semibold text-gray-500">Duration / Term:</span>
              <p className="font-medium text-gray-800">{effectiveAnalysis.summary.duration || 'Not explicitly specified'}</p>
            </div>
          </div>
          {effectiveAnalysis.summary.key_obligations && effectiveAnalysis.summary.key_obligations.length > 0 && (
            <div className="mt-3">
              <span className="font-semibold text-xs text-gray-500 uppercase tracking-wider block mb-1">Key Obligations:</span>
              <ul className="list-disc pl-5 text-xs text-gray-700 space-y-1">
                {effectiveAnalysis.summary.key_obligations.map((obl, i) => (
                  <li key={i}>{obl}</li>
                ))}
              </ul>
            </div>
          )}
        </section>

        <section className="space-y-3">
          <h2 className="text-lg font-bold text-gray-900 border-b pb-1">
            2. Contractual Risk Analysis ({effectiveAnalysis.risks.length} Findings)
          </h2>
          {effectiveAnalysis.risks.length === 0 ? (
            <p className="text-xs text-gray-600">No high-confidence contractual risks flagged by automated analysis.</p>
          ) : (
            <div className="space-y-3">
              {effectiveAnalysis.risks.map((risk) => (
                <div key={risk.id} className="border border-gray-200 rounded-lg p-3 text-xs space-y-1.5">
                  <div className="flex justify-between font-bold text-gray-900">
                    <span>
                      {risk.title} [{risk.severity.toUpperCase()}]
                      {risk.finding_category && (
                        <span className="ml-2 font-semibold text-gray-600">
                          [{risk.finding_category.replace('_', ' ').toUpperCase()}]
                        </span>
                      )}
                    </span>
                    {risk.priority_score !== undefined && (
                      <span>Priority {risk.priority_score} ({risk.priority_tier})</span>
                    )}
                  </div>
                  {risk.clause && (
                    <div className="text-gray-600 font-medium">
                      Clause: {risk.clause} {risk.page_span ? `(Page ${risk.page_span})` : (risk.page ? `(Page ${risk.page})` : '')}
                    </div>
                  )}
                  <p className="text-gray-800">{risk.explanation}</p>
                  {risk.relevantText && (
                    <div className="bg-gray-50 p-2 rounded italic text-gray-700">
                      "{risk.relevantText}"
                      {risk.evidence_unverified && (
                        <span className="block not-italic font-semibold text-amber-700 mt-1">
                          [Evidence Unverified in Source Text]
                        </span>
                      )}
                    </div>
                  )}
                  {risk.suggestion && (
                    <div className="text-blue-900 font-medium">
                      <strong>Recommendation:</strong> {risk.suggestion}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="space-y-3">
          <h2 className="text-lg font-bold text-gray-900 border-b pb-1">
            3. Key Clauses ({effectiveAnalysis.clauses.length} Extracted)
          </h2>
          <div className="space-y-2">
            {effectiveAnalysis.clauses.map((clause) => (
              <div key={clause.id} className="border-b border-gray-100 pb-2 text-xs">
                <div className="flex justify-between font-semibold text-gray-800">
                  <span>{clause.original_heading || clause.heading} [{clause.predicted_category || clause.type}]</span>
                  {(clause.page_span || clause.page) && <span>Page {clause.page_span || clause.page}</span>}
                </div>
                <p className="text-gray-600 mt-1 whitespace-pre-wrap">{clause.text}</p>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
