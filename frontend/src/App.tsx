/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import { ClaimDigitalTwin, CommandCenterMetrics, Language } from './types';
import { INITIAL_METRICS, MOCK_CASES } from './data/mockCases';
import { Navbar } from './components/Navbar';
import { ExecutiveDashboard } from './components/ExecutiveDashboard';
import { LiveWalkthrough } from './components/LiveWalkthrough';
import { DigitalTwinInspector } from './components/DigitalTwinInspector';
import { AISandbox } from './components/AISandbox';
import { RecoveryQueue } from './components/RecoveryQueue';
import { PolicyKnowledgeBase } from './components/PolicyKnowledgeBase';
import { Footer } from './components/Footer';

export default function App() {
  const [lang, setLang] = useState<Language>('ar');
  const [activeTab, setActiveTab] = useState<'dashboard' | 'walkthrough' | 'digitalTwin' | 'sandbox' | 'recovery' | 'policy'>('dashboard');
  const [cases, setCases] = useState<ClaimDigitalTwin[]>(MOCK_CASES);
  const [selectedCaseId, setSelectedCaseId] = useState<string>('case-4922');
  const [metrics, setMetrics] = useState<CommandCenterMetrics>(INITIAL_METRICS);

  const selectedCase = cases.find((c) => c.id === selectedCaseId) || cases[0];

  const handleSelectCase = (caseId: string) => {
    setSelectedCaseId(caseId);
    setActiveTab('digitalTwin');
  };

  // Run AI Evidence Hunter (A2) for a case.
  // Applies only the evidence that actually exists in that case's record (demo data).
  // If nothing new is found, the case is left unchanged and the miss is logged.
  const handleRunEvidenceHunter = (caseId: string) => {
    const target = cases.find((c) => c.id === caseId);
    if (!target) return;
    const found = target.discoverableEvidence;
    const now = new Date().toISOString().replace('T', ' ').substring(0, 19);

    if (!found || found.evidenceItems.length === 0) {
      setCases((prev) =>
        prev.map((c) =>
          c.id === caseId
            ? {
                ...c,
                auditTrail: [
                  ...c.auditTrail,
                  {
                    timestamp: now,
                    action: 'Evidence Hunter: deep record search found no additional evidence. Case unchanged.',
                    actionAr: 'وكيل صيد الأدلة: لم يُعثر على أدلة إضافية في السجل. لم تتغير الحالة.',
                    actor: 'Mujeaz Evidence Hunter Agent',
                  },
                ],
              }
            : c
        )
      );
      return;
    }

    const previousAtRisk = target.revenueRisk.revenueAtRisk;
    const value = target.revenueRisk.financialValue;
    const newAtRisk = Math.round(value * (found.denialRiskAfter / 100));
    const newOverall = found.readinessAfter.overallScore ?? target.readinessScore.overallScore;

    setCases((prev) =>
      prev.map((c) => {
        if (c.id !== caseId) return c;
        return {
          ...c,
          status: newOverall >= 90 ? 'DECISION_READY' : c.status,
          readinessScore: {
            ...c.readinessScore,
            ...found.readinessAfter,
            warningNotice: undefined,
            warningNoticeAr: undefined,
          },
          revenueRisk: {
            ...c.revenueRisk,
            denialRiskPercentage: found.denialRiskAfter,
            revenueAtRisk: newAtRisk,
            priority: found.denialRiskAfter >= 60 ? 'HIGH' : found.denialRiskAfter >= 30 ? 'MEDIUM' : 'LOW',
          },
          evidenceItems: found.evidenceItems,
          policyRules: c.policyRules.map((r) =>
            found.satisfiesRuleIds.includes(r.id)
              ? { ...r, status: 'PASSED', evidenceSource: found.evidenceSource }
              : r
          ),
          agentRuns: c.agentRuns.map((a) =>
            a.agentId === 'A2'
              ? { ...a, status: 'COMPLETED', outputSummary: found.summary, outputSummaryAr: found.summaryAr }
              : a
          ),
          // Evidence is consumed once attached.
          discoverableEvidence: undefined,
          auditTrail: [
            ...c.auditTrail,
            {
              timestamp: now,
              action: `Evidence Hunter: ${found.summary} Readiness ${c.readinessScore.overallScore} → ${newOverall}/100.`,
              actionAr: `وكيل صيد الأدلة: ${found.summaryAr} مؤشر الجاهزية ${c.readinessScore.overallScore} ← ${newOverall}/100.`,
              actor: 'Mujeaz Evidence Hunter Agent',
            },
          ],
        };
      })
    );

    const protectedAmount = Math.max(0, previousAtRisk - newAtRisk);
    setMetrics((prev) => ({
      ...prev,
      revenueProtectedTodaySAR: prev.revenueProtectedTodaySAR + protectedAmount,
      revenueAtRiskSAR: Math.max(0, prev.revenueAtRiskSAR - protectedAmount),
      preventedDenialsCount: prev.preventedDenialsCount + 1,
    }));
  };

  return (
    <div className={`min-h-screen bg-slate-950 text-slate-100 font-sans antialiased flex flex-col ${lang === 'ar' ? 'rtl' : 'ltr'}`} dir={lang === 'ar' ? 'rtl' : 'ltr'}>
      
      {/* Header Navigation Bar */}
      <Navbar
        lang={lang}
        setLang={setLang}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        selectedCaseId={selectedCaseId}
      />

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 pt-6">
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

        {activeTab === 'walkthrough' && (
          <LiveWalkthrough
            lang={lang}
            case4922={cases.find((c) => c.id === 'case-4922') || cases[0]}
            case8103={cases.find((c) => c.id === 'case-8103') || cases[1]}
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
          />
        )}

        {activeTab === 'sandbox' && <AISandbox lang={lang} />}

        {activeTab === 'recovery' && (
          <RecoveryQueue
            cases={cases}
            lang={lang}
            onSelectCase={handleSelectCase}
          />
        )}

        {activeTab === 'policy' && <PolicyKnowledgeBase lang={lang} />}
      </main>

      {/* Footer */}
      <Footer lang={lang} />

    </div>
  );
}
