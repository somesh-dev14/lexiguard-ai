import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Search, FileText, Clock, Trash2, AlertCircle, ChevronRight } from 'lucide-react';
import { motion } from 'framer-motion';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Card } from '../components/ui/Card';
import { Input } from '../components/ui/Input';
import { Modal } from '../components/ui/Modal';
import { useDocuments } from '../hooks/useDocuments';
import { useBackendStatus } from '../hooks/useBackendStatus';
import { formatRelativeTime, formatFileSize } from '../utils/cn';

export function DashboardPage() {
  const navigate = useNavigate();
  const { documents, deleteDocument } = useDocuments();
  const { status: backendStatus, aiMode } = useBackendStatus();
  const [search, setSearch] = useState('');
  const [sortBy, setSortBy] = useState<'date' | 'name'>('date');
  const [deleteId, setDeleteId] = useState<string | null>(null);

  const filtered = documents
    .filter(d => d.filename.toLowerCase().includes(search.toLowerCase()))
    .sort((a, b) => sortBy === 'date'
      ? new Date(b.uploadedAt).getTime() - new Date(a.uploadedAt).getTime()
      : a.filename.localeCompare(b.filename));

  const handleDelete = async () => {
    if (deleteId) { await deleteDocument(deleteId); setDeleteId(null); }
  };

  const statusBadge = (status: string, demoMode: boolean) => {
    if (demoMode) return <Badge variant="demo">Demo</Badge>;
    switch (status) {
      case 'ready': return <Badge variant="success">Ready</Badge>;
      case 'error': return <Badge variant="error">Error</Badge>;
      default: return <Badge variant="default">{status}</Badge>;
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold text-gray-900 tracking-tight">Dashboard</h1>
          <p className="text-gray-500 mt-1">Manage your contract analyses.</p>
        </div>
        <Button onClick={() => navigate('/upload')}>
          <Plus className="w-4 h-4" />
          New Analysis
        </Button>
      </div>

      {/* Backend status */}
      {backendStatus !== 'checking' && (
        <div className={`flex items-center gap-2.5 px-4 py-3 rounded-xl border text-sm ${backendStatus === 'online' ? 'bg-green-50 border-green-200 text-green-800' : 'bg-amber-50 border-amber-200 text-amber-800'}`}>
          <div className={`w-2 h-2 rounded-full ${backendStatus === 'online' ? 'bg-green-500' : 'bg-amber-500'}`} />
          {backendStatus === 'online'
            ? `Backend online \u00b7 AI mode: ${aiMode === 'demo' ? 'Demo (AI not connected)' : 'AI Active'}`
            : 'Backend offline \u00b7 Start the FastAPI server on port 8000 to enable PDF extraction'
          }
        </div>
      )}

      {/* Search and filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="flex-1">
          <Input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search documents..."
            leftIcon={<Search className="w-4 h-4" />}
          />
        </div>
        <select
          value={sortBy}
          onChange={e => setSortBy(e.target.value as 'date' | 'name')}
          className="px-3 py-2 rounded-xl border border-gray-200 text-sm text-gray-700 bg-white focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
        >
          <option value="date">Sort by date</option>
          <option value="name">Sort by name</option>
        </select>
      </div>

      {/* Documents list */}
      {filtered.length === 0 ? (
        <Card className="text-center py-20">
          <div className="flex flex-col items-center gap-4">
            <div className="w-16 h-16 bg-gray-100 rounded-2xl flex items-center justify-center">
              <FileText className="w-8 h-8 text-gray-400" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900 mb-1">{search ? 'No documents found' : 'No documents yet'}</h3>
              <p className="text-sm text-gray-500">{search ? 'Try a different search term.' : 'Upload your first contract to get started.'}</p>
            </div>
            {!search && (
              <Button size="sm" onClick={() => navigate('/upload')}>
                <Plus className="w-4 h-4" />
                Analyze a contract
              </Button>
            )}
          </div>
        </Card>
      ) : (
        <div className="space-y-2">
          {filtered.map((doc, i) => (
            <motion.div
              key={doc.id}
              initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.25, delay: i * 0.04 }}
            >
              <div
                className="group flex items-center gap-4 bg-white border border-gray-200/80 rounded-2xl px-5 py-4 hover:shadow-elevated hover:border-gray-300 transition-all duration-200 cursor-pointer"
                onClick={() => navigate(`/analysis/${doc.id}`)}
              >
                <div className="flex-shrink-0 w-10 h-10 bg-gray-100 rounded-xl flex items-center justify-center">
                  <FileText className="w-5 h-5 text-gray-500" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <p className="font-medium text-gray-900 truncate">{doc.filename}</p>
                    {statusBadge(doc.status, doc.demo_mode)}
                  </div>
                  <div className="flex items-center gap-3 text-xs text-gray-400">
                    <span className="flex items-center gap-1"><Clock className="w-3 h-3" />{formatRelativeTime(doc.uploadedAt)}</span>
                    <span>{doc.page_count} pages</span>
                    <span>{doc.word_count.toLocaleString()} words</span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <ChevronRight className="w-5 h-5 text-gray-300 group-hover:text-gray-500 transition-colors" />
                  <button
                    onClick={e => { e.stopPropagation(); setDeleteId(doc.id); }}
                    className="opacity-0 group-hover:opacity-100 transition-opacity p-2 rounded-lg text-gray-400 hover:text-red-600 hover:bg-red-50"
                    aria-label="Delete"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      )}

      {/* Delete confirm */}
      <Modal open={!!deleteId} onClose={() => setDeleteId(null)} title="Delete document?">
        <div className="space-y-4">
          <div className="flex items-start gap-3 p-4 bg-red-50 border border-red-100 rounded-xl">
            <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-red-800">This will permanently remove the document from your history. This action cannot be undone.</p>
          </div>
          <div className="flex gap-3 justify-end">
            <Button variant="secondary" onClick={() => setDeleteId(null)}>Cancel</Button>
            <Button variant="danger" onClick={handleDelete}>Delete</Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
