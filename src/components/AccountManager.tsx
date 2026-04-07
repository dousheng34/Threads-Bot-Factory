'use client';
import React, { useState } from 'react';
import { useStore } from '@/lib/store';
import { UserPlus, Trash2, Search, Upload, Eye, EyeOff, Copy, X } from 'lucide-react';
import type { ThreadsAccount } from '@/lib/types';

export default function AccountManager() {
  const { accounts, addAccount, updateAccount, removeAccount, proxies } = useStore();
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('all');
  const [showAdd, setShowAdd] = useState(false);
  const [showTokens, setShowTokens] = useState<Record<string, boolean>>({});
  const [username, setUsername] = useState('');
  const [userId, setUserId] = useState('');
  const [token, setToken] = useState('');
  const [proxy, setProxy] = useState('');
  const filtered = accounts.filter(a => a.username.toLowerCase().includes(search.toLowerCase()) && (filter === 'all' || a.status === filter));
  const handleAdd = () => {
    if (!username || !token) return;
    const acc: ThreadsAccount = { id: 'acc_' + Date.now(), username, threadsUserId: userId || 'id_' + Date.now(), accessToken: token, tokenExpiresAt: new Date(Date.now() + 60*24*60*60*1000).toISOString(), proxyId: proxy || null, status: 'active', avatar: '', followers: 0, following: 0, postsCount: 0, lastActivity: new Date().toISOString(), createdAt: new Date().toISOString(), notes: '', dailyPostLimit: 25, postsToday: 0 };
    addAccount(acc); setShowAdd(false); setUsername(''); setUserId(''); setToken(''); setProxy('');
  };
  const counts = { all: accounts.length, active: accounts.filter(a=>a.status==='active').length, warming: accounts.filter(a=>a.status==='warming').length, banned: accounts.filter(a=>a.status==='banned').length, limited: accounts.filter(a=>a.status==='limited').length };
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div><h2 className="text-2xl font-bold">Accounts</h2><p className="text-slate-400 text-sm mt-1">Manage Threads accounts</p></div>
        <div className="flex items-center gap-3">
          <button onClick={() => { const t = prompt('Accounts (one per line):\nFormat: username:accessToken:userId'); if (!t) return; t.split('\n').filter(Boolean).forEach(l => { const p = l.split(':'); if (p.length >= 2) addAccount({ id: 'acc_' + Date.now() + '_' + Math.random().toString(36).substr(2,5), username: p[0].trim(), threadsUserId: p[2]?.trim() || 'id_' + Date.now(), accessToken: p[1].trim(), tokenExpiresAt: new Date(Date.now()+60*24*60*60*1000).toISOString(), proxyId: null, status: 'active', avatar: '', followers: 0, following: 0, postsCount: 0, lastActivity: new Date().toISOString(), createdAt: new Date().toISOString(), notes: '', dailyPostLimit: 25, postsToday: 0 }); }); }} className="btn-secondary flex items-center gap-2"><Upload size={16} />Import</button>
          <button onClick={() => setShowAdd(true)} className="btn-primary flex items-center gap-2"><UserPlus size={16} />Add</button>
        </div>
      </div>
      <div className="flex items-center gap-4 flex-wrap">
        <div className="relative flex-1 min-w-[240px]"><Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" /><input type="text" placeholder="Search accounts..." value={search} onChange={e => setSearch(e.target.value)} className="glass-input pl-10" /></div>
        <div className="flex items-center gap-2">{Object.entries(counts).map(([s, c]) => <button key={s} onClick={() => setFilter(s)} className={'px-3 py-2 rounded-lg text-xs font-medium ' + (filter === s ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30' : 'bg-white/5 text-slate-400 border border-transparent')}>{s === 'all' ? 'All' : s === 'active' ? 'Active' : s === 'warming' ? 'Warming' : s === 'banned' ? 'Banned' : 'Limited'} ({c})</button>)}</div>
      </div>
      <div className="glass-card overflow-hidden"><div className="overflow-x-auto"><table className="w-full"><thead><tr className="text-left text-xs text-slate-400 border-b" style={{ borderColor: 'var(--glass-border)' }}><th className="p-4 font-medium">Account</th><th className="p-4 font-medium">Status</th><th className="p-4 font-medium">Token</th><th className="p-4 font-medium">Followers</th><th className="p-4 font-medium">Posts</th><th className="p-4 font-medium">Today</th><th className="p-4 font-medium">Actions</th></tr></thead>
        <tbody>{filtered.map(acc => (
          <tr key={acc.id} className="table-row">
            <td className="p-4"><div className="flex items-center gap-3"><div className="w-9 h-9 rounded-full flex items-center justify-center text-xs font-bold" style={{ background: 'var(--gradient-threads)' }}>{acc.username[0].toUpperCase()}</div><div><p className="text-sm font-medium">@{acc.username}</p><p className="text-xs text-slate-500">ID: {acc.threadsUserId}</p></div></div></td>
            <td className="p-4"><select value={acc.status} onChange={e => updateAccount(acc.id, { status: e.target.value as ThreadsAccount['status'] })} className="text-xs rounded-lg px-2 py-1 border-0 outline-none cursor-pointer" style={{ background: 'rgba(15,23,42,0.8)', color: 'var(--text-primary)' }}><option value="active">Active</option><option value="warming">Warming</option><option value="limited">Limited</option><option value="banned">Banned</option><option value="inactive">Inactive</option></select></td>
            <td className="p-4"><div className="flex items-center gap-1"><span className="text-xs text-slate-400 font-mono max-w-[100px] truncate">{showTokens[acc.id] ? acc.accessToken : '••••••••••••'}</span><button onClick={() => setShowTokens(prev => ({...prev, [acc.id]: !prev[acc.id]}))} className="text-slate-500 hover:text-slate-300">{showTokens[acc.id] ? <EyeOff size={12} /> : <Eye size={12} />}</button><button onClick={() => navigator.clipboard.writeText(acc.accessToken)} className="text-slate-500 hover:text-slate-300"><Copy size={12} /></button></div></td>
            <td className="p-4 text-sm">{acc.followers.toLocaleString()}</td>
            <td className="p-4 text-sm">{acc.postsCount}</td>
            <td className="p-4"><div className="flex items-center gap-1"><span className="text-sm font-medium">{acc.postsToday}</span><span className="text-xs text-slate-500">/{acc.dailyPostLimit}</span></div></td>
            <td className="p-4"><button onClick={() => removeAccount(acc.id)} className="p-1.5 rounded-lg text-slate-400 hover:text-red-400 hover:bg-red-500/10"><Trash2 size={14} /></button></td>
          </tr>
        ))}</tbody></table></div>
        {filtered.length === 0 && <div className="p-12 text-center text-slate-400"><UserPlus size={48} className="mx-auto mb-4 opacity-30" /><p>No accounts found</p></div>}
      </div>
      {showAdd && (
        <div className="modal-overlay" onClick={() => setShowAdd(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-6"><h3 className="text-lg font-semibold">Add Account</h3><button onClick={() => setShowAdd(false)} className="text-slate-400 hover:text-white"><X size={20} /></button></div>
            <div className="space-y-4">
              <div><label className="text-sm text-slate-400 mb-1 block">Username *</label><input type="text" placeholder="username (no @)" value={username} onChange={e => setUsername(e.target.value)} className="glass-input" /></div>
              <div><label className="text-sm text-slate-400 mb-1 block">Threads User ID</label><input type="text" placeholder="Numeric user ID" value={userId} onChange={e => setUserId(e.target.value)} className="glass-input" /></div>
              <div><label className="text-sm text-slate-400 mb-1 block">Access Token *</label><input type="text" placeholder="Long-lived access token" value={token} onChange={e => setToken(e.target.value)} className="glass-input" /></div>
              <div><label className="text-sm text-slate-400 mb-1 block">Proxy</label><select value={proxy} onChange={e => setProxy(e.target.value)} className="glass-input"><option value="">No proxy</option>{proxies.filter(p=>p.status==='active').map(p => <option key={p.id} value={p.id}>{p.country} — {p.host}:{p.port}</option>)}</select></div>
              <div className="flex gap-3 pt-2"><button onClick={() => setShowAdd(false)} className="btn-secondary flex-1">Cancel</button><button onClick={handleAdd} className="btn-primary flex-1">Add</button></div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
    }
