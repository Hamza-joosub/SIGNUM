export default function TabExplore() {
    return (
        <div className="flex flex-col">
            <div className="mb-8">
                <h1 className="font-fraunces text-3xl font-light text-[#eae6de] tracking-tight leading-tight">
                    <em>Models</em>
                </h1>
                <p className="text-[13px] text-white/30 mt-1.5">
                    Select a model to run an analysis. More models will be added over time.
                </p>
            </div>

            <div className="bg-gold-500/5 border border-gold-500/15 rounded-xl py-4 px-6 flex items-center gap-3.5 mb-6">
                <span className="text-lg">◈</span>
                <p className="text-[13px] text-white/45 leading-relaxed">
                    Welcome to QuantLab. Use the <strong>Models</strong> tab to access active analytics suites.
                </p>
            </div>

            <div className="grid grid-cols-[2fr_1fr] grid-rows-2 gap-4">
                <div className="col-span-2 bg-white/5 border border-white/10 rounded-xl backdrop-blur-3xl shadow-[inset_0_1px_0_rgba(255,255,255,0.07),_0_8px_40px_rgba(0,0,0,0.4)] overflow-hidden">
                    <div className="px-5 py-4 border-b border-white/5 flex justify-between items-center bg-white/5">
                        <h2 className="font-fraunces text-sm font-semibold text-[#eae6de]">System Health</h2>
                        <span className="text-[11px] text-white/25">All systems nominal</span>
                    </div>
                    <div className="p-5">
                        <div className="h-[160px] rounded-md bg-white/5 border border-dashed border-white/10 flex flex-col items-center justify-center gap-2.5 text-white/20 text-xs text-center p-4">
                            <span className="text-2xl opacity-30">◈</span>
                            <div>
                                <div className="text-[11px] text-white/20">Dashboard Metrics Pipeline</div>
                                <div className="text-[10px] text-white/10 mt-0.5">Awaiting first model execution...</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
