'use client';

import React from 'react';
import { useStore } from '@/lib/store';
import Sidebar from '@/components/Sidebar';
import Dashboard from '@/components/Dashboard';
import AccountManager from '@/components/AccountManager';
import PostScheduler from '@/components/PostScheduler';
import Automation from '@/components/Automation';
import ProxyManager from '@/components/ProxyManager';
import Templates from '@/components/Templates';
import SettingsPanel from '@/components/SettingsPanel';
import VideoAnalyzer from '@/components/VideoAnalyzer';

export default function DashboardPage() {
  const { activeTab } = useStore();

  const renderContent = () => {
    switch (activeTab) {
      case 'dashboard':   return <Dashboard />;
      case 'accounts':    return <AccountManager />;
      case 'posting':     return <PostScheduler />;
      case 'automation':  return <Automation />;
      case 'proxies':     return <ProxyManager />;
      case 'templates':   return <Templates />;
      case 'settings':    return <SettingsPanel />;
      case 'ai-video':    return <VideoAnalyzer />;
      default:            return <Dashboard />;
    }
  };

  return (
    <div className="min-h-screen relative z-10">
      <Sidebar />
      <main className="ml-72 p-8">
        {renderContent()}
      </main>
    </div>
  );
}
