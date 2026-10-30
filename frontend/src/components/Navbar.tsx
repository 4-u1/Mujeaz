import React from 'react';
import { Language } from '../types';
import { 
  ShieldCheck, 
  Activity, 
  Sparkles, 
  FileSearch, 
  RotateCcw, 
  BookOpen, 
  Globe, 
  Layers
} from 'lucide-react';

interface NavbarProps {
  lang: Language;
  setLang: (l: Language) => void;
  activeTab: 'dashboard' | 'walkthrough' | 'digitalTwin' | 'sandbox' | 'recovery' | 'policy';
  setActiveTab: (tab: 'dashboard' | 'walkthrough' | 'digitalTwin' | 'sandbox' | 'recovery' | 'policy') => void;
  selectedCaseId: string;
}

export const Navbar: React.FC<NavbarProps> = ({
  lang,
  setLang,
  activeTab,
  setActiveTab,
}) => {
  const isAr = lang === 'ar';

  return (
    <header className="sticky top-0 z-50 bg-slate-900 border-b border-slate-800 text-white shadow-xl">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          
          {/* Logo & Brand */}
          <div className="flex items-center gap-3 cursor-pointer" onClick={() => setActiveTab('dashboard')}>
            <div className="h-10 w-10 sm:h-11 sm:w-11 rounded-xl bg-slate-950 border border-blue-500/40 shadow-lg shadow-blue-950/50 flex items-center justify-center shrink-0 overflow-hidden ring-1 ring-cyan-500/20">
              <img 
                src="/logo_full.png" 
                alt="Mujeaz Healthcare Tech Logo" 
                className="h-full w-full object-cover"
                referrerPolicy="no-referrer"
              />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-extrabold text-xl tracking-tight bg-gradient-to-r from-white via-slate-100 to-slate-300 bg-clip-text text-transparent">
                  {isAr ? 'مُجاز' : 'Mujeaz'}
                </span>
                <span className="text-xs px-2 py-0.5 rounded-full bg-blue-950/80 text-cyan-300 border border-blue-800/60 font-semibold uppercase tracking-wider">
                  Command Center
                </span>
              </div>
              <p className="text-[11px] text-slate-400 font-medium hidden sm:block">
                {isAr ? 'منصة الذكاء الاصطناعي لضمان الإيرادات والموافقات الطبية' : 'AI Healthcare Revenue Assurance & Authorization'}
              </p>
            </div>
          </div>

          {/* Center Navigation Tabs */}
          <nav className="hidden lg:flex items-center gap-1 bg-slate-950/70 p-1 rounded-xl border border-slate-800">
            <button
              onClick={() => setActiveTab('dashboard')}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                activeTab === 'dashboard'
                  ? 'bg-emerald-600 text-white shadow-md shadow-emerald-950'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
              }`}
            >
              <Activity className="w-4 h-4" />
              {isAr ? 'لوحة القيادة' : 'Command Center'}
            </button>

            <button
              onClick={() => setActiveTab('walkthrough')}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                activeTab === 'walkthrough'
                  ? 'bg-emerald-600 text-white shadow-md shadow-emerald-950'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
              }`}
            >
              <Sparkles className="w-4 h-4 text-emerald-400 animate-pulse" />
              {isAr ? 'العرض الحي التفاعلي' : 'Live Walkthrough'}
            </button>

            <button
              onClick={() => setActiveTab('digitalTwin')}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                activeTab === 'digitalTwin'
                  ? 'bg-emerald-600 text-white shadow-md shadow-emerald-950'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
              }`}
            >
              <Layers className="w-4 h-4" />
              {isAr ? 'التوأم الرقمي' : 'Digital Twin'}
            </button>

            <button
              onClick={() => setActiveTab('sandbox')}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                activeTab === 'sandbox'
                  ? 'bg-emerald-600 text-white shadow-md shadow-emerald-950'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
              }`}
            >
              <FileSearch className="w-4 h-4" />
              {isAr ? 'مختبر تحليل الطلبات' : 'AI Order Sandbox'}
            </button>

            <button
              onClick={() => setActiveTab('recovery')}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all relative ${
                activeTab === 'recovery'
                  ? 'bg-emerald-600 text-white shadow-md shadow-emerald-950'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
              }`}
            >
              <RotateCcw className="w-4 h-4 text-amber-400" />
              {isAr ? 'مسار الاسترداد' : 'Recovery Queue'}
              <span className="w-2 h-2 rounded-full bg-amber-400 animate-ping absolute -top-0.5 -right-0.5" />
            </button>

            <button
              onClick={() => setActiveTab('policy')}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                activeTab === 'policy'
                  ? 'bg-emerald-600 text-white shadow-md shadow-emerald-950'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
              }`}
            >
              <BookOpen className="w-4 h-4" />
              {isAr ? 'قواعد السياسات' : 'Policy RAG'}
            </button>
          </nav>

          {/* Right Controls */}
          <div className="flex items-center gap-3">
            
            {/* NPHIES connection status (demo: simulated) */}
            <div className="hidden sm:flex items-center gap-2 px-2.5 py-1 rounded-full bg-slate-950 border border-slate-800 text-xs">
              <span className="w-2 h-2 rounded-full bg-amber-400" />
              <span className="text-slate-300 font-mono text-[11px]" title={isAr ? 'لا يوجد اتصال فعلي بمنصة نفيس؛ كل الاستجابات محاكاة' : 'No live NPHIES connection; all payer responses are simulated'}>
                NPHIES: {isAr ? 'وضع المحاكاة' : 'Simulated'}
              </span>
            </div>

            {/* Language Switcher */}
            <button
              onClick={() => setLang(isAr ? 'en' : 'ar')}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition-colors"
              title="Switch Language / تغيير اللغة"
            >
              <Globe className="w-3.5 h-3.5 text-emerald-400" />
              <span>{isAr ? 'English' : 'العربية'}</span>
            </button>
          </div>
        </div>

        {/* Mobile Navigation Dropdown/Bar */}
        <div className="flex lg:hidden overflow-x-auto py-2 gap-2 border-t border-slate-800 text-xs">
          <button
            onClick={() => setActiveTab('dashboard')}
            className={`whitespace-nowrap px-3 py-1 rounded-md ${activeTab === 'dashboard' ? 'bg-emerald-600 text-white' : 'bg-slate-800 text-slate-300'}`}
          >
            {isAr ? 'لوحة القيادة' : 'Dashboard'}
          </button>
          <button
            onClick={() => setActiveTab('walkthrough')}
            className={`whitespace-nowrap px-3 py-1 rounded-md ${activeTab === 'walkthrough' ? 'bg-emerald-600 text-white' : 'bg-slate-800 text-slate-300'}`}
          >
            {isAr ? 'العرض الحي' : 'Live Walkthrough'}
          </button>
          <button
            onClick={() => setActiveTab('digitalTwin')}
            className={`whitespace-nowrap px-3 py-1 rounded-md ${activeTab === 'digitalTwin' ? 'bg-emerald-600 text-white' : 'bg-slate-800 text-slate-300'}`}
          >
            {isAr ? 'التوأم الرقمي' : 'Digital Twin'}
          </button>
          <button
            onClick={() => setActiveTab('sandbox')}
            className={`whitespace-nowrap px-3 py-1 rounded-md ${activeTab === 'sandbox' ? 'bg-emerald-600 text-white' : 'bg-slate-800 text-slate-300'}`}
          >
            {isAr ? 'مختبر الطلبات' : 'AI Sandbox'}
          </button>
          <button
            onClick={() => setActiveTab('recovery')}
            className={`whitespace-nowrap px-3 py-1 rounded-md ${activeTab === 'recovery' ? 'bg-emerald-600 text-white' : 'bg-slate-800 text-slate-300'}`}
          >
            {isAr ? 'مسار الاسترداد' : 'Recovery Queue'}
          </button>
          <button
            onClick={() => setActiveTab('policy')}
            className={`whitespace-nowrap px-3 py-1 rounded-md ${activeTab === 'policy' ? 'bg-emerald-600 text-white' : 'bg-slate-800 text-slate-300'}`}
          >
            {isAr ? 'قواعد السياسات' : 'Policies'}
          </button>
        </div>

      </div>
    </header>
  );
};
