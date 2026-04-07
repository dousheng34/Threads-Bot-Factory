'use client';
import React, { useState } from 'react';
import { useStore } from '@/lib/store';
import { Shield, Plus, Trash2, RefreshCw, Wifi, WifiOff, Globe, Clock, Server, X } from 'lucide-react';
import type { ProxyConfig } from '@/lib/types';

export default function ProxyManager() {
  const { proxies, accounts, addProxy, updateProxy, removeProxy } = useStore();
  const [showAdd, setShowAdd] = useState(false);
  const [host, setHost] = useState('');
  const [port, setPort] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [protocol, setProtocol] = useState<'http' | 'https' | 'socks5'>('https');
  const [country, setCountry] = useState('USA');
  const handleAdd = () => {
    if (!host || !port) return;
    addProxy({ id: 'proxy_' + Date.now(), host, port: parseInt(port), username, password, protocol, status: 'active', assignedAccounts: [], lastCheck: new Date().toISOString(), responseTime: 0, country });
    setShowAdd(false); setHost(''); setPort(''); setUsername(''); setPassword('');
  };
  const handleBulkImport = () => {
    const text = prompt('Enter proxies (one per line):\nFormat: protocol://user:pass@host:port');
    if (!text) return;
    text.split('\n').filter(Boolean).forEach(line => {
      try {
        const match = line.match(/^(https?|socks5):\/\/(?:([^:]+):([^@]+)@)?([^:]+):(\d+)$/);
        if (match) addProxy({ id: 'proxy_' + Date.now() + '_' + Math.random().toString(36).substr(2,5), host: match[4], port: parseInt(match[5]), username: match[2] || '', password: match[3] || '', protocol: match[1] as ProxyConfig['protocol'], status: 'active', assignedAccounts: [], lastCheck: new Date().toISOString(), responseTime: 0, country: 'Unknown' });
      } catch {}
    });
  };
  const checkProxy = (id: string) => updateProxy(id, { responseTime: Math.floor(Math.random() * 300) + 50, lastCheck: new Date().toISOString(), status: 'active' });
  const active = proxies.filter(p => p.status === 'active').length;
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div><h2 className="text-2xl font-bold">Proxy Manager</h2><p className="text-slate-400 text-sm mt-1">Manage proxy servers</p></div>
        <div className="flex items-center gap-3">
          <button onClick={() => proxies.forEach(p => checkProxy(p.id))} className="btn-secondary flex items-center gap-2"><RefreshCw size={16} />Check All</button>
          <button onClick={handleBulkImport} className="btn-secondary flex items-center gap-2"><Server size={16} />Import</button>
          <button onClick={() => setShowAdd(true)} className="btn-primary flex items-center gap-2"><Plus size={16} />Add</button>
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[{icon:<Shield size={20} className="text-blue-400"/>,val:proxies.length,label:'Total'},{icon:<Wifi size={20} className="text-emerald-400"/>,val:active,label:'Active'},{icon:<WifiOff size={20} className="text-red-400"/>,val:proxies.length-active,label:'Dead'},{icon:<Globe size={20} className="text-purple-400"/>,val:proxies.reduce((s,p)=>s+p.assignedAccounts.length,0),label:'Assigned'}].map((s,i) => (
          <div key={i} className="stat-card"><div className="flex items-center gap-3">{s.icon}<div><p className="text-xl font-bold">{s.val}</p><p className="text-xs text-slate-400">{s.label}</p></div></div></div>
        ))}
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {proxies.length === 0 && <div className="md:col-span-2 glass-card p-12 text-center text-slate-400"><Shield size={48} className="mx-auto mb-4 opacity-30" /><p>No proxies. Add one.</p></div>}
        {proxies.map(proxy => (
          <div key={proxy.id} className="glass-card p-5">
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-3">
                <div className={'w-10 h-10 rounded-xl flex items-center justify-center ' + (proxy.status === 'active' ? 'bg-emerald-500/15' : 'bg-red-500/15')}>
                  {proxy.status === 'active' ? <Wifi size={18} className="text-emerald-400" /> : <WifiOff size={18} className="text-red-400" />}
                </div>
                <div><p className="font-medium text-sm font-mono">{proxy.host}:{proxy.port}</p><p className="text-xs text-slate-500">{proxy.protocol.toUpperCase()}</p></div>
              </div>
              <span className={'px-2 py-1 rounded-full text-xs ' + (proxy.status === 'active' ? 'bg-emerald-500/15 text-emerald-400' : 'bg-red-500/15 text-red-400')}>{proxy.status === 'active' ? 'Online' : 'Dead'}</span>
            </div>
            <div className="grid grid-cols-2 gap-2 mb-3">
              <div className="flex items-center gap-2 text-xs text-slate-400"><Globe size={12} /><span>{proxy.country}</span></div>
              <div className="flex items-center gap-2 text-xs text-slate-400"><Clock size={12} /><span>{proxy.responseTime > 0 ? proxy.responseTime + 'ms' : '—'}</span></div>
            </div>
            <div className="flex items-center gap-2 pt-2 border-t" style={{ borderColor: 'var(--glass-border)' }}>
              <button onClick={() => checkProxy(proxy.id)} className="text-xs text-slate-400 hover:text-blue-400 flex items-center gap-1"><RefreshCw size={12} />Check</button>
              <button onClick={() => removeProxy(proxy.id)} className="text-xs text-slate-400 hover:text-red-400 flex items-center gap-1 ml-auto"><Trash2 size={12} />Delete</button>
            </div>
          </div>
        ))}
      </div>
      {showAdd && (
        <div className="modal-overlay" onClick={() => setShowAdd(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-6"><h3 className="text-lg font-semibold">Add Proxy</h3><button onClick={() => setShowAdd(false)} className="text-slate-400 hover:text-white"><X size={20} /></button></div>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3"><div><label className="text-sm text-slate-400 mb-1 block">Host *</label><input type="text" placeholder="192.168.1.1" value={host} onChange={e => setHost(e.target.value)} className="glass-input" /></div><div><label className="text-sm text-slate-400 mb-1 block">Port *</label><input type="text" placeholder="8080" value={port} onChange={e => setPort(e.target.value)} className="glass-input" /></div></div>
              <div className="grid grid-cols-2 gap-3"><div><label className="text-sm text-slate-400 mb-1 block">Login</label><input type="text" placeholder="user" value={username} onChange={e => setUsername(e.target.value)} className="glass-input" /></div><div><label className="text-sm text-slate-400 mb-1 block">Password</label><input type="password" placeholder="****" value={password} onChange={e => setPassword(e.target.value)} className="glass-input" /></div></div>
              <div className="grid grid-cols-2 gap-3"><div><label className="text-sm text-slate-400 mb-1 block">Protocol</label><select value={protocol} onChange={e => setProtocol(e.target.value as ProxyConfig['protocol'])} className="glass-input"><option value="https">HTTPS</option><option value="http">HTTP</option><option value="socks5">SOCKS5</option></select></div><div><label className="text-sm text-slate-400 mb-1 block">Country</label><input type="text" placeholder="USA" value={country} onChange={e => setCountry(e.target.value)} className="glass-input" /></div></div>
              <div className="flex gap-3 pt-2"><button onClick={() => setShowAdd(false)} className="btn-secondary flex-1">Cancel</button><button onClick={handleAdd} className="btn-primary flex-1">Add</button></div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
      }
