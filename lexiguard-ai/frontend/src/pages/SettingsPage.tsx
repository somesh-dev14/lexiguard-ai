import React from 'react';
import { Card, CardHeader, CardBody } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { useTheme } from '../hooks/useTheme';
import { useBackendStatus } from '../hooks/useBackendStatus';
import { Shield, Cpu, Moon, Sun, Monitor, Info } from 'lucide-react';

export function SettingsPage() {
  const { theme, setTheme } = useTheme();
  const { status, aiMode } = useBackendStatus();

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-3xl font-semibold text-gray-900 tracking-tight">Settings & Architecture</h1>
        <p className="text-gray-500 mt-1">Configure workspace preferences and review service backend status.</p>
      </div>

      {/* Appearance */}
      <Card>
        <CardHeader>
          <h3 className="text-base font-semibold text-gray-900">Appearance & Theme</h3>
        </CardHeader>
        <CardBody className="space-y-4">
          <div className="flex items-center gap-3">
            {[
              { id: 'light', label: 'Light', icon: Sun },
              { id: 'dark', label: 'Dark', icon: Moon },
              { id: 'system', label: 'System', icon: Monitor },
            ].map(t => {
              const Icon = t.icon;
              const isSel = theme === t.id;
              return (
                <button
                  key={t.id}
                  onClick={() => setTheme(t.id as any)}
                  className={`flex items-center gap-2 px-4 py-2.5 rounded-xl border text-sm font-medium transition-all ${
                    isSel ? 'border-gray-900 bg-gray-900 text-white' : 'border-gray-200 text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span>{t.label}</span>
                </button>
              );
            })}
          </div>
        </CardBody>
      </Card>

      {/* Backend & AI Connection Status */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <h3 className="text-base font-semibold text-gray-900">Backend Integration Status</h3>
            <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${
              status === 'online' ? 'bg-green-50 text-green-700' : 'bg-amber-50 text-amber-700'
            }`}>
              <span className={`w-2 h-2 rounded-full ${status === 'online' ? 'bg-green-500' : 'bg-amber-500'}`} />
              {status === 'online' ? 'FastAPI Connected' : 'FastAPI Offline'}
            </span>
          </div>
        </CardHeader>
        <CardBody className="space-y-4">
          <div className="p-4 bg-gray-50 border border-gray-200/80 rounded-2xl space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold text-gray-800">Current AI Engine Mode</span>
              <Badge variant="demo">{aiMode === 'demo' ? 'Deterministic Demo Mode' : 'Connected Model'}</Badge>
            </div>
            <p className="text-xs text-gray-500 leading-relaxed">
              In demo mode, contract clauses and risk assessments provide structured mock findings for evaluation. 
              PDF text extraction remains 100% active and authentic via PyMuPDF.
            </p>
          </div>

          <div className="p-4 bg-blue-50/60 border border-blue-100 rounded-2xl flex items-start gap-3">
            <Info className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
            <div className="text-xs text-blue-900 leading-relaxed space-y-1">
              <strong className="block font-semibold">Configuring Production RAG / Models</strong>
              <p>
                To enable live zero-shot clause classification and custom RAG retrieval, set your API key in the backend environment variables:
              </p>
              <code className="block bg-blue-100/70 p-2 rounded text-blue-950 font-mono text-[11px] mt-1">
                OPENAI_API_KEY=your_key_here or DEBERTA_MODEL_PATH=./models
              </code>
            </div>
          </div>
        </CardBody>
      </Card>
    </div>
  );
}
