// @TASK Toast notification system - UI component
import { useEffect, useRef } from 'react';
import { useToastStore, type Toast, type ToastVariant } from '../../stores/toastStore';

// ---------------------------------------------------------------------------
// Icon helpers (inline SVG — no external icon dep required)
// ---------------------------------------------------------------------------

function CheckIcon() {
  return (
    <svg
      aria-hidden="true"
      className="h-5 w-5 shrink-0"
      viewBox="0 0 20 20"
      fill="currentColor"
    >
      <path
        fillRule="evenodd"
        d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z"
        clipRule="evenodd"
      />
    </svg>
  );
}

function ErrorIcon() {
  return (
    <svg
      aria-hidden="true"
      className="h-5 w-5 shrink-0"
      viewBox="0 0 20 20"
      fill="currentColor"
    >
      <path
        fillRule="evenodd"
        d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z"
        clipRule="evenodd"
      />
    </svg>
  );
}

function InfoIcon() {
  return (
    <svg
      aria-hidden="true"
      className="h-5 w-5 shrink-0"
      viewBox="0 0 20 20"
      fill="currentColor"
    >
      <path
        fillRule="evenodd"
        d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a.75.75 0 000 1.5h.253a.25.25 0 01.244.304l-.459 2.066A1.75 1.75 0 0010.747 15H11a.75.75 0 000-1.5h-.253a.25.25 0 01-.244-.304l.459-2.066A1.75 1.75 0 009.253 9H9z"
        clipRule="evenodd"
      />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg
      aria-hidden="true"
      className="h-4 w-4"
      viewBox="0 0 16 16"
      fill="currentColor"
    >
      <path d="M3.72 3.72a.75.75 0 011.06 0L8 6.94l3.22-3.22a.75.75 0 111.06 1.06L9.06 8l3.22 3.22a.75.75 0 11-1.06 1.06L8 9.06l-3.22 3.22a.75.75 0 01-1.06-1.06L6.94 8 3.72 4.78a.75.75 0 010-1.06z" />
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Per-variant style tokens (maps to CSS variables in index.css)
// ---------------------------------------------------------------------------

const VARIANT_STYLES: Record<
  ToastVariant,
  { bar: string; icon: string; label: string; IconComponent: () => JSX.Element }
> = {
  success: {
    bar: 'bg-success',
    icon: 'text-success',
    label: 'Success',
    IconComponent: CheckIcon,
  },
  error: {
    bar: 'bg-critical',
    icon: 'text-critical',
    label: 'Error',
    IconComponent: ErrorIcon,
  },
  info: {
    bar: 'bg-info',
    icon: 'text-info',
    label: 'Info',
    IconComponent: InfoIcon,
  },
};

// ---------------------------------------------------------------------------
// Single toast item
// ---------------------------------------------------------------------------

interface ToastItemProps {
  toast: Toast;
  onRemove: (id: string) => void;
}

function ToastItem({ toast, onRemove }: ToastItemProps) {
  const itemRef = useRef<HTMLLIElement>(null);
  const { bar, icon, label, IconComponent } = VARIANT_STYLES[toast.variant];

  // Trigger slide-in on mount via CSS class toggle
  useEffect(() => {
    const el = itemRef.current;
    if (!el) return;
    // rAF ensures the initial class is painted before the transition class applies
    requestAnimationFrame(() => {
      el.classList.add('toast-visible');
    });
  }, []);

  return (
    <li
      ref={itemRef}
      role="alert"
      aria-live="assertive"
      aria-atomic="true"
      className={[
        // Base layout
        'relative flex items-start gap-3 w-80 rounded-lg shadow-lg',
        'bg-surface border border-border overflow-hidden',
        // Slide-in transition (initial state: translate + opacity 0)
        'translate-x-full opacity-0 transition-[transform,opacity] duration-300 ease-out',
        // .toast-visible class applied via JS to trigger the entrance
        '[&.toast-visible]:translate-x-0 [&.toast-visible]:opacity-100',
      ].join(' ')}
    >
      {/* Coloured left accent bar */}
      <span className={`absolute left-0 top-0 h-full w-1 ${bar}`} aria-hidden="true" />

      {/* Content */}
      <div className="flex items-start gap-3 px-4 py-3 pl-5 w-full min-w-0">
        <span className={icon}>
          <IconComponent />
        </span>

        <div className="flex-1 min-w-0">
          <p className="text-xs font-semibold text-text-secondary uppercase tracking-wide mb-0.5">
            {label}
          </p>
          <p className="text-sm text-text-primary leading-snug break-words">{toast.message}</p>
        </div>

        <button
          onClick={() => onRemove(toast.id)}
          aria-label="Close notification"
          className={[
            'shrink-0 mt-0.5 rounded p-0.5',
            'text-text-muted hover:text-text-primary',
            'transition-colors duration-150',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-1',
          ].join(' ')}
        >
          <CloseIcon />
        </button>
      </div>
    </li>
  );
}

// ---------------------------------------------------------------------------
// Toast container — rendered once at app root
// ---------------------------------------------------------------------------

export function ToastContainer() {
  const toasts = useToastStore((s) => s.toasts);
  const removeToast = useToastStore((s) => s.removeToast);

  if (toasts.length === 0) return null;

  return (
    <div
      aria-label="Notifications"
      className="fixed top-4 right-4 z-50 flex flex-col gap-2 pointer-events-none"
    >
      <ul className="flex flex-col gap-2 list-none m-0 p-0 pointer-events-auto">
        {toasts.map((toast) => (
          <ToastItem key={toast.id} toast={toast} onRemove={removeToast} />
        ))}
      </ul>
    </div>
  );
}
