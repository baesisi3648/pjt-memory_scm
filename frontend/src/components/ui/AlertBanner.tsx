// @TASK P3-S1-T2 - Alert notification banner
// @SPEC main_supply_chain_dashboard design reference
import { useState, useEffect, useCallback } from 'react';
import api from '../../services/api';
import type { Alert, Company } from '../../types/index';

// ─── Props ─────────────────────────────────────────────────────────────────────

interface AlertBannerProps {
  alerts: Alert[];
  companies: Company[];
  onViewDetails: (companyId: number) => void;
  onAlertsChange: (updatedAlerts: Alert[]) => void;
}

// ─── Severity config ───────────────────────────────────────────────────────────

const SEVERITY_CLASSES = {
  critical: {
    wrapper: 'bg-red-50 border-b border-red-100',
    text:    'text-red-700',
    button:  'text-red-600 hover:text-red-800',
    icon:    'text-red-500',
  },
  warning: {
    wrapper: 'bg-amber-50 border-b border-amber-100',
    text:    'text-amber-700',
    button:  'text-amber-600 hover:text-amber-800',
    icon:    'text-amber-500',
  },
  info: {
    wrapper: 'bg-blue-50 border-b border-blue-100',
    text:    'text-blue-700',
    button:  'text-blue-600 hover:text-blue-800',
    icon:    'text-blue-500',
  },
} as const;

// ─── Icons ─────────────────────────────────────────────────────────────────────

function CriticalIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 flex-shrink-0" aria-hidden="true">
      <path
        fillRule="evenodd"
        d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
        clipRule="evenodd"
      />
    </svg>
  );
}

function WarningIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 flex-shrink-0" aria-hidden="true">
      <path
        fillRule="evenodd"
        d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
        clipRule="evenodd"
      />
    </svg>
  );
}

function InfoIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 flex-shrink-0" aria-hidden="true">
      <path
        fillRule="evenodd"
        d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
        clipRule="evenodd"
      />
    </svg>
  );
}

function DismissIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" className="w-3.5 h-3.5" aria-hidden="true">
      <path
        fillRule="evenodd"
        d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
        clipRule="evenodd"
      />
    </svg>
  );
}

function getSeverityIcon(severity: Alert['severity']) {
  if (severity === 'critical') return <CriticalIcon />;
  if (severity === 'warning')  return <WarningIcon />;
  return <InfoIcon />;
}

// ─── Single alert row ──────────────────────────────────────────────────────────

interface AlertRowProps {
  alert: Alert;
  companyName: string | undefined;
  onViewDetails: () => void;
  onDismiss: () => void;
  isDismissing: boolean;
}

function AlertRow({ alert, companyName, onViewDetails, onDismiss, isDismissing }: AlertRowProps) {
  const cfg = SEVERITY_CLASSES[alert.severity] ?? SEVERITY_CLASSES.info;

  return (
    <div
      role="alert"
      aria-live="polite"
      className={`${cfg.wrapper} px-6 py-2 flex items-center justify-between gap-4 text-sm`}
    >
      {/* Left: icon + message */}
      <div className={`flex items-center gap-2 min-w-0 ${cfg.text}`}>
        <span className={cfg.icon}>{getSeverityIcon(alert.severity)}</span>
        <span className="font-medium truncate">
          <span className="capitalize">{alert.severity}</span>
          {': '}
          {alert.title}
          {companyName && (
            <span className="font-normal opacity-75"> — {companyName}</span>
          )}
        </span>
      </div>

      {/* Right: actions */}
      <div className="flex items-center gap-3 flex-shrink-0">
        <button
          onClick={onViewDetails}
          className={`text-xs font-semibold ${cfg.button} transition-colors whitespace-nowrap`}
        >
          View Details
        </button>
        <button
          onClick={onDismiss}
          disabled={isDismissing}
          aria-label="Dismiss alert"
          className={`${cfg.button} transition-colors disabled:opacity-40`}
        >
          <DismissIcon />
        </button>
      </div>
    </div>
  );
}

// ─── Main component ────────────────────────────────────────────────────────────

const MAX_VISIBLE = 3;

export function AlertBanner({
  alerts,
  companies,
  onViewDetails,
  onAlertsChange,
}: AlertBannerProps) {
  const [dismissing, setDismissing] = useState<Set<number>>(new Set());
  const [showAll, setShowAll] = useState(false);

  // Reset showAll when alert count drops at or below MAX_VISIBLE
  useEffect(() => {
    if (alerts.length <= MAX_VISIBLE) setShowAll(false);
  }, [alerts.length]);

  const companyMap = new Map(Array.isArray(companies) ? companies.map((c) => [c.id, c.name_kr || c.name]) : []);

  // Sort: critical first, then warning, then info
  const severityOrder: Record<Alert['severity'], number> = { critical: 0, warning: 1, info: 2 };
  const sorted = [...alerts].sort(
    (a, b) => severityOrder[a.severity] - severityOrder[b.severity],
  );

  const visible = showAll ? sorted : sorted.slice(0, MAX_VISIBLE);
  const hiddenCount = sorted.length - MAX_VISIBLE;

  const handleDismiss = useCallback(
    async (alertId: number) => {
      setDismissing((prev) => new Set(prev).add(alertId));
      try {
        await api.patch(`/alerts/${alertId}/read`);
        onAlertsChange(alerts.filter((a) => a.id !== alertId));
      } catch {
        // Optimistically keep the banner visible; dismiss silently fails
      } finally {
        setDismissing((prev) => {
          const next = new Set(prev);
          next.delete(alertId);
          return next;
        });
      }
    },
    [alerts, onAlertsChange],
  );

  const handleViewDetails = useCallback(
    (alert: Alert) => {
      onViewDetails(alert.company_id);
    },
    [onViewDetails],
  );

  if (alerts.length === 0) return null;

  return (
    <div className="flex flex-col shrink-0 z-40 relative" role="region" aria-label="Active alerts">
      {visible.map((alert) => (
        <AlertRow
          key={alert.id}
          alert={alert}
          companyName={companyMap.get(alert.company_id)}
          onViewDetails={() => handleViewDetails(alert)}
          onDismiss={() => handleDismiss(alert.id)}
          isDismissing={dismissing.has(alert.id)}
        />
      ))}

      {/* Show "+N more" toggle when alerts exceed MAX_VISIBLE */}
      {!showAll && hiddenCount > 0 && (
        <button
          onClick={() => setShowAll(true)}
          className="bg-slate-100 border-b border-slate-200 px-6 py-1 text-xs font-medium text-slate-500 hover:text-slate-700 hover:bg-slate-200 transition-colors text-left"
        >
          +{hiddenCount} more alert{hiddenCount > 1 ? 's' : ''}
        </button>
      )}
      {showAll && hiddenCount > 0 && (
        <button
          onClick={() => setShowAll(false)}
          className="bg-slate-100 border-b border-slate-200 px-6 py-1 text-xs font-medium text-slate-500 hover:text-slate-700 hover:bg-slate-200 transition-colors text-left"
        >
          Show fewer
        </button>
      )}
    </div>
  );
}
