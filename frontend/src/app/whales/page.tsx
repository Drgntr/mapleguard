import WhaleTrackerPanel from "@/components/WhaleTrackerPanel";

export default function WhalesPage() {
    return (
        <div className="space-y-6 max-w-7xl mx-auto">
            <div>
                <h2 className="text-lg font-mono font-bold text-terminal-text tracking-wider">
                    WHALE TRACKER DASHBOARD
                </h2>
                <p className="text-xs font-mono text-terminal-muted mt-1">
                    Monitor macro-market movements, biggest spenders, earners, and bot farmers across the ecosystem.
                </p>
            </div>
            <WhaleTrackerPanel />
        </div>
    );
}
