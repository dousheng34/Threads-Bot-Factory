'use client';
import React, { useState } from 'react';
import { useStore } from '@/lib/store';
import { processSpintax } from '@/lib/threads-api';
import { Send, Clock, Plus, Trash2, Eye, Calendar, CheckCircle2, XCircle, Loader2, Shuffle, X } from 'lucide-react';
import type { ScheduledPost } from '@/lib/types';

export default function PostScheduler() {
  const { accounts, scheduledPosts, addScheduledPost, removeScheduledPost } = useStore();
  const [show, setShow] = useState(false);
  const [postText, setPostText] = useState('');
  const [selectedAccounts, setSelectedAccounts] = useState<string[]>([]);
  const [useSpintax, setUseSpintax] = useState(false);
  const [scheduleDate, setScheduleDate] = useState('');
  const [scheduleTime, setScheduleTime] = useState('');
  const [preview, setPreview] = useState('');
  const active = accounts.filter(a => a.status === 'active' || a.status === 'warming');
  const handleCreate = () => {
    if (!postText || selectedAccounts.length === 0) return;
    const post: ScheduledPost = { id: 'post_' + Date.now(), accountIds: selectedAccounts, content: { text: postText, mediaUrls: [], mediaType: 'text', useSpintax }, scheduledAt: scheduleDate && scheduleTime ? new Date(scheduleDate + 'T' + scheduleTime + ':00').toISOString() : new Date().toISOString(), status: 'pending', results: [] };
    addScheduledPost(post); setShow(false); setPostText(''); setSelectedAccounts([]); setUseSpintax(false); setScheduleDate(''); setScheduleTime(''); setPreview('');
  };
  const toggle = (id: string) => setSelectedAccounts(prev => prev.includes(id) ? prev.filter(a => a !== id) : [...prev, id]);
  const getIcon = (s: string) => { switch(s) { case 'published': return <CheckCircle2 size={16} className="text-emerald-400" />; case 'failed': return <XCircle size={16} className="text-red-400" />; case 'publishing': return <Loader2 size={16} className="text-blue-400 animate-spin" />; default: return <Clock size={16} className="text-amber-400" />; } };
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div><h2 className="text-2xl font-bold">Posting</h2><p className="text-slate-400 text-sm mt-1">Schedule and mass publish</p></div>
        <button onClick={() => setShow(true)} className="btn-primary flex items-center gap-2"><Plus size={16} />New Post</button>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[{l:'Pending',v:scheduledPosts.filter(p=>p.status==='pending').length},{l:'Published',v:scheduledPosts.filter(p=>p.status==='published').length},{l:'Errors',v:scheduledPosts.filter(p=>p.status==='failed').length},{l:'Total',v:scheduledPosts.length}].map((s,i) => (
          <div key={i} className="stat-card"><p className="text-xl font-bold">{s.v}</p><p className="text-xs text-slate-400">{s.l}</p></div>
        ))}
      </div>
      <div className="glass-card overflow-hidden">
        <div className="p-4 border-b" style={{ borderColor: 'var(--glass-border)' }}><h3 className="font-semibold">Post Queue</h3></div>
        {scheduledPosts.length === 0 ? <div className="p-12 text-center text-slate-400"><Send size={48} className="mx-auto mb-4 opacity-30" /><p>Queue empty. Create a post.</p></div> : (
          <div className="divide-y" style={{ borderColor: 'var(--glass-border)' }}>
            {scheduledPosts.map(post => (
              <div key={post.id} className="p-4 hover:bg-white/5 flex items-start gap-4">
                <div className="mt-1">{getIcon(post.status)}</div>
                <div className="flex-1 min-w-0"><p className="text-sm mb-1 line-clamp-2">{post.content.text}</p><div className="flex items-center gap-3 text-xs text-slate-500"><span><Calendar size={12} className="inline mr-1" />{new Date(post.scheduledAt).toLocaleString()}</span><span>{post.accountIds.length} accounts</span>{post.content.useSpintax && <span className="px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-400"><Shuffle size={10} className="inline mr-0.5" />Spintax</span>}</div></div>
                {post.status === 'pending' && <button onClick={() => removeScheduledPost(post.id)} className="p-1.5 rounded-lg text-slate-400 hover:text-red-400 hover:bg-red-500/10"><Trash2 size={14} /></button>}
              </div>
            ))}
          </div>
        )}
      </div>
      {show && (
        <div className="modal-overlay" onClick={() => setShow(false)}>
          <div className="modal-content max-w-2xl" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-6"><h3 className="text-lg font-semibold">New Post</h3><button onClick={() => setShow(false)} className="text-slate-400 hover:text-white"><X size={20} /></button></div>
            <div className="space-y-4">
              <div><div className="flex items-center justify-between mb-1"><label className="text-sm text-slate-400">Post Text</label><span className="text-xs text-slate-500">{postText.length}/500</span></div><textarea value={postText} onChange={e => setPostText(e.target.value)} placeholder="Write your post... For Spintax: {variant1|variant2|variant3}" className="glass-input resize-none h-32" maxLength={500} /></div>
              <div className="flex items-center gap-3"><label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" checked={useSpintax} onChange={e => setUseSpintax(e.target.checked)} className="w-4 h-4 rounded" /><span className="text-sm text-slate-300">Use Spintax</span></label>{useSpintax && <button onClick={() => setPreview(processSpintax(postText))} className="text-xs text-blue-400 hover:text-blue-300"><Eye size={14} className="inline mr-1" />Preview</button>}</div>
              {preview && <div className="p-3 rounded-xl text-sm" style={{ background: 'rgba(0,149,246,0.08)', border: '1px solid rgba(0,149,246,0.15)' }}><p className="text-xs text-blue-400 mb-1">Preview:</p><p className="text-slate-300">{preview}</p></div>}
              <div className="grid grid-cols-2 gap-3"><div><label className="text-sm text-slate-400 mb-1 block">Date</label><input type="date" value={scheduleDate} onChange={e => setScheduleDate(e.target.value)} className="glass-input" /></div><div><label className="text-sm text-slate-400 mb-1 block">Time</label><input type="time" value={scheduleTime} onChange={e => setScheduleTime(e.target.value)} className="glass-input" /></div></div>
              <div><div className="flex items-center justify-between mb-2"><label className="text-sm text-slate-400">Accounts</label><button onClick={() => setSelectedAccounts(selectedAccounts.length === active.length ? [] : active.map(a=>a.id))} className="text-xs text-blue-400">{selectedAccounts.length === active.length ? 'Deselect All' : 'Select All'}</button></div><div className="grid grid-cols-2 gap-2 max-h-40 overflow-y-auto">{active.map(acc => <button key={acc.id} onClick={() => toggle(acc.id)} className={'flex items-center gap-2 p-2 rounded-lg text-sm ' + (selectedAccounts.includes(acc.id) ? 'bg-blue-500/15 border border-blue-500/30' : 'bg-white/5 border border-transparent')}><div className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold" style={{ background: 'var(--gradient-threads)' }}>{acc.username[0].toUpperCase()}</div><span className="truncate">@{acc.username}</span></button>)}</div></div>
              <div className="flex gap-3 pt-2"><button onClick={() => setShow(false)} className="btn-secondary flex-1">Cancel</button><button onClick={handleCreate} disabled={!postText || selectedAccounts.length === 0} className="btn-primary flex-1 disabled:opacity-40 flex items-center justify-center gap-2"><Send size={16} />{scheduleDate ? 'Schedule' : 'Publish'}</button></div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
            }
