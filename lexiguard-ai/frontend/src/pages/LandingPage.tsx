import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Shield, FileText, AlertTriangle, MessageSquare, ChevronRight, Lock, Cpu, CheckCircle } from 'lucide-react';
import { motion } from 'framer-motion';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { useBackendStatus } from '../hooks/useBackendStatus';

const features = [
  { icon: FileText, title: 'Document Summarization', desc: 'Instantly distill lengthy contracts into clear, structured overviews covering parties, obligations, dates, and terms.' },
  { icon: Shield, title: 'Clause Analysis', desc: 'Every significant clause is identified, categorized, and explained in plain language with source references.' },
  { icon: AlertTriangle, title: 'Risk Identification', desc: 'Potential risks are flagged with severity ratings, impact assessments, and suggested review actions.' },
  { icon: MessageSquare, title: 'Evidence-Grounded Q&A', desc: 'Ask any question about your document. Every answer is anchored to the actual text with page references.' },
];

const steps = [
  { n: '01', title: 'Upload your contract', desc: 'Drag and drop or select a PDF. Files are processed locally and never sent to third parties without your configuration.' },
  { n: '02', title: 'Review the analysis', desc: 'Explore the executive summary, clause breakdown, risk report, and source document in an elegant workspace.' },
  { n: '03', title: 'Ask questions', desc: 'Ask anything about the contract. Get answers grounded in the document text, with page citations.' },
];

export function LandingPage() {
  const navigate = useNavigate();
  const { status, aiMode } = useBackendStatus();

  const renderHeroBadge = () => {
    if (status === 'checking') {
      return <Badge variant="default" className="mb-6">Connecting to AI Engine...</Badge>;
    }
    if (status === 'offline') {
      return <Badge variant="demo" className="mb-6">Backend Offline &mdash; Start server on port 8000</Badge>;
    }
    if (aiMode === 'demo') {
      return <Badge variant="demo" className="mb-6">Demo Mode &mdash; Connect Model in Settings</Badge>;
    }
    return (
      <Badge variant="success" className="mb-6 flex items-center gap-1.5 w-fit mx-auto">
        <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
        AI Active &mdash; Local DeBERTa &amp; Qwen3 Connected
      </Badge>
    );
  };

  return (
    <div className="min-h-screen bg-white">
      {/* Nav */}
      <header className="sticky top-0 z-40 bg-white/90 backdrop-blur-md border-b border-gray-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="flex items-center justify-center w-9 h-9 bg-gray-900 rounded-xl">
              <Shield className="w-5 h-5 text-white" />
            </div>
            <span className="text-lg font-semibold text-gray-900 tracking-tight">LexiGuard AI</span>
          </div>
          <div className="flex items-center gap-3">
            <button onClick={() => navigate('/dashboard')} className="text-sm text-gray-500 hover:text-gray-900 transition-colors hidden sm:block">Dashboard</button>
            <Button size="sm" onClick={() => navigate('/upload')}>Analyze a Contract</Button>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="pt-24 pb-20 px-4 sm:px-6 lg:px-8 text-center">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
          {renderHeroBadge()}
          <h1 className="text-5xl sm:text-6xl lg:text-7xl font-semibold text-gray-900 tracking-tight leading-[1.05] mb-6 max-w-4xl mx-auto">
            Understand legal contracts,<br className="hidden sm:block" />
            <span className="text-gray-400"> without the legal fees.</span>
          </h1>
          <p className="text-xl text-gray-500 max-w-2xl mx-auto leading-relaxed mb-10">
            LexiGuard AI extracts, summarizes, and analyses legal documents. Identify risks, understand obligations, and ask questions&mdash;all grounded in the actual text of your contract.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <Button size="lg" onClick={() => navigate('/upload')}>
              Analyze a Contract
              <ChevronRight className="w-5 h-5" />
            </Button>
            <Button size="lg" variant="secondary" onClick={() => navigate('/dashboard')}>
              Explore Dashboard
            </Button>
          </div>
          <p className="mt-6 text-sm text-gray-400">PDF upload &middot; Up to 50 MB &middot; Processed 100% locally on your machine</p>
        </motion.div>

        {/* Product preview */}
        <motion.div
          initial={{ opacity: 0, y: 40 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, delay: 0.2 }}
          className="mt-20 max-w-5xl mx-auto"
        >
          <div className="bg-gray-900 rounded-3xl p-1 shadow-2xl">
            <div className="bg-gray-800 rounded-2xl overflow-hidden">
              <div className="flex items-center gap-2 px-4 py-3 border-b border-gray-700">
                <div className="flex gap-1.5">
                  <div className="w-3 h-3 rounded-full bg-red-500/70"></div>
                  <div className="w-3 h-3 rounded-full bg-amber-500/70"></div>
                  <div className="w-3 h-3 rounded-full bg-green-500/70"></div>
                </div>
                <div className="flex-1 flex justify-center">
                  <div className="bg-gray-700 rounded-md px-4 py-1 text-xs text-gray-400">lexiguard.ai/analyze</div>
                </div>
              </div>
              <div className="p-6 grid grid-cols-3 gap-4 text-left min-h-64">
                <div className="col-span-1 space-y-3">
                  <div className="bg-gray-700/50 rounded-xl p-3">
                    <p className="text-xs text-gray-400 mb-1">Document</p>
                    <p className="text-sm text-white font-medium">Software_License.pdf</p>
                    <p className="text-xs text-gray-400 mt-1">24 pages &middot; 8,420 words</p>
                  </div>
                  {['Summary', 'Clauses', 'Risk Analysis', 'Q&A', 'Source'].map((tab, i) => (
                    <div key={tab} className={`px-3 py-2 rounded-lg text-sm ${i === 2 ? 'bg-blue-500/20 text-blue-300' : 'text-gray-400'}`}>{tab}</div>
                  ))}
                </div>
                <div className="col-span-2 space-y-3">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-medium text-white">Risk Analysis</p>
                    <span className="text-xs bg-blue-500/20 text-blue-300 px-2 py-0.5 rounded">4 items</span>
                  </div>
                  {[
                    { label: 'CRITICAL', color: 'bg-purple-500/20 text-purple-300', title: 'No Data Portability Clause' },
                    { label: 'HIGH', color: 'bg-red-500/20 text-red-300', title: 'Broad Termination Rights' },
                    { label: 'MEDIUM', color: 'bg-amber-500/20 text-amber-300', title: 'Liability Cap Excludes Damages' },
                  ].map(r => (
                    <div key={r.label} className="bg-gray-700/40 rounded-xl p-3">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`text-xs font-medium px-1.5 py-0.5 rounded ${r.color}`}>{r.label}</span>
                      </div>
                      <p className="text-sm text-white">{r.title}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      </section>

      {/* Features */}
      <section className="py-20 px-4 sm:px-6 lg:px-8 bg-gray-50">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-semibold text-gray-900 tracking-tight mb-4">Everything you need to understand a contract</h2>
            <p className="text-lg text-gray-500 max-w-2xl mx-auto">A complete legal document intelligence platform, designed for clarity and precision.</p>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {features.map((f, i) => (
              <motion.div
                key={f.title}
                initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: i * 0.08 }} viewport={{ once: true }}
                className="bg-white border border-gray-200 rounded-2xl p-6 hover:shadow-elevated hover:border-gray-300 transition-all duration-200"
              >
                <div className="w-10 h-10 bg-gray-900 rounded-xl flex items-center justify-center mb-4">
                  <f.icon className="w-5 h-5 text-white" />
                </div>
                <h3 className="font-semibold text-gray-900 mb-2">{f.title}</h3>
                <p className="text-sm text-gray-500 leading-relaxed">{f.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-semibold text-gray-900 tracking-tight mb-4">Three steps to clarity</h2>
          </div>
          <div className="space-y-8">
            {steps.map((s, i) => (
              <motion.div
                key={s.n}
                initial={{ opacity: 0, x: -20 }} whileInView={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.4, delay: i * 0.1 }} viewport={{ once: true }}
                className="flex gap-6 items-start"
              >
                <div className="flex-shrink-0 w-12 h-12 bg-gray-900 rounded-2xl flex items-center justify-center text-white text-sm font-mono font-semibold">{s.n}</div>
                <div>
                  <h3 className="font-semibold text-gray-900 mb-1">{s.title}</h3>
                  <p className="text-gray-500 leading-relaxed">{s.desc}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Privacy */}
      <section className="py-16 px-4 sm:px-6 lg:px-8 bg-gray-50">
        <div className="max-w-4xl mx-auto">
          <div className="grid md:grid-cols-3 gap-6">
            {[
              { icon: Lock, title: 'Privacy first', desc: 'Documents are processed locally. No data is sent externally without your explicit configuration.' },
              { icon: Cpu, title: 'Grounded analysis', desc: 'Every finding links back to the source text. No hallucinated citations or unsupported claims.' },
              { icon: CheckCircle, title: 'Honest limitations', desc: 'AI integration is clearly indicated. Demo mode is transparent. Outputs are informational only.' },
            ].map(item => (
              <div key={item.title} className="flex gap-4">
                <div className="flex-shrink-0 w-10 h-10 border border-gray-200 rounded-xl flex items-center justify-center">
                  <item.icon className="w-5 h-5 text-gray-600" />
                </div>
                <div>
                  <h4 className="font-semibold text-gray-900 mb-1">{item.title}</h4>
                  <p className="text-sm text-gray-500">{item.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-24 px-4 sm:px-6 lg:px-8 text-center bg-gray-900">
        <h2 className="text-4xl font-semibold text-white tracking-tight mb-4">Ready to analyze your contract?</h2>
        <p className="text-gray-400 mb-8 max-w-xl mx-auto">Upload your PDF and get an instant structured analysis. No account needed in demo mode.</p>
        <Button size="lg" variant="secondary" onClick={() => navigate('/upload')}>
          Get started free
          <ChevronRight className="w-5 h-5" />
        </Button>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 border-t border-gray-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex flex-col md:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Shield className="w-4 h-4 text-gray-400" />
            <span className="text-sm text-gray-400">LexiGuard AI</span>
          </div>
          <p className="text-xs text-gray-500">For informational purposes only. Not legal advice. &copy; {new Date().getFullYear()}</p>
        </div>
      </footer>
    </div>
  );
}
