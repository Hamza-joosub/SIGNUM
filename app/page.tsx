'use client';

import { useState } from 'react';
import Topbar from '@/components/Topbar';
import TabExplore from '@/components/TabExplore';
import TabModels from '@/components/TabModels';
import TabSoon from '@/components/TabSoon';

export default function Home() {
    const [activeTab, setActiveTab] = useState<'explore' | 'models' | 'soon'>('models');

    return (
        <div className="app-shell">
            <div className="bg-ambient"></div>
            <Topbar activeTab={activeTab} onTabChange={setActiveTab} />
            <main className="page-area">
                {activeTab === 'explore' && <TabExplore />}
                {activeTab === 'models' && <TabModels />}
                {activeTab === 'soon' && <TabSoon />}
            </main>
        </div>
    );
}
