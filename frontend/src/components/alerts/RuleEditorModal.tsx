// @TASK P5-S1-T2 - Alert Rule Editor Modal (create / edit)
// @SPEC P5: Alert Settings - Rule Editor Modal
import { useState, useEffect } from 'react';
import api from '../../services/api';
import type { AlertRule, Severity } from '../../types/index';

// ─── Condition types ─────────────────────────────────────────────────────────

type ConditionType = 'price_change' | 'lead_time' | 'news_detect' | 'inventory_change';

interface RuleCondition {
  type: ConditionType;
  threshold: number;
  severity: Severity;
  channels: Array<'email' | 'in_app'>;
}

const CONDITION_OPTIONS: { value: ConditionType; label: string; unit: string }[] = [
  { value: 'price_change',      label: '가격 변동',   unit: '%'    },
  { value: 'lead_time',         label: '리드타임 변동', unit: '일'  },
  { value: 'news_detect',       label: '뉴스 감지',   unit: '-'    },
  { value: 'inventory_change',  label: '재고 변동',   unit: 'count' },
];

const SEVERITY_OPTIONS: { value: Severity; label: string }[] = [
  { value: 'critical', label: 'Critical' },
  { value: 'warning',  label: 'Warning'  },
  { value: 'info',     label: 'Info'     },
];

// ─── Helpers ─────────────────────────────────────────────────────────────────

function parseCondition(raw: Record<string, unknown>): RuleCondition {
  return {
    type:      (raw.type      as ConditionType) ?? 'price_change',
    threshold: (raw.threshold as number)        ?? 0,
    severity:  (raw.severity  as Severity)      ?? 'info',
    channels:  (raw.channels  as Array<'email' | 'in_app'>) ?? [],
  };
}

// ─── Props ───────────────────────────────────────────────────────────────────

interface RuleEditorModalProps {
  /** Provide a rule to edit it; omit (undefined) for create mode */
  rule?: AlertRule;
  onClose: () => void;
  onSave: () => void;
}

// ─── Component ───────────────────────────────────────────────────────────────

export function RuleEditorModal({ rule, onClose, onSave }: RuleEditorModalProps) {
  const isEditMode = rule !== undefined;
  const existingCondition = isEditMode ? parseCondition(rule.condition) : null;

  // Form state
  const [name,      setName]      = useState(rule?.name ?? '');
  const [condType,  setCondType]  = useState<ConditionType>(existingCondition?.type ?? 'price_change');
  const [threshold, setThreshold] = useState<number>(existingCondition?.threshold ?? 5);
  const [severity,  setSeverity]  = useState<Severity>(existingCondition?.severity ?? 'warning');
  const [channels,  setChannels]  = useState<Array<'email' | 'in_app'>>(
    existingCondition?.channels ?? ['email']
  );

  const [isSaving, setIsSaving] = useState(false);
  const [error,    setError]    = useState<string | null>(null);

  // Re-populate when rule prop changes (e.g., modal re-used)
  useEffect(() => {
    if (rule) {
      const c = parseCondition(rule.condition);
      setName(rule.name);
      setCondType(c.type);
      setThreshold(c.threshold);
      setSeverity(c.severity);
      setChannels(c.channels);
    }
  }, [rule]);

  // Derived unit label
  const unitLabel = CONDITION_OPTIONS.find((o) => o.value === condType)?.unit ?? '';

  // Channel toggle helper
  function toggleChannel(ch: 'email' | 'in_app') {
    setChannels((prev) =>
      prev.includes(ch) ? prev.filter((c) => c !== ch) : [...prev, ch]
    );
  }

  async function handleSave() {
    if (!name.trim()) {
      setError('규칙 이름을 입력해 주세요.');
      return;
    }
    setError(null);
    setIsSaving(true);

    const payload = {
      name: name.trim(),
      condition: {
        type: condType,
        threshold,
        severity,
        channels,
      } satisfies RuleCondition,
    };

    try {
      if (isEditMode) {
        await api.put(`/alert-rules/${rule!.id}`, payload);
      } else {
        await api.post('/alert-rules', payload);
      }
      onSave();
      onClose();
    } catch {
      setError('저장 중 오류가 발생했습니다. 다시 시도해 주세요.');
    } finally {
      setIsSaving(false);
    }
  }

  // Close on backdrop click
  function handleBackdropClick(e: React.MouseEvent<HTMLDivElement>) {
    if (e.target === e.currentTarget) onClose();
  }

  // Severity button styling
  function severityButtonClass(val: Severity): string {
    const isSelected = severity === val;
    if (!isSelected) {
      return 'cursor-pointer border border-slate-200 rounded-lg p-2 flex items-center justify-center gap-2 hover:bg-slate-50 text-slate-600 transition-colors';
    }
    if (val === 'critical') return 'cursor-pointer border border-transparent rounded-lg p-2 flex items-center justify-center gap-2 bg-red-50 text-red-700 ring-2 ring-red-500';
    if (val === 'warning')  return 'cursor-pointer border border-transparent rounded-lg p-2 flex items-center justify-center gap-2 bg-amber-50 text-amber-700 ring-2 ring-amber-500';
    return                         'cursor-pointer border border-transparent rounded-lg p-2 flex items-center justify-center gap-2 bg-blue-50 text-blue-700 ring-2 ring-blue-500';
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
      className="fixed inset-0 z-50 overflow-y-auto"
      onClick={handleBackdropClick}
    >
      {/* Backdrop */}
      <div
        aria-hidden="true"
        className="fixed inset-0 bg-slate-900/75 backdrop-blur-sm transition-opacity"
      />

      <div className="flex min-h-full items-center justify-center p-4 sm:p-0">
        {/* Panel */}
        <div className="relative transform overflow-hidden rounded-2xl bg-white text-left shadow-2xl transition-all sm:my-8 w-full sm:max-w-[560px] border border-slate-200">

          {/* Header */}
          <div className="px-6 py-5 border-b border-slate-100 flex items-center justify-between">
            <h3
              id="modal-title"
              className="text-lg font-bold leading-6 text-slate-900"
            >
              {isEditMode ? '규칙 편집' : '새 규칙 추가'}
            </h3>
            <button
              type="button"
              onClick={onClose}
              aria-label="모달 닫기"
              className="text-slate-400 hover:text-slate-600 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-primary rounded"
            >
              {/* X icon */}
              <svg aria-hidden="true" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5">
                <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
              </svg>
            </button>
          </div>

          {/* Body */}
          <div className="px-6 py-6 space-y-6">

            {/* Error banner */}
            {error && (
              <div role="alert" className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
                {error}
              </div>
            )}

            {/* Rule name */}
            <div>
              <label
                htmlFor="rule-name"
                className="block text-sm font-medium leading-6 text-slate-900"
              >
                규칙 이름
              </label>
              <div className="mt-2">
                <input
                  id="rule-name"
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="예: DRAM 가격 급등 알림"
                  className="block w-full rounded-lg border-0 py-2.5 px-3 text-slate-900 bg-slate-50 shadow-sm ring-1 ring-inset ring-slate-300 placeholder:text-slate-400 focus:ring-2 focus:ring-inset focus:ring-primary sm:text-sm sm:leading-6"
                />
              </div>
            </div>

            {/* Condition type + Threshold */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label
                  htmlFor="condition-type"
                  className="block text-sm font-medium leading-6 text-slate-900"
                >
                  감지 조건
                </label>
                <div className="mt-2">
                  <select
                    id="condition-type"
                    value={condType}
                    onChange={(e) => setCondType(e.target.value as ConditionType)}
                    className="block w-full rounded-lg border-0 py-2.5 pl-3 pr-10 text-slate-900 bg-slate-50 ring-1 ring-inset ring-slate-300 focus:ring-2 focus:ring-primary sm:text-sm sm:leading-6"
                  >
                    {CONDITION_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label
                  htmlFor="threshold"
                  className="block text-sm font-medium leading-6 text-slate-900"
                >
                  임계값
                </label>
                <div className="mt-2 relative rounded-md">
                  <input
                    id="threshold"
                    type="number"
                    min={0}
                    value={threshold}
                    onChange={(e) => setThreshold(Number(e.target.value))}
                    disabled={condType === 'news_detect'}
                    placeholder="5"
                    className="block w-full rounded-lg border-0 py-2.5 px-3 pr-10 text-slate-900 bg-slate-50 shadow-sm ring-1 ring-inset ring-slate-300 placeholder:text-slate-400 focus:ring-2 focus:ring-inset focus:ring-primary sm:text-sm sm:leading-6 disabled:opacity-50 disabled:cursor-not-allowed"
                  />
                  {unitLabel && unitLabel !== '-' && (
                    <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-3">
                      <span className="text-slate-500 sm:text-sm">{unitLabel}</span>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Severity */}
            <div>
              <span className="block text-sm font-medium leading-6 text-slate-900 mb-2">
                중요도
              </span>
              <div className="grid grid-cols-3 gap-3" role="radiogroup" aria-label="중요도 선택">
                {SEVERITY_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    role="radio"
                    aria-checked={severity === opt.value}
                    onClick={() => setSeverity(opt.value)}
                    className={severityButtonClass(opt.value)}
                  >
                    <span className="text-sm font-semibold">{opt.label}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Channels */}
            <div>
              <span className="block text-sm font-medium leading-6 text-slate-900 mb-2">
                알림 채널
              </span>
              <div className="flex gap-6">
                {(
                  [
                    { id: 'channel-email', value: 'email',  label: '이메일'   },
                    { id: 'channel-inapp', value: 'in_app', label: '인앱 알림' },
                  ] as const
                ).map((ch) => (
                  <label
                    key={ch.value}
                    htmlFor={ch.id}
                    className="relative flex items-center gap-2 cursor-pointer group"
                  >
                    <input
                      id={ch.id}
                      type="checkbox"
                      checked={channels.includes(ch.value)}
                      onChange={() => toggleChannel(ch.value)}
                      className="h-4 w-4 rounded border-slate-300 text-primary focus:ring-primary"
                    />
                    <span className="text-sm font-medium text-slate-900 group-hover:text-primary transition-colors">
                      {ch.label}
                    </span>
                  </label>
                ))}
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="bg-slate-50 px-6 py-4 flex flex-row-reverse gap-3">
            <button
              type="button"
              onClick={handleSave}
              disabled={isSaving}
              className="inline-flex w-full justify-center rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-primary-hover sm:w-auto transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {isSaving ? '저장 중...' : '변경사항 저장'}
            </button>
            <button
              type="button"
              onClick={onClose}
              disabled={isSaving}
              className="inline-flex w-full justify-center rounded-lg bg-white px-4 py-2 text-sm font-semibold text-slate-900 shadow-sm ring-1 ring-inset ring-slate-300 hover:bg-slate-50 sm:w-auto transition-colors disabled:opacity-60"
            >
              취소
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
