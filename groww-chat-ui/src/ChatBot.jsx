import React, { useEffect, useMemo, useRef, useState } from 'react';
import './ChatBot.css';

const EXAMPLES = [
  'What is the expense ratio of ICICI Bluechip Fund?',
  'What is the lock-in period for ELSS?',
  'Who is the fund manager for Small Cap fund?',
];

const formatTime = (date = new Date()) =>
  date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

const TypingIndicator = () => (
  <div className="message-row bot">
    <div className="message-bubble bot-bubble typing" aria-label="Assistant is typing">
      <span />
      <span />
      <span />
    </div>
  </div>
);

const ChatBot = ({ onClose }) => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [piiError, setPiiError] = useState(false);

  const chatBodyRef = useRef(null);

  useEffect(() => {
    if (chatBodyRef.current) {
      chatBodyRef.current.scrollTo({ top: chatBodyRef.current.scrollHeight, behavior: 'smooth' });
    }
  }, [messages, isLoading]);

  const hasPii = (text) => {
    const lower = text.toLowerCase();
    return lower.includes('@') || lower.includes('aadhaar') || /\bpan\b/.test(lower) || /\d{10,}/.test(text);
  };

  const welcomeState = useMemo(
    () => ({
      title: 'Hi, I can help you with mutual fund info like NAV, expense ratio, returns, etc.',
      subtitle: 'Try one of these or ask your own question.',
    }),
    []
  );

  const handleSend = async (text) => {
    const query = (text ?? input).trim();
    if (!query || isLoading) return;

    if (hasPii(query)) {
      setPiiError(true);
      setInput('');
      setTimeout(() => setPiiError(false), 3000);
      return;
    }

    setErrorMessage('');

    const userMsg = {
      id: `${Date.now()}-user`,
      role: 'user',
      text: query,
      timestamp: formatTime(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
      });

      if (!response.ok) {
        throw new Error('Request failed');
      }

      const data = await response.json();
      const botMsg = {
        id: data.id || `${Date.now()}-bot`,
        role: 'bot',
        text: data.text,
        source_url: data.source_url,
        scraped_at: data.scraped_at,
        timestamp: formatTime(),
      };

      setMessages((prev) => [...prev, botMsg]);
    } catch {
      setErrorMessage('Unable to fetch response right now. Please try again.');
      setMessages((prev) => [
        ...prev,
        {
          id: `${Date.now()}-error`,
          role: 'error',
          text: 'I am having trouble connecting to data sources. Please retry in a moment.',
          timestamp: formatTime(),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <aside className="chatbot-drawer" role="dialog" aria-label="MF FAQ Assistant" aria-modal="true">
      <header className="chat-header">
        <div>
          <h1>MF FAQ Assistant</h1>
          <p>Powered by AI</p>
        </div>
        <button className="icon-button" onClick={onClose} aria-label="Close assistant">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </header>

      <main className="chat-body" ref={chatBodyRef}>
        {messages.length === 0 && (
          <section className="empty-state">
            <h2>{welcomeState.title}</h2>
            <p>{welcomeState.subtitle}</p>
            <div className="quick-actions">
              {EXAMPLES.map((example) => (
                <button key={example} className="suggestion-chip" onClick={() => handleSend(example)}>
                  {example}
                </button>
              ))}
            </div>
          </section>
        )}

        {messages.map((msg) => (
          <article key={msg.id} className={`message-row ${msg.role === 'user' ? 'user' : 'bot'}`}>
            <div className={`message-bubble ${msg.role === 'user' ? 'user-bubble' : msg.role === 'error' ? 'error-bubble' : 'bot-bubble'}`}>
              <p>{msg.text}</p>
              <time dateTime={new Date().toISOString()}>{msg.timestamp}</time>
            </div>

            {msg.role === 'bot' && msg.source_url && (
              <div className="message-actions">
                <a className="source-button" href={msg.source_url} target="_blank" rel="noreferrer noopener">
                  View source
                </a>
                {msg.scraped_at && <span className="meta-text">Updated: {msg.scraped_at.split('T')[0]}</span>}
              </div>
            )}
          </article>
        ))}

        {isLoading && <TypingIndicator />}
      </main>

      <footer className="chat-input-bar">
        {errorMessage && <div className="status-banner error">{errorMessage}</div>}
        {piiError && <div className="status-banner warning">Please do not enter personal information.</div>}
        <div className="input-shell">
          <input
            type="text"
            value={input}
            className="chat-input"
            placeholder="Ask about mutual funds…"
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={(event) => event.key === 'Enter' && handleSend()}
            aria-label="Ask your mutual fund question"
          />
          <button className="send-button" onClick={() => handleSend()} disabled={!input.trim() || isLoading} aria-label="Send message">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="22" y1="2" x2="11" y2="13" />
              <polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
          </button>
        </div>
      </footer>
    </aside>
  );
};

export default ChatBot;
