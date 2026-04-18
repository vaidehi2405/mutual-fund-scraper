import React, { useState, useEffect } from 'react';
import ChatBot from './ChatBot';
import './App.css';

function App() {
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [showDiscovery, setShowDiscovery] = useState(false);

  useEffect(() => {
    // Check if tooltip has been shown in this session
    const tooltipSeen = sessionStorage.getItem('chatbotTooltipSeen');
    if (!tooltipSeen && !isChatOpen) {
      // Delay slightly for smooth landing
      const timer = setTimeout(() => setShowDiscovery(true), 1200);
      return () => clearTimeout(timer);
    }
  }, [isChatOpen]);

  const handleOpenChat = () => {
    setIsChatOpen(true);
    handleDismissDiscovery();
  };

  const handleDismissDiscovery = () => {
    setShowDiscovery(false);
    sessionStorage.setItem('chatbotTooltipSeen', 'true');
  };

  return (
    <div className="App">
      <div className="background-overlay"></div>
      
      {/* Discovery Experience Overlay */}
      {showDiscovery && (
        <div className="discovery-overlay" onClick={handleDismissDiscovery}>
          <div className="discovery-tooltip" onClick={(e) => e.stopPropagation()}>
            <button className="tooltip-close" onClick={handleDismissDiscovery}>&times;</button>
            <p>Need help choosing funds? Chat with our AI assistant!</p>
            <div className="tooltip-arrow"></div>
          </div>
        </div>
      )}

      {/* Floating Action Button */}
      {!isChatOpen && (
        <button 
          className={`fab ${showDiscovery ? 'highlighted' : ''}`} 
          onClick={handleOpenChat}
          aria-label="Open AI Assistant"
        >
          <svg className="robot-icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect x="5" y="8" width="14" height="11" rx="2" stroke="white" strokeWidth="2" />
            <path d="M9 13H9.01M15 13H15.01" stroke="white" strokeWidth="2.5" strokeLinecap="round" />
            <path d="M10 16C10 16 11 17 12 17C13 17 14 16 14 16" stroke="white" strokeWidth="1.5" strokeLinecap="round" />
            <path d="M12 8V5M12 5L10 3M12 5L14 3" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            <rect x="3" y="11" width="2" height="5" rx="1" fill="white" />
            <rect x="19" y="11" width="2" height="5" rx="1" fill="white" />
          </svg>
        </button>
      )}

      {/* ChatBot Modal */}
      {isChatOpen && (
        <div className="chatbot-drawer-shell" role="presentation">
          <button className="chatbot-backdrop" aria-label="Close assistant" onClick={() => setIsChatOpen(false)} />
          <div className="chatbot-modal">
            <ChatBot onClose={() => setIsChatOpen(false)} />
          </div>
        </div>
      )}

      {/* Footer Ribbon with Scrolling Marquee */}
      <footer className="footer-ribbon">
        <div className="ribbon-label">This chatbot works for</div>
        <div className="marquee-container">
          <div className="marquee-content">
            <span className="fund-item">ICICI Prudential ELSS Tax Saver Fund</span>
            <span className="divider"></span>
            <span className="fund-item">ICICI Prudential Flexicap Fund</span>
            <span className="divider"></span>
            <span className="fund-item">ICICI Prudential Bluechip Fund</span>
            <span className="divider"></span>
            <span className="fund-item">ICICI Prudential Smallcap Fund</span>
            <span className="divider"></span>
            <span className="fund-item">ICICI Prudential Midcap Fund</span>
            <span className="divider"></span>
            {/* Duplicated for seamless loop */}
            <span className="fund-item">ICICI Prudential ELSS Tax Saver Fund</span>
            <span className="divider"></span>
            <span className="fund-item">ICICI Prudential Flexicap Fund</span>
            <span className="divider"></span>
            <span className="fund-item">ICICI Prudential Bluechip Fund</span>
            <span className="divider"></span>
            <span className="fund-item">ICICI Prudential Smallcap Fund</span>
            <span className="divider"></span>
            <span className="fund-item">ICICI Prudential Midcap Fund</span>
            <span className="divider"></span>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
