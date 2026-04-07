'use client';
import React from 'react';
import { useStore } from '@/lib/store';
import { Key, Clock, Shield, RefreshCw, Trash2, AlertCircle } from 'lucide-react';

export default function SettingsPanel() {
  const { settings, updateSettings } = useStore();
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">Settings</h2>
        <p className="text-slate-400 text-sm mt-1">Bot factory configuration</p>
      </div>
      <div className="glass-card p-6">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2"><Key size={18} className="text-blue-400" />Threads API</h3>
        <div className="space-y-4">
          <div>
            <label className="text-sm text-slate-400 mb-1 block">App ID</label>
            <input type="text" placeholder="Your Threads App ID" value={settings.threadsAppId} onChange={(e) => updateSettings({ threadsAppId: e.target.value })} className="glass-input" />
          </div>
          <div>
            <label className="text-sm text-slate-400 mb-1 block">App Secret</label>
            <input type="password" placeholder="Your Threads App Secret" value={settings.threadsAppSecret} onChange={(e) => updateSettings({ threadsAppSecret: e.target.value })} className="glass-input" />
          </div>
          <div>
            <label className="text-sm text-slate-400 mb-1 block">Redirect URI</label>
            <input type="text" value={settings.redirectUri} onChange={(e) => updateSettings({ redirectUri: e.target.value })} className="glass-input" />
          </div>
        </div>
      </div>
      <div className="glass-card p-6">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2"><Clock size={18} className="text-purple-400" />Automation Settings</h3>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-sm text-slate-400 mb-1 block">Default Delay (sec)</label>
            <input type="number" value={settings.defaultDelay} onChange={(e) => updateSettings({ defaultDelay: +e.target.value })} className="glass-input" />
          </div>
          <div>
            <label className="text-sm text-slate-400 mb-1 block">Max Daily Posts</label>
            <input type="number" value={settings.maxDailyPosts} onChange={(e) => updateSettings({ maxDailyPosts: +e.target.value })} className="glass-input" />
          </div>
        </div>
      </div>
      <div className="glass-card p-6" style={{ borderColor: 'rgba(239, 68, 68, 0.2)' }}>
        <h3 className="text-lg font-semibold mb-4 text-red-400 flex items-center gap-2"><AlertCircle size={18} />Danger Zone</h3>
        <button onClick={() => { if (confirm('Delete all data?')) { localStorage.clear(); window.location.reload(); } }} className="btn-danger text-xs flex items-center gap-2"><Trash2 size={14} />Clear localStorage</button>
      </div>
    </div>
  );
}
