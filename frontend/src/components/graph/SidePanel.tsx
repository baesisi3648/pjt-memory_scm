// @TASK P4-S1-T1 - Company Detail Side Panel
// @SPEC company_detail_side_panel design reference
import { useEffect, useRef, useCallback, useReducer } from 'react';
import api from '../../services/api';
import type { Alert, NewsItem, CompanyRelation, Severity, Tier } from '../../types/index';

// ─── Extended types for panel-specific API responses ──────────────────────────

interface CompanyDetail {
  id: number;
  name: string;
  name_kr: string;
  cluster_id: number;
  tier: Tier;
  country: string;
  description?: string;
}

interface PanelRelation {
  id: number;
  company_id: number;
  company_name: string;
  relation_type: string;
  strength: number;
  direction: 'upstream' | 'downstream';
}

// ─── Panel data state shape ────────────────────────────────────────────────────

interface PanelData {
  company: CompanyDetail | null;
  alerts: Alert[];
  news: NewsItem[];
  relations: PanelRelation[];
}

type PanelState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: PanelData }
  | { status: 'error'; message: string };

type PanelAction =
  | { type: 'FETCH_START' }
  | { type: 'FETCH_SUCCESS'; data: PanelData }
  | { type: 'FETCH_ERROR'; message: string }
  | { type: 'RESET' };

function panelReducer(_state: PanelState, action: PanelAction): PanelState {
  switch (action.type) {
    case 'FETCH_START':  return { status: 'loading' };
    case 'FETCH_SUCCESS': return { status: 'success', data: action.data };
    case 'FETCH_ERROR':  return { status: 'error', message: action.message };
    case 'RESET':        return { status: 'idle' };
    default:             return _state;
  }
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

/** Tier display labels */
const TIER_LABELS: Record<Tier, string> = {
  raw_material: 'Raw Material',
  equipment:    'Equipment',
  fab:          'FAB',
  packaging:    'Packaging',
  module:       'Module',
};

/** Tier badge colors (bg + text) */
const TIER_BADGE_COLORS: Record<Tier, string> = {
  raw_material: 'bg-indigo-100 text-indigo-700',
  equipment:    'bg-purple-100 text-purple-700',
  fab:          'bg-blue-100 text-blue-700',
  packaging:    'bg-emerald-100 text-emerald-700',
  module:       'bg-amber-100 text-amber-700',
};

/** Severity alert styles */
const SEVERITY_STYLES: Record<Severity, { border: string; bg: string; badge: string; icon: string }> = {
  critical: {
    border: 'border-l-4 border-l-red-500',
    bg:     'bg-red-50',
    badge:  'bg-red-100 text-red-700',
    icon:   'text-red-500',
  },
  warning: {
    border: 'border-l-4 border-l-amber-400',
    bg:     'bg-amber-50',
    badge:  'bg-amber-100 text-amber-700',
    icon:   'text-amber-500',
  },
  info: {
    border: 'border-l-4 border-l-blue-400',
    bg:     'bg-blue-50',
    badge:  'bg-blue-100 text-blue-700',
    icon:   'text-blue-500',
  },
};

/** Country code → flag emoji (limited set; falls back gracefully) */
function countryFlag(country: string): string {
  const map: Record<string, string> = {
    'KR': '🇰🇷', 'US': '🇺🇸', 'JP': '🇯🇵', 'NL': '🇳🇱',
    'TW': '🇹🇼', 'CN': '🇨🇳', 'DE': '🇩🇪', 'GB': '🇬🇧',
    'South Korea': '🇰🇷', 'USA': '🇺🇸', 'Japan': '🇯🇵',
    'Netherlands': '🇳🇱', 'Taiwan': '🇹🇼', 'China': '🇨🇳',
    'Germany': '🇩🇪', 'UK': '🇬🇧',
  };
  return map[country] ?? '🌐';
}

/** Format ISO date string as "X time ago" */
function timeAgo(isoString: string): string {
  const diff = Date.now() - new Date(isoString).getTime();
  const minutes = Math.floor(diff / 60_000);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

/** Clamp strength 0-1 → integer percent (0–100) */
function strengthPct(strength: number): number {
  return Math.round(Math.max(0, Math.min(1, strength)) * 100);
}

/** Initials from company name */
function initials(name: string): string {
  return name
    .split(/\s+/)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() ?? '')
    .join('');
}

// ─── Sub-components ────────────────────────────────────────────────────────────

// Close button icon
function CloseIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5" aria-hidden="true">
      <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
    </svg>
  );
}

// Arrow right icon for relation chevron
function ChevronRightIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4" aria-hidden="true">
      <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd" />
    </svg>
  );
}

// Warning icon for issue summary header
function WarningIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" className={className ?? 'w-4 h-4'} aria-hidden="true">
      <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
    </svg>
  );
}

// News article icon
function NewsIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5" aria-hidden="true">
      <path fillRule="evenodd" d="M2 5a2 2 0 012-2h8a2 2 0 012 2v10a2 2 0 002 2H4a2 2 0 01-2-2V5zm3 1h6v4H5V6zm6 6H5v2h6v-2z" clipRule="evenodd" />
      <path d="M15 7h1a2 2 0 012 2v5.5a1.5 1.5 0 01-3 0V7z" />
    </svg>
  );
}

// Arrow up/down for upstream/downstream
function UpstreamIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" className="w-3.5 h-3.5" aria-hidden="true">
      <path fillRule="evenodd" d="M10 3a1 1 0 011 1v10.586l2.293-2.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 111.414-1.414L9 14.586V4a1 1 0 011-1z" clipRule="evenodd" />
    </svg>
  );
}

function DownstreamIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" className="w-3.5 h-3.5 rotate-180" aria-hidden="true">
      <path fillRule="evenodd" d="M10 3a1 1 0 011 1v10.586l2.293-2.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 111.414-1.414L9 14.586V4a1 1 0 011-1z" clipRule="evenodd" />
    </svg>
  );
}

// ─── Loading skeleton ──────────────────────────────────────────────────────────

function SkeletonBlock({ className }: { className?: string }) {
  return (
    <div
      className={`animate-pulse bg-slate-200 rounded ${className ?? ''}`}
      aria-hidden="true"
    />
  );
}

function PanelSkeleton() {
  return (
    <div className="flex flex-col h-full" aria-label="Loading company details" role="status">
      {/* Header skeleton */}
      <div className="p-6 border-b border-slate-100">
        <div className="flex justify-between items-start mb-4">
          <SkeletonBlock className="w-14 h-14 rounded-lg" />
          <SkeletonBlock className="w-8 h-8 rounded-lg" />
        </div>
        <SkeletonBlock className="w-48 h-6 mb-2" />
        <SkeletonBlock className="w-32 h-4 mb-2" />
        <SkeletonBlock className="w-40 h-4" />
      </div>

      {/* Section skeletons */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        <SkeletonBlock className="w-28 h-4 mb-3" />
        <SkeletonBlock className="h-20 rounded-lg" />
        <SkeletonBlock className="h-20 rounded-lg" />
        <SkeletonBlock className="w-28 h-4 mt-4 mb-3" />
        <SkeletonBlock className="h-14 rounded-lg" />
        <SkeletonBlock className="h-14 rounded-lg" />
        <SkeletonBlock className="h-14 rounded-lg" />
      </div>
    </div>
  );
}

// ─── Panel header ──────────────────────────────────────────────────────────────

interface PanelHeaderProps {
  company: CompanyDetail;
  onClose: () => void;
}

function PanelHeader({ company, onClose }: PanelHeaderProps) {
  const badgeClass = TIER_BADGE_COLORS[company.tier] ?? 'bg-slate-100 text-slate-600';
  const tierLabel  = TIER_LABELS[company.tier] ?? company.tier;
  const flag       = countryFlag(company.country);

  return (
    <div className="p-6 border-b border-slate-100 flex-shrink-0">
      {/* Logo placeholder + close */}
      <div className="flex justify-between items-start mb-4">
        <div className="w-14 h-14 rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-center">
          <span className="text-lg font-bold text-slate-400" aria-hidden="true">
            {initials(company.name)}
          </span>
        </div>
        <button
          onClick={onClose}
          aria-label="Close company detail panel"
          className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
        >
          <CloseIcon />
        </button>
      </div>

      {/* Name + flag */}
      <div className="flex items-center gap-2 mb-1">
        <h2 className="text-xl font-bold text-slate-900 leading-tight">{company.name}</h2>
        <span aria-label={`Country: ${company.country}`}>{flag}</span>
      </div>

      {/* Tier badge + label */}
      <div className="flex items-center gap-2 mb-2">
        <span className={`px-2 py-0.5 rounded text-xs font-semibold uppercase tracking-wide ${badgeClass}`}>
          {tierLabel}
        </span>
        <span className="text-xs text-slate-500">Manufacturing Node</span>
      </div>

      {/* Meta */}
      <p className="text-sm text-slate-500 leading-relaxed">
        {company.country}
        {company.description && (
          <>
            <br />
            <span className="line-clamp-2">{company.description}</span>
          </>
        )}
      </p>
    </div>
  );
}

// ─── Issue summary section ─────────────────────────────────────────────────────

function IssueSummary({ alerts }: { alerts: Alert[] }) {
  if (alerts.length === 0) {
    return (
      <div className="p-6 pb-4">
        <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-3">
          Issue Summary
        </h3>
        <p className="text-sm text-slate-400 italic">No active alerts</p>
      </div>
    );
  }

  return (
    <div className="p-6 pb-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider">
          Issue Summary
        </h3>
        <WarningIcon className="w-4 h-4 text-red-500" />
      </div>

      <div className="flex flex-col gap-3">
        {alerts.map((alert) => {
          const styles = SEVERITY_STYLES[alert.severity];
          return (
            <div
              key={alert.id}
              className={`rounded-lg p-4 ${styles.bg} ${styles.border} hover:shadow-sm transition-shadow cursor-default`}
            >
              {/* Severity badge */}
              <div className="flex items-center gap-2 mb-1.5">
                <span className={`text-xs font-bold uppercase px-2 py-0.5 rounded-full ${styles.badge}`}>
                  {alert.severity}
                </span>
              </div>

              {/* Alert title */}
              <h4 className="text-sm font-semibold text-slate-900 mb-0.5 leading-snug">
                {alert.title}
              </h4>

              {/* Description */}
              {alert.description && (
                <p className="text-xs text-slate-600 mb-2 leading-relaxed line-clamp-2">
                  {alert.description}
                </p>
              )}

              {/* Time */}
              <p className={`text-xs ${styles.icon} font-medium`}>
                {timeAgo(alert.created_at)}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── Related news section ──────────────────────────────────────────────────────

function RelatedNews({ news }: { news: NewsItem[] }) {
  if (news.length === 0) {
    return (
      <div className="p-6 pt-2 border-t border-slate-100">
        <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-3 mt-2">
          Related News
        </h3>
        <p className="text-sm text-slate-400 italic">No recent news</p>
      </div>
    );
  }

  return (
    <div className="p-6 pt-2 border-t border-slate-100">
      <div className="flex items-center justify-between mb-4 mt-2">
        <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider">
          Related News
        </h3>
      </div>

      <div className="flex flex-col gap-1">
        {news.slice(0, 5).map((item) => (
          <a
            key={item.id}
            href={item.url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex gap-3 group hover:bg-slate-50 p-2 -mx-2 rounded-lg transition-colors"
            aria-label={`${item.title} — opens in new tab`}
          >
            {/* Icon */}
            <div className="shrink-0 w-10 h-10 rounded bg-slate-100 flex items-center justify-center text-slate-400 group-hover:bg-slate-200 transition-colors">
              <NewsIcon />
            </div>

            {/* Text */}
            <div className="flex flex-col min-w-0">
              <h5 className="text-sm font-medium text-slate-900 leading-snug group-hover:text-primary transition-colors line-clamp-2">
                {item.title}
              </h5>
              <span className="text-xs text-slate-400 mt-0.5">
                {item.source}
                {item.published_at && ` · ${timeAgo(item.published_at)}`}
              </span>
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}

// ─── Relations section ─────────────────────────────────────────────────────────

interface RelationItemProps {
  relation: PanelRelation;
  onClick: (companyId: number) => void;
}

function RelationItem({ relation, onClick }: RelationItemProps) {
  const abbr = initials(relation.company_name);
  const pct  = strengthPct(relation.strength);

  return (
    <button
      type="button"
      onClick={() => onClick(relation.company_id)}
      className="w-full flex items-center justify-between p-2 rounded-lg hover:bg-slate-50 transition-colors group text-left"
      aria-label={`View details for ${relation.company_name}`}
    >
      <div className="flex items-center gap-3 min-w-0">
        {/* Avatar */}
        <div className="w-8 h-8 shrink-0 rounded bg-blue-100 text-blue-600 flex items-center justify-center text-xs font-bold">
          {abbr}
        </div>

        {/* Info */}
        <div className="min-w-0">
          <p className="text-sm font-medium text-slate-900 group-hover:text-primary transition-colors truncate">
            {relation.company_name}
          </p>
          <div className="flex items-center gap-2 mt-0.5">
            {/* Relation type badge */}
            <span className="text-xs text-slate-400 capitalize">{relation.relation_type}</span>
            {/* Strength bar — width driven by --strength CSS var (no inline style) */}
            <div className="flex items-center gap-1">
              <div className={`w-12 h-1 bg-slate-200 rounded-full overflow-hidden [--strength:${pct}%]`}>
                <div
                  className="strength-bar h-full bg-primary rounded-full"
                  aria-label={`Relation strength: ${pct}%`}
                />
              </div>
              <span className="text-xs text-slate-400">{pct}%</span>
            </div>
          </div>
        </div>
      </div>

      {/* Chevron */}
      <span className="text-slate-300 group-hover:text-primary transition-colors shrink-0 ml-2">
        <ChevronRightIcon />
      </span>
    </button>
  );
}

interface RelationsProps {
  relations: PanelRelation[];
  onRelationClick: (companyId: number) => void;
}

function Relations({ relations, onRelationClick }: RelationsProps) {
  const upstream   = relations.filter((r) => r.direction === 'upstream');
  const downstream = relations.filter((r) => r.direction === 'downstream');

  if (relations.length === 0) {
    return (
      <div className="p-6 pt-2 border-t border-slate-100">
        <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-3 mt-2">
          Relations
        </h3>
        <p className="text-sm text-slate-400 italic">No known relations</p>
      </div>
    );
  }

  return (
    <div className="p-6 pt-2 border-t border-slate-100">
      <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-4 mt-2">
        Relations
      </h3>

      {/* Upstream */}
      {upstream.length > 0 && (
        <div className="mb-4">
          <p className="flex items-center gap-1 text-xs font-semibold text-slate-500 mb-2">
            <UpstreamIcon />
            Upstream (Suppliers)
          </p>
          <div className="space-y-0.5">
            {upstream.map((rel) => (
              <RelationItem key={rel.id} relation={rel} onClick={onRelationClick} />
            ))}
          </div>
        </div>
      )}

      {/* Downstream */}
      {downstream.length > 0 && (
        <div>
          <p className="flex items-center gap-1 text-xs font-semibold text-slate-500 mb-2">
            <DownstreamIcon />
            Downstream (Customers)
          </p>
          <div className="space-y-0.5">
            {downstream.map((rel) => (
              <RelationItem key={rel.id} relation={rel} onClick={onRelationClick} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Error state ───────────────────────────────────────────────────────────────

function PanelError({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center gap-3 p-8 text-center">
      <WarningIcon className="w-8 h-8 text-red-400" />
      <p className="text-sm text-slate-500">{message}</p>
      <button
        onClick={onRetry}
        className="px-4 py-2 bg-primary text-white text-sm font-medium rounded-lg hover:bg-primary-hover transition-colors"
      >
        Retry
      </button>
    </div>
  );
}

// ─── Main SidePanel component ──────────────────────────────────────────────────

export interface SidePanelProps {
  /** ID of the company to display; null/undefined means panel is hidden */
  companyId: number | null;
  /** Called when panel should close */
  onClose: () => void;
  /** Called when a relation is clicked — parent should focus graph + change companyId */
  onRelationClick: (companyId: number) => void;
}

export function SidePanel({ companyId, onClose, onRelationClick }: SidePanelProps) {
  const [state, dispatch] = useReducer(panelReducer, { status: 'idle' });

  // Track which companyId is currently being loaded to ignore stale responses
  const loadingIdRef = useRef<number | null>(null);

  // ── Data fetching ────────────────────────────────────────────────────────────
  const loadCompanyData = useCallback(async (id: number) => {
    loadingIdRef.current = id;
    dispatch({ type: 'FETCH_START' });

    try {
      const [companyRes, alertsRes, newsRes, relationsRes] = await Promise.all([
        api.get<CompanyDetail>(`/companies/${id}`),
        api.get<Alert[]>(`/companies/${id}/alerts`),
        api.get<NewsItem[]>(`/companies/${id}/news`, { params: { limit: 5 } }),
        api.get<PanelRelation[]>(`/companies/${id}/relations`),
      ]);

      // Guard against stale responses
      if (loadingIdRef.current !== id) return;

      dispatch({
        type: 'FETCH_SUCCESS',
        data: {
          company:   companyRes.data,
          alerts:    alertsRes.data,
          news:      newsRes.data,
          relations: relationsRes.data,
        },
      });
    } catch {
      if (loadingIdRef.current !== id) return;
      dispatch({
        type: 'FETCH_ERROR',
        message: 'Failed to load company details. Please try again.',
      });
    }
  }, []);

  useEffect(() => {
    if (companyId !== null && companyId !== undefined) {
      loadCompanyData(companyId);
    } else {
      dispatch({ type: 'RESET' });
      loadingIdRef.current = null;
    }
  }, [companyId, loadCompanyData]);

  // ── Click-outside to close ───────────────────────────────────────────────────
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (companyId === null) return;

    function handleClickOutside(e: MouseEvent) {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        onClose();
      }
    }

    // Delay binding to prevent the node-click that opened the panel from immediately closing it
    const timerId = setTimeout(() => {
      document.addEventListener('mousedown', handleClickOutside);
    }, 100);

    return () => {
      clearTimeout(timerId);
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [companyId, onClose]);

  // ── Keyboard: Escape to close ────────────────────────────────────────────────
  useEffect(() => {
    if (companyId === null) return;

    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose();
    }

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [companyId, onClose]);

  // ── Visibility: panel is open when companyId is not null ─────────────────────
  const isOpen = companyId !== null;

  // ── Render ───────────────────────────────────────────────────────────────────
  return (
    /*
     * Slide-in wrapper:
     *   - Fixed position on the right side, full height below the TopBar
     *   - translate-x-full when closed, translate-x-0 when open
     *   - z-40: above the graph canvas (z-10/z-20) but below modals
     *   - 200ms CSS transition on transform
     */
    <div
      ref={panelRef}
      role="complementary"
      aria-label="Company detail panel"
      aria-hidden={!isOpen}
      className={[
        'fixed top-14 right-0 bottom-0 w-[400px]',
        'bg-white border-l border-slate-200',
        'shadow-[-10px_0_30px_-15px_rgba(0,0,0,0.15)]',
        'flex flex-col',
        'z-40',
        'transition-transform duration-200 ease-in-out',
        isOpen ? 'translate-x-0' : 'translate-x-full',
      ].join(' ')}
    >
      {/* ── Loading ─────────────────────────────────────────────────────────── */}
      {state.status === 'loading' && <PanelSkeleton />}

      {/* ── Error ───────────────────────────────────────────────────────────── */}
      {state.status === 'error' && (
        <>
          {/* Minimal header with close button even on error */}
          <div className="flex justify-end p-4 border-b border-slate-100">
            <button
              onClick={onClose}
              aria-label="Close panel"
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
            >
              <CloseIcon />
            </button>
          </div>
          <PanelError
            message={state.message}
            onRetry={() => companyId !== null && loadCompanyData(companyId)}
          />
        </>
      )}

      {/* ── Success ─────────────────────────────────────────────────────────── */}
      {state.status === 'success' && state.data.company && (
        <>
          {/* Header — fixed at top, does not scroll */}
          <PanelHeader company={state.data.company} onClose={onClose} />

          {/* Scrollable content */}
          <div className="flex-1 overflow-y-auto" tabIndex={-1}>
            <IssueSummary alerts={state.data.alerts} />
            <RelatedNews news={state.data.news} />
            <Relations
              relations={state.data.relations}
              onRelationClick={onRelationClick}
            />
            {/* Bottom padding so last section is not flush with edge */}
            <div className="h-6" aria-hidden="true" />
          </div>
        </>
      )}

      {/* ── Idle (panel just opened but no data yet) ─────────────────────────── */}
      {state.status === 'idle' && isOpen && <PanelSkeleton />}
    </div>
  );
}
