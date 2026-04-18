/* groww-chat-ui/src/ChatBot.jsx */
import React, { useState, useEffect, useRef } from 'react';
import './ChatBot.css';

const EXAMPLES = [
    "What is the expense ratio of ICICI Bluechip Fund?",
    "What is the lock-in period for ELSS?",
    "Who is the fund manager for Small Cap fund?"
];

const ChatBot = ({ onClose }) => {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [piiError, setPiiError] = useState(false);
    
    const chatBodyRef = useRef(null);

    // Auto-scroll to bottom on new messages
    useEffect(() => {
        if (chatBodyRef.current) {
            chatBodyRef.current.scrollTop = chatBodyRef.current.scrollHeight;
        }
    }, [messages, isLoading]);

    const hasPii = (text) => {
        const lower = text.toLowerCase();
        if (lower.includes('@')) return true;
        if (lower.includes('aadhaar')) return true;
        
        // Exact word 'pan'
        if (/\bpan\b/.test(lower)) return true;
        
        // 10+ digits
        if (/\d{10,}/.test(text)) return true;
        
        return false;
    };

    const handleSend = async (text) => {
        const query = text || input;
        if (!query.trim()) return;

        if (hasPii(query)) {
            setPiiError(true);
            setInput('');
            setTimeout(() => setPiiError(false), 3000);
            return;
        }

        const userMsg = {
            id: Date.now() + '-user',
            role: 'user',
            text: query,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        };

        setMessages(prev => [...prev, userMsg]);
        setInput('');
        setIsLoading(true);

        try {
            const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
            const response = await fetch(`${apiUrl}/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query })
            });

            if (!response.ok) throw new Error('Network response was not ok');

            const data = await response.json();
            
            const botMsg = {
                id: data.id,
                role: data.role,
                text: data.text,
                source_url: data.source_url,
                scraped_at: data.scraped_at,
                timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
            };

            setMessages(prev => [...prev, botMsg]);
        } catch (error) {
            setMessages(prev => [...prev, {
                id: Date.now() + '-error',
                role: 'error',
                text: 'Something went wrong. Please try again.',
                timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
            }]);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="chatbot-container">
            {/* Header */}
            <header className="chat-header">
                <div className="header-left">
                    <div className="icon-circle">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#00B386" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                            <circle cx="12" cy="12" r="10"></circle>
                            <line x1="12" y1="16" x2="12" y2="12"></line>
                            <line x1="12" y1="8" x2="12.01" y2="8"></line>
                        </svg>
                    </div>
                    <div className="header-info">
                        <h1>MF FAQ Assistant</h1>
                        <p>Groww · Facts only · No investment advice</p>
                    </div>
                </div>
                <div className="header-right">
                    <div className="groww-badge">GROWW</div>
                    <button className="minimize-button" onClick={onClose} aria-label="Minimize chat">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                            <line x1="18" y1="6" x2="6" y2="18"></line>
                            <line x1="6" y1="6" x2="18" y2="18"></line>
                        </svg>
                    </button>
                </div>
            </header>

            {/* Disclaimer Bar */}
            <div className="disclaimer-bar">
                Facts only. No investment advice. Always consult a SEBI-registered advisor.
            </div>

            {/* Chat Body */}
            <main className="chat-body" ref={chatBodyRef}>
                {messages.length === 0 && (
                    <div className="examples-section">
                        <p className="examples-label">Try asking</p>
                        {EXAMPLES.map((ex, i) => (
                            <button key={i} className="pill-button" onClick={() => handleSend(ex)}>
                                <span className="dot"></span>
                                {ex}
                            </button>
                        ))}
                    </div>
                )}

                {messages.map((msg, idx) => (
                    <React.Fragment key={msg.id}>
                        {/* Timestamp Label (Simplified: show every few messages or start of group) */}
                        {idx === 0 && <div className="timestamp-label">Today</div>}
                        
                        <div className={`message-wrapper ${msg.role === 'user' ? 'user-wrapper' : 'bot-wrapper'}`}>
                            <div className={`message-bubble ${msg.role}-bubble`}>
                                {msg.text}
                            </div>
                            
                            {msg.role === 'bot' && msg.source_url && (
                                <div style={{ display: 'flex', flexDirection: 'column' }}>
                                    <a href={msg.source_url} target="_blank" rel="noreferrer" className="source-chip">
                                        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                                            <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path>
                                            <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path>
                                        </svg>
                                        Click here to view source
                                    </a>
                                    {msg.scraped_at && (
                                        <div className="last-updated">
                                            Last updated from sources: {msg.scraped_at.split('T')[0]}
                                        </div>
                                    )}
                                </div>
                            )}

                            {msg.role === 'refusal' && (
                                <div className="last-updated" style={{ marginTop: '8px' }}>
                                    Learn more: <a href="https://www.amfiindia.com/investor-corner" target="_blank" rel="noreferrer" style={{color: '#888'}}>amfiindia.com/investor-corner</a>
                                </div>
                            )}
                        </div>
                    </React.Fragment>
                ))}

                {isLoading && (
                    <div className="message-wrapper bot-wrapper">
                        <div className="typing-dots">
                            <div className="dot-anim"></div>
                            <div className="dot-anim"></div>
                            <div className="dot-anim"></div>
                        </div>
                    </div>
                )}
            </main>

            {/* Input Area */}
            <div className="input-area">
                {piiError && <div className="pii-warning">Please do not enter personal information.</div>}
                <input 
                    type="text" 
                    className="chat-input"
                    placeholder="Ask a factual question about MF schemes…"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && handleSend()}
                />
                <button className="send-button" onClick={() => handleSend()}>
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                        <line x1="22" y1="2" x2="11" y2="13"></line>
                        <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                    </svg>
                </button>
            </div>
        </div>
    );
};

export default ChatBot;
