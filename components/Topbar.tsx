export default function Topbar({
    activeTab,
    onTabChange,
}: {
    activeTab: 'explore' | 'models' | 'soon';
    onTabChange: (tab: 'explore' | 'models' | 'soon') => void;
}) {
    return (
        <header className="topbar">
            {/* Logo */}
            <div className="topbar-logo">
                <div className="topbar-logo-icon">Q</div>
                <span className="topbar-logo-name">Quant<span>Lab</span></span>
            </div>

            {/* Centered nav */}
            <nav className="nav-tabs">
                <div
                    onClick={() => onTabChange('explore')}
                    className={`nav-tab ${activeTab === 'explore' ? 'active' : ''}`}
                >
                    <span className="nav-tab-icon">❖</span>
                    Explore Overview
                </div>
                <div
                    onClick={() => onTabChange('models')}
                    className={`nav-tab ${activeTab === 'models' ? 'active' : ''}`}
                >
                    <span className="nav-tab-icon">⊞</span>
                    Models
                </div>
                <div
                    onClick={() => onTabChange('soon')}
                    className={`nav-tab ${activeTab === 'soon' ? 'active' : ''}`}
                >
                    <span className="nav-tab-icon">◎</span>
                    Coming Soon
                    <span className="nav-tab-badge">BETA</span>
                </div>
            </nav>

            {/* Right side */}
            <div className="topbar-right">
                <div className="status-dot">
                    <div className="dot"></div>
                    <span>Market data live · 14:02 UTC</span>
                </div>
                <div className="avatar">JR</div>
            </div>
        </header>
    );
}
