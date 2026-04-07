'use client';
import React, { useState } from 'react';
import { useStore } from '@/lib/store';
import { processSpintax } from '@/lib/threads-api';
import { FileText, Plus, Trash2, Eye, Copy, Shuffle, X } from 'lucide-react';
import type { ContentTemplate } from '@/lib/types';

export default function Templates() {
  const { templates, addTemplate, removeTemplate } = useStore();
  const [showCreate, setShowCreate] = useState(false);
  const [name, setName] = useState('');
  const [category, setCategory] = useState('general');
  const [content, setContent] = useState('');
  const [useSpintax, setUseSpintax] = useState(true);
  const [previewId, setPreviewId] = useState<string | null>(null);
  const [previewText, setPreviewText] = useState('');
  const cats = [
    { id: 'general', label: 'General', color: 'bg-blue-500/15 text-blue-400' },
    { id: 'technology', label: 'Tech', color: 'bg-purple-500/15 text-purple-400' },
    { id: 'crypto', label: 'Crypto', color: 'bg-amber-500/15 text-amber-400' },
    { id: 'lifestyle', label: 'Lifestyle', color: 'bg-pink-500/15 text-pink-400' },
    { id: 'news', label: 'News', color: 'bg-emerald-500/15 text-emerald-400' },
    { id: 'humor', label: 'Humor', color: 'bg-orange-500/15 text-orange-400' },
  ];
  const handleCreate = () => {
    if (!name || !content) return;
    addTemplate({ id: 'tmpl_' + Date.now(), name, category, content, useSpintax, variables: [], usageCount: 0, createdAt: new Date().toISOString() });
    setShowCreate(false); setName(''); setCategory('general'); setContent('');
  };
  const getCat = (id: string) => cats.find(c => c.id === id) || cats[0];
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div><h2 className="text-2xl font-bold">Templates</h2><p className="text-slate-400 text-sm mt-1">Content templates with Spintax support</p></div>
        <button onClick={() => setShowCreate(true)} className="btn-primary flex items-center gap-2"><Plus size={16} />New Template</button>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {templates.length === 0 && <div className="md:col-span-3 glass-card p-12 text-center text-slate-400"><FileText size={48} className="mx-auto mb-4 opacity-30" /><p>No templates. Create one.</p></div>}
        {templates.map(tmpl => {
          const catInfo = getCat(tmpl.category);
          return (
            <div key={tmpl.id} className="glass-card p-5 flex flex-col">
              <div className="flex items-start justify-between mb-3">
                <div><p className="font-semibold text-sm mb-1">{tmpl.name}</p><span className={'px-2 py-0.5 rounded-full text-xs ' + catInfo.color}>{catInfo.label}</span></div>
                {tmpl.useSpintax && <span className="px-2 py-0.5 rounded-full text-xs bg-purple-500/15 text-purple-400"><Shuffle size={10} className="inline mr-0.5" />Spintax</span>}
              </div>
              <div className="flex-1 p-3 rounded-xl mb-3 text-xs font-mono leading-relaxed overflow-hidden" style={{ background: 'rgba(15,23,42,0.8)', maxHeight: '120px' }}>
                <span className="text-slate-400">{previewId === tmpl.id ? previewText : tmpl.content}</span>
              </div>
              <div className="flex items-center gap-2 pt-2 border-t" style={{ borderColor: 'var(--glass-border)' }}>
                <button onClick={() => { setPreviewId(tmpl.id); setPreviewText(processSpintax(tmpl.content)); }} className="text-xs text-slate-400 hover:text-blue-400 flex items-center gap-1"><Eye size={12} />Preview</button>
                <button onClick={() => navigator.clipboard.writeText(tmpl.content)} className="text-xs text-slate-400 hover:text-emerald-400 flex items-center gap-1"><Copy size={12} />Copy</button>
                <button onClick={() => removeTemplate(tmpl.id)} className="text-xs text-slate-400 hover:text-red-400 flex items-center gap-1 ml-auto"><Trash2 size={12} />Delete</button>
              </div>
            </div>
          );
        })}
      </div>
      {showCreate && (
        <div className="modal-overlay" onClick={() => setShowCreate(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-6"><h3 className="text-lg font-semibold">New Template</h3><button onClick={() => setShowCreate(false)} className="text-slate-400 hover:text-white"><X size={20} /></button></div>
            <div className="space-y-4">
              <div><label className="text-sm text-slate-400 mb-1 block">Name *</label><input type="text" placeholder="My template" value={name} onChange={e => setName(e.target.value)} className="glass-input" /></div>
              <div><label className="text-sm text-slate-400 mb-1 block">Category</label><div className="grid grid-cols-3 gap-2">{cats.map(cat => <button key={cat.id} onClick={() => setCategory(cat.id)} className={'p-2 rounded-lg text-xs text-center transition-all ' + (category === cat.id ? 'bg-blue-500/15 border border-blue-500/30' : 'bg-white/5 border border-transparent')}>{cat.label}</button>)}</div></div>
              <div><label className="text-sm text-slate-400 mb-1 block">Content *</label><textarea value={content} onChange={e => setContent(e.target.value)} placeholder="Post template with {variant1|variant2}" className="glass-input resize-none h-36 font-mono text-sm" /></div>
              <div className="flex gap-3 pt-2"><button onClick={() => setShowCreate(false)} className="btn-secondary flex-1">Cancel</button><button onClick={handleCreate} className="btn-primary flex-1">Create</button></div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
