import React from 'react';
import { Card, CardHeader, CardBody } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { Calendar, Users, FileCheck, DollarSign, Clock, ShieldAlert } from 'lucide-react';

interface SummaryData {
  overview: string;
  contract_type?: string;
  parties: string[];
  effective_date?: string;
  duration?: string;
  key_obligations: string[];
}

interface SummaryTabProps {
  summary: SummaryData;
  onNavigateToSource?: (page: number) => void;
  isDemo?: boolean;
}

export function SummaryTab({ summary, onNavigateToSource, isDemo }: SummaryTabProps) {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900">Executive Summary</h3>
            {isDemo && <Badge variant="demo">Demo Analysis</Badge>}
          </div>
        </CardHeader>
        <CardBody className="space-y-4">
          <p className="text-gray-700 leading-relaxed text-base">{summary.overview}</p>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4 border-t border-gray-100">
            <div className="flex items-start gap-3 p-3 bg-gray-50/70 rounded-xl">
              <FileCheck className="w-5 h-5 text-gray-400 mt-0.5" />
              <div>
                <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Contract Type</span>
                <p className="font-medium text-gray-800">{summary.contract_type || 'Standard Commercial Agreement'}</p>
              </div>
            </div>

            <div className="flex items-start gap-3 p-3 bg-gray-50/70 rounded-xl">
              <Users className="w-5 h-5 text-gray-400 mt-0.5" />
              <div>
                <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Identified Parties</span>
                <p className="font-medium text-gray-800">{summary.parties.join(', ') || 'Not specified'}</p>
              </div>
            </div>
          </div>
        </CardBody>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <h4 className="font-semibold text-gray-900 flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-blue-600" />
              Key Obligations
            </h4>
          </CardHeader>
          <CardBody>
            <ul className="space-y-3">
              {summary.key_obligations.map((obl, idx) => (
                <li key={idx} className="flex items-start gap-2 text-sm text-gray-600">
                  <span className="w-1.5 h-1.5 rounded-full bg-blue-500 mt-2 flex-shrink-0" />
                  <span>{obl}</span>
                </li>
              ))}
            </ul>
          </CardBody>
        </Card>

        <Card>
          <CardHeader>
            <h4 className="font-semibold text-gray-900 flex items-center gap-2">
              <Calendar className="w-4 h-4 text-amber-600" />
              Dates & Duration
            </h4>
          </CardHeader>
          <CardBody className="space-y-4">
            <div>
              <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Effective Date</span>
              <p className="text-sm font-medium text-gray-800 mt-1 flex items-center gap-2">
                <Clock className="w-4 h-4 text-gray-400" />
                <span>{summary.effective_date || 'Not explicitly specified'}</span>
              </p>
            </div>

            <div className="pt-3 border-t border-gray-100">
              <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Term / Duration</span>
              <p className="text-sm text-gray-700 mt-1 flex items-start gap-2">
                <DollarSign className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
                <span>{summary.duration || 'Not explicitly specified'}</span>
              </p>
            </div>
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
