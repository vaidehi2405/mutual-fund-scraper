import React, { useEffect, useRef, useState } from 'react';

const EXAMPLES = [
  'Expense ratio of ICICI Bluechip',
  'ELSS lock-in',
  'Who manages ICICI Small Cap Fund?',
  'AUM of ICICI Flexi Cap Fund',
];

const formatTime = (date = new Date()) =>
  date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

const ChatHeader = ({ onClose, onNewChat }) => (
  <header className="flex items-start justify-between border-b border-slate-200 bg-slate-50 px-5 py-4">
    <div>
      <h2 className="text-base font-semibold tracking-tight text-slate-900">MF Assistant</h2>
      <p className="mt-0.5 text-xs text-slate-500">Facts only</p>
    </div>
    <div className="flex items-center gap-2">
      <button
        type="button"
        onClick={onNewChat}
        className="rounded-md px-2.5 py-1.5 text-xs font-medium text-slate-600 transition hover:bg-slate-100 hover:text-slate-800"
      >
        New chat
      </button>
      <button
        type="button"
        onClick={onClose}
        aria-label="Close assistant"
        className="rounded-md p-1.5 text-slate-500 transition hover:bg-slate-100 hover:text-slate-700"
      >
        <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path strokeLinecap="round" strokeLinejoin="round" d="M6 6l12 12M6 18L18 6" />
        </svg>
      </button>
    </div>
  </header>
);

const MessageBubble = ({ message }) => {
  const isUser = message.role === 'user';

  return (
    <article className={`flex ${isUser ? 'justify-end' : 'justify-start'} animate-fade-in`}>
      <div
        className={`max-w-[75%] rounded-xl px-3.5 py-2.5 text-sm leading-relaxed ${
          isUser
            ? 'bg-emerald-100 text-emerald-950'
            : 'border border-slate-200 bg-white text-slate-800 shadow-sm'
        }`}
      >
        <p className="whitespace-pre-wrap">{message.text}</p>
        <time className="mt-1.5 block text-[10px] text-slate-400">{message.timestamp}</time>
      </div>
    </article>
  );
};

const SuggestionChips = ({ items, onSelect }) => (
  <div className="-mx-1 flex gap-2 overflow-x-auto px-1 pb-1 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
    {items.map((item) => (
      <button
        key={item}
        type="button"
        onClick={() => onSelect(item)}
        className="shrink-0 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-600 transition hover:border-emerald-300 hover:bg-emerald-50 hover:text-emerald-700"
      >
        {item}
      </button>
    ))}
  </div>
);

const TypingIndicator = () => (
  <div className="flex justify-start animate-fade-in">
    <div className="flex items-center gap-1 rounded-xl border border-slate-200 bg-white px-3 py-2 shadow-sm">
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400 [animation-delay:0ms]" />
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400 [animation-delay:150ms]" />
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400 [animation-delay:300ms]" />
    </div>
  </div>
);

const ChatInput = ({ value, onChange, onSend, disabled }) => (
  <div className="sticky bottom-0 border-t border-slate-200 bg-white/95 px-4 pb-3 pt-2 backdrop-blur">
    <div className="flex items-center gap-2 rounded-full border border-slate-300 bg-white px-3 py-2 shadow-sm focus-within:border-emerald-400 focus-within:ring-2 focus-within:ring-emerald-100">
      <input
        type="text"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={(event) => event.key === 'Enter' && onSend()}
        placeholder="Ask about mutual funds..."
        className="w-full border-none bg-transparent text-sm text-slate-800 outline-none placeholder:text-slate-400"
        aria-label="Ask mutual fund question"
      />
      <button
        type="button"
        onClick={onSend}
        disabled={disabled}
        className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-emerald-600 text-white transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:bg-slate-300"
        aria-label="Send message"
      >
        <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path strokeLinecap="round" strokeLinejoin="round" d="M22 2L11 13" />
          <path strokeLinecap="round" strokeLinejoin="round" d="M22 2L15 22l-4-9-9-4 20-7z" />
        </svg>
      </button>
    </div>
    <p className="mt-2 text-center text-[10px] text-slate-400">
      Facts only. Not investment advice.
    </p>
  </div>
);

const ChatDrawer = ({ onClose }) => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
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

  const handleNewChat = () => {
    setMessages([]);
    setInput('');
  };

  const handleSend = async (draft) => {
    const query = (draft ?? input).trim();
    if (!query || isLoading || hasPii(query)) return;

    setMessages((prev) => [...prev, { id: `${Date.now()}-u`, role: 'user', text: query, timestamp: formatTime() }]);
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
      setMessages((prev) => [
        ...prev,
        {
          id: data.id || `${Date.now()}-b`,
          role: 'bot',
          text: data.text,
          timestamp: formatTime(),
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: `${Date.now()}-e`,
          role: 'bot',
          text: 'I could not fetch the latest fact right now. Please retry in a moment.',
          timestamp: formatTime(),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <aside
      role="dialog"
      aria-modal="true"
      aria-label="MF Assistant"
      className="fixed right-0 top-0 z-50 flex h-screen w-full animate-slide-in flex-col overflow-hidden rounded-none bg-white shadow-2xl sm:w-[380px] sm:rounded-l-3xl"
    >
      <ChatHeader onClose={onClose} onNewChat={handleNewChat} />

      <main ref={chatBodyRef} className="flex-1 space-y-4 overflow-y-auto bg-slate-50 px-4 py-4">
        {messages.length === 0 && (
          <section className="space-y-3 animate-fade-in">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Try asking</p>
            <SuggestionChips items={EXAMPLES} onSelect={handleSend} />
          </section>
        )}

        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}

        {isLoading && <TypingIndicator />}
      </main>

      <ChatInput value={input} onChange={setInput} onSend={() => handleSend()} disabled={!input.trim() || isLoading} />
    </aside>
  );
};

export default ChatDrawer;
