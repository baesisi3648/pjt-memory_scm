// @TASK P5-S1-T1 - Alert Settings Page: rule list + toggle + delete
// @SPEC P5: Alert Settings
import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import api from '../services/api';
import type { AlertRule, Severity } from '../types/index';
import { RuleEditorModal } from '../components/alerts/RuleEditorModal';

// ─── Condition helpers ────────────────────────────────────────────────────────

const CONDITION_LABELS: Record<string, string> = {
  price_change:     '가격 변동',
  lead_time:        '리드타임 변동',
  news_detect:      '뉴스 감지',
  inventory_change: '재고 변동',
};

const CHANNEL_LABELS: Record<string, string> = {
  email:  '이메일',
  in_app: '인앱 알림',
};

function buildConditionDescription(condition: Record<string, unknown>): string {
  const type      = condition.type      as string | undefined;
  const threshold = condition.threshold as number | undefined;
  const typeLabel = type ? (CONDITION_LABELS[type] ?? type) : '알 수 없음';

  if (!type || type === 'news_detect') return `${typeLabel} 감지 시 알림`;

  const unitMap: Record<string, string> = {
    price_change:     '%',
    lead_time:        '일',
    inventory_change: '개',
  };
  const unit = unitMap[type] ?? '';
  return threshold !== undefined
    ? `${typeLabel}이 ${threshold}${unit} 이상 변동 시 알림`
    : `${typeLabel} 감지 시 알림`;
}

// ─── Severity badge ───────────────────────────────────────────────────────────

function SeverityBadge({ severity }: { severity: Severity }) {
  const configs: Record<Severity, { label: string; classes: string; barClass: string; iconBg: string; iconText: string }> = {
    critical: {
      label:    'Critical',
      classes:  'bg-red-100 text-red-800 border border-red-200',
      barClass: 'bg-red-500',
      iconBg:   'bg-red-50 text-red-600',
      iconText: 'text-red-600',
    },
    warning: {
      label:    'Warning',
      classes:  'bg-amber-100 text-amber-800 border border-amber-200',
      barClass: 'bg-amber-500',
      iconBg:   'bg-amber-50 text-amber-600',
      iconText: 'text-amber-600',
    },
    info: {
      label:    'Info',
      classes:  'bg-blue-100 text-blue-800 border border-blue-200',
      barClass: 'bg-blue-500',
      iconBg:   'bg-blue-50 text-blue-600',
      iconText: 'text-blue-600',
    },
  };

  const cfg = configs[severity] ?? configs.info;

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${cfg.classes}`}
    >
      {cfg.label}
    </span>
  );
}

// ─── Rule icon (by condition type) ───────────────────────────────────────────

function RuleIcon({ condition, severity }: { condition: Record<string, unknown>; severity: Severity }) {
  const type = condition.type as string | undefined;

  const severityIconBg: Record<Severity, string> = {
    critical: 'bg-red-50 text-red-600',
    warning:  'bg-amber-50 text-amber-600',
    info:     'bg-blue-50 text-blue-600',
  };

  const bg = severityIconBg[severity] ?? 'bg-slate-100 text-slate-500';

  const icons: Record<string, React.ReactNode> = {
    price_change: (
      <svg aria-hidden="true" viewBox="0 0 20 20" fill="currentColor" className="w-6 h-6">
        <path d="M8.433 7.418c.155-.103.346-.196.567-.267v1.698a2.305 2.305 0 01-.567-.267C8.07 8.34 8 8.114 8 8c0-.114.07-.34.433-.582zM11 12.849v-1.698c.22.071.412.164.567.267.364.243.433.468.433.582 0 .114-.07.34-.433.582a2.305 2.305 0 01-.567.267z" />
        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-13a1 1 0 10-2 0v.092a4.535 4.535 0 00-1.676.662C6.602 6.234 6 7.009 6 8c0 .99.602 1.765 1.324 2.246.48.32 1.054.545 1.676.662v1.941c-.391-.127-.68-.317-.843-.504a1 1 0 10-1.51 1.31c.562.649 1.413 1.076 2.353 1.253V15a1 1 0 102 0v-.092a4.535 4.535 0 001.676-.662C13.398 13.766 14 12.991 14 12c0-.99-.602-1.765-1.324-2.246A4.535 4.535 0 0011 9.092V7.151c.391.127.68.317.843.504a1 1 0 101.511-1.31c-.563-.649-1.413-1.076-2.354-1.253V5z" clipRule="evenodd" />
      </svg>
    ),
    lead_time: (
      <svg aria-hidden="true" viewBox="0 0 20 20" fill="currentColor" className="w-6 h-6">
        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
      </svg>
    ),
    news_detect: (
      <svg aria-hidden="true" viewBox="0 0 20 20" fill="currentColor" className="w-6 h-6">
        <path fillRule="evenodd" d="M2 5a2 2 0 012-2h8a2 2 0 012 2v10a2 2 0 002 2H4a2 2 0 01-2-2V5zm3 1h6v4H5V6zm6 6H5v2h6v-2z" clipRule="evenodd" /><path d="M15 7h1a2 2 0 012 2v5.5a1.5 1.5 0 01-3 0V7z" />
      </svg>
    ),
    inventory_change: (
      <svg aria-hidden="true" viewBox="0 0 20 20" fill="currentColor" className="w-6 h-6">
        <path d="M4 3a2 2 0 100 4h12a2 2 0 100-4H4z" />
        <path fillRule="evenodd" d="M3 8h14v7a2 2 0 01-2 2H5a2 2 0 01-2-2V8zm5 3a1 1 0 011-1h2a1 1 0 110 2H9a1 1 0 01-1-1z" clipRule="evenodd" />
      </svg>
    ),
  };

  const icon = (type && icons[type]) ?? (
    <svg aria-hidden="true" viewBox="0 0 20 20" fill="currentColor" className="w-6 h-6">
      <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
    </svg>
  );

  return (
    <div className={`flex-shrink-0 size-12 rounded-lg flex items-center justify-center ${bg}`}>
      {icon}
    </div>
  );
}

// ─── Toggle switch ────────────────────────────────────────────────────────────

function ToggleSwitch({
  checked,
  onChange,
  label,
}: {
  checked: boolean;
  onChange: () => void;
  label: string;
}) {
  return (
    <label className="relative inline-flex items-center cursor-pointer flex-shrink-0">
      <input
        type="checkbox"
        className="sr-only peer"
        checked={checked}
        onChange={onChange}
        aria-label={label}
      />
      <div className="w-11 h-6 bg-slate-200 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-primary/20 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary" />
    </label>
  );
}

// ─── Confirm dialog ───────────────────────────────────────────────────────────

function ConfirmDialog({
  ruleName,
  onConfirm,
  onCancel,
  isDeleting,
}: {
  ruleName: string;
  onConfirm: () => void;
  onCancel: () => void;
  isDeleting: boolean;
}) {
  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-title"
      className="fixed inset-0 z-50 overflow-y-auto"
    >
      <div aria-hidden="true" className="fixed inset-0 bg-slate-900/75 backdrop-blur-sm" />
      <div className="flex min-h-full items-center justify-center p-4">
        <div className="relative bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-sm p-6">
          <h3 id="confirm-title" className="text-base font-bold text-slate-900 mb-2">
            규칙 삭제
          </h3>
          <p className="text-sm text-slate-600 mb-6">
            <span className="font-medium text-slate-900">"{ruleName}"</span> 규칙을 삭제하시겠습니까?
            이 작업은 되돌릴 수 없습니다.
          </p>
          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={onCancel}
              disabled={isDeleting}
              className="px-4 py-2 text-sm font-semibold text-slate-700 bg-white rounded-lg ring-1 ring-inset ring-slate-300 hover:bg-slate-50 transition-colors disabled:opacity-60"
            >
              취소
            </button>
            <button
              type="button"
              onClick={onConfirm}
              disabled={isDeleting}
              className="px-4 py-2 text-sm font-semibold text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors disabled:opacity-60"
            >
              {isDeleting ? '삭제 중...' : '삭제'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Rule card ────────────────────────────────────────────────────────────────

interface RuleCardProps {
  rule: AlertRule;
  onToggle: (rule: AlertRule) => void;
  onEdit:   (rule: AlertRule) => void;
  onDelete: (rule: AlertRule) => void;
}

function RuleCard({ rule, onToggle, onEdit, onDelete }: RuleCardProps) {
  const condition  = rule.condition;
  const severity   = (condition.severity as Severity | undefined) ?? 'info';
  const channels   = (condition.channels as string[] | undefined) ?? [];
  const description = buildConditionDescription(condition);

  const barColors: Record<Severity, string> = {
    critical: 'bg-red-500',
    warning:  'bg-amber-500',
    info:     'bg-blue-500',
  };
  const barColor = barColors[severity] ?? 'bg-slate-300';

  return (
    <article
      className={`group bg-white rounded-xl p-5 border border-slate-200 shadow-sm hover:shadow-md hover:border-primary/30 transition-all duration-200 relative overflow-hidden ${
        !rule.is_active ? 'opacity-75 hover:opacity-100' : ''
      }`}
    >
      {/* Left severity bar */}
      <div className={`absolute top-0 left-0 w-1 h-full ${rule.is_active ? barColor : 'bg-slate-300'}`} aria-hidden="true" />

      <div className="flex flex-col sm:flex-row gap-5 items-start">
        {/* Icon */}
        <RuleIcon
          condition={condition}
          severity={rule.is_active ? severity : 'info'}
        />

        <div className="flex-1 min-w-0 space-y-3 w-full">
          {/* Title row */}
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0">
              <h3 className={`text-lg font-bold leading-tight ${rule.is_active ? 'text-slate-900' : 'text-slate-600'}`}>
                {rule.name}
              </h3>
              <p className="text-sm text-slate-500 mt-1">{description}</p>
            </div>

            {/* Toggle */}
            <ToggleSwitch
              checked={rule.is_active}
              onChange={() => onToggle(rule)}
              label={`${rule.name} 활성화 토글`}
            />
          </div>

          {/* Meta row */}
          <div className="flex flex-wrap items-center gap-3">
            <SeverityBadge severity={severity} />

            {channels.length > 0 && (
              <>
                <div className="h-4 w-px bg-slate-200" aria-hidden="true" />
                <div className="flex items-center gap-2">
                  {channels.map((ch) => (
                    <span
                      key={ch}
                      className="inline-flex items-center gap-1 text-xs font-medium text-slate-600 bg-slate-100 px-2 py-1 rounded"
                    >
                      {CHANNEL_LABELS[ch] ?? ch}
                    </span>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="mt-4 pt-4 border-t border-slate-100 flex justify-end gap-4">
        <button
          type="button"
          onClick={() => onEdit(rule)}
          className="text-sm font-medium text-slate-500 hover:text-primary transition-colors"
        >
          편집
        </button>
        <button
          type="button"
          onClick={() => onDelete(rule)}
          className="text-sm font-medium text-slate-500 hover:text-red-600 transition-colors"
        >
          삭제
        </button>
      </div>
    </article>
  );
}

// ─── Loading skeleton ─────────────────────────────────────────────────────────

function RuleCardSkeleton() {
  return (
    <div className="bg-white rounded-xl p-5 border border-slate-200 shadow-sm animate-pulse relative overflow-hidden">
      <div className="absolute top-0 left-0 w-1 h-full bg-slate-200" />
      <div className="flex gap-5">
        <div className="size-12 rounded-lg bg-slate-100 flex-shrink-0" />
        <div className="flex-1 space-y-3">
          <div className="h-5 bg-slate-100 rounded w-48" />
          <div className="h-4 bg-slate-100 rounded w-72" />
          <div className="h-5 bg-slate-100 rounded w-20" />
        </div>
      </div>
    </div>
  );
}

// ─── Empty state ──────────────────────────────────────────────────────────────

function EmptyState({ onAdd }: { onAdd: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-4 text-center">
      <div className="w-16 h-16 rounded-full bg-slate-100 flex items-center justify-center mb-4">
        <svg aria-hidden="true" viewBox="0 0 20 20" fill="currentColor" className="w-8 h-8 text-slate-400">
          <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
        </svg>
      </div>
      <h3 className="text-base font-semibold text-slate-900 mb-1">알림 규칙이 없습니다</h3>
      <p className="text-sm text-slate-500 mb-6 max-w-xs">
        새 규칙을 추가하여 공급망 위험을 실시간으로 감지하세요.
      </p>
      <button
        type="button"
        onClick={onAdd}
        className="inline-flex items-center gap-2 px-5 h-10 rounded-lg bg-primary hover:bg-primary-hover text-white font-medium text-sm transition-colors shadow-sm"
      >
        <svg aria-hidden="true" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
          <path fillRule="evenodd" d="M10 5a1 1 0 011 1v3h3a1 1 0 110 2h-3v3a1 1 0 11-2 0v-3H6a1 1 0 110-2h3V6a1 1 0 011-1z" clipRule="evenodd" />
        </svg>
        새 규칙 추가
      </button>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export function AlertSettingsPage() {
  const [rules,      setRules]      = useState<AlertRule[]>([]);
  const [isLoading,  setIsLoading]  = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);

  // Modal state
  const [isModalOpen,   setIsModalOpen]   = useState(false);
  const [editingRule,   setEditingRule]   = useState<AlertRule | undefined>(undefined);

  // Delete confirm state
  const [deleteTarget,  setDeleteTarget]  = useState<AlertRule | null>(null);
  const [isDeleting,    setIsDeleting]    = useState(false);

  // ── Fetch ──────────────────────────────────────────────────────────────────

  const fetchRules = useCallback(async () => {
    setIsLoading(true);
    setFetchError(null);
    try {
      const res = await api.get<{ items: AlertRule[]; count: number }>('/alert-rules');
      setRules(res.data.items);
    } catch {
      setFetchError('알림 규칙을 불러오는 데 실패했습니다.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRules();
  }, [fetchRules]);

  // ── Toggle (optimistic) ────────────────────────────────────────────────────

  async function handleToggle(rule: AlertRule) {
    // Optimistic update
    setRules((prev) =>
      prev.map((r) => (r.id === rule.id ? { ...r, is_active: !r.is_active } : r))
    );
    try {
      await api.patch(`/alert-rules/${rule.id}/toggle`);
    } catch {
      // Revert on failure
      setRules((prev) =>
        prev.map((r) => (r.id === rule.id ? { ...r, is_active: rule.is_active } : r))
      );
    }
  }

  // ── Delete ─────────────────────────────────────────────────────────────────

  async function handleDeleteConfirm() {
    if (!deleteTarget) return;
    setIsDeleting(true);
    try {
      await api.delete(`/alert-rules/${deleteTarget.id}`);
      setRules((prev) => prev.filter((r) => r.id !== deleteTarget.id));
      setDeleteTarget(null);
    } catch {
      // Keep dialog open so user can retry
    } finally {
      setIsDeleting(false);
    }
  }

  // ── Modal helpers ──────────────────────────────────────────────────────────

  function openCreateModal() {
    setEditingRule(undefined);
    setIsModalOpen(true);
  }

  function openEditModal(rule: AlertRule) {
    setEditingRule(rule);
    setIsModalOpen(true);
  }

  function closeModal() {
    setIsModalOpen(false);
    setEditingRule(undefined);
  }

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-background">
      <main className="w-full max-w-[960px] mx-auto px-4 sm:px-6 lg:px-8 py-8 flex flex-col gap-8">

        {/* Breadcrumb + header */}
        <div className="flex flex-col gap-6">
          <nav aria-label="Breadcrumb" className="flex items-center text-sm text-slate-500">
            <Link to="/dashboard" className="hover:text-primary transition-colors">
              대시보드
            </Link>
            <span className="mx-2 text-slate-300" aria-hidden="true">/</span>
            <span className="text-slate-900 font-medium">알림 설정</span>
          </nav>

          <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
            <div className="space-y-2">
              <h1 className="text-3xl font-black tracking-tight text-slate-900">알림 설정</h1>
              <p className="text-slate-500 max-w-xl text-sm leading-relaxed">
                공급망 위험 감지 규칙 및 알림 채널을 관리하여 중요한 변화에 즉각 대응하세요.
              </p>
            </div>

            <button
              type="button"
              onClick={openCreateModal}
              className="inline-flex items-center justify-center gap-2 h-10 px-5 rounded-lg bg-primary hover:bg-primary-hover text-white font-medium text-sm transition-colors shadow-sm flex-shrink-0"
            >
              <svg aria-hidden="true" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
                <path fillRule="evenodd" d="M10 5a1 1 0 011 1v3h3a1 1 0 110 2h-3v3a1 1 0 11-2 0v-3H6a1 1 0 110-2h3V6a1 1 0 011-1z" clipRule="evenodd" />
              </svg>
              규칙 추가
            </button>
          </div>
        </div>

        {/* Rule list area */}
        <div className="space-y-4">

          {/* Loading skeletons */}
          {isLoading && (
            <>
              <RuleCardSkeleton />
              <RuleCardSkeleton />
              <RuleCardSkeleton />
            </>
          )}

          {/* Fetch error */}
          {!isLoading && fetchError && (
            <div role="alert" className="rounded-xl border border-red-200 bg-red-50 px-5 py-4 flex items-center gap-3">
              <svg aria-hidden="true" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5 text-red-500 flex-shrink-0">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
              <p className="text-sm text-red-700">{fetchError}</p>
              <button
                type="button"
                onClick={fetchRules}
                className="ml-auto text-sm font-medium text-red-700 hover:text-red-900 underline"
              >
                재시도
              </button>
            </div>
          )}

          {/* Empty state */}
          {!isLoading && !fetchError && rules.length === 0 && (
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm">
              <EmptyState onAdd={openCreateModal} />
            </div>
          )}

          {/* Rule cards */}
          {!isLoading && !fetchError && rules.map((rule) => (
            <RuleCard
              key={rule.id}
              rule={rule}
              onToggle={handleToggle}
              onEdit={openEditModal}
              onDelete={(r) => setDeleteTarget(r)}
            />
          ))}

          {/* Add rule dashed button */}
          {!isLoading && !fetchError && rules.length > 0 && (
            <button
              type="button"
              onClick={openCreateModal}
              className="w-full h-24 rounded-xl border-2 border-dashed border-slate-300 flex flex-col items-center justify-center gap-2 text-slate-500 hover:text-primary hover:border-primary hover:bg-slate-50 transition-all duration-200 group"
            >
              <div className="p-2 rounded-full bg-slate-100 group-hover:bg-blue-50 transition-colors">
                <svg aria-hidden="true" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5">
                  <path fillRule="evenodd" d="M10 5a1 1 0 011 1v3h3a1 1 0 110 2h-3v3a1 1 0 11-2 0v-3H6a1 1 0 110-2h3V6a1 1 0 011-1z" clipRule="evenodd" />
                </svg>
              </div>
              <span className="text-sm font-medium">새로운 알림 규칙 만들기</span>
            </button>
          )}
        </div>

        {/* Back to dashboard link */}
        <div className="pt-2">
          <Link
            to="/dashboard"
            className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-primary transition-colors"
          >
            <svg aria-hidden="true" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
              <path fillRule="evenodd" d="M9.707 16.707a1 1 0 01-1.414 0l-6-6a1 1 0 010-1.414l6-6a1 1 0 011.414 1.414L5.414 9H17a1 1 0 110 2H5.414l4.293 4.293a1 1 0 010 1.414z" clipRule="evenodd" />
            </svg>
            대시보드로 돌아가기
          </Link>
        </div>
      </main>

      {/* Rule editor modal */}
      {isModalOpen && (
        <RuleEditorModal
          rule={editingRule}
          onClose={closeModal}
          onSave={fetchRules}
        />
      )}

      {/* Delete confirmation dialog */}
      {deleteTarget && (
        <ConfirmDialog
          ruleName={deleteTarget.name}
          onConfirm={handleDeleteConfirm}
          onCancel={() => setDeleteTarget(null)}
          isDeleting={isDeleting}
        />
      )}
    </div>
  );
}
