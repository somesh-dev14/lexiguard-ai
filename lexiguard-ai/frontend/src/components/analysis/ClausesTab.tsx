import React, { useState } from 'react';
import type { Clause } from '../../types';
import { Badge } from '../ui/Badge';
import { Search, ChevronDown, ChevronRight, FileSearch } from 'lucide-react';
import { Input } from '../ui/Input';

interface ClausesTabProps {
  clauses: Clause[];
  onNavigateToSource?: (page: number) => void;
}

export function ClausesTab({ clauses, onNavigateToSource }: ClausesTabProps) {
  const [search, setSearch] = useState('');
  const [selectedType, setSelectedType] = useState<string>('All');
  const [expandedIds, setExpandedIds] = useState<Record<string, boolean>>({});

  const types = ['All', ...Array.from(new Set(clauses.map(c => c.type)))];

  const filtered = clauses.filter(c => {
    const matchesSearch = c.heading.toLowerCase().includes(search.toLowerCase()) ||
                          c.text.toLowerCase().includes(search.toLowerCase());
    const matchesType = selectedType === 'All' || c.type === selectedType;
    return matchesSearch && matchesType;
  });

  const toggleExpand = (id: string) => {
    setExpandedIds(prev => ({ ...prev, [id]: !prev[id] }));
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="flex-1">
          <Input
            placeholder="Search clause headings or text..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            leftIcon={<Search className="w-4 h-4" />}
          />
        </div>
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
          {types.map(t => (
            <button
              key={t}
              onClick={() => setSelectedType(t)}
              className={`px-3 py-1.5 rounded-xl text-xs font-medium whitespace-nowrap transition-colors ${
                selectedType === t
                  ? 'bg-gray-900 text-white'
                  : 'bg-white border border-gray-200 text-gray-600 hover:bg-gray-50'
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-3">
        {filtered.length === 0 ? (
          <div className="text-center py-12 bg-white rounded-2xl border border-gray-100">
            <p className="text-sm text-gray-500">No clauses match your filter criteria.</p>
          </div>
        ) : (
          filtered.map(clause => {
            const isExpanded = !!expandedIds[clause.id];
            return (
              <div
                key={clause.id}
                className="bg-white border border-gray-200/80 rounded-2xl overflow-hidden hover:border-gray-300 transition-all"
              >
                <div
                  onClick={() => toggleExpand(clause.id)}
                  className="p-4 flex items-center justify-between cursor-pointer select-none"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-gray-400">
                      {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                    </span>
                    <div>
                      <h4 className="font-semibold text-gray-900 text-sm sm:text-base">
                        {clause.original_heading || clause.heading}
                      </h4>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="text-xs font-medium text-gray-500 bg-gray-100 px-2 py-0.5 rounded">
                          {clause.predicted_category || clause.type}
                        </span>
                        {(clause.page_span || clause.page) && (
                          <span className="text-xs text-blue-600 bg-blue-50 px-2 py-0.5 rounded-md font-mono">
                            Page {clause.page_span || clause.page}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  {clause.demo && <Badge variant="demo">Demo</Badge>}
                </div>

                {isExpanded && (
                  <div className="px-5 pb-5 pt-2 border-t border-gray-50 bg-gray-50/30 space-y-3">
                    <div className="p-3 bg-white rounded-xl border border-gray-100 text-sm text-gray-700 font-mono leading-relaxed whitespace-pre-wrap">
                      {clause.text}
                    </div>

                    {clause.page && onNavigateToSource && (
                      <div className="flex justify-end">
                        <button
                          onClick={() => onNavigateToSource(clause.page!)}
                          className="text-xs font-medium text-blue-600 hover:text-blue-800 flex items-center gap-1.5"
                        >
                          <FileSearch className="w-3.5 h-3.5" />
                          View in Source Document (Page {clause.page_span || clause.page})
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
