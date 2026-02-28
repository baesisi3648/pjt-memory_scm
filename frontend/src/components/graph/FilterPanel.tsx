// @TASK P4-S2-T1 - Filter Overlay Panel
// @SPEC company_filter_overlay design reference
import { useEffect, useMemo, useRef, useState } from 'react';
import api from '../../services/api';
import type { Company, Cluster, Alert, UserFilter } from '../../types/index';

// ─── Tier preset configuration ────────────────────────────────────────────────

type TierPreset = 'all' | 'fab' | 'equipment' | 'raw_material';

const TIER_PRESET_LABELS: Record<TierPreset, string> = {
  all:          '전체',
  fab:          '메모리 제조사',
  equipment:    '장비사',
  raw_material: '원자재',
};

// ─── Small icons (inline SVG — no extra deps) ─────────────────────────────────

function SearchIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5" aria-hidden="true">
      <path fillRule="evenodd" d="M9 3a6 6 0 100 12A6 6 0 009 3zM1 9a8 8 0 1114.32 4.906l4.387 4.387a1 1 0 01-1.414 1.414l-4.387-4.387A8 8 0 011 9z" clipRule="evenodd" />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5" aria-hidden="true">
      <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
    </svg>
  );
}

function ChevronDownIcon({ open }: { open: boolean }) {
  return (
    <svg
      viewBox="0 0 20 20"
      fill="currentColor"
      className={`w-5 h-5 transition-transform duration-200 ${open ? 'rotate-180' : ''}`}
      aria-hidden="true"
    >
      <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
    </svg>
  );
}

function RefreshIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4" aria-hidden="true">
      <path fillRule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clipRule="evenodd" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4" aria-hidden="true">
      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
    </svg>
  );
}

// ─── Alert dot ─────────────────────────────────────────────────────────────────

function AlertDot({ severity }: { severity: 'critical' | 'warning' }) {
  const cls =
    severity === 'critical'
      ? 'bg-red-500'
      : 'bg-amber-400';
  return (
    <span
      className={`inline-block w-2 h-2 rounded-full flex-shrink-0 ${cls}`}
      aria-label={severity === 'critical' ? '위험 경보' : '경고'}
    />
  );
}

// ─── Cluster Accordion section ─────────────────────────────────────────────────

interface ClusterSectionProps {
  cluster: Cluster;
  companies: Company[];
  alertMap: Map<number, 'critical' | 'warning'>;
  selected: Set<number>;
  searchQuery: string;
  onToggle: (id: number) => void;
}

function ClusterSection({
  cluster,
  companies,
  alertMap,
  selected,
  searchQuery,
  onToggle,
}: ClusterSectionProps) {
  const [open, setOpen] = useState(true);

  // Filter companies by search query
  const filtered = useMemo(() => {
    if (!searchQuery) return companies;
    const q = searchQuery.toLowerCase();
    return companies.filter(
      (c) =>
        c.name.toLowerCase().includes(q) ||
        c.name_kr.toLowerCase().includes(q),
    );
  }, [companies, searchQuery]);

  // Auto-open when a search narrows results
  useEffect(() => {
    if (searchQuery && filtered.length > 0) setOpen(true);
  }, [searchQuery, filtered.length]);

  const selectedCount = companies.filter((c) => selected.has(c.id)).length;
  const hasPartialSelection = selectedCount > 0 && selectedCount < companies.length;
  const badgeClass =
    selectedCount > 0
      ? 'bg-blue-100 text-blue-700'
      : 'bg-slate-100 text-slate-500';

  // Hide entire section if search returns no results
  if (searchQuery && filtered.length === 0) return null;

  return (
    <div className="rounded-xl border border-slate-200 bg-white overflow-hidden">
      {/* Accordion header */}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-4 py-3 bg-slate-50 hover:bg-slate-100 transition-colors select-none text-left"
        aria-expanded={open}
      >
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-slate-800">{cluster.name}</span>
          <span className={`px-1.5 py-0.5 rounded-md text-[10px] font-bold ${badgeClass}`}>
            {selectedCount}/{companies.length}
          </span>
          {hasPartialSelection && (
            <span className="w-1.5 h-1.5 rounded-full bg-primary flex-shrink-0" />
          )}
        </div>
        <ChevronDownIcon open={open} />
      </button>

      {/* Company checkboxes */}
      {open && (
        <div className="px-4 pb-3 pt-1 space-y-0.5 border-t border-slate-100">
          {filtered.map((company) => {
            const alertSeverity = alertMap.get(company.id);
            const isChecked = selected.has(company.id);
            return (
              <label
                key={company.id}
                className="flex items-center gap-3 p-2 rounded-lg hover:bg-slate-50 cursor-pointer group transition-colors"
              >
                <input
                  type="checkbox"
                  checked={isChecked}
                  onChange={() => onToggle(company.id)}
                  className="w-4 h-4 rounded border-slate-300 text-primary focus:ring-primary focus:ring-offset-0 cursor-pointer transition-colors"
                />
                <span className="flex-1 text-sm text-slate-700 group-hover:text-primary transition-colors">
                  {company.name_kr || company.name}
                </span>
                {alertSeverity && <AlertDot severity={alertSeverity} />}
              </label>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ─── Preset Pills ──────────────────────────────────────────────────────────────

interface PresetPillProps {
  label: string;
  active: boolean;
  onClick: () => void;
}

function PresetPill({ label, active, onClick }: PresetPillProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`px-3 py-1.5 text-xs font-medium rounded-full transition-colors ${
        active
          ? 'bg-primary text-white shadow-sm'
          : 'bg-slate-100 border border-slate-200 text-slate-500 hover:text-primary hover:border-primary'
      }`}
    >
      {label}
    </button>
  );
}

// ─── Saved preset row ──────────────────────────────────────────────────────────

interface SavedPresetRowProps {
  preset: UserFilter;
  onLoad: (ids: number[]) => void;
  onDelete: (id: number) => void;
}

function SavedPresetRow({ preset, onLoad, onDelete }: SavedPresetRowProps) {
  return (
    <div className="flex items-center justify-between py-1.5 px-2 rounded-lg hover:bg-slate-50 group transition-colors">
      <button
        type="button"
        onClick={() => onLoad(preset.company_ids)}
        className="flex-1 text-left text-sm text-slate-700 group-hover:text-primary transition-colors truncate"
      >
        {preset.name}
        <span className="ml-1 text-xs text-slate-400">({preset.company_ids.length}개)</span>
      </button>
      <button
        type="button"
        onClick={() => onDelete(preset.id)}
        aria-label={`${preset.name} 삭제`}
        className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-red-50 text-slate-400 hover:text-red-500 transition-all"
      >
        <CloseIcon />
      </button>
    </div>
  );
}

// ─── Props ─────────────────────────────────────────────────────────────────────

export interface FilterPanelProps {
  isOpen: boolean;
  companies: Company[];
  clusters: Cluster[];
  alerts: Alert[];
  currentFilter: number[] | null;
  onApply: (selectedIds: number[] | null) => void;
  onClose: () => void;
}

// ─── Main FilterPanel component ────────────────────────────────────────────────

export function FilterPanel({
  isOpen,
  companies,
  clusters,
  alerts,
  currentFilter,
  onApply,
  onClose,
}: FilterPanelProps) {
  // ── Local state ─────────────────────────────────────────────────────────────
  const [selected, setSelected] = useState<Set<number>>(
    () => new Set(currentFilter ?? companies.map((c) => c.id)),
  );
  const [searchInput, setSearchInput] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [activePreset, setActivePreset] = useState<TierPreset | null>('all');
  const [savedPresets, setSavedPresets] = useState<UserFilter[]>([]);
  const [savePresetName, setSavePresetName] = useState('');
  const [showSaveInput, setShowSaveInput] = useState(false);

  const searchDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  // ── Sync selected when panel opens ──────────────────────────────────────────
  useEffect(() => {
    if (isOpen) {
      setSelected(new Set(currentFilter ?? companies.map((c) => c.id)));
      setActivePreset(currentFilter === null ? 'all' : null);
      setSearchInput('');
      setSearchQuery('');
    }
  }, [isOpen, companies, currentFilter]);

  // ── Load saved presets from API ──────────────────────────────────────────────
  useEffect(() => {
    if (!isOpen) return;
    api
      .get<UserFilter[]>('/filters')
      .then((res) => setSavedPresets(res.data))
      .catch(() => {
        // Non-fatal — saved presets section just stays empty
      });
  }, [isOpen]);

  // ── Debounced search ─────────────────────────────────────────────────────────
  const handleSearchChange = (value: string) => {
    setSearchInput(value);
    if (searchDebounceRef.current) clearTimeout(searchDebounceRef.current);
    searchDebounceRef.current = setTimeout(() => {
      setSearchQuery(value.trim());
    }, 300);
  };

  // ── Cleanup on unmount ───────────────────────────────────────────────────────
  useEffect(() => {
    return () => {
      if (searchDebounceRef.current) clearTimeout(searchDebounceRef.current);
    };
  }, []);

  // ── Build alert map (company_id → highest severity) ──────────────────────────
  const alertMap = useMemo(() => {
    const map = new Map<number, 'critical' | 'warning'>();
    alerts.forEach((a) => {
      const existing = map.get(a.company_id);
      if (!existing || (a.severity === 'critical' && existing !== 'critical')) {
        if (a.severity === 'critical' || a.severity === 'warning') {
          map.set(a.company_id, a.severity);
        }
      }
    });
    return map;
  }, [alerts]);

  // ── Group companies by cluster ───────────────────────────────────────────────
  const companiesByCluster = useMemo(() => {
    const map = new Map<number, Company[]>();
    clusters.forEach((cl) => map.set(cl.id, []));
    companies.forEach((c) => {
      const arr = map.get(c.cluster_id);
      if (arr) arr.push(c);
      else map.set(c.cluster_id, [c]);
    });
    return map;
  }, [companies, clusters]);

  // ── Preset handlers ──────────────────────────────────────────────────────────
  const applyPreset = (preset: TierPreset) => {
    setActivePreset(preset);
    if (preset === 'all') {
      setSelected(new Set(companies.map((c) => c.id)));
    } else {
      setSelected(new Set(companies.filter((c) => c.tier === preset).map((c) => c.id)));
    }
  };

  // ── Checkbox toggle ──────────────────────────────────────────────────────────
  const toggleCompany = (id: number) => {
    setActivePreset(null);
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  // ── Reset ────────────────────────────────────────────────────────────────────
  const handleReset = () => {
    setSelected(new Set());
    setActivePreset(null);
  };

  // ── Apply ────────────────────────────────────────────────────────────────────
  const handleApply = () => {
    // null = show all
    if (selected.size === companies.length) {
      onApply(null);
    } else {
      onApply(Array.from(selected));
    }
    onClose();
  };

  // ── Save preset to API ───────────────────────────────────────────────────────
  const handleSavePreset = async () => {
    const name = savePresetName.trim();
    if (!name || selected.size === 0) return;
    try {
      const res = await api.post<UserFilter>('/filters', {
        name,
        company_ids: Array.from(selected),
      });
      setSavedPresets((prev) => [...prev, res.data]);
      setSavePresetName('');
      setShowSaveInput(false);
    } catch {
      // Silently fail — UI stays intact
    }
  };

  // ── Delete preset from API ───────────────────────────────────────────────────
  const handleDeletePreset = async (id: number) => {
    try {
      await api.delete(`/filters/${id}`);
      setSavedPresets((prev) => prev.filter((p) => p.id !== id));
    } catch {
      // Silently fail
    }
  };

  // ── Load saved preset ────────────────────────────────────────────────────────
  const handleLoadPreset = (ids: number[]) => {
    setSelected(new Set(ids));
    setActivePreset(null);
  };

  // ── ESC to close ─────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!isOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [isOpen, onClose]);

  // ── Focus trap: return focus to trigger on close ─────────────────────────────
  useEffect(() => {
    if (isOpen) {
      panelRef.current?.focus();
    }
  }, [isOpen]);

  const selectedCount = selected.size;

  // ─── Render ─────────────────────────────────────────────────────────────────
  return (
    <>
      {/* Backdrop */}
      <div
        className={`fixed inset-0 bg-black/30 backdrop-blur-[2px] z-20 transition-opacity duration-300 ${
          isOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'
        }`}
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Panel — slides in from the right */}
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label="기업 필터"
        tabIndex={-1}
        className={`fixed top-0 right-0 h-full w-80 max-h-screen bg-white shadow-2xl flex flex-col z-30
          transform transition-transform duration-300 ease-out outline-none
          ${isOpen ? 'translate-x-0' : 'translate-x-full'}`}
      >
        {/* ── Header ──────────────────────────────────────────────────────── */}
        <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between flex-shrink-0">
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-bold text-slate-900 tracking-tight">기업 필터</h2>
            {selectedCount > 0 && (
              <span className="px-2 py-0.5 rounded-full bg-primary/10 text-primary text-xs font-semibold">
                {selectedCount}개 선택됨
              </span>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="필터 패널 닫기"
            className="p-1.5 rounded-full text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
          >
            <CloseIcon />
          </button>
        </div>

        {/* ── Search ──────────────────────────────────────────────────────── */}
        <div className="px-5 py-3 flex-shrink-0">
          <div className="relative group">
            <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-slate-400 group-focus-within:text-primary transition-colors pointer-events-none">
              <SearchIcon />
            </span>
            <input
              type="text"
              value={searchInput}
              onChange={(e) => handleSearchChange(e.target.value)}
              placeholder="기업명 검색"
              aria-label="기업명 검색"
              className="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-transparent focus:border-primary focus:ring-1 focus:ring-primary rounded-lg text-sm text-slate-800 placeholder-slate-400 outline-none transition-all"
            />
          </div>
        </div>

        {/* ── Preset pills ────────────────────────────────────────────────── */}
        <div className="px-5 pb-4 border-b border-slate-200 flex-shrink-0">
          <div className="flex flex-wrap gap-2">
            {(Object.keys(TIER_PRESET_LABELS) as TierPreset[]).map((preset) => (
              <PresetPill
                key={preset}
                label={TIER_PRESET_LABELS[preset]}
                active={activePreset === preset}
                onClick={() => applyPreset(preset)}
              />
            ))}
          </div>
        </div>

        {/* ── Scrollable content ───────────────────────────────────────────── */}
        <div
          className="flex-1 overflow-y-auto px-5 py-4 space-y-3 min-h-0 filter-panel-scroll"
        >
          {/* Saved presets section */}
          {savedPresets.length > 0 && (
            <div className="mb-2">
              <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5 px-2">
                저장된 필터
              </p>
              {savedPresets.map((preset) => (
                <SavedPresetRow
                  key={preset.id}
                  preset={preset}
                  onLoad={handleLoadPreset}
                  onDelete={handleDeletePreset}
                />
              ))}
            </div>
          )}

          {/* Save current selection */}
          <div className="mb-2">
            {showSaveInput ? (
              <div className="flex gap-2">
                <input
                  type="text"
                  value={savePresetName}
                  onChange={(e) => setSavePresetName(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleSavePreset();
                    if (e.key === 'Escape') setShowSaveInput(false);
                  }}
                  placeholder="필터 이름 입력"
                  aria-label="저장할 필터 이름"
                  className="flex-1 px-3 py-1.5 text-sm border border-slate-200 rounded-lg outline-none focus:border-primary focus:ring-1 focus:ring-primary"
                  autoFocus
                />
                <button
                  type="button"
                  onClick={handleSavePreset}
                  disabled={!savePresetName.trim()}
                  className="px-3 py-1.5 text-xs font-medium bg-primary text-white rounded-lg disabled:opacity-40 hover:bg-primary-hover transition-colors"
                >
                  저장
                </button>
                <button
                  type="button"
                  onClick={() => setShowSaveInput(false)}
                  className="px-2 py-1.5 text-xs text-slate-500 hover:text-slate-700 rounded-lg hover:bg-slate-100 transition-colors"
                >
                  취소
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => setShowSaveInput(true)}
                className="w-full text-left text-xs text-slate-400 hover:text-primary py-1 px-2 rounded-lg hover:bg-slate-50 transition-colors"
              >
                + 현재 선택 필터로 저장
              </button>
            )}
          </div>

          {/* Section divider */}
          <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider px-2">
            클러스터별 기업
          </p>

          {/* Cluster accordion sections */}
          {clusters.map((cluster) => {
            const clusterCompanies = companiesByCluster.get(cluster.id) ?? [];
            if (clusterCompanies.length === 0) return null;
            return (
              <ClusterSection
                key={cluster.id}
                cluster={cluster}
                companies={clusterCompanies}
                alertMap={alertMap}
                selected={selected}
                searchQuery={searchQuery}
                onToggle={toggleCompany}
              />
            );
          })}

          {/* Empty search state */}
          {searchQuery && clusters.every((cl) => {
            const comps = companiesByCluster.get(cl.id) ?? [];
            const q = searchQuery.toLowerCase();
            return comps.every(
              (c) => !c.name.toLowerCase().includes(q) && !c.name_kr.toLowerCase().includes(q),
            );
          }) && (
            <p className="text-sm text-slate-400 text-center py-8">
              "{searchQuery}"에 해당하는 기업이 없습니다.
            </p>
          )}
        </div>

        {/* ── Footer ──────────────────────────────────────────────────────── */}
        <div className="px-5 py-4 border-t border-slate-200 bg-white flex-shrink-0">
          <div className="flex gap-3">
            <button
              type="button"
              onClick={handleReset}
              className="flex-1 py-2.5 px-4 rounded-lg border border-slate-200 text-slate-700 font-semibold text-sm hover:bg-slate-50 transition-colors flex items-center justify-center gap-2"
            >
              <RefreshIcon />
              초기화
            </button>
            <button
              type="button"
              onClick={handleApply}
              className="flex-1 py-2.5 px-4 rounded-lg bg-primary text-white font-semibold text-sm hover:bg-primary-hover shadow-md hover:shadow-lg transition-all flex items-center justify-center gap-2"
            >
              <CheckIcon />
              적용
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
