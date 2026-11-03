import React, { useState } from 'react';
import { PageText } from '../../types';
import { Search, ChevronLeft, ChevronRight, Copy, Check } from 'lucide-react';
import { Input } from '../ui/Input';

interface SourceTabProps {
  pages: PageText[];
  initialPage?: number;
}

export function SourceTab({ pages, initialPage = 1 }: SourceTabProps) {
  const [currentPage, setCurrentPage] = useState<number>(initialPage);
  const [search, setSearch] = useState('');
  const [copied, setCopied] = useState(false);

  const totalPages = pages.length || 1;
  const activePageData = pages.find(p => p.page_number === currentPage) || pages[0];

  const handleCopy = () => {
    if (activePageData?.text) {
      navigator.clipboard.writeText(activePageData.text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="space-y-4">
      {/* Controls Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-white p-3 rounded-2xl border border-gray-200">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
            disabled={currentPage <= 1}
            className="p-1.5 rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50 disabled:opacity-40"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <span className="text-sm font-medium text-gray-700">
            Page {currentPage} of {totalPages}
          </span>
          <button
            onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
            disabled={currentPage >= totalPages}
            className="p-1.5 rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50 disabled:opacity-40"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>

        <div className="flex items-center gap-2 flex-1 max-w-xs">
          <Input
            placeholder="Search within page..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            leftIcon={<Search className="w-3.5 h-3.5" />}
          />
        </div>

        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-700 bg-gray-50 hover:bg-gray-100 rounded-xl border border-gray-200 transition-colors"
        >
          {copied ? <Check className="w-3.5 h-3.5 text-green-600" /> : <Copy className="w-3.5 h-3.5" />}
          {copied ? 'Copied' : 'Copy Text'}
        </button>
      </div>

      {/* Page Viewer Box */}
      <div className="bg-white border border-gray-200 rounded-2xl p-6 sm:p-8 min-h-[500px] shadow-sm font-serif text-gray-800 leading-relaxed text-sm whitespace-pre-wrap select-text">
        {activePageData ? (
          activePageData.text || <span className="text-gray-400 italic">No extractable text found on this page.</span>
        ) : (
          <span className="text-gray-400 italic">No document pages available to display.</span>
        )}
      </div>
    </div>
  );
}
