import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { ThreadsAccount, ProxyConfig, AutomationTask, ScheduledPost, ContentTemplate, TabType } from './types';

interface AppSettings {
  threadsAppId: string;
  threadsAppSecret: string;
  redirectUri: string;
  defaultDelay: number;
  maxDailyPosts: number;
  autoRefreshTokens: boolean;
}

interface Store {
  accounts: ThreadsAccount[];
  proxies: ProxyConfig[];
  automationTasks: AutomationTask[];
  scheduledPosts: ScheduledPost[];
  templates: ContentTemplate[];
  settings: AppSettings;
  activeTab: TabType;
  addAccount: (acc: ThreadsAccount) => void;
  updateAccount: (id: string, updates: Partial<ThreadsAccount>) => void;
  removeAccount: (id: string) => void;
  addProxy: (proxy: ProxyConfig) => void;
  updateProxy: (id: string, updates: Partial<ProxyConfig>) => void;
  removeProxy: (id: string) => void;
  addAutomationTask: (task: AutomationTask) => void;
  updateAutomationTask: (id: string, updates: Partial<AutomationTask>) => void;
  removeAutomationTask: (id: string) => void;
  addScheduledPost: (post: ScheduledPost) => void;
  updateScheduledPost: (id: string, updates: Partial<ScheduledPost>) => void;
  removeScheduledPost: (id: string) => void;
  addTemplate: (tmpl: ContentTemplate) => void;
  removeTemplate: (id: string) => void;
  updateSettings: (updates: Partial<AppSettings>) => void;
  setActiveTab: (tab: TabType) => void;
  getAnalytics: () => { totalAccounts: number; activeAccounts: number; postsToday: number; totalFollowers: number; followersGained: number; activeProxies: number; runningTasks: number; chartData: Array<{ date: string; posts: number; followers: number }> };
}

const makeAccount = (username: string, status: ThreadsAccount['status'], followers: number, posts: number, postsToday: number, proxyId: string | null): ThreadsAccount => ({
  id: 'acc_' + username,
  username,
  threadsUserId: Math.floor(Math.random() * 9e14 + 1e14).toString(),
  accessToken: 'EAABsbCS' + Math.random().toString(36).slice(2,18).toUpperCase(),
  tokenExpiresAt: new Date(Date.now() + 45 * 24 * 60 * 60 * 1000).toISOString(),
  proxyId,
  status,
  avatar: '',
  followers,
  following: Math.floor(followers * 0.1),
  postsCount: posts,
  lastActivity: new Date(Date.now() - Math.random() * 3600000).toISOString(),
  createdAt: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString(),
  notes: '',
  dailyPostLimit: 25,
  postsToday,
});

const demoAccounts: ThreadsAccount[] = [
  makeAccount('tech_insider_bot', 'active', 12450, 342, 8, 'proxy_1'),
  makeAccount('crypto_signals_x', 'active', 8230, 156, 5, 'proxy_2'),
  makeAccount('fitness_daily_tips', 'warming', 3100, 89, 2, null),
  makeAccount('news_breaker_ai', 'active', 21000, 567, 12, 'proxy_1'),
  makeAccount('memes_factory_24', 'limited', 45600, 1203, 0, 'proxy_2'),
  makeAccount('style_curator_vip', 'banned', 6780, 234, 0, null),
];

const demoProxies: ProxyConfig[] = [
  { id: 'proxy_1', host: '45.77.123.45', port: 8080, username: 'user1', password: 'pass1', protocol: 'https', status: 'active', assignedAccounts: ['acc_tech_insider_bot', 'acc_news_breaker_ai'], lastCheck: new Date().toISOString(), responseTime: 124, country: 'USA' },
  { id: 'proxy_2', host: '91.198.174.192', port: 3128, username: 'user2', password: 'pass2', protocol: 'socks5', status: 'active', assignedAccounts: ['acc_crypto_signals_x', 'acc_memes_factory_24'], lastCheck: new Date().toISOString(), responseTime: 87, country: 'Germany' },
];

const demoTasks: AutomationTask[] = [
  { id: 'task_1', type: 'auto_post', accountIds: ['acc_tech_insider_bot', 'acc_crypto_signals_x'], status: 'running', config: { delayMin: 300, delayMax: 900, dailyLimit: 20, targetHashtags: ['tech', 'ai'], useSpintax: true, workingHoursStart: 8, workingHoursEnd: 22 }, progress: 65, totalActions: 20, completedActions: 13, startedAt: new Date(Date.now() - 3600000).toISOString(), errors: [] },
  { id: 'task_2', type: 'warm_up', accountIds: ['acc_fitness_daily_tips'], status: 'running', config: { delayMin: 600, delayMax: 1800, dailyLimit: 5, targetHashtags: [], useSpintax: false, workingHoursStart: 9, workingHoursEnd: 20 }, progress: 40, totalActions: 5, completedActions: 2, startedAt: new Date(Date.now() - 7200000).toISOString(), errors: [] },
];

const demoTemplates: ContentTemplate[] = [
  { id: 'tmpl_1', name: 'Tech News Template', category: 'technology', content: '{Breaking|Hot} news in tech today!\n\n{description}\n\n#tech #ai #innovation', useSpintax: true, variables: ['description'], usageCount: 23, createdAt: new Date().toISOString() },
  { id: 'tmpl_2', name: 'Crypto Signal', category: 'crypto', content: '{BTC|ETH|SOL} {signal|update}: {content}\n\n{Bullish|Bearish} trend detected!\n\n#crypto #trading', useSpintax: true, variables: ['content'], usageCount: 47, createdAt: new Date().toISOString() },
];

export const useStore = create<Store>()(
  persist(
    (set, get) => ({
      accounts: demoAccounts,
      proxies: demoProxies,
      automationTasks: demoTasks,
      scheduledPosts: [],
      templates: demoTemplates,
      settings: { threadsAppId: '', threadsAppSecret: '', redirectUri: typeof window !== 'undefined' ? window.location.origin + '/api/auth/callback' : '', defaultDelay: 60, maxDailyPosts: 50, autoRefreshTokens: true },
      activeTab: 'dashboard' as TabType,
      addAccount: (acc) => set(s => ({ accounts: [...s.accounts, acc] })),
      updateAccount: (id, updates) => set(s => ({ accounts: s.accounts.map(a => a.id === id ? { ...a, ...updates } : a) })),
      removeAccount: (id) => set(s => ({ accounts: s.accounts.filter(a => a.id !== id) })),
      addProxy: (proxy) => set(s => ({ proxies: [...s.proxies, proxy] })),
      updateProxy: (id, updates) => set(s => ({ proxies: s.proxies.map(p => p.id === id ? { ...p, ...updates } : p) })),
      removeProxy: (id) => set(s => ({ proxies: s.proxies.filter(p => p.id !== id) })),
      addAutomationTask: (task) => set(s => ({ automationTasks: [...s.automationTasks, task] })),
      updateAutomationTask: (id, updates) => set(s => ({ automationTasks: s.automationTasks.map(t => t.id === id ? { ...t, ...updates } : t) })),
      removeAutomationTask: (id) => set(s => ({ automationTasks: s.automationTasks.filter(t => t.id !== id) })),
      addScheduledPost: (post) => set(s => ({ scheduledPosts: [...s.scheduledPosts, post] })),
      updateScheduledPost: (id, updates) => set(s => ({ scheduledPosts: s.scheduledPosts.map(p => p.id === id ? { ...p, ...updates } : p) })),
      removeScheduledPost: (id) => set(s => ({ scheduledPosts: s.scheduledPosts.filter(p => p.id !== id) })),
      addTemplate: (tmpl) => set(s => ({ templates: [...s.templates, tmpl] })),
      removeTemplate: (id) => set(s => ({ templates: s.templates.filter(t => t.id !== id) })),
      updateSettings: (updates) => set(s => ({ settings: { ...s.settings, ...updates } })),
      setActiveTab: (tab) => set({ activeTab: tab }),
      getAnalytics: () => {
        const { accounts, proxies, automationTasks } = get();
        const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
        return {
          totalAccounts: accounts.length,
          activeAccounts: accounts.filter(a => a.status === 'active').length,
          postsToday: accounts.reduce((sum, a) => sum + a.postsToday, 0),
          totalFollowers: accounts.reduce((sum, a) => sum + a.followers, 0),
          followersGained: Math.floor(accounts.reduce((sum, a) => sum + a.followers, 0) * 0.02),
          activeProxies: proxies.filter(p => p.status === 'active').length,
          runningTasks: automationTasks.filter(t => t.status === 'running').length,
          chartData: days.map((date, i) => ({ date, posts: Math.floor(20 + Math.random() * 40), followers: Math.floor(100 + Math.random() * 500) })),
        };
      },
    }),
    { name: 'threads-bot-factory-v1' }
  )
);
