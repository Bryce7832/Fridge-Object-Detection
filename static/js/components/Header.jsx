function Header({ health, firebaseEnabled }) {
    return (
        <div className="header">
            <h1> Smart Fridge — <span>Team 18</span></h1>
            <div className="status-bar">
                <span><span className={`status-dot ${health.jetson}`}></span>Jetson Nano</span>
                <span><span className={`status-dot ${health.pi}`}></span>Raspberry Pi</span>
                <span>
                    <span className="status-dot" style={{ background: firebaseEnabled ? '#4ade80' : '#475569' }}></span>
                    Firebase: {firebaseEnabled ? 'Connected' : 'Not configured'}
                </span>
            </div>
        </div>
    );
}