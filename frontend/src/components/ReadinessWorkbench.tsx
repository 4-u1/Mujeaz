import React, { useEffect, useState } from 'react';
import { Calculator, FileText, FlaskConical, Send } from 'lucide-react';
import { api, CaseDocuments, PhysicianAnswer, WhatIfResult } from '../api/client';
import { ClaimDigitalTwin, Language } from '../types';
import { TherapyAnswerForm } from './TherapyAnswerForm';

/** Splits text into plain and highlighted runs using UTF-16 offsets (JavaScript string indices). */
export function highlightRuns(text: string, ranges: { start: number; end: number }[]): { text: string; hit: boolean }[] {
  const sorted = [...ranges].filter((r) => r.end > r.start).sort((a, b) => a.start - b.start);
  const out: { text: string; hit: boolean }[] = [];
  let pos = 0;
  for (const r of sorted) {
    const s = Math.max(r.start, pos);
    if (s > pos) out.push({ text: text.slice(pos, s), hit: false });
    if (r.end > s) out.push({ text: text.slice(s, r.end), hit: true });
    pos = Math.max(pos, r.end);
  }
  if (pos < text.length) out.push({ text: text.slice(pos), hit: false });
  return out;
}

interface Props {
  claim: ClaimDigitalTwin;
  lang: Language;
  canApproveSubmission: boolean;
  onChanged: (caseId: string) => Promise<void>;
}

export const ReadinessWorkbench: React.FC<Props> = ({ claim, lang, canApproveSubmission, onChanged }) => {
  const isAr = lang === 'ar';
  const ex = claim.readinessExplanation;
  const [sim, setSim] = useState<WhatIfResult | null>(null);
  const [docs, setDocs] = useState<CaseDocuments | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setSim(null);
    setDocs(null);
    if (claim.analysis) api.documents(claim.id).then(setDocs).catch(() => setDocs(null));
  }, [claim.id, claim.analysis?.id]);

  const simulate = async (answer: PhysicianAnswer) => {
    setBusy(true);
    setError(null);
    try {
      setSim(await api.whatIf(claim.id, answer, lang));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const approve = async () => {
    setBusy(true);
    setError(null);
    try {
      await api.transition(claim.id, 'SUBMITTED', 'Reviewed after agent analysis');
      await onChanged(claim.id);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  if (!claim.analysis || !ex) return null;
  const queries = claim.documentationQueries ?? [];
  const fixable = claim.status === 'RISK_DETECTED' || claim.status === 'EVIDENCE_SEARCHING';

  return (
    <div className="space-y-4">
      {claim.status === 'DECISION_READY' && canApproveSubmission && (
        <div className="flex flex-wrap items-center justify-between gap-2 bg-emerald-950/40 border border-emerald-800/60 rounded-xl p-3">
          <span className="text-xs text-emerald-200">
            {isAr ? 'جاهز للقرار. الإرسال يحتاج موافقة بشرية.' : 'Decision ready. Submission needs a human approval.'}
          </span>
          <button data-testid="approve-submission" disabled={busy} onClick={() => void approve()}
            className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold flex items-center gap-1.5">
            <Send className="w-3.5 h-3.5" /> {isAr ? 'اعتماد الإرسال' : 'Approve submission'}
          </button>
        </div>
      )}

      {/* Score explanation */}
      <section className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-3" data-testid="readiness-explanation">
        <div className="flex items-center gap-2">
          <Calculator className="w-4 h-4 text-emerald-400" />
          <h3 className="text-sm font-bold text-slate-100">{isAr ? 'لماذا هذه الدرجة؟' : 'Why this score?'}</h3>
          <span className="text-[10px] text-slate-500">
            {isAr ? `المجموع الموزون ${ex.weightedTotal}` : `weighted total ${ex.weightedTotal}`}
            {ex.gateReduction > 0 && (isAr ? ` − سقف ${ex.gateReduction}` : ` − cap ${ex.gateReduction}`)} = {ex.overall}
          </span>
        </div>
        <table className="w-full text-[11px]">
          <thead className="text-slate-500">
            <tr>
              <th className="text-start font-medium py-1">{isAr ? 'المكوّن' : 'Component'}</th>
              <th className="text-end font-medium">{isAr ? 'الدرجة' : 'Score'}</th>
              <th className="text-end font-medium">{isAr ? 'الوزن' : 'Weight'}</th>
              <th className="text-end font-medium">{isAr ? 'المساهمة' : 'Points'}</th>
              <th className="text-start font-medium ps-3">{isAr ? 'السبب' : 'Why points were lost'}</th>
            </tr>
          </thead>
          <tbody>
            {ex.components.map((c) => (
              <tr key={c.component} className="border-t border-slate-800 align-top">
                <td className="py-1.5 text-slate-200">{isAr ? c.labelAr : c.label}</td>
                <td className="text-end text-slate-300">{c.score}</td>
                <td className="text-end text-slate-500">{Math.round(c.weight * 100)}%</td>
                <td className="text-end text-slate-200">{c.contribution.toFixed(1)}</td>
                <td className="ps-3 text-slate-400">{(isAr ? c.causesAr : c.causes).join(' · ') || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {ex.gate && <p className="text-[11px] text-rose-300">{isAr ? ex.gateTextAr : ex.gateText}</p>}
      </section>

      {/* Documentation queries for this case */}
      {queries.length > 0 && (
        <section className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2" data-testid="case-queries">
          <h3 className="text-sm font-bold text-slate-100">{isAr ? 'أسئلة التوثيق للطبيب' : 'Physician documentation queries'}</h3>
          {queries.map((q) => (
            <div key={q.id} className="text-[11px] flex flex-wrap gap-2 items-center">
              <span className="px-2 py-0.5 rounded-md border border-slate-700 text-slate-300 font-bold">{q.status}</span>
              <span className="text-slate-400">{q.requirementId}</span>
              {q.addendumRef && <span className="text-emerald-300">→ {q.addendumRef}</span>}
              {q.declineReason && <span className="text-rose-300">“{q.declineReason}”</span>}
            </div>
          ))}
        </section>
      )}

      {/* What-if */}
      {fixable && (
        <section className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-3" data-testid="what-if">
          <div className="flex items-center gap-2">
            <FlaskConical className="w-4 h-4 text-indigo-300" />
            <h3 className="text-sm font-bold text-slate-100">{isAr ? 'ماذا لو وُثّق العلاج؟ (محاكاة)' : 'What if the therapy were documented? (simulation)'}</h3>
          </div>
          <TherapyAnswerForm lang={lang} requestedOn={claim.createdDate} busy={busy} testId="what-if-form"
            submitLabel={isAr ? 'احسب الأثر' : 'Simulate'} onSubmit={(a) => void simulate(a)} />
          {sim && (
            <div className="text-xs space-y-1" data-testid="what-if-result">
              <div className="text-slate-200">
                {isAr ? 'الجاهزية' : 'Readiness'}: {sim.before.readiness} → <b>{sim.after.readiness}</b> ·{' '}
                {isAr ? 'الحالة' : 'Status'}: {sim.before.status} → <b>{sim.after.status}</b>
              </div>
              {!sim.addendumAccepted && (
                <div className="text-amber-300">{isAr ? 'هذه الجهة لا تقبل الملاحق بعد الطلب.' : 'This payer does not accept post-request addenda.'}</div>
              )}
              <div className="text-[10px] text-slate-500">{isAr ? 'محاكاة فقط — لم يُحفظ شيء.' : 'Simulation only — nothing was saved.'}</div>
            </div>
          )}
        </section>
      )}

      {error && <div className="text-xs text-rose-300 bg-rose-950/40 border border-rose-900/60 rounded-lg p-2">{error}</div>}

      {/* Document viewer */}
      {docs && (
        <section className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-3" data-testid="document-viewer">
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-slate-300" />
            <h3 className="text-sm font-bold text-slate-100">{isAr ? 'المستندات والأدلة المظللة' : 'Documents with highlighted evidence'}</h3>
          </div>
          {docs.documents.map((d) => {
            const ranges = docs.facts.filter((f) => f.docRef === d.docRef).map((f) => ({ start: f.utf16Start, end: f.utf16End }));
            return (
              <div key={d.docRef} className="space-y-1">
                <div className="text-[10px] text-slate-500 flex gap-2">
                  <span className="font-mono">{d.docRef}</span>
                  <span>{d.docType}</span>
                  <span>{d.authoredOn}</span>
                  {d.postRequestAddendum && (
                    <span className="text-amber-300 font-bold">{isAr ? 'ملحق بعد الطلب' : 'post-request addendum'}</span>
                  )}
                </div>
                <p dir="auto" className="text-[11px] leading-relaxed text-slate-300 whitespace-pre-wrap bg-slate-900 border border-slate-800 rounded-md p-2">
                  {highlightRuns(d.content, ranges).map((r, i) =>
                    r.hit ? <mark key={i} className="bg-emerald-800/60 text-emerald-50 rounded px-0.5">{r.text}</mark> : <span key={i}>{r.text}</span>,
                  )}
                </p>
              </div>
            );
          })}
        </section>
      )}
    </div>
  );
};
