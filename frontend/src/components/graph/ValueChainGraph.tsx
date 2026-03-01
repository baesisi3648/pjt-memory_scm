// @TASK P3-S1-T1 - Value Chain Graph component using Cytoscape.js
// @SPEC main_supply_chain_dashboard design reference
import { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import type { ElementDefinition, Stylesheet } from 'cytoscape';
import { useCytoscape } from '../../hooks/useCytoscape';
import type { Company, Cluster, CompanyRelation, Alert } from '../../types/index';

// ─── Tier configuration ────────────────────────────────────────────────────────

const TIER_ORDER = ['raw_material', 'equipment', 'fab', 'packaging', 'module'] as const;

const TIER_LABELS: Record<string, string> = {
  raw_material: 'RAW MATERIALS',
  equipment: 'EQUIPMENT',
  fab: 'FAB',
  packaging: 'PACKAGING',
  module: 'MODULE',
};

const TIER_COLORS: Record<string, string> = {
  raw_material: '#6366f1',
  equipment:    '#8b5cf6',
  fab:          '#3b82f6',
  packaging:    '#10b981',
  module:       '#f59e0b',
};

// Company name → logo filename mapping
const COMPANY_LOGOS: Record<string, string> = {
  'SK Materials': 'sk-materials',
  'Soulbrain': 'soulbrain',
  'DNF': 'dnf',
  'Hansol Chemical': 'hansol-chemical',
  'SUMCO': 'sumco',
  'Shin-Etsu Chemical': 'shin-etsu',
  'ASML': 'asml',
  'Applied Materials': 'applied-materials',
  'Lam Research': 'lam-research',
  'Tokyo Electron': 'tokyo-electron',
  'SEMES': 'semes',
  'PSK': 'psk',
  'Samsung Electronics': 'samsung',
  'SK hynix': 'sk-hynix',
  'Micron Technology': 'micron',
  'TSMC': 'tsmc',
  'Intel': 'intel',
  'Kioxia': 'kioxia',
  'ASE Group': 'ase-group',
  'Amkor Technology': 'amkor',
  'JCET': 'jcet',
  'NEPES': 'nepes',
  'SFA Semicon': 'sfa-semicon',
  'Hana Micron': 'hana-micron',
  'Samsung SDI': 'samsung-sdi',
  'SK Nexilis': 'sk-nexilis',
  'LG Innotek': 'lg-innotek',
  'Innox Advanced Materials': 'innox',
  'BH': 'bh',
  'Daeduck Electronics': 'daeduck',
};

// Layout constants
const CLUSTER_X_START = 120;
const CLUSTER_X_GAP   = 300;
const CLUSTER_Y       = 300;
const CLUSTER_W       = 240;
const CLUSTER_H       = 340;
const COMPANY_RADIUS  = 34;

// ─── Element builder ───────────────────────────────────────────────────────────

function buildElements(
  companies: Company[],
  clusters: Cluster[],
  relations: CompanyRelation[],
  alerts: Alert[],
): ElementDefinition[] {
  const elements: ElementDefinition[] = [];

  // Build alert lookup: company_id → highest severity
  const alertMap = new Map<number, string>();
  alerts.forEach((a) => {
    const existing = alertMap.get(a.company_id);
    if (!existing || (a.severity === 'critical' && existing !== 'critical')) {
      alertMap.set(a.company_id, a.severity);
    }
  });

  // Build relation count lookup: company_id → number of edges
  const relationCountMap = new Map<number, number>();
  relations.forEach((rel) => {
    relationCountMap.set(rel.source_id, (relationCountMap.get(rel.source_id) || 0) + 1);
    relationCountMap.set(rel.target_id, (relationCountMap.get(rel.target_id) || 0) + 1);
  });

  // Group companies by tier
  const companiesByTier = new Map<string, Company[]>();
  TIER_ORDER.forEach((t) => companiesByTier.set(t, []));
  companies.forEach((c) => {
    const arr = companiesByTier.get(c.tier);
    if (arr) arr.push(c);
  });

  // Cluster parent nodes (compound nodes as background rectangles)
  const usedTiers = new Set(companies.map((c) => c.tier));
  TIER_ORDER.forEach((tier, tierIdx) => {
    if (!usedTiers.has(tier) && clusters.filter((cl) => cl.tier === tier).length === 0) return;

    const cx = CLUSTER_X_START + tierIdx * CLUSTER_X_GAP;
    const tierCompanyCount = companiesByTier.get(tier)?.length ?? 0;
    elements.push({
      data: {
        id: `cluster-${tier}`,
        label: `${TIER_LABELS[tier]} (${tierCompanyCount})`,
        type: 'cluster',
        tier,
        color: TIER_COLORS[tier],
      },
      position: { x: cx, y: CLUSTER_Y },
    });
  });

  // Company nodes — positioned in a 2-column grid inside their cluster area
  const GRID_COLS = 2;
  const COL_GAP = 50;   // horizontal gap between columns
  const ROW_GAP = 70;   // vertical gap between rows

  companiesByTier.forEach((comps, tier) => {
    const tierIdx = TIER_ORDER.indexOf(tier as typeof TIER_ORDER[number]);
    if (tierIdx === -1) return;

    const cx = CLUSTER_X_START + tierIdx * CLUSTER_X_GAP;

    // Sort by relation count descending so important nodes appear first (top)
    const sorted = [...comps].sort(
      (a, b) => (relationCountMap.get(b.id) || 0) - (relationCountMap.get(a.id) || 0),
    );

    const rows = Math.ceil(sorted.length / GRID_COLS);
    const totalW = (GRID_COLS - 1) * COL_GAP;
    const totalH = (rows - 1) * ROW_GAP;
    const startX = cx - totalW / 2;
    const startY = CLUSTER_Y - totalH / 2;

    sorted.forEach((company, i) => {
      const col = i % GRID_COLS;
      const row = Math.floor(i / GRID_COLS);
      const alertSeverity = alertMap.get(company.id) ?? null;
      const logoFile = COMPANY_LOGOS[company.name];
      const logoUrl = logoFile ? `/logos/${logoFile}.png` : undefined;
      elements.push({
        data: {
          id: `company-${company.id}`,
          label: company.name_kr || company.name,
          type: 'company',
          companyId: company.id,
          tier,
          color: TIER_COLORS[tier],
          alertSeverity,
          relCount: relationCountMap.get(company.id) || 0,
          ...(logoUrl ? { logoUrl } : {}),
        },
        position: {
          x: startX + col * COL_GAP,
          y: sorted.length === 1 ? CLUSTER_Y : startY + row * ROW_GAP,
        },
      });
    });
  });

  // Edge elements from relations — colored by source company's tier
  // Uses unbundled-bezier with per-edge control-point-distance so parallel
  // edges between the same tier pair fan out instead of overlapping.
  const companyIdSet = new Set(companies.map((c) => c.id));
  const companyTierMap = new Map(companies.map((c) => [c.id, c.tier]));
  const SPREAD_GAP = 20;

  // Collect valid edges with tier-pair metadata
  const edgeInfos: { rel: CompanyRelation; sourceTier: string; targetTier: string; tierPairKey: string }[] = [];
  relations.forEach((rel) => {
    if (!companyIdSet.has(rel.source_id) || !companyIdSet.has(rel.target_id)) return;
    const sourceTier = companyTierMap.get(rel.source_id) ?? 'fab';
    const targetTier = companyTierMap.get(rel.target_id) ?? 'fab';
    const tierPairKey = `${sourceTier}->${targetTier}`;
    edgeInfos.push({ rel, sourceTier, targetTier, tierPairKey });
  });

  // Count edges per tier-pair
  const tierPairCount = new Map<string, number>();
  edgeInfos.forEach((info) => {
    tierPairCount.set(info.tierPairKey, (tierPairCount.get(info.tierPairKey) || 0) + 1);
  });

  // Build edge elements with spread distance
  const tierPairIdx = new Map<string, number>();
  edgeInfos.forEach((info) => {
    const count = tierPairCount.get(info.tierPairKey) || 1;
    const idx = tierPairIdx.get(info.tierPairKey) || 0;
    tierPairIdx.set(info.tierPairKey, idx + 1);

    const cpDist = (idx - (count - 1) / 2) * SPREAD_GAP;
    const sameTier = info.sourceTier === info.targetTier;

    elements.push({
      data: {
        id: `edge-${info.rel.id}`,
        source: `company-${info.rel.source_id}`,
        target: `company-${info.rel.target_id}`,
        type: 'relation',
        strength: info.rel.strength,
        color: TIER_COLORS[info.sourceTier] ?? '#94a3b8',
        cpDist,
        ...(sameTier ? { sameTier: 'yes' } : {}),
      },
    });
  });

  // Fallback tier-to-tier edges when no relation data exists
  if (relations.length === 0) {
    for (let i = 0; i < TIER_ORDER.length - 1; i++) {
      const fromTier = TIER_ORDER[i];
      const toTier   = TIER_ORDER[i + 1];
      const fromComps = companiesByTier.get(fromTier) ?? [];
      const toComps   = companiesByTier.get(toTier)   ?? [];
      fromComps.slice(0, 1).forEach((src) => {
        toComps.slice(0, 1).forEach((tgt) => {
          elements.push({
            data: {
              id: `fallback-edge-${src.id}-${tgt.id}`,
              source: `company-${src.id}`,
              target: `company-${tgt.id}`,
              type: 'relation',
              strength: 1,
              color: TIER_COLORS[fromTier],
            },
          });
        });
      });
    }
  }

  return elements;
}

// ─── Stylesheet builder ────────────────────────────────────────────────────────

function buildStylesheet(): Stylesheet[] {
  return [
    // Cluster background
    {
      selector: 'node[type = "cluster"]',
      style: {
        'background-color': 'data(color)',
        'background-opacity': 0.05,
        'border-color': 'data(color)',
        'border-width': 1.5,
        'border-style': 'solid',
        'border-opacity': 0.3,
        'shape': 'roundrectangle',
        'width': CLUSTER_W,
        'height': CLUSTER_H,
        'label': 'data(label)',
        'text-valign': 'top',
        'text-halign': 'center',
        'font-size': 10,
        'font-weight': 700,
        'color': '#475569',
        'text-margin-y': -10,
        'text-background-color': '#f8fafc',
        'text-background-opacity': 1,
        'text-background-padding': 6,
        'text-background-shape': 'roundrectangle',
      },
    },
    // Company node — normal
    {
      selector: 'node[type = "company"]',
      style: {
        'background-color': '#ffffff',
        'border-color': 'data(color)',
        'border-width': 2,
        'border-opacity': 0.9,
        'width': 'mapData(relCount, 0, 10, 44, 64)',
        'height': 'mapData(relCount, 0, 10, 44, 64)',
        'shape': 'ellipse',
        'label': 'data(label)',
        'text-valign': 'bottom',
        'text-halign': 'center',
        'font-size': 10,
        'font-weight': 500,
        'color': '#1e293b',
        'text-margin-y': 5,
        'text-background-color': 'rgba(248,250,252,0.95)',
        'text-background-opacity': 1,
        'text-background-padding': 2,
        'text-background-shape': 'roundrectangle',
        'text-wrap': 'wrap',
        'text-max-width': 100,
        'shadow-color': '#94a3b8',
        'shadow-blur': 6,
        'shadow-offset-x': 0,
        'shadow-offset-y': 2,
        'shadow-opacity': 0.2,
        'transition-property': 'border-color, border-width, background-color, opacity',
        'transition-duration': 200,
      },
    },
    // Company node with logo
    {
      selector: 'node[type = "company"][logoUrl]',
      style: {
        'background-image': 'data(logoUrl)' as unknown as string,
        'background-fit': 'contain',
        'background-clip': 'node',
        'background-image-containment': 'over',
        'background-width': '70%',
        'background-height': '70%',
      } as Record<string, unknown>,
    },
    // Warning node overlay
    {
      selector: 'node[type = "company"][alertSeverity = "warning"]',
      style: {
        'border-color': '#f59e0b',
        'border-width': 3,
        'background-color': '#fffbeb',
        'overlay-color': '#f59e0b',
        'overlay-padding': 6,
        'overlay-opacity': 0.15,
      },
    },
    // Critical node overlay
    {
      selector: 'node[type = "company"][alertSeverity = "critical"]',
      style: {
        'border-color': '#ef4444',
        'border-width': 3,
        'background-color': '#fef2f2',
        'overlay-color': '#ef4444',
        'overlay-padding': 8,
        'overlay-opacity': 0.2,
      },
    },
    // Company node hover
    {
      selector: 'node[type = "company"]:active',
      style: {
        'border-width': 3,
        'background-color': '#f0f9ff',
      },
    },
    // Focused node (from alert navigation)
    {
      selector: 'node.focused',
      style: {
        'border-width': 4,
        'border-color': '#2563eb',
        'overlay-color': '#2563eb',
        'overlay-padding': 10,
        'overlay-opacity': 0.2,
      },
    },
    // Selected node
    {
      selector: 'node:selected',
      style: {
        'border-color': '#8b5cf6',
        'border-width': 3,
        'background-color': '#f5f3ff',
      },
    },
    // Edge — width proportional to relationship strength, colored by source tier
    // unbundled-bezier gives each edge an independent control point so parallel
    // edges between the same tier pair fan out visually.
    {
      selector: 'edge[type = "relation"]',
      style: {
        'line-color': 'data(color)',
        'target-arrow-color': 'data(color)',
        'target-arrow-shape': 'vee',
        'arrow-scale': 0.7,
        'width': 'mapData(strength, 0, 1, 1, 4)',
        'curve-style': 'unbundled-bezier',
        'control-point-distances': 'data(cpDist)',
        'control-point-weights': 0.5,
        'opacity': 'mapData(strength, 0, 1, 0.3, 0.8)',
        'transition-property': 'opacity, line-color, width',
        'transition-duration': 200,
      },
    },
    // Partner edges (same tier) — dashed to distinguish from cross-tier edges
    {
      selector: 'edge[sameTier = "yes"]',
      style: {
        'line-style': 'dashed',
        'line-dash-pattern': [6, 3] as unknown as string,
      },
    },
    // Edge hover
    {
      selector: 'edge:selected',
      style: {
        'line-color': '#2563eb',
        'target-arrow-color': '#2563eb',
        'width': 2.5,
        'opacity': 1,
      },
    },
    // Faded elements (non-connected on hover)
    {
      selector: '.faded',
      style: {
        'opacity': 0.15,
        'transition-property': 'opacity',
        'transition-duration': 200,
      },
    },
    // Highlighted elements (connected on hover)
    {
      selector: 'node.highlighted',
      style: {
        'opacity': 1,
        'border-width': 3,
        'shadow-opacity': 0.35,
        'transition-property': 'opacity, border-width, shadow-opacity',
        'transition-duration': 200,
      },
    },
    {
      selector: 'edge.highlighted',
      style: {
        'opacity': 0.9,
        'width': 3,
        'transition-property': 'opacity, width',
        'transition-duration': 200,
      },
    },
  ];
}

// ─── Props ─────────────────────────────────────────────────────────────────────

interface ValueChainGraphProps {
  companies: Company[];
  clusters: Cluster[];
  relations: CompanyRelation[];
  alerts: Alert[];
  filteredCompanyIds?: number[] | null;
  onNodeClick?: (companyId: number) => void;
  onFocusRef?: React.MutableRefObject<((companyId: number) => void) | null>;
}

// ─── Component ─────────────────────────────────────────────────────────────────

export function ValueChainGraph({
  companies,
  clusters,
  relations,
  alerts,
  filteredCompanyIds,
  onNodeClick,
  onFocusRef,
}: ValueChainGraphProps) {
  const [zoomPercent, setZoomPercent] = useState(100);
  const minimapRef = useRef<HTMLDivElement | null>(null);
  const navigatorInitRef = useRef(false);

  const stylesheet = useMemo(() => buildStylesheet(), []);
  const elements = useMemo(
    () => buildElements(companies, clusters, relations, alerts),
    [companies, clusters, relations, alerts],
  );

  const handleNodeClick = useCallback(
    (nodeId: string) => {
      // nodeId format: "company-{id}"
      const match = nodeId.match(/^company-(\d+)$/);
      if (match) {
        onNodeClick?.(parseInt(match[1], 10));
      }
    },
    [onNodeClick],
  );

  const { containerRef, cy, zoomIn, zoomOut, fitToScreen, focusNode, getZoomPercent, initNavigator } =
    useCytoscape({ elements, stylesheet, onNodeClick: handleNodeClick });

  // Expose focusNode via ref so parent (DashboardPage) can call it
  useEffect(() => {
    if (onFocusRef) {
      onFocusRef.current = (companyId: number) => {
        focusNode(`company-${companyId}`);
      };
    }
  }, [onFocusRef, focusNode]);

  // Apply company visibility filter to the Cytoscape graph.
  // null  → show all nodes/edges (reset to visible)
  // number[] → hide company nodes not in the list, hide edges with no visible endpoint
  useEffect(() => {
    const instance = cy.current;
    if (!instance) return;

    instance.batch(() => {
      if (!filteredCompanyIds) {
        // Show everything
        instance.elements().style('display', 'element');
        return;
      }

      const visibleSet = new Set(filteredCompanyIds.map((id) => `company-${id}`));

      // Company nodes: show only those in the filter set
      instance.nodes('[type = "company"]').forEach((node) => {
        const visible = visibleSet.has(node.id());
        node.style('display', visible ? 'element' : 'none');
      });

      // Cluster nodes: always visible
      instance.nodes('[type = "cluster"]').style('display', 'element');

      // Edges: hide if either endpoint is hidden
      instance.edges().forEach((edge) => {
        const srcVisible = visibleSet.has(edge.data('source') as string);
        const tgtVisible = visibleSet.has(edge.data('target') as string);
        edge.style('display', srcVisible && tgtVisible ? 'element' : 'none');
      });
    });
  }, [cy, filteredCompanyIds]);

  // Update zoom display on cy events
  const cyRef = cy;
  useEffect(() => {
    const instance = cyRef.current;
    if (!instance) return;

    const update = () => setZoomPercent(getZoomPercent());
    instance.on('zoom', update);
    return () => { instance.off('zoom', update); };
  }, [cyRef, getZoomPercent]);

  // Initialize the navigator minimap once the cy instance exists and elements
  // have been loaded (elements.length > 0 means the first sync has run).
  // Guard with navigatorInitRef so we only call it once.
  useEffect(() => {
    if (navigatorInitRef.current) return;
    if (!cy.current) return;
    if (elements.length === 0) return;
    const container = minimapRef.current;
    if (!container) return;

    // Small delay so Cytoscape has finished its first layout/fit before the
    // navigator measures the viewport.
    const id = setTimeout(() => {
      initNavigator(container);
      navigatorInitRef.current = true;
    }, 300);

    return () => clearTimeout(id);
  }, [cy, elements, initNavigator]);

  return (
    <div className="absolute inset-0 overflow-hidden bg-slate-50">
      {/* Dot grid background */}
      <div
        aria-hidden="true"
        className="absolute inset-0 pointer-events-none graph-dot-grid"
      />

      {/* Cytoscape canvas — wrapper needed because Cytoscape overrides container position to relative */}
      <div className="absolute inset-0 z-[1]">
        <div
          ref={containerRef}
          className="w-full h-full"
          aria-label="Supply chain value graph"
        />
      </div>

{/* ── Zoom controls (bottom-left) ─────────────────────────── */}
      <div className="absolute bottom-6 left-6 flex flex-col z-10">
        <div className="flex flex-col bg-white shadow-lg rounded-lg border border-slate-200 overflow-hidden">
          <button
            onClick={zoomIn}
            aria-label="Zoom in"
            className="p-2 hover:bg-slate-50 text-slate-600 border-b border-slate-100 transition-colors"
          >
            <PlusIcon />
          </button>
          <button
            onClick={zoomOut}
            aria-label="Zoom out"
            className="p-2 hover:bg-slate-50 text-slate-600 transition-colors"
          >
            <MinusIcon />
          </button>
        </div>
        <button
          onClick={fitToScreen}
          aria-label="Fit to screen"
          className="mt-1 bg-white shadow-lg rounded-lg border border-slate-200 p-2 hover:bg-slate-50 text-slate-600 transition-colors"
        >
          <FitIcon />
        </button>
        <div className="mt-1 bg-white shadow rounded-md border border-slate-200 px-3 py-1 text-xs font-medium text-slate-600 text-center">
          {zoomPercent}%
        </div>
      </div>

      {/* ── Minimap navigator (above legend, bottom-right) ──────── */}
      {/*
        The plugin writes canvas/img children directly into this div.
        Dimensions and positioning are supplied via Tailwind utilities.
        The .cytoscape-navigator overrides (position, size, colours) live
        in index.css so the plugin's injected class is styled correctly.
        bottom-14 (56px) leaves room for the legend row below.
      */}
      <div
        ref={minimapRef}
        aria-hidden="true"
        className="absolute z-10 w-[150px] h-[100px] bottom-14 right-6"
      />

      {/* ── Legend + Filter (bottom-right) ─────────────────────── */}
      <div className="absolute bottom-6 right-6 z-10 flex items-center gap-3">
        <div className="bg-white shadow-lg rounded-lg border border-slate-200 py-2 px-4 flex items-center gap-4">
          <LegendItem variant="normal"   label="Normal" />
          <LegendItem variant="critical" label="Critical" />
          <LegendItem variant="warning"  label="Warning" />
        </div>
      </div>
    </div>
  );
}

// ─── Small sub-components ──────────────────────────────────────────────────────

type LegendVariant = 'normal' | 'critical' | 'warning';

const LEGEND_DOT_CLASS: Record<LegendVariant, string> = {
  normal:   'legend-dot-normal',
  critical: 'legend-dot-critical',
  warning:  'legend-dot-warning',
};

function LegendItem({ variant, label }: { variant: LegendVariant; label: string }) {
  return (
    <div className="flex items-center gap-1.5">
      <span className={`w-3 h-3 rounded-full flex-shrink-0 ${LEGEND_DOT_CLASS[variant]}`} />
      <span className="text-xs font-medium text-slate-600">{label}</span>
    </div>
  );
}

function PlusIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5" aria-hidden="true">
      <path fillRule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clipRule="evenodd" />
    </svg>
  );
}

function MinusIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5" aria-hidden="true">
      <path fillRule="evenodd" d="M3 10a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z" clipRule="evenodd" />
    </svg>
  );
}

function FitIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5" aria-hidden="true">
      <path fillRule="evenodd" d="M3 4a1 1 0 011-1h4a1 1 0 010 2H5.414l3.293 3.293a1 1 0 01-1.414 1.414L4 6.414V8a1 1 0 01-2 0V4zm9 1a1 1 0 010-2h4a1 1 0 011 1v4a1 1 0 01-2 0V5.414l-3.293 3.293a1 1 0 01-1.414-1.414L14.586 4H13zm-9 7a1 1 0 012 0v1.586l3.293-3.293a1 1 0 011.414 1.414L6.414 14H8a1 1 0 010 2H4a1 1 0 01-1-1v-4zm13-1a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 010-2h1.586l-3.293-3.293a1 1 0 011.414-1.414L16 13.586V12a1 1 0 011-1z" clipRule="evenodd" />
    </svg>
  );
}
