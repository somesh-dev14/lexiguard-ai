import React from 'react';
import { Outlet } from 'react-router-dom';
import { Navbar } from './Navbar';
import { useBackendStatus } from '../../hooks/useBackendStatus';

export function AppLayout() {
  const { status, aiMode } = useBackendStatus();

  const aiModeLabel = () => {
    if (status === 'offline') return 'Backend offline';
    if (aiMode === 'demo') return 'Demo mode (AI not connected)';
    return 'AI Active';
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>
      <footer className="border-t border-gray-100 mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 flex flex-col md:flex-row items-center justify-between gap-3">
          <p className="text-sm text-gray-400">
            &copy; {new Date().getFullYear()} LexiGuard AI &mdash; For informational purposes only. Not legal advice.
          </p>
          <p className="text-xs text-gray-400">
            AI integration: <span className="font-medium text-gray-600">{aiModeLabel()}</span>
          </p>
        </div>
      </footer>
    </div>
  );
}
