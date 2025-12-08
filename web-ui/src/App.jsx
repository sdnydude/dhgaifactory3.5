import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import MainLayout from './components/MainLayout';
import ChatArea from './components/ChatArea';
import { useWebSocket } from './hooks/useWebSocket';
import AdminPage from './pages/AdminPage';
import SettingsPage from './pages/SettingsPage';

// Orchestrator runs on 8011 in docker-compose.
// Use environment variable if available, otherwise fallback to localhost default
const WS_URL = import.meta.env.VITE_ORCHESTRATOR_URL || "ws://localhost:8011/ws";

const ChatRoute = () => {
  const { messages, isConnected, isProcessing, sendMessage, clearMessages } = useWebSocket(WS_URL);

  // Pass disconnected status down if needed, or handle globally
  return (
    <ChatArea
      messages={messages}
      onSendMessage={sendMessage}
      isProcessing={isProcessing}
    />
  );
};

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<Navigate to="/chat" replace />} />
          <Route path="chat" element={<ChatRoute />} />
          <Route path="admin" element={<AdminPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
