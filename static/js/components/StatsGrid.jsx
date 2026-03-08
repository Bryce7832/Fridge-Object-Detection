function StatsGrid({ stats }) {
    return (
        <div className="card full-width">
            <h2>Scan Results</h2>
            <div className="stats-grid">
                <div className="stat-box">
                    <div className="stat-value">{stats.total}</div>
                    <div className="stat-label">Items Detected</div>
                </div>
                <div className="stat-box">
                    <div className="stat-value">{stats.unique}</div>
                    <div className="stat-label">Unique Items</div>
                </div>
                <div className="stat-box">
                    <div className="stat-value">{stats.removed}</div>
                    <div className="stat-label">Filtered Out</div>
                </div>
                <div className="stat-box">
                    <div className="stat-value">{stats.time}</div>
                    <div className="stat-label">Inference (ms)</div>
                </div>
            </div>
        </div>
    );
}