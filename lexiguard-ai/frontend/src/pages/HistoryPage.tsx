import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDocuments } from '../hooks/useDocuments';
import { DocumentCard } from '../components/documents/DocumentCard';
import { Input } from '../components/ui/Input';
import { Modal } from '../components/ui/Modal';
import { Button } from '../components/ui/Button';
import { Search, Clock, Trash2, AlertCircle } from 'lucide-react';

export function HistoryPage() {
  const navigate = useNavigate();
  const { documents, deleteDocument } = useDocuments();
  const [search, setSearch] = useState('');
  const [deleteTargetId, setDeleteTargetId] = useState<string | null>(null);

  const filtered = documents.filter(d =>
    d.filename.toLowerCase().includes(search.toLowerCase())
  );

  const handleDelete = async () => {
    if (deleteTargetId) {
      await deleteDocument(deleteTargetId);
      setDeleteTargetId(null);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold text-gray-900 tracking-tight">Analysis History</h1>
        <p className="text-gray-500 mt-1">Review and manage past processed documents and extracted metadata.</p>
      </div>

      <div className="max-w-md">
        <Input
          placeholder="Filter history by file name..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          leftIcon={<Search className="w-4 h-4" />}
        />
      </div>

      <div className="space-y-3">
        {filtered.length === 0 ? (
          <div className="text-center py-16 bg-white border border-gray-100 rounded-2xl">
            <Clock className="w-8 h-8 text-gray-300 mx-auto mb-2" />
            <p className="text-gray-500 font-medium text-sm">No analysis history found.</p>
          </div>
        ) : (
          filtered.map((doc) => (
            <DocumentCard
              key={doc.id}
              document={doc}
              onClick={() => navigate(`/analysis/${doc.id}`)}
              onDelete={() => setDeleteTargetId(doc.id)}
            />
          ))
        )}
      </div>

      <Modal open={!!deleteTargetId} onClose={() => setDeleteTargetId(null)} title="Delete Document History?">
        <div className="space-y-4">
          <div className="p-3 bg-red-50 border border-red-100 rounded-xl flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
            <p className="text-xs text-red-800 leading-relaxed">
              This action will remove the extracted contract metadata and cached analysis from local records.
            </p>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setDeleteTargetId(null)}>Cancel</Button>
            <Button variant="danger" onClick={handleDelete}>Delete</Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
