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
  fetchAccounts: () => Promise<void>;
  addAccount: (acc: ThreadsAccount) => Promise<void>;
  updateAccount: (id: string, updates: Partial<ThreadsAccount>) => Promise<void>;
  removeAccount: (id: string) => Promise<void>;
  fetchProxies: () => Promise<void>;
  addProxy: (proxy: ProxyConfig) => void;
  updateProxy: (id: string, updates: Partial<ProxyConfig>) => void;
  removeProxy: (id: string) => void;
  addAutomationTask: (task: AutomationTask) => void;
  updateAutomationTask: (id: string, updates: Partial<AutomationTask>) => void;
  removeAutomationTask: (id: string) => void;
  fetchTemplates: () => Promise<void>;
  addTemplate: (tmpl: ContentTemplate) => void;
  removeTemplate: (id: string) => void;
  fetchScheduledPosts: () => Promise<void>;
  addScheduledPost: (post: ScheduledPost) => void;
  updateScheduledPost: (id: string, updates: Partial<ScheduledPost>) => void;
  removeScheduledPost: (id: string) => void;
  updateSettings: (updates: Partial<AppSettings>) => void;
  setActiveTab: (tab: TabType) => void;
  getAnalytics: () => { totalAccounts: number; activeAccounts: number; postsToday: number; totalFollowers: number; followersGained: number; activeProxies: number; runningTasks: number; chartData: Array<{ date: string; posts: number; followers: number }> };
}

const makeAccount = (username: string, status: ThreadsAccount['status'], followers: number, posts: number, postsToday: number, proxyId: string | null): ThreadsAccount => ({
  id: 'acc_' + username,
  platform: 'threads',
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
  makeAccount('fitness_daily_tips', 'active', 3100, 89, 2, null),
];

const demoProxies: ProxyConfig[] = [
  { id: 'proxy_1', host: '45.77.123.45', port: 8080, username: 'user1', password: 'pass1', protocol: 'https', status: 'active', assignedAccounts: ['acc_tech_insider_bot'], lastCheck: new Date().toISOString(), responseTime: 124, country: 'USA' },
  { id: 'proxy_2', host: '91.198.174.192', port: 3128, username: 'user2', password: 'pass2', protocol: 'socks5', status: 'active', assignedAccounts: ['acc_crypto_signals_x'], lastCheck: new Date().toISOString(), responseTime: 87, country: 'Germany' },
];

const demoTasks: AutomationTask[] = [
  { id: 'task_1', type: 'auto_post', accountIds: ['acc_tech_insider_bot', 'acc_crypto_signals_x'], status: 'running', config: { delayMin: 300, delayMax: 900, dailyLimit: 20, targetHashtags: ['tech', 'ai'], useSpintax: true, workingHoursStart: 8, workingHoursEnd: 22 }, progress: 65, totalActions: 20, completedActions: 13, startedAt: new Date(Date.now() - 3600000).toISOString(), errors: [] },
];

const demoTemplates: ContentTemplate[] = [
  { id: 'tmpl_1', name: 'Tech News Template', category: 'technology', content: '{Breaking|Hot} news in tech today!\n\n{description}\n\n#tech #ai #innovation', useSpintax: true, variables: ['description'], usageCount: 23, createdAt: new Date().toISOString() },
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

      fetchAccounts: async () => {
        try {
          const res = await fetch('/api/accounts');
          if (res.ok) {
            const data = await res.json();
            const mapped = data.accounts.map((a: any) => {
              let settingsObj: any = {};
              try { settingsObj = JSON.parse(a.settings || '{}'); } catch(e){}
              return {
                id: String(a.id),
                platform: a.platform || 'threads',
                username: a.username,
                threadsUserId: a.platform_user_id || '',
                accessToken: a.access_token || '',
                tokenExpiresAt: a.token_expires_at || '',
                proxyId: settingsObj['proxy_id'] || null,
                status: a.status || 'active',
                avatar: '',
                followers: a.followers_count || 0,
                following: 0,
                postsCount: a.posts_count || 0,
                lastActivity: a.last_activity || new Date().toISOString(),
                createdAt: a.created_at || new Date().toISOString(),
                notes: settingsObj['notes'] || '',
                dailyPostLimit: settingsObj['daily_limit'] || 25,
                postsToday: 0
              };
            });
            set({ accounts: mapped });
          }
        } catch(e) {
          console.error('[store] fetchAccounts failed, using local:', e);
        }
      },

      addAccount: async (acc) => {
        try {
          const r = await fetch('/api/accounts/add', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
              platform: acc.platform,
              username: acc.username,
              access_token: acc.accessToken,
              threads_user_id: acc.threadsUserId
            })
          });
          if (r.ok) {
            await get().fetchAccounts();
          } else {
            set(s => ({ accounts: [...s.accounts, acc] }));
          }
        } catch(e) {
          set(s => ({ accounts: [...s.accounts, acc] }));
        }
      },

      updateAccount: async (id, updates) => {
        try {
          const dbId = id.startsWith('acc_') ? id.replace('acc_', '') : id;
          const r = await fetch(`/api/accounts/${dbId}`, {
            method: 'PATCH',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(updates)
          });
          if (r.ok) {
            await get().fetchAccounts();
          } else {
            set(s => ({ accounts: s.accounts.map(a => a.id === id ? { ...a, ...updates } : a) }));
          }
        } catch(e) {
          set(s => ({ accounts: s.accounts.map(a => a.id === id ? { ...a, ...updates } : a) }));
        }
      },

      removeAccount: async (id) => {
        try {
          const dbId = id.startsWith('acc_') ? id.replace('acc_', '') : id;
          const r = await fetch(`/api/accounts/${dbId}`, { method: 'DELETE' });
          if (r.ok) {
            await get().fetchAccounts();
          } else {
            set(s => ({ accounts: s.accounts.filter(a => a.id !== id) }));
          }
        } catch(e) {
          set(s => ({ accounts: s.accounts.filter(a => a.id !== id) }));
        }
      },

      fetchProxies: async () => {
        // Implementation for proxies can be added similarly
      },
      addProxy: async (proxy) => set(s => ({ proxies: [...s.proxies, proxy] })),
      updateProxy: async (id, updates) => set(s => ({ proxies: s.proxies.map(p => p.id === id ? { ...p, ...updates } : p) })),
      removeProxy: (id) => set(s => ({ proxies: s.proxies.filter(p => p.id !== id) })),

      addAutomationTask: (task) => set(s => ({ automationTasks: [...s.automationTasks, task] })),
      updateAutomationTask: (id, updates) => set(s => ({ automationTasks: s.automationTasks.map(t => t.id === id ? { ...t, ...updates } : t) })),
      removeAutomationTask: (id) => set(s => ({ automationTasks: s.automationTasks.filter(t => t.id !== id) })),

      fetchTemplates: async () => {
        // Template fetching implementation
      },
      addTemplate: async (tmpl) => set(s => ({ templates: [...s.templates, tmpl] })),
      removeTemplate: async (id) => set(s => ({ templates: s.templates.filter(t => t.id !== id) })),

      fetchScheduledPosts: async () => {
        // Scheduled post fetching implementation
      },
      addScheduledPost: async (post) => set(s => ({ scheduledPosts: [...s.scheduledPosts, post] })),
      updateScheduledPost: async (id, updates) => set(s => ({ scheduledPosts: s.scheduledPosts.map(p => p.id === id ? { ...p, ...updates } : p) })),
      removeScheduledPost: async (id) => set(s => ({ scheduledPosts: s.scheduledPosts.filter(p => p.id !== id) })),

      updateSettings: (updates) => set(s => ({ settings: { ...s.settings, ...updates } })),
      setActiveTab: (tab) => set({ activeTab: tab }),

      getAnalytics: () => {
        const { accounts, proxies, automationTasks } = get();
        const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
        return {
          totalAccounts: accounts.length,
          activeAccounts: accounts.filter(a => a.status === 'active').length,
          postsToday: accounts.reduce((sum, a) => sum + (a.postsToday || 0), 0),
          totalFollowers: accounts.reduce((sum, a) => sum + a.followers, 0),
          followersGained: Math.floor(accounts.reduce((sum, a) => sum + a.followers, 0) * 0.02),
          activeProxies: proxies.filter(p => p.status === 'active').length,
          runningTasks: automationTasks.filter(t => t.status === 'running').length,
          chartData: days.map((date) => ({ date, posts: Math.floor(20 + Math.random() * 40), followers: Math.floor(100 + Math.random() * 500) })),
        };
      },
    }),
    { name: 'threads-bot-factory-v1' }
  )
);
