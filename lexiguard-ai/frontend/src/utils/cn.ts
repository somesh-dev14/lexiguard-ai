import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

export function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

export function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);
  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return diffMins + 'm ago';
  if (diffHours < 24) return diffHours + 'h ago';
  if (diffDays < 7) return diffDays + 'd ago';
  return formatDate(dateString);
}

export function getRiskColor(severity: string): string {
  switch (severity) {
    case 'low': return 'text-green-700 bg-green-50 border-green-200';
    case 'medium': return 'text-amber-700 bg-amber-50 border-amber-200';
    case 'high': return 'text-red-700 bg-red-50 border-red-200';
    case 'critical': return 'text-purple-700 bg-purple-50 border-purple-200';
    default: return 'text-gray-700 bg-gray-50 border-gray-200';
  }
}

export function getRiskDot(severity: string): string {
  switch (severity) {
    case 'low': return 'bg-green-500';
    case 'medium': return 'bg-amber-500';
    case 'high': return 'bg-red-500';
    case 'critical': return 'bg-purple-600';
    default: return 'bg-gray-400';
  }
}
