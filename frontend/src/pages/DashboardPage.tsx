// @TASK P3-S1-T3 - Main dashboard page
// @SPEC main_supply_chain_dashboard design reference
// @TASK P4-S1-T1 - Side Panel (Company Detail) integration
// @TASK P4-S2-T1 - Filter Overlay Panel integration
import { useEffect, useState, useRef, useCallback } from 'react';
import api from '../services/api';
import type { Company, Cluster, CompanyRelation, Alert } from '../types/index';
import { ValueChainGraph } from '../components/graph/ValueChainGraph';
import { AlertBanner } from '../components/ui/AlertBanner';
import { FilterPanel } from '../components/graph/FilterPanel';
import { SidePanel } from '../components/graph/SidePanel';

// ─── Loading spinner ───────────────────────────────────────────────────────────

function Spinner() {
  return (
    <div className="flex items-center justify-center w-full h-full" role="status" aria-label="Loading dashboard">
      <svg
        aria-hidden="true"
        className="h-10 w-10 animate-spin text-primary"
        viewBox="0 0 24 24"
        fill="none"
      >
        <circle
          className="opacity-20"
          cx="12"
          cy="12"
          r="10"
          stroke="currentColor"
          strokeWidth="4"
        />
        <path
          className="opacity-80"
          fill="currentColor"
          d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
        />
      </svg>
    </div>
  );
}

// ─── Error state ───────────────────────────────────────────────────────────────

function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center w-full h-full gap-4 text-center px-4">
      <svg
        aria-hidden="true"
        viewBox="0 0 20 20"
        fill="currentColor"
        className="w-12 h-12 text-critical opacity-60"
      >
        <path
          fillRule="evenodd"
          d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
          clipRule="evenodd"
        />
      </svg>
      <p className="text-text-secondary text-sm max-w-xs">{message}</p>
      <button
        onClick={onRetry}
        className="px-4 py-2 rounded-lg bg-primary text-white text-sm font-medium hover:bg-primary-hover transition-colors"
      >
        Retry
      </button>
    </div>
  );
}

// ─── Filter toggle button ──────────────────────────────────────────────────────

function FilterToggleButton({
  isActive,
  hasFilter,
  onClick,
}: {
  isActive: boolean;
  hasFilter: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={isActive ? '필터 패널 닫기' : '기업 필터 열기'}
      aria-expanded={isActive}
      className={`relative flex items-center gap-2 px-4 py-2.5 rounded-lg shadow-lg transition-colors text-sm font-medium
        ${isActive
          ? 'bg-slate-700 hover:bg-slate-800 text-white'
          : 'bg-primary hover:bg-primary-hover text-white'
        }`}
    >
      <FilterIcon />
      필터
      {hasFilter && !isActive && (
        <span
          className="absolute -top-1 -right-1 w-3 h-3 bg-warning rounded-full border-2 border-white"
          aria-label="필터 적용 중"
        />
      )}
    </button>
  );
}

function FilterIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4" aria-hidden="true">
      <path
        fillRule="evenodd"
        d="M3 3a1 1 0 011-1h12a1 1 0 011 1v3a1 1 0 01-.293.707L12 11.414V15a1 1 0 01-.553.894l-4 2A1 1 0 016 17v-5.586L3.293 6.707A1 1 0 013 6V3z"
        clipRule="evenodd"
      />
    </svg>
  );
}

// ─── Dashboard data shape ──────────────────────────────────────────────────────

interface DashboardData {
  companies: Company[];
  clusters: Cluster[];
  relations: CompanyRelation[];
  alerts: Alert[];
}

// ─── Main component ────────────────────────────────────────────────────────────

export function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Ref to the graph's focusNode function — wired up by ValueChainGraph via onFocusRef
  const focusNodeRef = useRef<((companyId: number) => void) | null>(null);

  // ── P4-S1-T1: Selected company for side panel (null = panel closed) ───────────
  const [selectedCompanyId, setSelectedCompanyId] = useState<number | null>(null);

  // ── Filter panel state ────────────────────────────────────────────────────────
  const [filterPanelOpen, setFilterPanelOpen] = useState(false);
  // null = show all companies; number[] = show only those IDs
  const [selectedCompanyIds, setSelectedCompanyIds] = useState<number[] | null>(null);

  // ── Fetch all dashboard data in parallel ──────────────────────────────────────
  const loadData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [companiesRes, clustersRes, relationsRes, alertsRes] = await Promise.all([
        api.get<Company[]>('/companies'),
        api.get<Cluster[]>('/clusters'),
        api.get<CompanyRelation[]>('/relations'),
        api.get<Alert[]>('/alerts', { params: { is_read: false } }),
      ]);

      setData({
        companies: companiesRes.data,
        clusters:  clustersRes.data,
        relations: relationsRes.data,
        alerts:    alertsRes.data,
      });
    } catch {
      setError('Failed to load dashboard data. Please check your connection and try again.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // ── Graph node click → open side panel ───────────────────────────────────────
  const handleNodeClick = useCallback((companyId: number) => {
    setSelectedCompanyId(companyId);
  }, []);

  // ── Side panel close ──────────────────────────────────────────────────────────
  const handlePanelClose = useCallback(() => {
    setSelectedCompanyId(null);
  }, []);

  // ── Relation click → focus graph node + switch panel to that company ──────────
  const handleRelationClick = useCallback((companyId: number) => {
    focusNodeRef.current?.(companyId);
    setSelectedCompanyId(companyId);
  }, []);

  // ── Alert "View Details" → focus graph node ───────────────────────────────────
  const handleViewDetails = useCallback((companyId: number) => {
    focusNodeRef.current?.(companyId);
  }, []);

  // ── Alert dismiss updates local state ────────────────────────────────────────
  const handleAlertsChange = useCallback((updatedAlerts: Alert[]) => {
    setData((prev) => (prev ? { ...prev, alerts: updatedAlerts } : prev));
  }, []);

  // ── Render ────────────────────────────────────────────────────────────────────
  return (
    // Full-screen below fixed TopBar (h-14 = 56px), injected via AuthenticatedLayout
    <div className="flex flex-col dashboard-page-height">

      {/* Alert banner — zero height when no alerts */}
      {data && (
        <AlertBanner
          alerts={data.alerts}
          companies={data.companies}
          onViewDetails={handleViewDetails}
          onAlertsChange={handleAlertsChange}
        />
      )}

      {/* Graph area fills remaining space */}
      <div className="flex-1 min-h-0 relative">
        {isLoading && <Spinner />}

        {!isLoading && error && (
          <ErrorState message={error} onRetry={loadData} />
        )}

        {!isLoading && !error && data && (
          <ValueChainGraph
            companies={data.companies}
            clusters={data.clusters}
            relations={data.relations}
            alerts={data.alerts}
            filteredCompanyIds={selectedCompanyIds}
            onNodeClick={handleNodeClick}
            onFocusRef={focusNodeRef}
          />
        )}
      </div>

      {/* Filter toggle — floating bottom-right */}
      <div className="absolute bottom-6 right-6 z-20 pointer-events-none">
        <div className="pointer-events-auto">
          <FilterToggleButton
            isActive={filterPanelOpen}
            hasFilter={selectedCompanyIds !== null}
            onClick={() => setFilterPanelOpen((v) => !v)}
          />
        </div>
      </div>

      {/* Filter panel — rendered at this level so it overlays the graph */}
      {data && (
        <FilterPanel
          isOpen={filterPanelOpen}
          companies={data.companies}
          clusters={data.clusters}
          alerts={data.alerts}
          currentFilter={selectedCompanyIds}
          onApply={(ids) => setSelectedCompanyIds(ids)}
          onClose={() => setFilterPanelOpen(false)}
        />
      )}

      {/* P4-S1-T1: Company Detail Side Panel — overlays graph, slides in from right */}
      <SidePanel
        companyId={selectedCompanyId}
        onClose={handlePanelClose}
        onRelationClick={handleRelationClick}
      />
    </div>
  );
}
