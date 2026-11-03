import type { Document, AnalysisData } from '../types';

export const SAMPLE_DOCUMENTS: Document[] = [
  {
    id: 'sample-001',
    filename: 'Software_License_Agreement_2024.pdf',
    uploadedAt: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
    status: 'demo',
    page_count: 24,
    word_count: 8420,
    char_count: 47200,
    has_text: true,
    scanned_warning: false,
    demo_mode: true,
  },
  {
    id: 'sample-002',
    filename: 'Employment_Contract_Template.pdf',
    uploadedAt: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(),
    status: 'demo',
    page_count: 12,
    word_count: 4100,
    char_count: 23600,
    has_text: true,
    scanned_warning: false,
    demo_mode: true,
  },
  {
    id: 'sample-003',
    filename: 'Vendor_Services_Agreement.pdf',
    uploadedAt: new Date(Date.now() - 10 * 24 * 60 * 60 * 1000).toISOString(),
    status: 'demo',
    page_count: 18,
    word_count: 6800,
    char_count: 38900,
    has_text: true,
    scanned_warning: false,
    demo_mode: true,
  },
];

export const SAMPLE_ANALYSIS: AnalysisData = {
  document_id: 'sample-001',
  demo_mode: true,
  disclaimer: 'This analysis is illustrative demo data. AI integration (DeBERTa + RAG pipeline) is not yet connected. Do not rely on this for legal decisions.',
  summary: {
    overview: '[DEMO] This Software License Agreement grants the Licensee a non-exclusive, non-transferable right to use the specified software. Key terms cover intellectual property ownership, restrictions on reverse engineering, payment obligations, and termination conditions.',
    contract_type: 'Software License Agreement',
    parties: ['TechCorp Inc. (Licensor)', 'Acme Solutions Ltd. (Licensee)'],
    effective_date: '1 January 2024',
    duration: '12 months, auto-renews with 30 days notice to cancel',
    key_obligations: [
      'Licensee must pay annual license fees of ,000 within 30 days of invoice',
      'Licensor must provide updates and patches during the license term',
      'Licensee must not reverse-engineer or decompile the software',
      'Both parties must maintain confidentiality of proprietary information',
    ],
  },
  clauses: [
    { id: 'clause-01', heading: 'Grant of License', type: 'License Grant', text: '[DEMO] The Licensor hereby grants to the Licensee a limited, non-exclusive, non-transferable, revocable license to install and use the Software solely for internal business purposes during the License Term.', page: 2, demo: true },
    { id: 'clause-02', heading: 'Limitation of Liability', type: 'Liability', text: '[DEMO] In no event shall either party be liable for any indirect, incidental, special, consequential, or exemplary damages, including but not limited to loss of profits, goodwill, or data, arising out of or in connection with this Agreement.', page: 8, demo: true },
    { id: 'clause-03', heading: 'Termination for Cause', type: 'Termination', text: '[DEMO] Either party may terminate this Agreement immediately upon written notice if the other party materially breaches any provision and fails to cure such breach within thirty (30) days after receiving written notice.', page: 14, demo: true },
    { id: 'clause-04', heading: 'Intellectual Property Ownership', type: 'Intellectual Property', text: '[DEMO] The Software, including all modifications, enhancements, and derivative works, shall remain the exclusive property of the Licensor. This Agreement does not transfer any intellectual property rights to the Licensee.', page: 4, demo: true },
    { id: 'clause-05', heading: 'Confidentiality', type: 'Confidentiality', text: '[DEMO] Each party agrees to maintain in strict confidence all Confidential Information received from the other party and to use such information solely for the purposes of this Agreement.', page: 10, demo: true },
    { id: 'clause-06', heading: 'Governing Law', type: 'Governing Law', text: '[DEMO] This Agreement shall be governed by and construed in accordance with the laws of the State of Delaware, without regard to its conflict of law provisions.', page: 20, demo: true },
  ],
  risks: [
    { id: 'risk-01', severity: 'high', title: 'Broad Licensor Termination Rights', explanation: '[DEMO] The termination clause grants broad discretion to terminate for material breach without a clear definition, creating uncertainty about business continuity.', relevantText: '[DEMO] ...immediately upon written notice if the other party materially breaches any provision...', page: 14, impact: 'Potential immediate loss of software access without adequate transition time.', suggestion: 'Request an exhaustive definition of material breach and extend the cure period to 60-90 days.', demo: true },
    { id: 'risk-02', severity: 'medium', title: 'Limitation of Liability Cap', explanation: '[DEMO] The clause excludes consequential and indirect damages. Depending on your context, this could limit recovery for significant losses.', relevantText: '[DEMO] In no event shall either party be liable for any indirect, incidental, special, consequential...', page: 8, impact: 'Limited financial recovery if software failure causes major business disruption.', suggestion: 'Negotiate carve-outs for gross negligence, wilful misconduct, or IP indemnification.', demo: true },
    { id: 'risk-03', severity: 'low', title: 'Automatic Renewal Clause', explanation: '[DEMO] The agreement auto-renews unless terminated with 30 days notice. This is a short window that could result in an unintended renewal.', relevantText: '[DEMO] ...with automatic renewal unless terminated with 30 days notice...', page: 3, impact: 'Potential obligation for an additional year of license fees.', suggestion: 'Set a calendar reminder 60 days before renewal. Negotiate a 60-day notice period.', demo: true },
    { id: 'risk-04', severity: 'critical', title: 'No Data Portability Clause', explanation: '[DEMO] No provision requires the Licensor to return or export your data upon termination. This could result in data loss.', page: undefined, impact: 'Loss of business-critical data upon contract termination.', suggestion: 'Add an explicit data return clause requiring portable format delivery within 30 days of termination.', demo: true },
  ],
};

export const SUGGESTED_QUESTIONS = [
  'What are the payment terms and penalties for late payment?',
  'Under what conditions can either party terminate this contract?',
  'Who owns intellectual property created during this engagement?',
  'What is the liability cap and what damages are excluded?',
  'Are there any non-compete or exclusivity provisions?',
  'What notice periods are required for termination?',
  'How are disputes resolved under this agreement?',
  'What confidentiality obligations apply after the contract ends?',
];
