// @TASK P3-S1-T3 - Main dashboard page
// @SPEC main_supply_chain_dashboard design reference
import { useEffect, useState, useRef, useCallback } from 'react';
import api from '../services/api';
import type { Company, Cluster, CompanyRelation, Alert } from '../types/index';
import { ValueChainGraph } from '../components/graph/ValueChainGraph';
import { AlertBanner } from '../components/ui/AlertBanner';

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

// ─── Filter placeholder button ─────────────────────────────────────────────────

function FilterButton() {
  return (
    <button
      aria-label="Filter supply chain (coming in P4)"
      title="Filter — coming in P4"
      className="flex items-center gap-2 bg-primary hover:bg-primary-hover text-white px-4 py-2.5 rounded-lg shadow-lg transition-colors text-sm font-medium"
    >
      <FilterIcon />
      Filter
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

  // ── Graph node click ──────────────────────────────────────────────────────────
  const handleNodeClick = useCallback((_companyId: number) => {
    // P4 will open the company side panel; handler wired, no action yet
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
            onNodeClick={handleNodeClick}
            onFocusRef={focusNodeRef}
          />
        )}
      </div>

      {/* Filter toggle — floating bottom-right, placeholder for P4 */}
      <div className="absolute bottom-6 right-6 z-20 pointer-events-none">
        {/* Positioned via parent relative; pointer-events re-enabled on button */}
        <div className="pointer-events-auto">
          <FilterButton />
        </div>
      </div>
    </div>
  );
}
