import {
  CheckCircle,
  Loader2,
  Clock,
  AlertCircle,
} from "lucide-react";
import React from 'react';

export function StatusTag({ status }: { status: string }) {
    const statusConfig: Record<
      string,
      { label: string; className: string; icon?: React.ReactNode }
    > = {
      submitted: {
        label: "SUBMITTED",
        className: "bg-blue-50 text-blue-700 border border-blue-200",
        icon: <Clock className="h-3 w-3" />,
      },
      processing: {
        label: "PROCESSING",
        className: "bg-amber-50 text-amber-700 border border-amber-200",
        icon: <Loader2 className="h-3 w-3 animate-spin" />,
      },
      processed: {
        label: "READY",
        className: "bg-green-50 text-green-700 border border-green-200",
        icon: <CheckCircle className="h-3 w-3" />,
      },
      error: {
        label: "ERROR",
        className: "bg-red-50 text-red-700 border border-red-200",
        icon: <AlertCircle className="h-3 w-3" />,
      },
    };
  
    const config = statusConfig[status] || {
      label: status.toUpperCase(),
      className: "bg-gray-50 text-gray-700 border border-gray-200",
    };
  
    return (
      <span
        className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-semibold tracking-wide ${config.className}`}
        aria-label={`Status: ${config.label}`}
      >
        {config.icon}
        {config.label}
      </span>
    );
  }
