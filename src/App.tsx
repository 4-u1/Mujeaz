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

  // Run AI Evidence Hunter for a case
  const handleRunEvidenceHunter = (caseId: string) => {
    setCases((prevCases) =>
      prevCases.map((c) => {
        if (c.id === caseId) {
          return {
            ...c,
            status: 'DECISION_READY',
            readinessScore: {
              ...c.readinessScore,
              overallScore: 98,
              readinessLabel: 'Decision Ready',
              readinessLabelAr: 'جاهز للقرار والموافقة',
              warningNotice: undefined,
              warningNoticeAr: undefined,
              clinicalEvidence: 98,
              policyMatch: 96,
              requiredAttachments: 99,
            },
            revenueRisk: {
              ...c.revenueRisk,
              denialRiskPercentage: 2,
              revenueAtRisk: 0,
            },
            evidenceItems: [
              {
                id: 'e-hunter-1',
                requirement: 'Proof of conservative physiotherapy and medications in EMR',
                requirementAr: 'إثبات توثيق جلسات العلاج الطبيعي وأدويتها في السجل الطبي',
                status: 'FOUND',
                matchedFact: '6 Physiotherapy sessions found in Encounter #1820',
                sourceEncounter: 'Physical Therapy Suite Encounter #1820',
                date: '2026-06-11',
                confidence: 99,
              },
            ],
            policyRules: c.policyRules.map((r) =>
              r.id === 'pr-1'
                ? { ...r, status: 'PASSED', evidenceSource: 'Encounter #1820 - Physical Therapy' }
                : r
            ),
            agentRuns: c.agentRuns.map((a) =>
              a.agentId === 'A2'
                ? {
                    ...a,
                    status: 'COMPLETED',
                    outputSummary: 'Found 6 Physio sessions & NSAID prescription in EMR history.',
                    outputSummaryAr: 'تم العثور على 6 جلسات علاج طبيعي ووصفة مسكنات في سجل المريض.',
                  }
                : a
            ),
            auditTrail: [
              ...c.auditTrail,
              {
                timestamp: new Date().toISOString().replace('T', ' ').substring(0, 19),
                action: 'Evidence Hunter Discovered 6 Physio Sessions in EMR #1820 - Readiness Score upgraded to 98/100',
                actionAr: 'وكيل صيد الأدلة وجد 6 جلسات في السجل الطبي - ترقية مؤشر الجاهزية إلى 98/100',
                actor: 'Mujeaz Evidence Hunter Agent',
              },
            ],
          };
        }
        return c;
      })
    );

    // Update global metrics
    setMetrics((prev) => ({
      ...prev,
      revenueProtectedTodaySAR: prev.revenueProtectedTodaySAR + 378000,
      revenueAtRiskSAR: Math.max(0, prev.revenueAtRiskSAR - 378000),
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
