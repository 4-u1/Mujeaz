import React from 'react';
import { Language } from '../types';
import { ShieldCheck, Lock, Activity, HeartHandshake } from 'lucide-react';

interface FooterProps {
  lang: Language;
}

export const Footer: React.FC<FooterProps> = ({ lang }) => {
  const isAr = lang === 'ar';

  return (
    <footer className="bg-slate-950 border-t border-slate-800 text-slate-400 py-10 mt-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-8">
        
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
          <div className="space-y-2 max-w-xl">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-slate-900 border border-emerald-500/40 shadow-md flex items-center justify-center shrink-0 overflow-hidden">
                <img 
                  src="/logo_full.png" 
                  alt="Mujeaz Logo" 
                  className="h-full w-full object-cover"
                  referrerPolicy="no-referrer"
                />
              </div>
              <span className="font-extrabold text-white text-lg tracking-tight">
                {isAr ? 'مُجاز | Mujeaz' : 'Mujeaz Command Center'}
              </span>
            </div>
            
            <p className="text-xs text-slate-400 leading-relaxed">
              {isAr
                ? 'مُجاز: نمنع الرفض. نحمي الإيراد. نستعيد المفقود. منصة الذكاء الاصطناعي لضمان الإيرادات والموافقات الطبية للقطاع الصحي في المملكة العربية السعودية.'
                : 'Mujeaz: Prevent the denial. Protect the revenue. Recover the lost. AI-Powered Healthcare Revenue Assurance & Authorization Command Center.'}
            </p>
          </div>

          {/* Badges */}
          <div className="flex flex-wrap items-center gap-3 text-xs">
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-300">
              <Lock className="w-3.5 h-3.5 text-emerald-400" />
              <span>{isAr ? 'نموذج أولي — بيانات اصطناعية فقط' : 'Prototype — synthetic data only'}</span>
            </div>
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-300">
              <Activity className="w-3.5 h-3.5 text-cyan-400" />
              <span>{isAr ? 'مصمم لمعايير FHIR R4 ونفيس' : 'Designed for FHIR R4 / NPHIES'}</span>
            </div>
          </div>
        </div>

        <div className="border-t border-slate-900 pt-6 flex flex-col sm:flex-row items-center justify-between text-[11px] text-slate-500 gap-4">
          <div>
            © {new Date().getFullYear()} Mujeaz · {isAr ? 'تصميم وتطوير يزيد حمد الحارثي' : 'Designed & built by Yazeed Hamad Alharthi'}
          </div>
          <div className="flex items-center gap-4">
            <span>{isAr ? 'مبدأ: لا دليل = لا مطالبة' : 'Principle: "No Evidence, No Claim"'}</span>
            <span>•</span>
            <span>{isAr ? 'مركز قيادة الضمان الصحي' : 'Healthcare Revenue Assurance'}</span>
          </div>
        </div>

      </div>
    </footer>
  );
};
