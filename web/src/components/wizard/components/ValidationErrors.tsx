/**
 * ValidationErrors Component
 * Displays validation errors in a styled alert
 */

import React from 'react';
import { AlertCircle } from 'lucide-react';

interface ValidationErrorsProps {
  errors: string[];
}

export function ValidationErrors({ errors }: ValidationErrorsProps) {
  if (errors.length === 0) return null;

  return (
    <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20">
      <div className="flex items-start gap-3">
        <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
        <div className="flex-1">
          <h4 className="text-sm font-medium text-red-400 mb-2">
            Por favor, corrija os seguintes campos:
          </h4>
          <ul className="space-y-1">
            {errors.map((error, idx) => (
              <li
                key={idx}
                className="text-sm text-red-300/80 flex items-start gap-2"
              >
                <span className="text-red-400/60 mt-1">•</span>
                <span>{error}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}

export default ValidationErrors;
