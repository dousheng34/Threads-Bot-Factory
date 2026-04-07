// ============================================
// Threads Bot Factory - Core Types
// ============================================

export interface ThreadsAccount {
  id: string;
  username: string;
  threadsUserId: string;
  accessToken: string;
  tokenExpiresAt: string;
  proxyId: string | null;
  status: 'active' | 'warming' | 'banned' | 'limited' | 'inactive';
  avatar: string;
  followers: number;
  following: number;
  postsCount: number;
  lastActivity: string;
  createdAt: string;
  notes: string;
  dailyPostLimit: number;
  postsToday: number;
}

export interface ProxyConfig {
  id: string;
  host: string;
  port: number;
  username: string;
  password: string;
  protocol: 'http' | 'https' | 'socks5';
  status: 'active' | 'dead' | 'slow';
  assignedAccounts: string[];
  lastCheck: string;
  responseTime: number;
  country: string;
}

export interface ScheduledPost {
  id: string;
  accountIds: string[];
  content: PostContent;
  scheduledAt: string;
  status: 'pending' | 'publishing' | 'published' | 'failed' | 'cancelled';
  publishedAt?: string;
  error?: string;
  results: PostResult[];
}

export interface PostContent {
  text: string;
  mediaUrls: string[];
  mediaType: 'text' | 'image' | 'video' | 'carousel';
  replyToId?: string;
  useSpintax: boolean;
}

export interface PostResult {
  accountId: string;
  threadId?: string;
  status: 'success' | 'failed';
  error?: string;
  publishedAt: string;
}

export interface AutomationTask {
  id: string;
  type: 'auto_post' | 'auto_reply' | 'auto_like' | 'mass_follow' | 'mass_unfollow' | 'warm_up';
  accountIds: string[];
  status: 'running' | 'paused' | 'stopped' | 'completed';
  config: AutomationConfig;
  progress: number;
  totalActions: number;
  completedActions: number;
  startedAt: string;
  lastActionAt?: string;
  errors: string[];
}

export interface AutomationConfig {
  delayMin: number;
  delayMax: number;
  dailyLimit: number;
  targetHashtags?: string[];
  targetUsers?: string[];
  contentTemplates?: string[];
  replyTemplates?: string[];
  useSpintax: boolean;
  workingHoursStart: number;
  workingHoursEnd: number;
}

export interface ContentTemplate {
  id: string;
  name: string;
  category: string;
  content: string;
  useSpintax: boolean;
  variables: string[];
  usageCount: number;
  createdAt: string;
}

export interface AnalyticsData {
  totalAccounts: number;
  activeAccounts: number;
  bannedAccounts: number;
  totalPosts: number;
  postsToday: number;
  postsThisWeek: number;
  totalFollowers: number;
  followersGained: number;
  successRate: number;
  activeProxies: number;
  runningTasks: number;
  chartData: ChartPoint[];
}

export interface ChartPoint {
  date: string;
  posts: number;
  followers: number;
  engagement: number;
}

export type TabType = 'dashboard' | 'accounts' | 'posting' | 'automation' | 'proxies' | 'templates' | 'settings' | 'ai-video';
