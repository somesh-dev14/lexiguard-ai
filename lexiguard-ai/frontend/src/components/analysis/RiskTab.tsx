import React from 'react';
import type { Risk, RiskSeverity } from '../../types';
import { Badge } from '../ui/Badge';
import { AlertCircle, AlertTriangle, ShieldCheck, ArrowRight } from 'lucide-react';

interface RiskTabProps {
  risks: Risk[];
  onNavigateToSource?: (page: number) => void;
}

export function RiskTab({ risks, onNavigateToSource }: RiskTabProps) {
  const getSeverityBadge = (severity: RiskSeverity) => {
    switch (severity) {
      case 'critical':
      case 'high':
        return <Badge variant="error">{severity.toUpperCase()}</Badge>;
      case 'medium':
        return <Badge variant="warning">MEDIUM</Badge>;
      case 'low':
        return <Badge variant="info">LOW</Badge>;
      default:
        return <Badge variant="default">{severity}</Badge>;
    }
  };

  const getCategoryBadge = (category?: string) => {
    switch (category) {
      case 'contractual_defect':
        return (
          <span className="text-[11px] font-semibold text-rose-700 bg-rose-50 px-2 py-0.5 rounded border border-rose-200">
            Defect
          </span>
        );
      case 'negotiation_point':
        return (
          <span className="text-[11px] font-semibold text-purple-700 bg-purple-50 px-2 py-0.5 rounded border border-purple-200">
            Negotiation Point
          </span>
        );
      case 'informational':
        return (
          <span className="text-[11px] font-semibold text-slate-700 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
            Informational
          </span>
        );
      default:
        return null;
    }
  };

  const getSeverityIcon = (severity: RiskSeverity) => {
    switch (severity) {
      case 'critical':
      case 'high':
        return <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" />;
      case 'medium':
        return <AlertTriangle className="w-5 h-5 text-amber-500 flex-shrink-0" />;
      default:
        return <ShieldCheck className="w-5 h-5 text-blue-500 flex-shrink-0" />;
    }
  };

  return (
    <div className="space-y-6">
      <div className="p-4 bg-amber-50/80 border border-amber-200/60 rounded-2xl flex items-start gap-3">
        <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
        <div className="text-xs text-amber-900 leading-relaxed">
          <strong className="font-semibold block mb-0.5">Automated Risk Analysis Disclaimer</strong>
          Risk assessments evaluate potential legal liabilities and unhedged commitments based on common corporate law benchmarks. Findings are for informational orientation and should be verified with licensed counsel.
        </div>
      </div>

      <div className="space-y-4">
        {risks.length === 0 ? (
          <div className="p-8 bg-white border border-gray-200 rounded-2xl text-center space-y-3">
            <ShieldCheck className="w-10 h-10 text-emerald-600 mx-auto" />
            <h4 className="text-base font-semibold text-gray-900">No High-Confidence Contractual Risks Flagged</h4>
            <p className="text-sm text-gray-600 max-w-md mx-auto">
              Automated analysis did not identify definitive high-exposure liabilities or missing mandatory clauses in the extracted text. This automated assessment does not imply or certify that the contract is risk-free; formal legal review by qualified counsel remains strongly recommended.
            </p>
          </div>
        ) : (
          risks.map((risk) => (
            <div
              key={risk.id}
              className="bg-white border border-gray-200 rounded-2xl p-5 hover:border-gray-300 transition-all shadow-subtle space-y-4"
            >
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-start gap-3">
                {getSeverityIcon(risk.severity)}
                <div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <h4 className="font-semibold text-gray-900">{risk.title}</h4>
                    {getCategoryBadge(risk.finding_category)}
                    {getSeverityBadge(risk.severity)}
                    {risk.clause && (
                      <span className="text-[11px] font-medium text-gray-600 bg-gray-100 px-2 py-0.5 rounded border border-gray-200">
                        {risk.clause} {risk.page_span ? `(p. ${risk.page_span})` : risk.page ? `(p. ${risk.page})` : ''}
                      </span>
                    )}
                    {risk.evidence_unverified && (
                      <span className="text-[11px] font-medium text-amber-700 bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                        Evidence Unverified
                      </span>
                    )}
                    {risk.priority_score !== undefined && (
                      <span className={`text-[11px] font-bold px-2 py-0.5 rounded border ${
                        risk.priority_tier === 'URGENT'
                          ? 'bg-red-100 text-red-800 border-red-300'
                          : risk.priority_tier === 'HIGH'
                          ? 'bg-orange-100 text-orange-800 border-orange-300'
                          : risk.priority_tier === 'MODERATE'
                          ? 'bg-blue-100 text-blue-800 border-blue-300'
                          : 'bg-gray-100 text-gray-700 border-gray-300'
                      }`}>
                        Priority {risk.priority_score} ({risk.priority_tier})
                      </span>
                    )}
                    {risk.demo && <Badge variant="demo">Demo</Badge>}
                  </div>
                  <p className="text-sm text-gray-600 mt-1">{risk.explanation}</p>
                  {risk.priority_breakdown && (
                    <details className="mt-2 text-xs text-gray-500">
                      <summary className="cursor-pointer font-medium text-blue-600 hover:text-blue-800 select-none">
                        View Factor Breakdown (Explainable Scoring)
                      </summary>
                      <div className="mt-2 p-3 bg-gray-50 rounded-xl border border-gray-200 space-y-1.5 font-mono text-[11px] text-gray-700">
                        <div><strong>Formula:</strong> {risk.priority_breakdown.formula}</div>
                        <div><strong>Base Severity:</strong> {risk.priority_breakdown.factors.severity.rating} (weight {risk.priority_breakdown.factors.severity.weight}, score {risk.priority_breakdown.factors.severity.score})</div>
                        <div><strong>Financial Exposure:</strong> {risk.priority_breakdown.factors.financial_exposure.rationale} (weight {risk.priority_breakdown.factors.financial_exposure.weight}, score {risk.priority_breakdown.factors.financial_exposure.score})</div>
                        <div><strong>Obligation Asymmetry:</strong> {risk.priority_breakdown.factors.obligation_asymmetry.rationale} (weight {risk.priority_breakdown.factors.obligation_asymmetry.weight}, score {risk.priority_breakdown.factors.obligation_asymmetry.score})</div>
                        <div><strong>Evidence Confidence Multiplier:</strong> {risk.priority_breakdown.factors.evidence_confidence.multiplier} ({risk.priority_breakdown.factors.evidence_confidence.rationale})</div>
                      </div>
                    </details>
                  )}
                </div>
              </div>
            </div>

            {risk.relevantText && (
              <div
                className={`p-3 rounded-xl border text-xs italic ${
                  risk.evidence_unverified
                    ? 'bg-amber-50/50 border-amber-200 text-amber-800 border-l-4 border-l-amber-400'
                    : 'bg-gray-50 border-gray-100 text-gray-700 border-l-4 border-l-gray-400'
                }`}
              >
                "{risk.relevantText}"
                {risk.evidence_unverified && (
                  <span className="block not-italic font-normal text-[11px] text-amber-700 mt-1">
                    ⚠️ Note: This excerpt could not be verified against the source clause text.
                  </span>
                )}
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2 text-xs">
              {risk.impact && (
                <div className="bg-red-50/50 p-2.5 rounded-xl border border-red-100/60 text-red-900">
                  <span className="font-semibold block mb-0.5">Potential Impact:</span>
                  {risk.impact}
                </div>
              )}
              {risk.suggestion && (
                <div className="bg-blue-50/50 p-2.5 rounded-xl border border-blue-100/60 text-blue-900">
                  <span className="font-semibold block mb-0.5">Recommended Action:</span>
                  {risk.suggestion}
                </div>
              )}
            </div>

            {risk.page && onNavigateToSource && (
              <div className="flex justify-end pt-1">
                <button
                  onClick={() => onNavigateToSource(risk.page!)}
                  className="text-xs font-medium text-blue-600 hover:text-blue-800 flex items-center gap-1"
                >
                  Jump to Page {risk.page} <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            )}
          </div>
        )))}
      </div>
    </div>
  );
}
