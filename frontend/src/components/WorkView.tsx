import React, { useCallback, useEffect, useState } from 'react';
import { ClipboardList, Inbox } from 'lucide-react';
import { api, InboxQuery, PhysicianAnswer, QueueItem } from '../api/client';
import { Language } from '../types';
import { TherapyAnswerForm } from './TherapyAnswerForm';

interface Props {
  lang: Language;
  roles: string[];
  onSelectCase: (caseId: string) => void;
  onCaseChanged: (caseId: string) => Promise<void>;
}

const SAR = (n: number, ar: boolean) =>
  new Intl.NumberFormat(ar ? 'ar-SA' : 'en-US', { style: 'currency', currency: 'SAR', maximumFractionDigits: 0 }).format(n);

export const WorkView: React.FC<Props> = ({ lang, roles, onSelectCase, onCaseChanged }) => {
  const isAr = lang === 'ar';
  const isPhysician = roles.includes('physician');
  const [queue, setQueue] = useState<{ items: QueueItem[]; formula: string; formulaAr: string } | null>(null);
  const [inbox, setInbox] = useState<InboxQuery[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      if (isPhysician) setInbox((await api.queries('OPEN')).items);
      else setQueue(await api.queue());
    } catch (e) {
      setError((e as Error).message);
    }
  }, [isPhysician]);

  useEffect(() => {
    void load();
  }, [load]);

  const answer = async (q: InboxQuery, a: PhysicianAnswer) => {
    setBusy(q.id);
    setError(null);
    try {
      const r = await api.answerQuery(q.id, a, lang);
      setMessage(
        isAr
          ? `حُفظ الملحق ${r.document}. أُعيد التحليل: الجاهزية ${r.analysis.readiness} — ${r.analysis.status}`
          : `Addendum ${r.document} saved. Re-analysed: readiness ${r.analysis.readiness} — ${r.analysis.status}`,
      );
      await onCaseChanged(q.caseId);
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  };

  const decline = async (q: InboxQuery) => {
    setBusy(q.id);
    try {
      await api.declineQuery(q.id, isAr ? 'لم يُقدَّم علاج تحفظي' : 'No conservative therapy was given');
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="space-y-4">
      {message && <div className="text-xs text-emerald-200 bg-emerald-950/40 border border-emerald-800/60 rounded-lg p-2" data-testid="work-message">{message}</div>}
      {error && <div className="text-xs text-rose-300 bg-rose-950/40 border border-rose-900/60 rounded-lg p-2">{error}</div>}

      {isPhysician ? (
        <section className="space-y-3" data-testid="physician-inbox">
          <div className="flex items-center gap-2">
            <Inbox className="w-4 h-4 text-indigo-300" />
            <h2 className="text-sm font-bold">{isAr ? `أسئلة التوثيق المفتوحة (${inbox.length})` : `Open documentation queries (${inbox.length})`}</h2>
          </div>
          {inbox.length === 0 && <p className="text-xs text-slate-400">{isAr ? 'لا توجد أسئلة مفتوحة.' : 'No open queries.'}</p>}
          {inbox.map((q) => (
            <article key={q.id} className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3" data-testid={`query-${q.caseNumber}`}>
              <div className="flex flex-wrap items-center gap-2 text-xs">
                <span className="font-bold text-slate-100">{q.caseNumber}</span>
                <span className="text-slate-400">{q.requestedService}</span>
                <span className="text-slate-500">{isAr ? `تاريخ الطلب ${q.requestedOn}` : `requested ${q.requestedOn}`}</span>
                {q.dueOn && <span className="text-amber-300">{isAr ? `مطلوب قبل ${q.dueOn}` : `due ${q.dueOn}`}</span>}
              </div>
              <p className="text-xs text-indigo-100">{isAr ? q.questionAr : q.question}</p>
              <TherapyAnswerForm lang={lang} requestedOn={q.requestedOn} busy={busy === q.id} testId={`answer-form-${q.caseNumber}`}
                submitLabel={isAr ? 'توقيع الملحق وإرساله' : 'Sign and submit addendum'} onSubmit={(a) => void answer(q, a)} />
              <button onClick={() => void decline(q)} disabled={busy === q.id} className="text-[11px] text-slate-400 hover:text-rose-300 underline">
                {isAr ? 'لم يُقدَّم علاج — اعتذار عن السؤال' : 'No therapy was given — decline'}
              </button>
            </article>
          ))}
        </section>
      ) : (
        <section className="space-y-3" data-testid="work-queue">
          <div className="flex items-center gap-2">
            <ClipboardList className="w-4 h-4 text-emerald-300" />
            <h2 className="text-sm font-bold">{isAr ? 'قائمة العمل حسب الأولوية' : 'Work queue by priority'}</h2>
          </div>
          {queue && <p className="text-[10px] text-slate-500">{isAr ? queue.formulaAr : queue.formula}</p>}
          <div className="overflow-x-auto">
            <table className="w-full text-[11px]">
              <thead className="text-slate-500">
                <tr>
                  <th className="text-start py-1 font-medium">{isAr ? 'الحالة' : 'Case'}</th>
                  <th className="text-start font-medium">{isAr ? 'الجهة' : 'Payer'}</th>
                  <th className="text-start font-medium">{isAr ? 'الوضع' : 'Status'}</th>
                  <th className="text-end font-medium">{isAr ? 'المبلغ' : 'Amount'}</th>
                  <th className="text-end font-medium">{isAr ? 'الأيام' : 'Days'}</th>
                  <th className="text-end font-medium">{isAr ? 'الأولوية' : 'Priority'}</th>
                  <th className="text-start font-medium ps-3">{isAr ? 'الإجراء التالي' : 'Next action'}</th>
                </tr>
              </thead>
              <tbody>
                {queue?.items.map((i) => (
                  <tr key={i.id} className="border-t border-slate-800 hover:bg-slate-900 cursor-pointer" onClick={() => onSelectCase(i.id)}>
                    <td className="py-1.5 font-semibold text-slate-100">{i.caseNumber}</td>
                    <td className="text-slate-400">{i.payerCode}</td>
                    <td className="text-slate-300">{i.status}</td>
                    <td className="text-end text-slate-200" title={i.amountBasis}>{SAR(i.amount, isAr)}</td>
                    <td className="text-end text-slate-400">{i.daysSinceRequest}</td>
                    <td className="text-end font-bold text-emerald-300">{i.priority.toLocaleString()}</td>
                    <td className="ps-3 text-slate-300">{isAr ? i.nextActionAr : i.nextAction}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
};
