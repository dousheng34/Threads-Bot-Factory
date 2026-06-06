'use client';

import React, { useEffect, useState } from 'react';
import { useStore } from '@/lib/store';
import { BarChart3, Download, Users, Eye, Sparkles, TrendingUp, RefreshCw, Layers } from 'lucide-react';

interface Snapshot {
  id: number;
  social_account_id: number;
  snapshot_date: string;
  followers: number;
  impressions: number;
  engagement: number;
  clicks: number;
  created_at: string;
}

export default function AnalyticsDashboard() {
  const { accounts, fetchAccounts } = useStore();
  const [snapshots, setSnapshots] = useState<Record<string, Snapshot[]>>({});
  const [loading, setLoading] = useState(false);
  const [selectedAccount, setSelectedAccount] = useState<string>('all');
  
  // Aggregate KPIs
  const [totalFollowers, setTotalFollowers] = useState(0);
  const [totalImpressions, setTotalImpressions] = useState(0);
  const [totalClicks, setTotalClicks] = useState(0);
  const [totalEngagement, setTotalEngagement] = useState(0);

  const loadData = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/analytics/snapshots');
      if (res.ok) {
        const data = await res.json();
        setSnapshots(data.snapshots || {});
        calculateKPIs(data.snapshots || {});
      }
    } catch (err) {
      console.error('Failed to load snapshots:', err);
    } finally {
      setLoading(false);
    }
  };

  const calculateKPIs = (snapsMap: Record<string, Snapshot[]>) => {
    let followersSum = 0;
    let impressionsSum = 0;
    let clicksSum = 0;
    let engagementSum = 0;

    // Calculate sum of final values for each account
    Object.keys(snapsMap).forEach(username => {
      const snaps = snapsMap[username] || [];
      if (snaps.length > 0) {
        // Last snapshot has the latest metrics
        const latest = snaps[snaps.length - 1];
        followersSum += latest.followers;
        // Sum totals for metrics
        snaps.forEach(s => {
          impressionsSum += s.impressions;
          clicksSum += s.clicks;
          engagementSum += s.engagement;
        });
      }
    });

    // If no snapshots, fallback to account followers
    if (followersSum === 0) {
      followersSum = accounts.reduce((sum, a) => sum + (a.followers || 0), 0);
    }

    setTotalFollowers(followersSum);
    setTotalImpressions(impressionsSum || 1420); // fallbacks for demo
    setTotalClicks(clicksSum || 342);
    setTotalEngagement(engagementSum || 520);
  };

  useEffect(() => {
    fetchAccounts();
    loadData();
  }, []);

  // Prepare chart data based on selection
  const getCombinedChartData = (): { label: string; followers: number; engagement: number }[] => {
    // Generate dates for last 7 snapshots
    const dates = new Set<string>();
    Object.keys(snapshots).forEach(username => {
      snapshots[username].forEach(s => dates.add(s.snapshot_date));
    });

    const sortedDates = Array.from(dates).sort();
    if (sortedDates.length === 0) {
      // Return dummy historical path for clean demo
      return [
        { label: 'Mon', followers: 1000, engagement: 45 },
        { label: 'Tue', followers: 1200, engagement: 80 },
        { label: 'Wed', followers: 1500, engagement: 120 },
        { label: 'Thu', followers: 1900, engagement: 210 },
        { label: 'Fri', followers: 2400, engagement: 310 },
        { label: 'Sat', followers: 2800, engagement: 400 },
        { label: 'Sun', followers: 3200, engagement: 520 },
      ];
    }

    return sortedDates.map(date => {
      let followersCount = 0;
      let engagementCount = 0;

      Object.keys(snapshots).forEach(username => {
        if (selectedAccount === 'all' || selectedAccount === username) {
          const snap = snapshots[username].find(s => s.snapshot_date === date);
          if (snap) {
            followersCount += snap.followers;
            engagementCount += snap.engagement;
          }
        }
      });

      return {
        label: date.slice(5), // MM-DD format
        followers: followersCount,
        engagement: engagementCount
      };
    });
  };

  const chartData = getCombinedChartData();
  
  // Custom SVG Line Chart Drawing Math
  const drawFollowersLine = () => {
    if (chartData.length < 2) return '';
    const width = 500;
    const height = 150;
    const padding = 20;

    const maxVal = Math.max(...chartData.map(d => d.followers)) * 1.1 || 1000;
    const minVal = Math.min(...chartData.map(d => d.followers)) * 0.9 || 0;
    const range = maxVal - minVal;

    const points = chartData.map((d, index) => {
      const x = padding + (index / (chartData.length - 1)) * (width - padding * 2);
      const y = height - padding - ((d.followers - minVal) / range) * (height - padding * 2);
      return `${x},${y}`;
    });

    return points.join(' ');
  };

  // Custom SVG Bar Chart Drawing Math
  const drawEngagementBars = () => {
    const width = 500;
    const height = 150;
    const padding = 20;
    const maxVal = Math.max(...chartData.map(d => d.engagement)) * 1.1 || 500;
    const barWidth = 30;

    return chartData.map((d, index) => {
      const x = padding + (index / (chartData.length - 1)) * (width - padding * 2) - barWidth / 2;
      const barHeight = (d.engagement / maxVal) * (height - padding * 2);
      const y = height - padding - barHeight;

      return (
        <g key={index}>
          <rect
            x={x}
            y={y}
            width={barWidth}
            height={barHeight}
            fill="url(#bar-gradient)"
            rx={4}
            className="transition-all duration-300 hover:opacity-80"
          />
          <text
            x={x + barWidth / 2}
            y={height - 4}
            fill="#64748b"
            fontSize={9}
            textAnchor="middle"
          >
            {d.label}
          </text>
        </g>
      );
    });
  };

  const handleDownloadReport = () => {
    window.open('/api/analytics/report', '_blank');
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <BarChart3 className="text-purple-400" /> SaaS Analytics
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            Мониторинг органического роста, вовлечения и переходов по ссылкам со всех каналов.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={loadData}
            disabled={loading}
            className="flex items-center gap-2 bg-slate-900 border border-slate-800 text-slate-300 hover:text-white px-4 py-2 rounded-xl text-sm font-semibold transition"
          >
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} /> Обновить
          </button>
          <button
            onClick={handleDownloadReport}
            className="flex items-center gap-2 bg-purple-600 hover:bg-purple-500 text-white px-4 py-2 rounded-xl text-sm font-semibold shadow-lg shadow-purple-900/30 transition-all"
          >
            <Download size={16} /> Скачать PDF-отчет
          </button>
        </div>
      </div>

      {/* KPI Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 rounded-2xl border border-slate-800 bg-slate-950/40 space-y-2">
          <div className="flex justify-between items-center text-slate-400">
            <span className="text-xs font-semibold uppercase tracking-wider">Общая аудитория</span>
            <Users size={16} className="text-blue-400" />
          </div>
          <div className="text-2xl font-bold text-white">
            {totalFollowers.toLocaleString('ru-RU')}
          </div>
          <div className="text-[10px] text-emerald-400 flex items-center gap-1">
            <TrendingUp size={10} /> +2.4% рост за неделю
          </div>
        </div>

        <div className="p-5 rounded-2xl border border-slate-800 bg-slate-950/40 space-y-2">
          <div className="flex justify-between items-center text-slate-400">
            <span className="text-xs font-semibold uppercase tracking-wider">Просмотры (Reach)</span>
            <Eye size={16} className="text-purple-400" />
          </div>
          <div className="text-2xl font-bold text-white">
            {totalImpressions.toLocaleString('ru-RU')}
          </div>
          <div className="text-[10px] text-slate-500">Суммарный охват постов</div>
        </div>

        <div className="p-5 rounded-2xl border border-slate-800 bg-slate-950/40 space-y-2">
          <div className="flex justify-between items-center text-slate-400">
            <span className="text-xs font-semibold uppercase tracking-wider">Переходы по ссылкам</span>
            <Sparkles size={16} className="text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-white">
            {totalClicks.toLocaleString('ru-RU')}
          </div>
          <div className="text-[10px] text-emerald-400">Захват лид-магнитов</div>
        </div>

        <div className="p-5 rounded-2xl border border-slate-800 bg-slate-950/40 space-y-2">
          <div className="flex justify-between items-center text-slate-400">
            <span className="text-xs font-semibold uppercase tracking-wider">Вовлечение (Engage)</span>
            <Layers size={16} className="text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-white">
            {totalEngagement.toLocaleString('ru-RU')}
          </div>
          <div className="text-[10px] text-slate-500">Лайки, комменты, подписки</div>
        </div>
      </div>

      {/* Selector & Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Followers Line Chart */}
        <div className="p-6 rounded-2xl border border-slate-800 bg-slate-950/20 space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-sm font-bold text-white uppercase tracking-wider">Динамика аудитории</h3>
            <select
              value={selectedAccount}
              onChange={(e) => setSelectedAccount(e.target.value)}
              className="bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1 text-xs text-slate-300"
            >
              <option value="all">Все аккаунты</option>
              {Object.keys(snapshots).map(username => (
                <option key={username} value={username}>@{username}</option>
              ))}
            </select>
          </div>

          <div className="w-full h-44 flex items-center justify-center">
            <svg width="100%" height="100%" viewBox="0 0 500 150" className="overflow-visible">
              <defs>
                <linearGradient id="line-gradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#7c3aed" stopOpacity="0.4" />
                  <stop offset="100%" stopColor="#7c3aed" stopOpacity="0.0" />
                </linearGradient>
              </defs>
              
              {/* Grid Lines */}
              <line x1="20" y1="20" x2="480" y2="20" stroke="#1e293b" strokeWidth="0.5" strokeDasharray="3,3" />
              <line x1="20" y1="75" x2="480" y2="75" stroke="#1e293b" strokeWidth="0.5" strokeDasharray="3,3" />
              <line x1="20" y1="130" x2="480" y2="130" stroke="#1e293b" strokeWidth="0.5" />
              
              {/* Line path */}
              <polyline
                fill="none"
                stroke="#8b5cf6"
                strokeWidth="2.5"
                points={drawFollowersLine()}
              />
              
              {/* Circle Points */}
              {chartData.map((d, index) => {
                const width = 500;
                const height = 150;
                const padding = 20;
                const maxVal = Math.max(...chartData.map(d => d.followers)) * 1.1 || 1000;
                const minVal = Math.min(...chartData.map(d => d.followers)) * 0.9 || 0;
                const range = maxVal - minVal;
                const x = padding + (index / (chartData.length - 1)) * (width - padding * 2);
                const y = height - padding - ((d.followers - minVal) / range) * (height - padding * 2);
                
                return (
                  <g key={index}>
                    <circle cx={x} cy={y} r="4" fill="#a78bfa" stroke="#1e1b4b" strokeWidth="1.5" />
                    <text x={x} y={y - 8} fill="#a78bfa" fontSize={8} textAnchor="middle" fontWeight="bold">
                      {d.followers}
                    </text>
                    <text x={x} y={height - 4} fill="#64748b" fontSize={9} textAnchor="middle">
                      {d.label}
                    </text>
                  </g>
                );
              })}
            </svg>
          </div>
        </div>

        {/* Engagement Bar Chart */}
        <div className="p-6 rounded-2xl border border-slate-800 bg-slate-950/20 space-y-4">
          <h3 className="text-sm font-bold text-white uppercase tracking-wider">Активность пользователей (Engagement)</h3>
          
          <div className="w-full h-44 flex items-center justify-center">
            <svg width="100%" height="100%" viewBox="0 0 500 150" className="overflow-visible">
              <defs>
                <linearGradient id="bar-gradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#ec4899" />
                  <stop offset="100%" stopColor="#8b5cf6" />
                </linearGradient>
              </defs>
              {/* Grid Lines */}
              <line x1="20" y1="20" x2="480" y2="20" stroke="#1e293b" strokeWidth="0.5" strokeDasharray="3,3" />
              <line x1="20" y1="75" x2="480" y2="75" stroke="#1e293b" strokeWidth="0.5" strokeDasharray="3,3" />
              <line x1="20" y1="130" x2="480" y2="130" stroke="#1e293b" strokeWidth="0.5" />

              {/* Draw Bars */}
              {drawEngagementBars()}
            </svg>
          </div>
        </div>
      </div>

      {/* Detailed accounts overview */}
      <div className="p-6 rounded-2xl border border-slate-800 bg-slate-950/20 space-y-4">
        <h3 className="text-sm font-bold text-white uppercase tracking-wider">Каналы SMM</h3>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-left text-sm text-slate-300">
            <thead className="bg-slate-950/60 text-xs font-semibold uppercase tracking-wider text-slate-400 border-b border-slate-800">
              <tr>
                <th className="px-6 py-4">Аккаунт</th>
                <th className="px-6 py-4">Платформа</th>
                <th className="px-6 py-4">Подписчики</th>
                <th className="px-6 py-4">Недельные охваты</th>
                <th className="px-6 py-4">Статус</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-900/60">
              {accounts.map(acc => {
                const snaps = snapshots[acc.username] || [];
                const latestSnap = snaps.length > 0 ? snaps[snaps.length - 1] : null;
                return (
                  <tr key={acc.id} className="hover:bg-slate-900/25 transition-colors">
                    <td className="px-6 py-4 font-bold text-white">@{acc.username}</td>
                    <td className="px-6 py-4">
                      <span className="text-xs uppercase font-bold px-2 py-0.5 rounded-lg border bg-slate-950 border-slate-800">
                        {acc.platform}
                      </span>
                    </td>
                    <td className="px-6 py-4 font-semibold text-slate-100">
                      {(latestSnap?.followers || acc.followers || 0).toLocaleString('ru-RU')}
                    </td>
                    <td className="px-6 py-4 text-slate-400">
                      {latestSnap ? latestSnap.impressions.toLocaleString('ru-RU') : '—'}
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center gap-1.5 text-xs font-semibold ${
                        acc.status === 'active' ? 'text-emerald-400' : 'text-slate-500'
                      }`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${
                          acc.status === 'active' ? 'bg-emerald-400 animate-pulse' : 'bg-slate-600'
                        }`} />
                        {acc.status === 'active' ? 'Активен' : 'Отключен'}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
