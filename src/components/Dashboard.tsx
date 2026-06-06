'use client';
import React from 'react';
import { useStore } from '@/lib/store';
import { TrendingUp, Users, Send, Activity, CheckCircle2, ArrowUpRight, ArrowDownRight, Bot, Shield } from 'lucide-react';

export default function Dashboard() {
  const { accounts, automationTasks, scheduledPosts, proxies, getAnalytics } = useStore();
  const analytics = getAnalytics();
  const stats: { label: string; value: string | number; change: string; changeType: 'up' | 'down' | 'neutral'; icon: React.JSX.Element; gradient: string }[] = [
    { label: 'Total Accounts', value: analytics.totalAccounts, change: '+2 this week', changeType: 'up', icon: <Users size={20} />, gradient: 'var(--gradient-threads)' },
    { label: 'Active', value: analytics.activeAccounts, change: Math.round((analytics.activeAccounts / (analytics.totalAccounts || 1)) * 100) + '%', changeType: 'up', icon: <CheckCircle2 size={20} />, gradient: 'var(--gradient-success)' },
    { label: 'Posts Today', value: analytics.postsToday, change: '+12/hour', changeType: 'up', icon: <Send size={20} />, gradient: 'var(--gradient-purple)' },
    { label: 'Followers', value: analytics.totalFollowers.toLocaleString(), change: '+' + analytics.followersGained.toLocaleString(), changeType: 'up', icon: <TrendingUp size={20} />, gradient: 'linear-gradient(135deg, #0095f6, #00d4ff)' },
    { label: 'Active Proxies', value: analytics.activeProxies, change: 'of ' + proxies.length, changeType: 'neutral', icon: <Shield size={20} />, gradient: 'var(--gradient-warning)' },
    { label: 'Running Tasks', value: analytics.runningTasks, change: 'Active', changeType: 'up', icon: <Bot size={20} />, gradient: 'var(--gradient-success)' },
  ];
  const recentActivity = [
    { account: 'tech_insider_bot', text: 'Post about AI published', time: '2m ago', status: 'success' },
    { account: 'crypto_signals_x', text: 'BTC signal post published', time: '18m ago', status: 'success' },
    { account: 'memes_factory_24', text: 'Rate limit - 15min pause', time: '12m ago', status: 'warning' },
    { account: 'style_curator_vip', text: 'Account banned', time: '1h ago', status: 'error' },
  ];
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div><h2 className="text-2xl font-bold">Dashboard</h2><p className="text-slate-400 text-sm mt-1">Bot factory overview</p></div>
        <div className="flex items-center gap-2"><span className="pulse-dot bg-emerald-400" /><span className="text-sm text-emerald-400 font-medium">All systems operational</span></div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {stats.map((stat, i) => (
          <div key={i} className="stat-card group">
            <div className="flex items-start justify-between mb-3">
              <div className="w-10 h-10 rounded-xl flex items-center justify-center text-white" style={{ background: stat.gradient }}>{stat.icon}</div>
              <div className={'flex items-center gap-1 text-xs font-medium ' + (stat.changeType === 'up' ? 'text-emerald-400' : stat.changeType === 'down' ? 'text-red-400' : 'text-slate-400')}>
                {stat.changeType === 'up' && <ArrowUpRight size={14} />}{stat.changeType === 'down' && <ArrowDownRight size={14} />}{stat.change}
              </div>
            </div>
            <p className="text-2xl font-bold mb-1">{stat.value}</p><p className="text-sm text-slate-400">{stat.label}</p>
          </div>
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 glass-card p-6">
          <h3 className="text-lg font-semibold mb-4">Weekly Activity</h3>
          <div className="flex items-end justify-between gap-2 h-48 px-2">
            {analytics.chartData.map((point, i) => (
              <div key={i} className="flex-1 flex flex-col items-center gap-1">
                <div className="w-full flex items-end justify-center gap-1" style={{ height: '160px' }}>
                  <div className="w-5 rounded-t-md" style={{ height: (point.posts / 60 * 100) + '%', background: 'var(--gradient-threads)', minHeight: '8px' }} />
                  <div className="w-5 rounded-t-md bg-emerald-400/70" style={{ height: (point.followers / 600 * 100) + '%', minHeight: '8px' }} />
                </div>
                <span className="text-xs text-slate-500">{point.date}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="glass-card p-6">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2"><Activity size={18} />Activity</h3>
          <div className="space-y-3">
            {recentActivity.map((item, i) => (
              <div key={i} className="flex items-start gap-3 p-2 rounded-lg hover:bg-white/5">
                <div className={'w-2 h-2 mt-2 rounded-full flex-shrink-0 ' + (item.status === 'success' ? 'bg-emerald-400' : item.status === 'warning' ? 'bg-amber-400' : 'bg-red-400')} />
                <div className="flex-1 min-w-0"><p className="text-sm truncate">{item.text}</p><p className="text-xs text-slate-500">@{item.account} - {item.time}</p></div>
              </div>
            ))}
          </div>
        </div>
      </div>
      <div className="glass-card p-6">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2"><Bot size={18} />Running Tasks</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {automationTasks.filter(t => t.status === 'running').map(task => (
            <div key={task.id} className="p-4 rounded-xl border" style={{ background: 'rgba(15,23,42,0.5)', borderColor: 'var(--glass-border)' }}>
              <p className="text-sm font-medium mb-2">{task.type === 'auto_post' ? 'Auto Post' : task.type === 'auto_reply' ? 'Auto Reply' : task.type === 'warm_up' ? 'Warm Up' : task.type}</p>
              <p className="text-xs text-slate-400 mb-3">{task.accountIds.length} accounts - {task.completedActions}/{task.totalActions}</p>
              <div className="progress-bar"><div className="progress-bar-fill" style={{ width: task.progress + '%' }} /></div>
              <p className="text-xs text-slate-500 mt-2">{task.progress}% done</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
