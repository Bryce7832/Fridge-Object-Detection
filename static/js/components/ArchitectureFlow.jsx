function ArchitectureFlow({ activeNode }) {
    return (
        <div className="card full-width">
            <div className="arch-flow">
                <div className={`arch-node ${activeNode === 'pc' ? 'active' : ''}`}>
                    💻 PC (Fog)<br/>
                    <small>You are here</small>
                </div>
                <span className="arch-arrow">➡</span>
                <div className={`arch-node ${activeNode === 'pi' ? 'active' : ''}`}>
                    🍓 Raspberry Pi<br/>
                    <small>Filter ≥75%</small>
                </div>
                <span className="arch-arrow">➡</span>
                <div className={`arch-node ${activeNode === 'jetson' ? 'active' : ''}`}>
                    📷 Jetson Nano<br/>
                    <small>YOLOv7-tiny</small>
                </div>
                <span className="arch-arrow">➡</span>
                <div className={`arch-node ${activeNode === 'camera' ? 'active' : ''}`}>
                    📸 Webcam<br/>
                    <small>Capture</small>
                </div>
            </div>
        </div>
    );
}