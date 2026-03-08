function InventoryTable({ inventory, imageB64 }) {
    return (
        <div className="card">
            <h2>Fridge Inventory</h2>
            
            {/* Display the annotated image if it exists */}
            {imageB64 && (
                <div style={{ marginBottom: '16px' }}>
                    <img 
                        src={`data:image/jpeg;base64,${imageB64}`} 
                        style={{ width: '100%', borderRadius: '8px', border: '1px solid #334155' }} 
                        alt="Annotated Fridge" 
                    />
                </div>
            )}
            
            {/* Display empty state or the table */}
            {!inventory || inventory.length === 0 ? (
                <div className="empty-state">No scan yet. Click "Scan My Fridge" to start.</div>
            ) : (
                <table className="inventory-table">
                    <thead>
                        <tr>
                            <th>Item</th>
                            <th>Qty</th>
                            <th>Confidence</th>
                        </tr>
                    </thead>
                    <tbody>
                        {inventory.map((item, idx) => {
                            const conf = item.avg_confidence_pct;
                            // Determine color class based on confidence score
                            const confClass = conf >= 90 ? 'conf-high' : conf >= 80 ? 'conf-med' : 'conf-low';
                            
                            return (
                                <tr key={idx}>
                                    <td style={{ fontWeight: 500 }}>{item.item}</td>
                                    <td>{item.count}x</td>
                                    <td>
                                        <div className="confidence-bar">
                                            <div className={`confidence-fill ${confClass}`} style={{ width: `${conf}%` }}></div>
                                        </div>
                                        {conf.toFixed(1)}%
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            )}
        </div>
    );
}