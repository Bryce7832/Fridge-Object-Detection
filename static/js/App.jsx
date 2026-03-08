var { useState, useEffect } = React;

function App() {
    const [health, setHealth] = useState({ jetson: 'unknown', pi: 'unknown' });
    const [inventory, setInventory] = useState([]);
    const [imageB64, setImageB64] = useState(null);
    const [stats, setStats] = useState({ total: '-', unique: '-', removed: '-', time: '-' });
    
    const [isScanning, setIsScanning] = useState(false);
    const [scanStatus, setScanStatus] = useState('Press the button to scan your fridge');
    
    const [firebaseStatus, setFirebaseStatus] = useState('');
    const [isPushing, setIsPushing] = useState(false);

    const firebaseEnabled = window.APP_CONFIG.firebaseEnabled;

    const checkHealth = async () => {
        try {
            const res = await fetch('/api/health');
            const data = await res.json();
            setHealth({ jetson: data.jetson === 'online' ? 'online' : 'offline', pi: data.pi === 'online' ? 'online' : 'offline' });
        } catch (e) {
            console.log('Health check failed:', e);
        }
    };

    useEffect(() => {
        checkHealth();
        const interval = setInterval(checkHealth, 30000);
        return () => clearInterval(interval);
    }, []);

    const scanFridge = async () => {
        setIsScanning(true);
        setFirebaseStatus('');
        setScanStatus('Sending request via Raspberry Pi to Jetson Nano...');

        try {
            const res = await fetch('/api/scan');
            const data = await res.json();

            if (data.error) {
                setScanStatus(`Error: ${data.error}`);
            } else {
                setInventory(data.inventory_summary || []);
                setImageB64(data.annotated_image_base64 || null);
                setStats({
                    total: data.total_items_detected || 0,
                    unique: data.unique_items || 0,
                    removed: data.items_removed || 0,
                    time: data.inference_time_ms || 0
                });
                setScanStatus(`Scan complete at ${data.report_timestamp}`);
            }
        } catch (e) {
            setScanStatus('Connection error: Cannot reach Raspberry Pi.');
        } finally {
            setIsScanning(false);
        }
    };

    const pushToFirebase = async () => {
        setIsPushing(true);
        setFirebaseStatus('Pushing to Firebase...');
        try {
            const res = await fetch('/api/firebase-push', { method: 'POST' });
            const data = await res.json();
            if (data.success) {
                setFirebaseStatus(`Pushed to Firebase at ${new Date().toLocaleTimeString()}`);
            } else {
                setFirebaseStatus(data.error || 'Firebase push failed.');
            }
        } catch (e) {
            setFirebaseStatus(`Error: ${e.message}`);
        } finally {
            setIsPushing(false);
        }
    };

    return (
        <div>
            <Header health={health} firebaseEnabled={firebaseEnabled} />
            
            <div className="container">
                {/* Top Row: Full Width Scan Button */}
                <div className="card full-width scan-section">
                    <button className="scan-btn" onClick={scanFridge} disabled={isScanning}>
                        {isScanning ? <span><span className="loading-spinner"></span> Scanning...</span> : "🔍 Scan My Fridge"}
                    </button>
                    <div className="scan-status">{scanStatus}</div>
                </div>

                {/* Second Row: Full Width Stats Grid */}
                <StatsGrid stats={stats} />

                {/* Bottom Row Left: Inventory & Firebase */}
                <div>
                    <InventoryTable inventory={inventory} imageB64={imageB64} />
                    <div className="card" style={{ marginTop: '24px' }}>
                        <button className="firebase-btn" onClick={pushToFirebase} disabled={isScanning || isPushing || inventory.length === 0}>
                            ☁ Push to Firebase
                        </button>
                        <div className="firebase-status">{firebaseStatus}</div>
                    </div>
                </div>

                {/* Bottom Row Right: Recipe Assistant */}
                <div>
                    <RecipeAssistant />
                </div>
            </div>
        </div>
    );
}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);