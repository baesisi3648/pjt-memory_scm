// @TASK METRIC-CARDS-T1 - Dashboard summary metric cards
// @SPEC main_supply_chain_dashboard design reference
import { useEffect, useState } from 'react';
import api from '../../services/api';
import type { Alert, Company } from '../../types/index';

// ─── API response types ────────────────────────────────────────────────────────

interface RiskScoreEntry {
  company_id: number;
  company_name: string;
  score: number;
  level: 'low' | 'medium' | 'high' | 'critical';
}

interface ConcentrationEntry {
  tier: string;
  tier_label: string;
  hhi: number;
  level: 'competitive' | 'moderately_concentrated' | 'highly_concentrated' | 'unknown';
  company_count: number;
}

// ─── Props ────────────────────────────────────────────────────────────────────

interface MetricCardsProps {
  companies: Company[];
  alerts: Alert[];
}

// ─── Card base ────────────────────────────────────────────────────────────────

interface CardProps {
  label: string;
  icon: React.ReactNode;
  children: React.ReactNode;
  accent: 'blue' | 'green' | 'amber' | 'red';
}

const ACCENT_ICON_BG: Record<CardProps['accent'], string> = {
  blue:  'bg-blue-50 text-blue-600',
  green: 'bg-green-50 text-green-600',
  amber: 'bg-amber-50 text-amber-600',
  red:   'bg-red-50 text-red-600',
};

function Card({ label, icon, children, accent }: CardProps) {
  return (
    <article className="bg-white border border-slate-200 rounded-xl p-4 flex flex-col gap-3 shadow-sm">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-slate-500 tracking-wide uppercase">
          {label}
        </span>
        <span
          className={`w-8 h-8 rounded-lg flex items-center justify-center ${ACCENT_ICON_BG[accent]}`}
          aria-hidden="true"
        >
          {icon}
        </span>
      </div>
      {children}
    </article>
  );
}

// ─── Skeleton value (loading state) ──────────────────────────────────────────

function SkeletonValue() {
  return (
    <div className="h-8 w-16 rounded-md bg-slate-100 animate-pulse" aria-label="Loading" />
  );
}

// ─── Icons (inline SVG — no dependency) ──────────────────────────────────────

function BuildingIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4" aria-hidden="true">
      <path
        fillRule="evenodd"
        d="M4 4a2 2 0 012-2h8a2 2 0 012 2v12a1 1 0 01-1 1h-2a1 1 0 01-1-1v-2a1 1 0 00-1-1H9a1 1 0 00-1 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V4zm3 1h2v2H7V5zm2 4H7v2h2V9zm2-4h2v2h-2V5zm2 4h-2v2h2V9z"
        clipRule="evenodd"
      />
    </svg>
  );
}

function BellIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4" aria-hidden="true">
      <path d="M10 2a6 6 0 00-6 6v3.586l-.707.707A1 1 0 004 14h12a1 1 0 00.707-1.707L16 11.586V8a6 6 0 00-6-6zm0 16a2 2 0 01-1.732-1h3.464A2 2 0 0110 18z" />
    </svg>
  );
}

function ShieldIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4" aria-hidden="true">
      <path
        fillRule="evenodd"
        d="M10 1.944A11.954 11.954 0 012.166 5C2.056 5.649 2 6.319 2 7c0 5.225 3.34 9.67 8 11.317C14.66 16.67 18 12.225 18 7c0-.682-.057-1.35-.166-2.001A11.954 11.954 0 0110 1.944zM11 14a1 1 0 11-2 0 1 1 0 012 0zm0-7a1 1 0 10-2 0v3a1 1 0 102 0V7z"
        clipRule="evenodd"
      />
    </svg>
  );
}

function ChainIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4" aria-hidden="true">
      <path
        fillRule="evenodd"
        d="M12.586 4.586a2 2 0 112.828 2.828l-3 3a2 2 0 01-2.828 0 1 1 0 00-1.414 1.414 4 4 0 005.656 0l3-3a4 4 0 00-5.656-5.656l-1.5 1.5a1 1 0 101.414 1.414l1.5-1.5zm-5 5a2 2 0 012.828 0 1 1 0 101.414-1.414 4 4 0 00-5.656 0l-3 3a4 4 0 105.656 5.656l1.5-1.5a1 1 0 10-1.414-1.414l-1.5 1.5a2 2 0 11-2.828-2.828l3-3z"
        clipRule="evenodd"
      />
    </svg>
  );
}

// ─── Card 1: Companies ────────────────────────────────────────────────────────

function CompaniesCard({ companies }: { companies: Company[] }) {
  const count = companies.length;

  // Tier breakdown for sub-label
  const tierCounts: Partial<Record<string, number>> = {};
  for (const c of companies) {
    tierCounts[c.tier] = (tierCounts[c.tier] ?? 0) + 1;
  }
  const tierSummary = Object.entries(tierCounts)
    .sort((a, b) => (b[1] ?? 0) - (a[1] ?? 0))
    .slice(0, 2)
    .map(([tier]) => tier.replace('_', ' '))
    .join(', ');

  return (
    <Card label="Companies" icon={<BuildingIcon />} accent="blue">
      <div className="flex flex-col gap-1">
        <span className="text-2xl font-bold text-slate-900 tabular-nums leading-none">
          {count}
        </span>
        {tierSummary && (
          <span className="text-xs text-slate-400 truncate">
            Top tiers: {tierSummary}
          </span>
        )}
      </div>
    </Card>
  );
}

// ─── Card 2: Active Alerts ────────────────────────────────────────────────────

function AlertsCard({ alerts }: { alerts: Alert[] }) {
  const total = alerts.length;
  const critical = alerts.filter((a) => a.severity === 'critical').length;
  const warning  = alerts.filter((a) => a.severity === 'warning').length;
  const info     = alerts.filter((a) => a.severity === 'info').length;

  const accent: CardProps['accent'] =
    critical > 0 ? 'red' : warning > 0 ? 'amber' : total > 0 ? 'blue' : 'green';

  const valueColor =
    critical > 0
      ? 'text-red-600'
      : warning > 0
        ? 'text-amber-600'
        : total > 0
          ? 'text-blue-600'
          : 'text-green-600';

  return (
    <Card label="Active Alerts" icon={<BellIcon />} accent={accent}>
      <div className="flex flex-col gap-2">
        <span className={`text-2xl font-bold tabular-nums leading-none ${valueColor}`}>
          {total}
        </span>
        {total > 0 ? (
          <div className="flex items-center gap-2 flex-wrap">
            {critical > 0 && (
              <span className="inline-flex items-center gap-1 text-xs font-medium text-red-600 bg-red-50 px-1.5 py-0.5 rounded">
                <span className="w-1.5 h-1.5 rounded-full bg-red-500 inline-block" aria-hidden="true" />
                {critical} critical
              </span>
            )}
            {warning > 0 && (
              <span className="inline-flex items-center gap-1 text-xs font-medium text-amber-600 bg-amber-50 px-1.5 py-0.5 rounded">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-500 inline-block" aria-hidden="true" />
                {warning} warning
              </span>
            )}
            {info > 0 && (
              <span className="inline-flex items-center gap-1 text-xs font-medium text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded">
                <span className="w-1.5 h-1.5 rounded-full bg-blue-400 inline-block" aria-hidden="true" />
                {info} info
              </span>
            )}
          </div>
        ) : (
          <span className="text-xs text-green-600 font-medium">All clear</span>
        )}
      </div>
    </Card>
  );
}

// ─── Card 3: Risk Score ───────────────────────────────────────────────────────

type RiskLevel = 'low' | 'medium' | 'high' | 'critical' | null;

const RISK_LEVEL_STYLES: Record<NonNullable<RiskLevel>, { text: string; badge: string; accent: CardProps['accent'] }> = {
  low:      { text: 'text-green-600',  badge: 'text-green-700 bg-green-50',  accent: 'green' },
  medium:   { text: 'text-amber-600',  badge: 'text-amber-700 bg-amber-50',  accent: 'amber' },
  high:     { text: 'text-red-500',    badge: 'text-red-600 bg-red-50',      accent: 'red'   },
  critical: { text: 'text-red-700',    badge: 'text-red-800 bg-red-100',     accent: 'red'   },
};

function RiskScoreCard() {
  const [scores, setScores] = useState<RiskScoreEntry[] | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    api
      .get<RiskScoreEntry[]>('/risk-scores')
      .then((res) => {
        if (!cancelled) setScores(res.data);
      })
      .catch(() => {
        if (!cancelled) setScores([]);
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => { cancelled = true; };
  }, []);

  const avg =
    scores && scores.length > 0
      ? Math.round(scores.reduce((sum, s) => sum + s.score, 0) / scores.length)
      : null;

  const dominantLevel: RiskLevel =
    avg === null
      ? null
      : avg >= 60
        ? 'critical'
        : avg >= 40
          ? 'high'
          : avg >= 20
            ? 'medium'
            : 'low';

  const styles = dominantLevel ? RISK_LEVEL_STYLES[dominantLevel] : null;
  const accent = styles?.accent ?? 'green';

  // Highest-risk company for the sub-line
  const topRisk = scores && scores.length > 0 ? scores[0] : null;

  return (
    <Card label="Avg Risk Score" icon={<ShieldIcon />} accent={accent}>
      <div className="flex flex-col gap-2">
        {isLoading ? (
          <SkeletonValue />
        ) : avg === null ? (
          <span className="text-2xl font-bold text-slate-400 tabular-nums leading-none">--</span>
        ) : (
          <div className="flex items-baseline gap-2">
            <span className={`text-2xl font-bold tabular-nums leading-none ${styles?.text ?? 'text-slate-900'}`}>
              {avg}
              <span className="text-sm font-normal text-slate-400">/100</span>
            </span>
            {dominantLevel && (
              <span className={`text-xs font-semibold px-1.5 py-0.5 rounded capitalize ${styles?.badge}`}>
                {dominantLevel}
              </span>
            )}
          </div>
        )}
        {!isLoading && topRisk && topRisk.score > 0 && (
          <span className="text-xs text-slate-400 truncate">
            Highest: {topRisk.company_name} ({topRisk.score})
          </span>
        )}
      </div>
    </Card>
  );
}

// ─── Card 4: Supply Chain Health (HHI) ───────────────────────────────────────

const HHI_LEVEL_STYLES: Record<ConcentrationEntry['level'], {
  label: string;
  valueColor: string;
  badge: string;
  accent: CardProps['accent'];
}> = {
  competitive:             { label: 'Healthy',     valueColor: 'text-green-600', badge: 'text-green-700 bg-green-50',  accent: 'green' },
  moderately_concentrated: { label: 'Moderate',    valueColor: 'text-amber-600', badge: 'text-amber-700 bg-amber-50',  accent: 'amber' },
  highly_concentrated:     { label: 'Concentrated',valueColor: 'text-red-600',   badge: 'text-red-700 bg-red-50',      accent: 'red'   },
  unknown:                 { label: 'Unknown',      valueColor: 'text-slate-400', badge: 'text-slate-600 bg-slate-100', accent: 'blue'  },
};

function HealthCard() {
  const [tiers, setTiers] = useState<ConcentrationEntry[] | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    api
      .get<ConcentrationEntry[]>('/concentration')
      .then((res) => {
        if (!cancelled) setTiers(res.data);
      })
      .catch(() => {
        if (!cancelled) setTiers([]);
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => { cancelled = true; };
  }, []);

  // Determine overall health from the worst tier
  const worstTier =
    tiers && tiers.length > 0
      ? tiers.reduce((worst, t) => {
          const order: Record<ConcentrationEntry['level'], number> = {
            unknown: 0,
            competitive: 1,
            moderately_concentrated: 2,
            highly_concentrated: 3,
          };
          return order[t.level] > order[worst.level] ? t : worst;
        }, tiers[0])
      : null;

  const styles = worstTier ? HHI_LEVEL_STYLES[worstTier.level] : HHI_LEVEL_STYLES.unknown;

  // Count tiers with issues
  const issuedTiers = tiers
    ? tiers.filter((t) => t.level !== 'competitive' && t.level !== 'unknown').length
    : 0;
  const totalTiers = tiers ? tiers.filter((t) => t.level !== 'unknown').length : 0;

  return (
    <Card label="Supply Chain Health" icon={<ChainIcon />} accent={styles.accent}>
      <div className="flex flex-col gap-2">
        {isLoading ? (
          <SkeletonValue />
        ) : worstTier === null ? (
          <span className="text-2xl font-bold text-slate-400 tabular-nums leading-none">--</span>
        ) : (
          <div className="flex items-baseline gap-2">
            <span className={`text-2xl font-bold leading-none ${styles.valueColor}`}>
              {styles.label}
            </span>
            {issuedTiers > 0 && (
              <span className={`text-xs font-semibold px-1.5 py-0.5 rounded ${styles.badge}`}>
                {issuedTiers}/{totalTiers} tiers
              </span>
            )}
          </div>
        )}
        {!isLoading && worstTier && (
          <span className="text-xs text-slate-400 truncate">
            {issuedTiers === 0
              ? 'All tiers competitive'
              : `Worst: ${worstTier.tier_label} (HHI ${worstTier.hhi.toLocaleString()})`}
          </span>
        )}
      </div>
    </Card>
  );
}

// ─── Main export ──────────────────────────────────────────────────────────────

export function MetricCards({ companies, alerts }: MetricCardsProps) {
  return (
    <section
      aria-label="Supply chain summary metrics"
      className="shrink-0 px-4 py-3 bg-slate-50 border-b border-slate-200"
    >
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <CompaniesCard companies={companies} />
        <AlertsCard alerts={alerts} />
        <RiskScoreCard />
        <HealthCard />
      </div>
    </section>
  );
}
