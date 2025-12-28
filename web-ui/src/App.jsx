import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import MainLayout from './components/MainLayout';
import ChatArea from './components/ChatArea';
import { useWebSocket } from './hooks/useWebSocket';
import AdminPage from './pages/AdminPage';
import SettingsPage from './pages/SettingsPage';
import { useStudio, StudioProvider } from './context/StudioContext';

const WalkthroughPage = () => (
  <div style={{ padding: 'var(--space-8)', color: 'var(--color-text)', maxWidth: '60rem', margin: '0 auto' }}>
    <h1 style={{ color: 'var(--color-dhg-primary)' }}>System Walkthrough</h1>
    <p style={{ color: 'var(--color-text-muted)' }}>The walkthrough documentation is being updated. Please refer to `walkthrough.md` in the repository for now.</p>
    <div style={{ marginTop: 'var(--space-8)', padding: 'var(--space-6)', background: 'var(--glass-bg)', borderRadius: 'var(--radius-xl)', border: '1px solid var(--glass-border)' }}>
      <h3>Key Features</h3>
      <ul>
        <li>Triple-Column Cockpit Layout</li>
        <li>Intelligent Model Selection</li>
        <li>Real-time Prompt Refinement</li>
        <li>Advanced Admin Telemetry</li>
      </ul>
    </div>
  </div>
);

// Orchestrator runs on 8011 in docker-compose.
// Use environment variable if available, otherwise fallback to localhost default
const WS_URL = import.meta.env.VITE_ORCHESTRATOR_URL || "ws://localhost:8011/ws";

const ChatRoute = () => {
  const { messages, isConnected, isProcessing, sendMessage: wsSendMessage, clearMessages } = useWebSocket(WS_URL);
  const { selectedModel, theme } = useStudio();

  const handleSendMessage = (content) => {
    wsSendMessage(content, {
      model: selectedModel || 'gpt-4o', // Default fallback
      theme,
      mode: 'auto' // Default compliance mode
    });
  };

  return (
    <ChatArea
      messages={messages}
      onSendMessage={handleSendMessage}
      isProcessing={isProcessing}
    />
  );
};


function App() {
  return (
    <StudioProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<MainLayout />}>
            <Route index element={<Navigate to="/chat" replace />} />
            <Route path="chat" element={<ChatRoute />} />
            <Route path="admin" element={<AdminPage />} />
            <Route path="settings" element={<SettingsPage />} />
            <Route path="walkthrough" element={<WalkthroughPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </StudioProvider>
  );
}

export default App;
