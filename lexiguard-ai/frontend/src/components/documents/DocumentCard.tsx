import React from 'react';
import { FileText, ChevronRight, Clock, Trash2 } from 'lucide-react';
import { Document } from '../../types';
import { Badge } from '../ui/Badge';
import { formatRelativeTime } from '../../utils/cn';

interface DocumentCardProps {
  document: Document;
  onClick: () => void;
  onDelete?: () => void;
}

export function DocumentCard({ document, onClick, onDelete }: DocumentCardProps) {
  return (
    <div
      onClick={onClick}
      className="group flex items-center justify-between p-4 bg-white border border-gray-100 rounded-2xl hover:border-gray-200 hover:shadow-subtle transition-all cursor-pointer"
    >
      <div className="flex items-center gap-4 min-w-0">
        <div className="w-12 h-12 rounded-xl bg-gray-50 flex items-center justify-center text-gray-400 group-hover:bg-blue-50 group-hover:text-blue-600 transition-colors">
          <FileText className="w-6 h-6 stroke-[1.5]" />
        </div>
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <h4 className="font-medium text-gray-900 truncate max-w-xs sm:max-w-md">{document.filename}</h4>
            {document.demo_mode && <Badge variant="demo">Demo</Badge>}
          </div>
          <div className="flex items-center gap-3 text-xs text-gray-400 mt-1">
            <span className="flex items-center gap-1">
              <Clock className="w-3.5 h-3.5" />
              {formatRelativeTime(document.uploadedAt)}
            </span>
            <span>&middot;</span>
            <span>{document.page_count} pages</span>
            <span>&middot;</span>
            <span>{document.word_count.toLocaleString()} words</span>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2">
        {onDelete && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDelete();
            }}
            className="p-2 text-gray-300 hover:text-red-500 rounded-lg hover:bg-red-50 opacity-0 group-hover:opacity-100 transition-all"
            title="Delete document"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        )}
        <ChevronRight className="w-5 h-5 text-gray-300 group-hover:text-gray-500 transition-colors" />
      </div>
    </div>
  );
}
