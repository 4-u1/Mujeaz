import React, { useState } from 'react';
import { Language } from '../types';
import { BookOpen, ShieldCheck, Search, FileText, CheckCircle2 } from 'lucide-react';

interface PolicyKnowledgeBaseProps {
  lang: Language;
}

const POLICY_DOCS = [
  {
    id: 'pol-1',
    payer: 'Tawuniya Insurance',
    code: 'TAW-LUMBAR-POL-04',
    titleEn: 'Lumbar Spine MRI Prior Authorization Policy',
    titleAr: 'سياسة الموافقة المسبقة للرنين المغناطيسي للفقرات القطنية',
    rules: [
      {
        ruleEn: 'Requires at least 6 weeks of documented conservative management (Physiotherapy / NSAIDs) prior to Lumbar MRI.',
        ruleAr: 'يتطلب توثيق 6 أسابيع على الأقل من العلاج التحفظي (علاج طبيعي / مسكنات) قبل إجراء الطلب.',
      },
      {
        ruleEn: 'Exemption allowed if neurological deficit (cauda equina, progressive weakness, severe SLR < 30 deg) is documented.',
        ruleAr: 'يُستثنى المريض في حال توثيق أعراض عصبية طارئة أو ضعف حركي متقدم.',
      },
    ],
  },
  {
    id: 'pol-2',
    payer: 'Bupa Arabia',
    code: 'BUP-BIO-L40-02',
    titleEn: 'Specialty Biologic Therapy Coverage Exemption Policy',
    titleAr: 'سياسة استثناءات تغطية العلاجات البيولوجية المتخصصة',
    rules: [
      {
        ruleEn: 'Requires failure of conventional DMARD (Methotrexate) for 12 weeks prior to IL-17 / TNF-alpha inhibitors.',
        ruleAr: 'يتطلب إثبات عدم الاستجابة للعلاج التقليدي بالميثوتركسيت لمدة 12 أسبوعاً.',
      },
      {
        ruleEn: 'Step therapy exemption applies if patient has documented severe adverse drug reaction / allergy to TNF-alpha inhibitor.',
        ruleAr: 'يستثنى المريض من العلاج المتدرج في حال ثبوت تفاعل تحسسي حاد أو موانع استعمال موثقة في السجل.',
      },
    ],
  },
  {
    id: 'pol-3',
    payer: 'Medgulf Insurance',
    code: 'MED-CARD-01',
    titleEn: 'Coronary Angioplasty & Stent Coverage Rules',
    titleAr: 'شروط تغطية قسطرة الشرايين التاجية والدعامات',
    rules: [
      {
        ruleEn: 'Stenosis > 70% verified via QCA angiogram report is eligible for immediate approval.',
        ruleAr: 'تضيق أكبر من 70% مثبت بتقرير القسطرة الكمي يحصل على الموافقة الفورية.',
      },
      {
        ruleEn: 'Ischemia must be confirmed via Stress Test / Echo or FFR < 0.80.',
        ruleAr: 'يجب إثبات وجود نقص التروية عبر اختبار الإجهاد أو قياس الضغط الفسيولوجي FFR.',
      },
    ],
  },
];

export const PolicyKnowledgeBase: React.FC<PolicyKnowledgeBaseProps> = ({ lang }) => {
  const isAr = lang === 'ar';
  const [search, setSearch] = useState('');

  const filteredDocs = POLICY_DOCS.filter(
    (p) =>
      p.titleEn.toLowerCase().includes(search.toLowerCase()) ||
      p.titleAr.toLowerCase().includes(search.toLowerCase()) ||
      p.payer.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6 pb-12">
      
      {/* Header */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl text-white">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-950 border border-blue-800 flex items-center justify-center text-blue-400">
              <BookOpen className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-xl font-bold">
                {isAr ? 'قاعدة معرفة السياسات والتغطية (RAG Knowledge Base)' : 'Payer Coverage Policy RAG Engine'}
              </h1>
              <p className="text-xs text-slate-400">
                {isAr ? 'فصل واضح بين التفسير بالذكاء الاصطناعي والقواعد المحددة القابلة للاختبار (Deterministic Rules)' : 'RAG policy knowledge retrieval and deterministic rules engine for Saudi Payers'}
              </p>
            </div>
          </div>

          <div className="w-full sm:w-64 relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder={isAr ? 'بحث في السياسات...' : 'Search policies...'}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-3 py-1.5 text-xs text-white focus:outline-none focus:border-emerald-500"
            />
          </div>
        </div>
      </div>

      {/* Policy Cards */}
      <div className="space-y-4">
        {filteredDocs.map((doc) => (
          <div key={doc.id} className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl text-white space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div>
                <span className="px-2.5 py-0.5 rounded bg-emerald-950 border border-emerald-800 text-emerald-400 text-xs font-bold">
                  {doc.payer}
                </span>
                <h2 className="text-base font-bold text-white mt-1">
                  {isAr ? doc.titleAr : doc.titleEn}
                </h2>
              </div>
              <span className="font-mono text-xs text-slate-400 bg-slate-950 px-2.5 py-1 rounded border border-slate-800">
                {doc.code}
              </span>
            </div>

            <div className="space-y-2">
              <div className="text-xs font-bold text-slate-300">{isAr ? 'القواعد المحددة الحاكمة (Deterministic Rules):' : 'Governing Rules:'}</div>
              <div className="space-y-2">
                {doc.rules.map((r, i) => (
                  <div key={i} className="bg-slate-950 p-3 rounded-xl border border-slate-800 text-xs flex items-start gap-2.5 text-slate-300">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                    <span>{isAr ? r.ruleAr : r.ruleEn}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>

    </div>
  );
};
