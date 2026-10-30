import React, { useState } from 'react';
import { BrainCircuit, CheckCircle2, CircleDashed, FileSearch, HelpCircle, Loader2, ShieldAlert } from 'lucide-react';
import { api, AnalyzeEvent } from '../api/client';
import { ClaimDigitalTwin, Language } from '../types';

const AGENTS: { id: string; en: string; ar: string }[] = [
  { id: 'A1', en: 'Clinical understanding', ar: 'الفهم السريري' },
  { id: 'A2', en: 'Evidence hunter', ar: 'صيد الأدلة' },
  { id: 'A3', en: 'Policy rules', ar: 'مطابقة السياسة' },
  { id: 'A5', en: 'Readiness & risk', ar: 'الجاهزية والمخاطر' },
];
const ANALYZABLE = new Set(['DRAFT', 'RISK_DETECTED', 'EVIDENCE_SEARCHING', 'DECISION_READY']);
const LABELS: Record<string, { en: string; ar: string }> = {
  symptom_duration: { en: 'Symptom duration', ar: 'مدة الأعراض' },
  exam_slr: { en: 'Exam finding', ar: 'نتيجة الفحص' },
  conservative_therapy: { en: 'Conservative therapy', ar: 'علاج تحفظي' },
  medication: { en: 'Medication', ar: 'دواء' },
  persistent_symptoms: { en: 'Persistent symptoms', ar: 'استمرار الأعراض' },
  red_flag: { en: 'Red flag', ar: 'مؤشر خطير' },
  claimed_therapy: { en: 'Therapy claimed', ar: 'علاج مُدّعى' },
  therapy_not_attended: { en: 'Therapy not attended', ar: 'لم يحضر العلاج' },
  therapy_negated: { en: 'No therapy documented', ar: 'نفي العلاج' },
  requested_service: { en: 'Requested service', ar: 'الخدمة المطلوبة' },
};
const STATUS_STYLE: Record<string, string> = {
  FOUND: 'bg-emerald-950/60 text-emerald-300 border-emerald-800',
  PARTIAL: 'bg-amber-950/60 text-amber-300 border-amber-800',
  MISSING: 'bg-rose-950/60 text-rose-300 border-rose-800',
};

interface Props {
  claim: ClaimDigitalTwin;
  lang: Language;
  canAnalyze: boolean;
  onAnalyzed: (caseId: string) => Promise<void>;
}

export const AnalysisPanel: React.FC<Props> = ({ claim, lang, canAnalyze, onAnalyzed }) => {
  const isAr = lang === 'ar';
  const [running, setRunning] = useState(false);
  const [steps, setSteps] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    setRunning(true);
    setError(null);
    setSteps({});
    try {
      await api.analyzeCase(claim.id, (e: AnalyzeEvent) => {
        if (e.event === 'step') setSteps((s) => ({ ...s, [e.data.agent]: e.data.status }));
      });
      await onAnalyzed(claim.id);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setRunning(false);
    }
  };

  const a = claim.analysis;
  const agentFacts = claim.clinicalFacts.filter((f) => f.label && f.quote);
  const showSteps = running || Object.keys(steps).length > 0;

  return (
    <section className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-4" data-testid="analysis-panel">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <BrainCircuit className="w-4 h-4 text-emerald-400" />
          <h3 className="text-sm font-bold text-slate-100">{isAr ? 'تحليل الوكلاء' : 'Agent analysis'}</h3>
          {a && (
            <span
              data-testid="analysis-mode"
              className={`text-[10px] font-bold px-2 py-0.5 rounded-md border ${
                a.mode === 'llm' ? 'bg-indigo-950 text-indigo-300 border-indigo-800' : 'bg-slate-900 text-slate-300 border-slate-700'
              }`}
            >
              {a.mode === 'llm' ? (isAr ? 'نموذج لغوي + تحقق' : 'LLM + verifier') : isAr ? 'أساس حتمي' : 'Deterministic baseline'}
            </span>
          )}
          {a?.policyVersion && <span className="text-[10px] text-slate-500 font-mono">{a.policyVersion}</span>}
        </div>
        {canAnalyze && ANALYZABLE.has(claim.status) && (
          <button
            data-testid="analyze-button"
            onClick={() => void run()}
            disabled={running}
            className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-60 text-white text-xs font-bold flex items-center gap-1.5"
          >
            {running ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <FileSearch className="w-3.5 h-3.5" />}
            {running ? (isAr ? 'جارٍ التحليل…' : 'Analyzing…') : a ? (isAr ? 'إعادة التحليل' : 'Re-analyze') : isAr ? 'تحليل الحالة' : 'Analyze case'}
          </button>
        )}
      </div>

      {showSteps && (
        <ol className="grid grid-cols-2 sm:grid-cols-4 gap-2" data-testid="analysis-progress">
          {AGENTS.map((ag) => {
            const st = steps[ag.id];
            return (
              <li key={ag.id} className="flex items-center gap-2 text-[11px] bg-slate-900 border border-slate-800 rounded-lg px-2 py-1.5">
                {st === 'COMPLETED' ? (
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                ) : st === 'RUNNING' ? (
                  <Loader2 className="w-3.5 h-3.5 text-amber-300 animate-spin" />
                ) : (
                  <CircleDashed className="w-3.5 h-3.5 text-slate-600" />
                )}
                <span className="font-mono text-slate-500">{ag.id}</span>
                <span className="text-slate-300">{isAr ? ag.ar : ag.en}</span>
              </li>
            );
          })}
        </ol>
      )}

      {error && <div className="text-xs text-rose-300 bg-rose-950/40 border border-rose-900/60 rounded-lg p-2">{error}</div>}

      {a?.fallbackReason && (
        <div className="text-[11px] text-amber-200 bg-amber-950/30 border border-amber-900/50 rounded-lg p-2">{a.fallbackReason}</div>
      )}
      {a && a.injectionFlags > 0 && (
        <div className="flex items-start gap-2 text-[11px] text-amber-200 bg-amber-950/30 border border-amber-900/50 rounded-lg p-2">
          <ShieldAlert className="w-3.5 h-3.5 shrink-0 mt-0.5" />
          {isAr
            ? `رُصد ${a.injectionFlags} مقطع يشبه التعليمات داخل النص السريري. تم تجاهله؛ القرار يعتمد على الأدلة الموثقة وقواعد السياسة فقط.`
            : `${a.injectionFlags} instruction-like passage(s) found in the clinical text and ignored; outcomes rely only on verified evidence and policy rules.`}
        </div>
      )}

      {!a && !running && (
        <p className="text-xs text-slate-400">
          {isAr
            ? 'لم تُحلَّل هذه الحالة بعد. التحليل يستخرج الحقائق من كل مستندات المريض ويربط كل حقيقة بنصها الحرفي.'
            : 'Not analyzed yet. Analysis extracts facts from every document in the record and ties each fact to its verbatim text.'}
        </p>
      )}

      {a && claim.evidenceItems.length > 0 && (
        <div className="space-y-2" data-testid="analysis-evidence">
          {claim.evidenceItems.map((e) => (
            <div key={e.id} className="bg-slate-900 border border-slate-800 rounded-lg p-3 space-y-2">
              <div className="flex flex-wrap items-center gap-2">
                <span className={`text-[10px] font-bold px-2 py-0.5 rounded-md border ${STATUS_STYLE[e.status] ?? ''}`}>{e.status}</span>
                <span className="text-xs font-semibold text-slate-200">{isAr ? e.requirementAr : e.requirement}</span>
              </div>
              {e.matchedFact && <p className="text-[11px] text-slate-400">{e.matchedFact}</p>}
              {e.cdiQuestion && (
                <div className="flex items-start gap-2 bg-indigo-950/40 border border-indigo-900/60 rounded-md p-2" data-testid="cdi-question">
                  <HelpCircle className="w-3.5 h-3.5 text-indigo-300 shrink-0 mt-0.5" />
                  <div className="text-[11px] text-indigo-100">
                    <div className="font-bold text-indigo-300 mb-0.5">{isAr ? 'سؤال توثيق للطبيب' : 'Physician documentation query'}</div>
                    {isAr ? e.cdiQuestionAr : e.cdiQuestion}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {a && agentFacts.length > 0 && (
        <div className="space-y-1.5">
          <div className="text-[11px] font-bold text-slate-400">
            {isAr ? `الحقائق الموثقة (${agentFacts.length})` : `Verified facts (${agentFacts.length})`}
          </div>
          <ul className="space-y-1.5" data-testid="analysis-facts">
            {agentFacts.map((f) => (
              <li key={f.id} className="text-[11px] bg-slate-900 border border-slate-800 rounded-md px-2.5 py-1.5">
                <span className="font-semibold text-emerald-300">{LABELS[f.label!]?.[isAr ? 'ar' : 'en'] ?? f.label}</span>
                <span className="text-slate-500"> · {f.docRef} [{f.charStart}–{f.charEnd}]</span>
                <div className="text-slate-300 mt-0.5" dir="auto">“{f.quote}”</div>
              </li>
            ))}
          </ul>
          {a.rejectedQuotes > 0 && (
            <p className="text-[10px] text-slate-500">
              {isAr
                ? `رُفض ${a.rejectedQuotes} اقتباس من النموذج لأنه غير موجود في المستندات.`
                : `${a.rejectedQuotes} model quote(s) rejected because they do not appear in the documents.`}
            </p>
          )}
        </div>
      )}
    </section>
  );
};
