export default function TabSoon() {
    return (
        <div className="flex items-center justify-center min-h-[60vh]">
            <div className="text-center max-w-[480px]">
                <span className="text-5xl mb-6 opacity-30 block">◎</span>
                <h2 className="font-fraunces text-[32px] font-light text-[#eae6de] mb-3 tracking-tight">
                    Something is <em className="text-gold-500 italic">coming</em>
                </h2>
                <p className="text-sm text-white/30 leading-relaxed mb-8">
                    This section is reserved for upcoming features — news feeds, macro event calendars, and live data integrations. Check back as the platform evolves.
                </p>
                <div className="inline-flex items-center gap-2 py-2.5 px-5 bg-gold-500/10 border border-gold-500/20 rounded-lg text-xs text-gold-500 font-semibold tracking-wider">
                    <div className="w-1.5 h-1.5 rounded-full bg-gold-500/60 animate-pulse"></div>
                    IN DEVELOPMENT
                </div>
            </div>
        </div>
    );
}
