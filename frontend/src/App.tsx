/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useCallback, useEffect, useState } from 'react';
import { LogOut, RefreshCw, AlertTriangle } from 'lucide-react';
import { ClaimDigitalTwin, CommandCenterMetrics, Language } from './types';
import { api, ApiError, onUnauthorized, ROLE_LABELS, session, SessionUser } from './api/client';
import { Navbar } from './components/Navbar';
import { ExecutiveDashboard } from './components/ExecutiveDashboard';
import { LiveWalkthrough } from './components/LiveWalkthrough';
import { DigitalTwinInspector } from './components/DigitalTwinInspector';
import { AISandbox } from './components/AISandbox';
import { RecoveryQueue } from './components/RecoveryQueue';
import { PolicyKnowledgeBase } from './components/PolicyKnowledgeBase';
import { Footer } from './components/Footer';
import { LoginScreen } from './components/LoginScreen';

type Tab = 'dashboard' | 'walkthrough' | 'digitalTwin' | 'sandbox' | 'recovery' | 'policy';

export default function App() {
  const [lang, setLang] = useState<Language>('ar');
  const [user, setUser] = useState<SessionUser | null>(() => (session.token() ? session.user() : null));
  const [activeTab, setActiveTab] = useState<Tab>('dashboard');
  const [cases, setCases] = useState<ClaimDigitalTwin[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);
  // null = this role has no metrics:read permission (the dashboard says so instead of showing zeros)
  const [metrics, setMetrics] = useState<CommandCenterMetrics | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const isAr = lang === 'ar';

  useEffect(() => onUnauthorized(() => setUser(null)), []);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [twins, m] = await Promise.all([
        api.twins(),
        api.metrics().catch((e) => {
          if (e instanceof ApiError && e.status === 403) return null;
          throw e;
        }),
      ]);
      setCases(twins.items);
      setMetrics(m);
      setSelectedCaseId((cur) => cur ?? twins.items.find((c) => c.legacyId === 'case-4922')?.id ?? twins.items[0]?.id ?? null);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (user) void load();
  }, [user, load]);

  const refreshCase = useCallback(async (caseId: string) => {
    const [twin, m] = await Promise.all([api.twin(caseId), api.metrics().catch(() => null)]);
    setCases((prev) => prev.map((c) => (c.id === caseId ? twin : c)));
    setMetrics(m);
  }, []);

  const handleSelectCase = (caseId: string) => {
    setSelectedCaseId(caseId);
    setActiveTab('digitalTwin');
  };

  // Evidence Hunter (A2). In M1 this applies only evidence that the demo record contains;
  // the server writes the audit entry and recomputes the state.
  const handleRunEvidenceHunter = async (caseId: string) => {
    try {
      await api.evidenceHunterDemo(caseId);
      await refreshCase(caseId);
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const logout = () => {
    session.clear();
    setUser(null);
    setCases([]);
    setSelectedCaseId(null);
  };

  if (!user) {
    return <LoginScreen lang={lang} setLang={setLang} onLoggedIn={setUser} />;
  }

  const selectedCase = cases.find((c) => c.id === selectedCaseId) || cases[0];
  const case4922 = cases.find((c) => c.legacyId === 'case-4922');
  const case8103 = cases.find((c) => c.legacyId === 'case-8103');
  // Mirrors the server's RBAC matrix (case:analyze); the server still enforces it.
  const canAnalyze = user.roles.some((r) => r === 'auth_officer' || r === 'coder');
  const role = ROLE_LABELS[user.roles[0]] ?? { en: user.roles[0], ar: user.roles[0] };

  return (
    <div className={`min-h-screen bg-slate-950 text-slate-100 font-sans antialiased flex flex-col ${isAr ? 'rtl' : 'ltr'}`} dir={isAr ? 'rtl' : 'ltr'}>
      <Navbar
        lang={lang}
        setLang={setLang}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        selectedCaseId={selectedCaseId ?? ''}
      />

      <div className="max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 pt-3 flex flex-wrap items-center justify-between gap-2 text-xs">
        <div className="flex items-center gap-2 text-slate-400">
          <span className="px-2 py-0.5 rounded-md bg-slate-900 border border-slate-800 text-slate-200 font-semibold">{user.name}</span>
          <span>{isAr ? role.ar : role.en}</span>
          <span className="text-slate-600">·</span>
          <span>{isAr ? `${cases.length} حالة من قاعدة البيانات` : `${cases.length} cases from the database`}</span>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => void load()} className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-900 border border-slate-800 hover:bg-slate-800">
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            {isAr ? 'تحديث' : 'Refresh'}
          </button>
          <button onClick={logout} className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-900 border border-slate-800 hover:bg-slate-800">
            <LogOut className="w-3.5 h-3.5" />
            {isAr ? 'خروج' : 'Sign out'}
          </button>
        </div>
      </div>

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 pt-4">
        {error && (
          <div className="mb-4 flex items-start gap-2 text-xs text-red-200 bg-red-950/50 border border-red-800/60 rounded-xl p-3">
            <AlertTriangle className="w-4 h-4 shrink-0 text-red-400" />
            <span>{error}</span>
          </div>
        )}

        {loading && cases.length === 0 && (
          <div className="text-sm text-slate-400 py-16 text-center">{isAr ? 'جارٍ تحميل الحالات…' : 'Loading cases…'}</div>
        )}

        {cases.length > 0 && selectedCase && (
          <>
            {activeTab === 'dashboard' && (
              <ExecutiveDashboard
                metrics={metrics}
                cases={cases}
                lang={lang}
                onSelectCase={handleSelectCase}
                onNavigateTab={setActiveTab}
                onRunEvidenceHunter={handleRunEvidenceHunter}
              />
            )}

            {activeTab === 'walkthrough' && case4922 && case8103 && (
              <LiveWalkthrough
                lang={lang}
                case4922={case4922}
                case8103={case8103}
                onRunEvidenceHunter={handleRunEvidenceHunter}
                onSelectCase={handleSelectCase}
              />
            )}

            {activeTab === 'digitalTwin' && (
              <DigitalTwinInspector
                claim={selectedCase}
                lang={lang}
                onBack={() => setActiveTab('dashboard')}
                onRunEvidenceHunter={handleRunEvidenceHunter}
                canAnalyze={canAnalyze}
                onAnalyzed={refreshCase}
              />
            )}

            {activeTab === 'sandbox' && <AISandbox lang={lang} />}

            {activeTab === 'recovery' && <RecoveryQueue cases={cases} lang={lang} onSelectCase={handleSelectCase} />}

            {activeTab === 'policy' && <PolicyKnowledgeBase lang={lang} />}
          </>
        )}
      </main>

      <Footer lang={lang} />
    </div>
  );
}
