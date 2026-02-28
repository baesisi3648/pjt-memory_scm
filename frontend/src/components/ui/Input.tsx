// @TASK P1-S0-T1 - Reusable Input component
import React from 'react';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  leftIcon?: React.ReactNode;
  rightElement?: React.ReactNode;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, leftIcon, rightElement, id, className = '', ...props }, ref) => {
    const inputId = id ?? label?.toLowerCase().replace(/\s+/g, '-');

    return (
      <div className="flex flex-col gap-1.5 w-full">
        {label && (
          <label
            htmlFor={inputId}
            className="text-sm font-medium text-text-primary"
          >
            {label}
          </label>
        )}
        <div className="relative">
          {leftIcon && (
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted pointer-events-none flex items-center">
              {leftIcon}
            </span>
          )}
          <input
            ref={ref}
            id={inputId}
            aria-invalid={!!error}
            aria-describedby={error ? `${inputId}-error` : undefined}
            className={[
              'w-full h-11 rounded-lg border bg-surface text-text-primary',
              'text-sm placeholder:text-text-muted',
              'outline-none transition-colors duration-150',
              'focus:border-primary focus:ring-1 focus:ring-primary',
              'disabled:opacity-50 disabled:cursor-not-allowed',
              error
                ? 'border-critical focus:border-critical focus:ring-critical'
                : 'border-border',
              leftIcon ? 'pl-10' : 'pl-3',
              rightElement ? 'pr-10' : 'pr-3',
              className,
            ].join(' ')}
            {...props}
          />
          {rightElement && (
            <span className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center">
              {rightElement}
            </span>
          )}
        </div>
        {error && (
          <p
            id={`${inputId}-error`}
            role="alert"
            className="text-xs text-critical"
          >
            {error}
          </p>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';
