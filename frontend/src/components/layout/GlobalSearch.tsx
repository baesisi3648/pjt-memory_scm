import { useState, useRef, useEffect } from 'react';
import api from '../../services/api';
import type { Company } from '../../types/index';

interface SearchResult {
  id: number;
  name: string;
  name_kr: string;
  tier: string;
  country: string;
}

export function GlobalSearch() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Search companies as user types (debounced)
  useEffect(() => {
    if (query.trim().length < 1) {
      setResults([]);
      return;
    }

    const timer = setTimeout(async () => {
      setIsLoading(true);
      try {
        const res = await api.get<{ items: Company[]; count: number }>('/companies', {
          params: { limit: 100 },
        });
        // Client-side filter (simple approach)
        const q = query.toLowerCase();
        const filtered = res.data.items
          .filter(
            (c) =>
              c.name.toLowerCase().includes(q) ||
              (c.name_kr && c.name_kr.toLowerCase().includes(q)) ||
              c.tier.toLowerCase().includes(q) ||
              c.country.toLowerCase().includes(q)
          )
          .slice(0, 8);
        setResults(filtered.map(c => ({ id: c.id, name: c.name, name_kr: c.name_kr || '', tier: c.tier, country: c.country })));
      } catch {
        setResults([]);
      } finally {
        setIsLoading(false);
      }
    }, 200);

    return () => clearTimeout(timer);
  }, [query]);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  // Ctrl+K shortcut to focus search
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        inputRef.current?.focus();
        setIsOpen(true);
      }
      if (e.key === 'Escape') {
        setIsOpen(false);
        inputRef.current?.blur();
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);

  const tierLabels: Record<string, string> = {
    raw_material: '원자재',
    equipment: '장비',
    fab: '팹',
    packaging: '패키징',
    module: '모듈',
  };

  return (
    <div ref={containerRef} className="relative">
      <div className="relative">
        <svg className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-500" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
          <path fillRule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clipRule="evenodd" />
        </svg>
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => { setQuery(e.target.value); setIsOpen(true); }}
          onFocus={() => setIsOpen(true)}
          placeholder="검색 (Ctrl+K)"
          aria-label="기업 검색"
          className="w-48 h-8 pl-8 pr-3 rounded-md bg-neutral-800 border border-neutral-700 text-sm text-white placeholder-neutral-500 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-colors"
        />
      </div>

      {/* Dropdown results */}
      {isOpen && query.trim().length > 0 && (
        <div className="absolute top-full mt-1 left-0 w-72 bg-white rounded-lg shadow-xl border border-slate-200 overflow-hidden z-50">
          {isLoading && (
            <div className="px-4 py-3 text-sm text-slate-500">검색 중...</div>
          )}
          {!isLoading && results.length === 0 && (
            <div className="px-4 py-3 text-sm text-slate-500">결과 없음</div>
          )}
          {!isLoading && results.map((r) => (
            <button
              key={r.id}
              onClick={() => {
                setIsOpen(false);
                setQuery('');
                // Dispatch a custom event that DashboardPage can listen to
                window.dispatchEvent(new CustomEvent('select-company', { detail: { companyId: r.id } }));
              }}
              className="w-full px-4 py-2.5 text-left hover:bg-slate-50 flex items-center gap-3 transition-colors"
            >
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-slate-900 truncate">{r.name_kr || r.name}</div>
                <div className="text-xs text-slate-500">{r.name} · {tierLabels[r.tier] || r.tier} · {r.country}</div>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
