import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import MainLayout from './components/MainLayout';
import ChatArea from './components/ChatArea';
import { useWebSocket } from './hooks/useWebSocket';
import AdminPage from './pages/AdminPage';
import SettingsPage from './pages/SettingsPage';
import { useStudio, StudioProvider } from './context/StudioContext';
import ReviewPanel from './components/panels/ReviewPanel';

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

const ReviewPage = () => (
  <div style={{ height: '100vh', width: '100%', background: '#0a0a0a' }}>
    <ReviewPanel
      projectId="demo"
      projectName="CME Grant Review Demo"
      documentContent="<h1>CME Grant Proposal</h1><p>This is a sample document for review. You can select any text to add comments or suggestions.</p><h2>Background</h2><p>The proposed program addresses gaps in cardiology training for primary care physicians.</p><h2>Objectives</h2><ul><li>Improve diagnostic accuracy</li><li>Reduce referral delays</li><li>Enhance patient outcomes</li></ul>"
      slaDeadline={new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString()}
      onSubmitReview={(data) => { console.log('Review submitted:', data); alert('Review submitted: ' + data.decision); }}
      onClose={() => window.history.back()}
    />
  </div>
);

const getWebSocketUrl = () => {
  if (import.meta.env.VITE_ORCHESTRATOR_URL) {
    return import.meta.env.VITE_ORCHESTRATOR_URL;
  }
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${window.location.host}/ws`;
};

const WS_URL = getWebSocketUrl();

const AppInner = () => {
  const {
    messages,
    isConnected,
    isProcessing,
    streamingContent,
    agentEvents,
    validationResult,
    sendMessage: wsSendMessage,
    clearMessages,
    addMessage,
    setIsProcessing
  } = useWebSocket(WS_URL);

  const { selectedModel, theme } = useStudio();

  const handleSendMessage = async (content) => {
    if (selectedModel && selectedModel.type === 'ollama') {
      addMessage({ role: 'user', content });
      setIsProcessing(true);
      try {
        const response = await fetch('http://10.0.0.251:8011/api/ollama/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ model: selectedModel.name, message: content })
        });
        if (response.ok) {
          const data = await response.json();
          addMessage({ role: 'assistant', content: data.response });
        } else {
          addMessage({ role: 'assistant', content: 'Error: Could not get response from Ollama' });
        }
      } catch (error) {
        addMessage({ role: 'assistant', content: `Error: ${error.message}` });
      } finally {
        setIsProcessing(false);
      }
    } else {
      wsSendMessage(content, {
        model: selectedModel?.id || 'gpt-4o',
        theme,
        mode: 'auto'
      });
    }
  };

  return (
    <Routes>
      <Route path="/" element={<MainLayout agentEvents={agentEvents} validationResult={validationResult} />}>
        <Route index element={<Navigate to="/chat" replace />} />
        <Route path="chat" element={
          <ChatArea
            messages={messages}
            onSendMessage={handleSendMessage}
            isProcessing={isProcessing}
            streamingContent={streamingContent}
          />
        } />
        <Route path="admin" element={<AdminPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="walkthrough" element={<WalkthroughPage />} />
      </Route>
      <Route path="/review" element={<ReviewPage />} />
    </Routes>
  );
};

function App() {
  return (
    <StudioProvider>
      <BrowserRouter>
        <AppInner />
      </BrowserRouter>
    </StudioProvider>
  );
}

export default App;
