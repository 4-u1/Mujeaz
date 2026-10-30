import React, { useEffect, useState } from 'react';
import { LogIn, ShieldCheck, AlertTriangle } from 'lucide-react';
import { api, DemoUser, ROLE_LABELS, SessionUser } from '../api/client';
import { Language } from '../types';

interface LoginScreenProps {
  lang: Language;
  setLang: (l: Language) => void;
  onLoggedIn: (u: SessionUser) => void;
}

/** Development sign-in: pick a synthetic demo user. A real identity provider replaces this (ADR 0003). */
export const LoginScreen: React.FC<LoginScreenProps> = ({ lang, setLang, onLoggedIn }) => {
  const isAr = lang === 'ar';
  const [users, setUsers] = useState<DemoUser[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.devUsers()
      .then((r) => setUsers(r.users))
      .catch((e: Error) => setError(e.message));
  }, []);

  const login = async (username: string) => {
    setBusy(username);
    setError(null);
    try {
      onLoggedIn(await api.devLogin(username));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-4" dir={isAr ? 'rtl' : 'ltr'}>
      <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-5 shadow-2xl">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <img src="/logo.png" alt="" className="w-10 h-10 rounded-xl" />
            <div>
              <h1 className="text-lg font-extrabold">{isAr ? 'مُجاز' : 'Mujeaz'}</h1>
              <p className="text-[11px] text-slate-400">{isAr ? 'تسجيل دخول تجريبي' : 'Development sign-in'}</p>
            </div>
          </div>
          <button
            onClick={() => setLang(isAr ? 'en' : 'ar')}
            className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold border border-slate-700"
          >
            {isAr ? 'English' : 'العربية'}
          </button>
        </div>

        <div className="flex items-start gap-2 text-[11px] text-amber-200 bg-amber-950/50 border border-amber-800/60 rounded-xl p-3">
          <AlertTriangle className="w-4 h-4 shrink-0 text-amber-400" />
          <span>
            {isAr
              ? 'بيئة تطوير ببيانات اصطناعية فقط. اختر مستخدمًا تجريبيًا لتجربة صلاحيات كل دور.'
              : 'Development environment with synthetic data only. Pick a demo user to try each role’s permissions.'}
          </span>
        </div>

        {error && <div className="text-xs text-red-300 bg-red-950/50 border border-red-800/60 rounded-xl p-3">{error}</div>}

        <div className="space-y-2">
          {users.map((u) => {
            const label = ROLE_LABELS[u.role] ?? { en: u.role, ar: u.role };
            return (
              <button
                key={u.username}
                disabled={busy !== null}
                onClick={() => login(u.username)}
                className="w-full flex items-center justify-between gap-3 px-4 py-3 rounded-xl bg-slate-950 hover:bg-slate-800 border border-slate-800 hover:border-cyan-700 transition-colors text-start disabled:opacity-60"
              >
                <div>
                  <div className="text-sm font-bold">{isAr ? label.ar : label.en}</div>
                  <div className="text-[11px] text-slate-400 font-mono">{u.username}</div>
                </div>
                {busy === u.username ? (
                  <span className="text-[11px] text-cyan-300">…</span>
                ) : (
                  <LogIn className="w-4 h-4 text-cyan-400" />
                )}
              </button>
            );
          })}
          {users.length === 0 && !error && <div className="text-xs text-slate-400">{isAr ? 'جارٍ التحميل…' : 'Loading…'}</div>}
        </div>

        <div className="flex items-center gap-2 text-[11px] text-slate-500">
          <ShieldCheck className="w-3.5 h-3.5" />
          <span>{isAr ? 'رمز دخول RS256 · صلاحيات حسب الدور · عزل بيانات المنشأة' : 'RS256 token · role-based permissions · tenant isolation'}</span>
        </div>
      </div>
    </div>
  );
};
