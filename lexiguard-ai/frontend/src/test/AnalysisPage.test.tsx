import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { AnalysisPage } from '../pages/AnalysisPage';
import { SummaryTab } from '../components/analysis/SummaryTab';
import { RiskTab } from '../components/analysis/RiskTab';
import { api } from '../services/api';
import type { Document, AnalysisData } from '../types';

vi.mock('../services/api', () => ({
  api: {
    getDocument: vi.fn(),
    getDocumentAnalysis: vi.fn(),
    getDocumentPages: vi.fn(),
  },
}));

describe('AnalysisPage & SummaryTab regression tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it('renders live analysis data without Demo Analysis badge for live contracts', async () => {
    const liveDoc: Document = {
      id: 'doc_12345678',
      filename: 'lexiguard_sample_contract.pdf',
      uploadedAt: new Date().toISOString(),
      status: 'ready',
      page_count: 2,
      word_count: 540,
      char_count: 3240,
      has_text: true,
      scanned_warning: false,
      demo_mode: false,
      pages: [{ page_number: 1, text: 'Services Agreement', word_count: 270, char_count: 1620 }],
    };

    const liveAnalysis: AnalysisData = {
      document_id: 'doc_12345678',
      demo_mode: false,
      summary: {
        overview: 'Services Agreement governing development between the parties.',
        contract_type: 'Services Agreement',
        parties: ['Example Client Ltd.', 'Sample Solutions Pvt. Ltd.'],
        effective_date: 'March 1, 2026',
        duration: '24 months',
        key_obligations: ['Deliver specifications on schedule', 'Maintain confidentiality'],
      },
      clauses: [
        { id: 'clause-01', heading: '1. Services Scope', type: 'Services', text: 'Scope details', page: 1, demo: false },
      ],
      risks: [
        { id: 'risk-01', severity: 'medium', title: 'Indemnity Exposure', explanation: 'Broad indemnity clause', demo: false },
      ],
    };

    localStorage.setItem('lexiguard_documents', JSON.stringify([liveDoc]));
    vi.mocked(api.getDocument).mockResolvedValue(liveDoc);
    vi.mocked(api.getDocumentAnalysis).mockResolvedValue(liveAnalysis);

    render(
      <MemoryRouter initialEntries={['/analysis/doc_12345678']}>
        <Routes>
          <Route path="/analysis/:id" element={<AnalysisPage />} />
        </Routes>
      </MemoryRouter>
    );

    // Wait for live analysis to render
    await waitFor(() => {
      expect(screen.getAllByText('Services Agreement governing development between the parties.').length).toBeGreaterThanOrEqual(1);
    });

    // Verify live contract details are rendered
    expect(screen.getAllByText('Example Client Ltd., Sample Solutions Pvt. Ltd.').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('March 1, 2026').length).toBeGreaterThanOrEqual(1);

    // Verify Demo Analysis badge is NOT present
    expect(screen.queryByText('Demo Analysis')).not.toBeInTheDocument();

    // Verify TechCorp (sample document party) is not rendered
    expect(screen.queryByText(/TechCorp/i)).not.toBeInTheDocument();
  });

  it('displays clear error state on analysis failure and does not silently fall back to sample data', async () => {
    const liveDoc: Document = {
      id: 'doc_error_test',
      filename: 'failing_contract.pdf',
      uploadedAt: new Date().toISOString(),
      status: 'ready',
      page_count: 1,
      word_count: 200,
      char_count: 1200,
      has_text: true,
      scanned_warning: false,
      demo_mode: false,
    };

    localStorage.setItem('lexiguard_documents', JSON.stringify([liveDoc]));
    vi.mocked(api.getDocument).mockResolvedValue(liveDoc);
    vi.mocked(api.getDocumentAnalysis).mockRejectedValue(new Error('AI analysis timed out: Ollama process unreachable'));

    render(
      <MemoryRouter initialEntries={['/analysis/doc_error_test']}>
        <Routes>
          <Route path="/analysis/:id" element={<AnalysisPage />} />
        </Routes>
      </MemoryRouter>
    );

    // Wait for error state
    await waitFor(() => {
      expect(screen.getByText('Analysis Failed')).toBeInTheDocument();
    });

    // Error message must be visible
    expect(screen.getByText(/AI analysis timed out: Ollama process unreachable/i)).toBeInTheDocument();

    // Must offer a retry button
    expect(screen.getByRole('button', { name: /Retry Analysis/i })).toBeInTheDocument();

    // SAMPLE_ANALYSIS content must NOT be displayed
    expect(screen.queryByText(/Software License Agreement grants the Licensee/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/TechCorp Inc\./i)).not.toBeInTheDocument();
  });

  it('SummaryTab shows Demo Analysis badge only when isDemo is true', () => {
    const summaryData = {
      overview: 'Test overview',
      contract_type: 'Test Agreement',
      parties: ['Alpha', 'Beta'],
      effective_date: 'Today',
      duration: '1 year',
      key_obligations: ['Obligation 1'],
    };

    // When isDemo is false
    const { rerender } = render(<SummaryTab summary={summaryData} isDemo={false} />);
    expect(screen.queryByText('Demo Analysis')).not.toBeInTheDocument();

    // When isDemo is true
    rerender(<SummaryTab summary={summaryData} isDemo={true} />);
    expect(screen.getByText('Demo Analysis')).toBeInTheDocument();
  });

  it('RiskTab clearly displays finding categories (defect, negotiation point) and multi-page spans', () => {
    const risks = [
      {
        id: 'r-1',
        title: 'Omission of Termination Remedy',
        finding_category: 'contractual_defect' as const,
        severity: 'high' as const,
        clause: '5. Termination',
        page: 1,
        page_start: 1,
        page_end: 2,
        page_span: '1-2',
        explanation: 'Clause 5 lacks expedited termination for payment default.',
        relevantText: 'Either party may terminate for material breach.',
        impact: 'High exposure to delay',
        suggestion: 'Add 7-day cure period',
        demo: false,
        evidence_unverified: false,
      },
      {
        id: 'r-2',
        title: 'Dispute Window Duration',
        finding_category: 'negotiation_point' as const,
        severity: 'medium' as const,
        clause: '3. Payment Obligations',
        page: 1,
        explanation: 'Fifteen days dispute is standard but negotiable.',
        relevantText: 'Client may dispute within 15 days.',
        impact: 'Operational constraint',
        suggestion: 'Seek 30 days',
        demo: false,
        evidence_unverified: false,
      },
    ];

    render(<RiskTab risks={risks} />);

    // Distinct category labels must be rendered separately from severity
    expect(screen.getByText('Defect')).toBeInTheDocument();
    expect(screen.getByText('Negotiation Point')).toBeInTheDocument();

    // Severity badges must also be rendered (rendered as uppercase e.g. HIGH, MEDIUM)
    expect(screen.getByText('HIGH')).toBeInTheDocument();
    expect(screen.getByText('MEDIUM')).toBeInTheDocument();

    // Multi-page span must be displayed
    expect(screen.getByText(/p\.\s*1-2/)).toBeInTheDocument();
  });

  it('RiskTab safely renders legacy findings without finding_category (backward compatibility)', () => {
    const legacyRisks = [
      {
        id: 'legacy-1',
        title: 'Legacy Contract Risk',
        severity: 'low' as const,
        clause: '1. General',
        page: 2,
        explanation: 'Legacy risk explanation without category field.',
        relevantText: 'General terms apply.',
        impact: 'Minor',
        suggestion: 'Keep track',
        demo: false,
        evidence_unverified: false,
      },
    ];

    render(<RiskTab risks={legacyRisks} />);

    expect(screen.getByText('Legacy Contract Risk')).toBeInTheDocument();
    expect(screen.getByText('LOW')).toBeInTheDocument();
    expect(screen.getByText(/p\.\s*2/)).toBeInTheDocument();
    // Doesn't crash and renders safely
    expect(screen.queryByText('Defect')).not.toBeInTheDocument();
    expect(screen.queryByText('Negotiation Point')).not.toBeInTheDocument();
  });
});

