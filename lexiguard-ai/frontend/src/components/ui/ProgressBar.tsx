import React from 'react';
import { cn } from '../../utils/cn';

interface ProgressBarProps {
  value: number;
  className?: string;
  color?: 'blue' | 'green' | 'amber';
  size?: 'sm' | 'md';
  label?: string;
}

const colors = { blue: 'bg-blue-500', green: 'bg-green-500', amber: 'bg-amber-500' };
const heights = { sm: 'h-1.5', md: 'h-2' };

export function ProgressBar({ value, className, color = 'blue', size = 'sm', label }: ProgressBarProps) {
  const clamped = Math.min(100, Math.max(0, value));
  return (
    <div className={className}>
      {label && (
        <div className="flex justify-between items-center mb-1.5">
          <span className="text-xs text-gray-600">{label}</span>
          <span className="text-xs font-medium text-gray-900">{clamped}%</span>
        </div>
      )}
      <div className={cn('w-full bg-gray-100 rounded-full overflow-hidden', heights[size])}>
        <div
          className={cn('rounded-full transition-all duration-500', colors[color], heights[size])}
          style={{ width: `${clamped}%` }}
          role="progressbar" aria-valuenow={clamped} aria-valuemin={0} aria-valuemax={100}
        />
      </div>
    </div>
  );
}
