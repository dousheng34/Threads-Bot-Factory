'use client';
import React from 'react';
import { useStore } from '@/lib/store';
import type { TabType } from '@/lib/types';
import { LayoutDashboard, Users, Send, Bot, Shield, FileText, Settings, Zap, Activity, Wand2 } from 'lucide-react';

const navItems: { id: TabType; label: string; icon: React.ReactNode; isAI?: boolean }[] = [
  { id: 'dashboard', label: 'Dashboard', icon: <LayoutDashboard size={20} /> },
  { id: 'accounts', label: 'Accounts', icon: <Users size={20} /> },
  { id: 'posting', label: 'Posting', icon: <Send size={20} /> },
  { id: 'automation', label: 'Automation', icon: <Bot size={20} /> },
  { id: 'proxies', label: 'Proxies', icon: <Shield size={20} /> },
  { id: 'templates', label: 'Templates', icon: <FileText size={20} /> },
  { id: 'settings', label: 'Settings', icon: <Settings size={20} /> },
  { id: 'ai-video', label: 'AI Video Analysis', icon: <Wand2 size={20} />, isAI: true },
];

export default function Sidebar() {
  const { activeTab, setActiveTab, accounts, automationTasks } = useStore();
  const activeAccounts = accounts.filter(a => a.status === 'active').length;
  const runningTasks = automationTasks.filter(t => t.status === 'running').length;
  return (
    <aside className="fixed left-0 top-0 bottom-0 w-72 flex flex-col z-30" style={{ background: 'rgba(3,7,18,0.9)', borderRight: '1px solid rgba(51,65,85,0.3)' }}>
      <div className="p-6 flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: 'var(--gradient-threads)' }}><Zap size={22} className="text-white" /></div>
        <div><h1 className="text-lg font-bold threads-gradient-text">ThreadsBot</h1><p className="text-xs text-slate-500">Factory v1.0</p></div>
      </div>
      <div className="mx-4 mb-4 p-3 rounded-xl" style={{ background: 'rgba(16,185,129,0.08)', border: '1px solid rgba(16,185,129,0.15)' }}>
        <div className="flex items-center gap-2 mb-1"><Activity size={14} className="text-emerald-400" /><span className="text-xs font-medium text-emerald-400">System Active</span></div>
        <div className="flex items-center justify-between text-xs text-slate-400"><span>{activeAccounts} accounts online</span><span>{runningTasks} tasks</span></div>
      </div>
      <nav className="flex-1 px-3 space-y-1 overflow-y-auto">
        {navItems.map(item => (
          <button key={item.id} onClick={() => setActiveTab(item.id)} className={'nav-item w-full ' + (activeTab === item.id ? 'active' : '')}
            style={item.isAI && activeTab !== item.id ? { background: 'linear-gradient(135deg,rgba(139,92,246,0.08),rgba(225,48,108,0.08))', border: '1px solid rgba(139,92,246,0.2)' } : {}}>
            <span style={item.isAI ? { color: activeTab === item.id ? 'white' : '#a78bfa' } : {}}>{item.icon}</span>
            <span style={item.isAI && activeTab !== item.id ? { color: '#a78bfa', fontWeight: 600 } : {}}>{item.label}</span>
            {item.id === 'accounts' && <span className="ml-auto text-xs px-2 py-0.5 rounded-full" style={{ background: 'rgba(0,149,246,0.15)', color: '#0095f6' }}>{accounts.length}</span>}
            {item.isAI && <span className="ml-auto text-xs px-2 py-0.5 rounded-full font-bold" style={{ background: 'linear-gradient(135deg,#8b5cf6,#e1306c)', color: 'white', fontSize: '10px' }}>AI</span>}
          </button>
        ))}
      </nav>
      <div className="p-4 border-t" style={{ borderColor: 'rgba(51,65,85,0.3)' }}>
        <div className="flex items-center gap-3 p-2 rounded-xl" style={{ background: 'rgba(15,23,42,0.5)' }}>
          <div className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold" style={{ background: 'var(--gradient-threads)' }}>A</div>
          <div className="flex-1 min-w-0"><p className="text-sm font-medium truncate">Admin</p><p className="text-xs text-slate-500">Pro License</p></div>
        </div>
      </div>
    </aside>
  );
}
