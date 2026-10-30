import React, { useState } from 'react';
import { PhysicianAnswer } from '../api/client';
import { Language } from '../types';

/** Structured physician answer (decision D1): dates, sessions and provider — never free text. */
export function validateTherapy(start: string, end: string, sessions: number, provider: string, requestedOn?: string): string | null {
  if (!start || !end) return 'Start and end dates are required';
  if (end <= start) return 'End date must be after start date';
  if (requestedOn && end > requestedOn) return 'Therapy must have ended on or before the request date';
  if (!Number.isInteger(sessions) || sessions < 1 || sessions > 60) return 'Sessions must be between 1 and 60';
  if (provider.trim().length < 2) return 'Provider is required';
  return null;
}

interface Props {
  lang: Language;
  requestedOn?: string;
  submitLabel: string;
  busy?: boolean;
  testId: string;
  onSubmit: (answer: PhysicianAnswer) => void;
}

export const TherapyAnswerForm: React.FC<Props> = ({ lang, requestedOn, submitLabel, busy, testId, onSubmit }) => {
  const isAr = lang === 'ar';
  const [start, setStart] = useState('');
  const [end, setEnd] = useState('');
  const [sessions, setSessions] = useState(8);
  const [provider, setProvider] = useState('');
  const [nsaid, setNsaid] = useState<'' | 'naproxen' | 'ibuprofen' | 'diclofenac' | 'celecoxib'>('');
  const [error, setError] = useState<string | null>(null);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const err = validateTherapy(start, end, sessions, provider, requestedOn);
    setError(err);
    if (err) return;
    onSubmit({ kind: 'therapy', start_date: start, end_date: end, sessions, provider: provider.trim(), nsaid: nsaid || null });
  };

  const field = 'w-full bg-slate-950 border border-slate-700 rounded-md px-2 py-1 text-xs text-slate-100';
  return (
    <form onSubmit={submit} className="grid grid-cols-2 sm:grid-cols-5 gap-2 items-end" data-testid={testId}>
      <label className="text-[10px] text-slate-400 space-y-1">
        <span>{isAr ? 'بداية العلاج' : 'Therapy start'}</span>
        <input type="date" aria-label="Therapy start" className={field} value={start} max={requestedOn} onChange={(e) => setStart(e.target.value)} />
      </label>
      <label className="text-[10px] text-slate-400 space-y-1">
        <span>{isAr ? 'نهاية العلاج' : 'Therapy end'}</span>
        <input type="date" aria-label="Therapy end" className={field} value={end} max={requestedOn} onChange={(e) => setEnd(e.target.value)} />
      </label>
      <label className="text-[10px] text-slate-400 space-y-1">
        <span>{isAr ? 'عدد الجلسات' : 'Sessions'}</span>
        <input type="number" aria-label="Sessions" min={1} max={60} className={field} value={sessions} onChange={(e) => setSessions(Number(e.target.value))} />
      </label>
      <label className="text-[10px] text-slate-400 space-y-1">
        <span>{isAr ? 'مقدم الخدمة' : 'Provider'}</span>
        <input type="text" aria-label="Provider" className={field} value={provider} onChange={(e) => setProvider(e.target.value)} />
      </label>
      <label className="text-[10px] text-slate-400 space-y-1">
        <span>{isAr ? 'مضاد التهاب (اختياري)' : 'NSAID (optional)'}</span>
        <select aria-label="NSAID" className={field} value={nsaid} onChange={(e) => setNsaid(e.target.value as typeof nsaid)}>
          <option value="">—</option>
          <option value="naproxen">naproxen</option>
          <option value="ibuprofen">ibuprofen</option>
          <option value="diclofenac">diclofenac</option>
          <option value="celecoxib">celecoxib</option>
        </select>
      </label>
      <div className="col-span-2 sm:col-span-5 flex items-center gap-3">
        <button type="submit" disabled={busy} className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-60 text-white text-xs font-bold">
          {submitLabel}
        </button>
        {error && <span className="text-[11px] text-rose-300">{error}</span>}
      </div>
    </form>
  );
};
