'use client';
import React, { useState } from 'react';
import { useStore } from '@/lib/store';
import { Bot, Play, Pause, Square, Plus, Trash2, Clock, Target, Users, AlertCircle, X, Flame, Heart, UserPlus, UserMinus, MessageSquare } from 'lucide-react';
import type { AutomationTask } from '@/lib/types';

const taskTypes = [
  { id: 'auto_post', label: 'Auto-Post', emoji: 'post', desc: 'Auto-publish by schedule' },
  { id: 'auto_reply', label: 'Auto-Reply', emoji: 'reply', desc: 'Auto-reply to posts' },
  { id: 'auto_like', label: 'Auto-Like', emoji: 'like', desc: 'Auto-like posts' },
  { id: 'mass_follow', label: 'Mass Follow', emoji: 'follow', desc: 'Mass-follow accounts' },
  { id: 'mass_unfollow', label: 'Mass Unfollow', emoji: 'unfollow', desc: 'Mass-unfollow accounts' },
  { id: 'warm_up', label: 'Warm Up', emoji: 'warmup', desc: 'Gradually warm up accounts' },
];

export default function Automation() {
  const { accounts, automationTasks, addAutomationTask, updateAutomationTask, removeAutomationTask } = useStore();
  const [showCreate, setShowCreate] = useState(false);
  const [taskType, setTaskType] = useState('auto_post');
  const [taskAccounts, setTaskAccounts] = useState<string[]>([]);
  const [delayMin, setDelayMin] = useState(300);
  const [delayMax, setDelayMax] = useState(900);
  const [dailyLimit, setDailyLimit] = useState(20);
  const [workStart, setWorkStart] = useState(8);
  const [workEnd, setWorkEnd] = useState(22);
  const active = accounts.filter(a => a.status === 'active' || a.status === 'warming');
  const handleCreate = () => {
    if (taskAccounts.length === 0) return;
    const task: AutomationTask = { id: 'task_' + Date.now(), type: taskType as AutomationTask['type'], accountIds: taskAccounts, status: 'running', config: { delayMin, delayMax, dailyLimit, targetHashtags: [], useSpintax: false, workingHoursStart: workStart, workingHoursEnd: workEnd }, progress: 0, totalActions: dailyLimit, completedActions: 0, startedAt: new Date().toISOString(), errors: [] };
    addAutomationTask(task); setShowCreate(false); setTaskAccounts([]);
  };
  const typeInfo = (type: string) => taskTypes.find(t => t.id === type) || taskTypes[0];
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div><h2 className="text-2xl font-bold">Automation</h2><p className="text-slate-400 text-sm mt-1">Configure automatic actions</p></div>
        <button onClick={() => setShowCreate(true)} className="btn-primary flex items-center gap-2"><Plus size={16} />New Task</button>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {taskTypes.map(type => { const running = automationTasks.filter(t => t.type === type.id && t.status === 'running').length; return (
          <div key={type.id} className="stat-card text-center"><p className="text-lg font-bold mb-1">{type.emoji}</p><p className="text-xs font-medium mb-1">{type.label}</p><p className="text-xs text-slate-500">{running > 0 ? <span className="text-emerald-400">{running} active</span> : 'Idle'}</p></div>
        ); })}
      </div>
      <div className="space-y-4">
        {automationTasks.length === 0 && <div className="glass-card p-12 text-center text-slate-400"><Bot size={48} className="mx-auto mb-4 opacity-30" /><p>No tasks. Create one.</p></div>}
        {automationTasks.map(task => { const ti = typeInfo(task.type); const names = task.accountIds.map(id => accounts.find(a => a.id === id)?.username).filter(Boolean); return (
          <div key={task.id} className="glass-card p-5">
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-3"><div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: 'rgba(15,23,42,0.8)' }}><Bot size={18} /></div><div><h4 className="font-semibold">{ti.label}</h4><p className="text-xs text-slate-400">{names.map(n => '@' + n).join(', ')}</p></div></div>
              <span className={'px-2 py-1 rounded-full text-xs font-medium ' + (task.status === 'running' ? 'bg-emerald-500/15 text-emerald-400' : task.status === 'paused' ? 'bg-amber-500/15 text-amber-400' : 'bg-red-500/15 text-red-400')}>
                {task.status === 'running' && <span className="pulse-dot bg-emerald-400 inline-block mr-1" />}{task.status === 'running' ? 'Running' : task.status === 'paused' ? 'Paused' : 'Stopped'}
              </span>
            </div>
            <div className="mb-4"><div className="flex justify-between text-xs text-slate-400 mb-1"><span>Progress: {task.completedActions}/{task.totalActions}</span><span>{task.progress}%</span></div><div className="progress-bar"><div className="progress-bar-fill" style={{ width: task.progress + '%' }} /></div></div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
              <div className="flex items-center gap-2 text-xs text-slate-400"><Clock size={12} /><span>Delay: {task.config.delayMin}-{task.config.delayMax}s</span></div>
              <div className="flex items-center gap-2 text-xs text-slate-400"><Target size={12} /><span>Limit: {task.config.dailyLimit}/day</span></div>
              <div className="flex items-center gap-2 text-xs text-slate-400"><Clock size={12} /><span>Hours: {task.config.workingHoursStart}:00-{task.config.workingHoursEnd}:00</span></div>
              <div className="flex items-center gap-2 text-xs text-slate-400"><Users size={12} /><span>{task.accountIds.length} accounts</span></div>
            </div>
            <div className="flex items-center gap-2">
              {(task.status === 'running' || task.status === 'paused') && <>
                <button onClick={() => updateAutomationTask(task.id, { status: task.status === 'running' ? 'paused' : 'running' })} className="btn-secondary flex items-center gap-1.5 text-xs">{task.status === 'running' ? <Pause size={14} /> : <Play size={14} />}{task.status === 'running' ? 'Pause' : 'Resume'}</button>
                <button onClick={() => updateAutomationTask(task.id, { status: 'stopped' })} className="btn-secondary flex items-center gap-1.5 text-xs text-red-400"><Square size={14} />Stop</button>
              </>}
              <button onClick={() => removeAutomationTask(task.id)} className="btn-secondary flex items-center gap-1.5 text-xs text-red-400 ml-auto"><Trash2 size={14} />Delete</button>
            </div>
          </div>
        ); })}
      </div>
      {showCreate && (
        <div className="modal-overlay" onClick={() => setShowCreate(false)}>
          <div className="modal-content max-w-lg" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-6"><h3 className="text-lg font-semibold">New Task</h3><button onClick={() => setShowCreate(false)} className="text-slate-400 hover:text-white"><X size={20} /></button></div>
            <div className="space-y-4">
              <div><label className="text-sm text-slate-400 mb-2 block">Task Type</label><div className="grid grid-cols-2 gap-2">{taskTypes.map(type => <button key={type.id} onClick={() => setTaskType(type.id)} className={'p-3 rounded-xl text-left text-sm ' + (taskType === type.id ? 'bg-blue-500/15 border border-blue-500/30' : 'bg-white/5 border border-transparent')}><span className="font-medium">{type.label}</span><p className="text-xs text-slate-500 mt-0.5">{type.desc}</p></button>)}</div></div>
              <div><label className="text-sm text-slate-400 mb-2 block">Accounts</label><div className="grid grid-cols-2 gap-2 max-h-32 overflow-y-auto">{active.map(acc => <button key={acc.id} onClick={() => setTaskAccounts(prev => prev.includes(acc.id) ? prev.filter(a=>a!==acc.id) : [...prev,acc.id])} className={'flex items-center gap-2 p-2 rounded-lg text-sm ' + (taskAccounts.includes(acc.id) ? 'bg-blue-500/15 border border-blue-500/30' : 'bg-white/5 border border-transparent')}><div className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold" style={{ background: 'var(--gradient-threads)' }}>{acc.username[0].toUpperCase()}</div><span className="truncate">@{acc.username}</span></button>)}</div></div>
              <div className="grid grid-cols-2 gap-3"><div><label className="text-xs text-slate-400 mb-1 block">Min Delay (sec)</label><input type="number" value={delayMin} onChange={e=>setDelayMin(+e.target.value)} className="glass-input" /></div><div><label className="text-xs text-slate-400 mb-1 block">Max Delay (sec)</label><input type="number" value={delayMax} onChange={e=>setDelayMax(+e.target.value)} className="glass-input" /></div><div><label className="text-xs text-slate-400 mb-1 block">Daily Limit</label><input type="number" value={dailyLimit} onChange={e=>setDailyLimit(+e.target.value)} className="glass-input" /></div><div><label className="text-xs text-slate-400 mb-1 block">Work Start</label><input type="number" min={0} max={23} value={workStart} onChange={e=>setWorkStart(+e.target.value)} className="glass-input" /></div></div>
              <div className="flex gap-3 pt-2"><button onClick={() => setShowCreate(false)} className="btn-secondary flex-1">Cancel</button><button onClick={handleCreate} disabled={taskAccounts.length === 0} className="btn-primary flex-1 disabled:opacity-40 flex items-center justify-center gap-2"><Play size={16} />Launch</button></div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
      }
