
export default function TabBar({
    activeTab,
    onTabChange,
}: {
    activeTab: 'explore' | 'models' | 'soon';
    onTabChange: (tab: 'explore' | 'models' | 'soon') => void;
}) {
    return (
        <nav className="flex items-center px-8 h-12 bg-white/5 backdrop-blur-xl border-b border-white/5 gap-0.5 shrink-0">
            <TabButton
                icon="◈"
                label="Explore Overview"
                isActive={activeTab === 'explore'}
                onClick={() => onTabChange('explore')}
            />
            <TabButton
                icon="⊞"
                label="Models"
                isActive={activeTab === 'models'}
                onClick={() => onTabChange('models')}
            />
            <TabButton
                icon="◎"
                label="Coming Soon"
                isActive={activeTab === 'soon'}
                badge="BETA"
                onClick={() => onTabChange('soon')}
            />
        </nav>
    );
}

function TabButton({
    icon,
    label,
    isActive,
    badge,
    onClick,
}: {
    icon: string;
    label: string;
    isActive: boolean;
    badge?: string;
    onClick: () => void;
}) {
    return (
        <div
            onClick={onClick}
            className={`px-5 h-9 flex items-center gap-2 text-[12px] font-medium cursor-pointer rounded-md border border-transparent transition-all select-none relative ${isActive
                ? 'bg-gradient-to-br from-gold-500 to-gold-600 text-canvas font-bold shadow-[0_2px_12px_rgba(200,169,110,0.2)]'
                : 'text-white/30 hover:text-white/65 hover:bg-white/5'
                }`}
        >
            <span className="text-[13px] leading-none">{icon}</span>
            {label}
            {badge && (
                <span
                    className={`text-[9px] px-1.5 py-0.5 rounded-full tracking-wider font-semibold border ${isActive
                        ? 'bg-canvas/20 border-canvas/15 text-canvas/60'
                        : 'bg-white/10 border-white/10 text-white/30'
                        }`}
                >
                    {badge}
                </span>
            )}
        </div>
    );
}
