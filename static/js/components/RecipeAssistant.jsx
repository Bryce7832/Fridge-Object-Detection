var { useState, useEffect, useRef } = React;

function RecipeAssistant() {
    const [messages, setMessages] = useState([
        { role: 'assistant', text: "Hi! Scan your fridge first, then ask me things like:\n• Can I make pasta?\n• What can I cook with what I have?" }
    ]);
    const [input, setInput] = useState('');
    const [isThinking, setIsThinking] = useState(false);
    const messagesEndRef = useRef(null);

    useEffect(() => {
        if (messagesEndRef.current) {
            messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
        }
    }, [messages, isThinking]);

    const askLLM = async () => {
        if (!input.trim()) return;
        
        const userMsg = input;
        setInput('');
        setMessages(prev => [...prev, { role: 'user', text: userMsg }]);
        setIsThinking(true);

        try {
            const res = await fetch('/api/ask', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question: userMsg })
            });
            const data = await res.json();
            setMessages(prev => [...prev, { role: 'assistant', text: data.answer || 'No response received.' }]);
        } catch (e) {
            setMessages(prev => [...prev, { role: 'assistant', text: 'Error connecting to LLM service.' }]);
        } finally {
            setIsThinking(false);
        }
    };

    return (
        <div className="card">
            <h2>👨‍🍳 Recipe Assistant</h2>
            <div className="chat-container">
                <div className="chat-messages">
                    {messages.map((msg, idx) => (
                        <div key={idx} className={`chat-msg ${msg.role === 'user' ? 'chat-user' : 'chat-assistant'}`}>
                            {msg.text.split('\n').map((line, i) => <React.Fragment key={i}>{line}<br/></React.Fragment>)}
                        </div>
                    ))}
                    {isThinking && (
                        <div className="chat-msg chat-assistant">
                            <span className="loading-spinner"></span> Thinking...
                        </div>
                    )}
                    <div ref={messagesEndRef} />
                </div>
                <div className="chat-input-row">
                    <input 
                        type="text" 
                        className="chat-input" 
                        placeholder="Ask about recipes..." 
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyPress={(e) => e.key === 'Enter' && askLLM()}
                    />
                    <button className="chat-send" onClick={askLLM} disabled={isThinking}>Ask</button>
                </div>
            </div>
        </div>
    );
}