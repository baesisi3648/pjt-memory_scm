// @TASK P3-S1-T1 - Value Chain Graph component using Cytoscape.js
// @SPEC main_supply_chain_dashboard design reference
import { useEffect, useState, useCallback, useRef, useMemo } from 'react';
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

// Layout constants
const CLUSTER_X_START = 120;
const CLUSTER_X_GAP   = 260;
const CLUSTER_Y       = 260;
const CLUSTER_W       = 180;
const CLUSTER_H       = 220;
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
    elements.push({
      data: {
        id: `cluster-${tier}`,
        label: TIER_LABELS[tier],
        type: 'cluster',
        tier,
        color: TIER_COLORS[tier],
      },
      position: { x: cx, y: CLUSTER_Y },
    });
  });

  // Company nodes — positioned inside their cluster area
  companiesByTier.forEach((comps, tier) => {
    const tierIdx = TIER_ORDER.indexOf(tier as typeof TIER_ORDER[number]);
    if (tierIdx === -1) return;

    const cx = CLUSTER_X_START + tierIdx * CLUSTER_X_GAP;
    const totalH = comps.length > 1 ? CLUSTER_H - 40 : 0;
    const spacing = comps.length > 1 ? totalH / (comps.length - 1) : 0;
    const startY = CLUSTER_Y - totalH / 2;

    comps.forEach((company, i) => {
      const alertSeverity = alertMap.get(company.id) ?? null;
      elements.push({
        data: {
          id: `company-${company.id}`,
          label: company.name_kr || company.name,
          type: 'company',
          companyId: company.id,
          tier,
          color: TIER_COLORS[tier],
          alertSeverity,
        },
        position: {
          x: cx + (i % 2 === 0 ? 0 : 18),
          y: comps.length === 1 ? CLUSTER_Y : startY + i * spacing,
        },
      });
    });
  });

  // Edge elements from relations
  const companyIds = new Set(companies.map((c) => c.id));
  relations.forEach((rel) => {
    if (!companyIds.has(rel.source_id) || !companyIds.has(rel.target_id)) return;
    elements.push({
      data: {
        id: `edge-${rel.id}`,
        source: `company-${rel.source_id}`,
        target: `company-${rel.target_id}`,
        type: 'relation',
        strength: rel.strength,
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
        'background-opacity': 0.08,
        'border-color': 'data(color)',
        'border-width': 2,
        'border-style': 'dashed',
        'border-opacity': 0.5,
        'shape': 'roundrectangle',
        'width': CLUSTER_W,
        'height': CLUSTER_H,
        'label': 'data(label)',
        'text-valign': 'top',
        'text-halign': 'center',
        'font-size': 10,
        'font-weight': 700,
        'color': '#64748b',
        'text-margin-y': -8,
        'text-background-color': '#f8fafc',
        'text-background-opacity': 1,
        'text-background-padding': 4,
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
        'width': COMPANY_RADIUS,
        'height': COMPANY_RADIUS,
        'shape': 'ellipse',
        'label': 'data(label)',
        'text-valign': 'bottom',
        'text-halign': 'center',
        'font-size': 9,
        'font-weight': 500,
        'color': '#334155',
        'text-margin-y': 4,
        'text-background-color': 'rgba(248,250,252,0.9)',
        'text-background-opacity': 1,
        'text-background-padding': 2,
        'text-background-shape': 'roundrectangle',
        'text-wrap': 'wrap',
        'text-max-width': 80,
        'transition-property': 'border-color, border-width, background-color',
        'transition-duration': 200,
      },
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
    // Edge — default
    {
      selector: 'edge[type = "relation"]',
      style: {
        'line-color': '#cbd5e1',
        'target-arrow-color': '#cbd5e1',
        'target-arrow-shape': 'triangle',
        'arrow-scale': 0.8,
        'width': 1.5,
        'curve-style': 'bezier',
        'opacity': 0.7,
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

  const { containerRef, cy, zoomIn, zoomOut, fitToScreen, focusNode, getZoomPercent } =
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

  // Interval-free zoom label sync on mount
  const zoomIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  useEffect(() => {
    zoomIntervalRef.current = setInterval(() => {
      setZoomPercent(getZoomPercent());
    }, 500);
    return () => {
      if (zoomIntervalRef.current) clearInterval(zoomIntervalRef.current);
    };
  }, [getZoomPercent]);

  return (
    <div className="relative w-full h-full overflow-hidden bg-slate-50 graph-canvas-wrapper">
      {/* Dot grid background */}
      <div
        aria-hidden="true"
        className="absolute inset-0 pointer-events-none graph-dot-grid"
      />

      {/* Cytoscape canvas */}
      <div
        ref={containerRef}
        className="absolute inset-0 z-[1]"
        aria-label="Supply chain value graph"
      />

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
