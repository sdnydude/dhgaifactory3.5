// DHG AI Factory - Main App Layout
// Three-panel layout: Chat/Status | Main Content | Results/Validation

import React, { useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  PanelLeft, 
  PanelRight, 
  Settings, 
  Activity,
  Home,
  Plus,
  History,
  Wifi,
  WifiOff,
  Menu
} from 'lucide-react';
import { cn } from './lib/utils';
import { useAppStore, selectUI, selectIsConnected } from './store/useAppStore';
import { useWebSocket, WebSocketProvider } from './hooks/useAgentWebSocket';

// Components
import ChatPanel from './components/ChatPanel';
import AgentStatusPanel from './components/AgentStatusPanel';
import ContentPreviewPanel from './components/ContentPreviewPanel';
import RequestForm from './components/RequestForm';
import UserSettings from './components/UserSettings';
import AdminSettings from './components/AdminSettings';

// ============================================================================
// HEADER COMPONENT
// ============================================================================

const Header: React.FC = () => {
  const isConnected = useAppStore(selectIsConnected);
  const { leftPanelOpen, rightPanelOpen, activeView } = useAppStore(selectUI);
  const toggleLeftPanel = useAppStore(state => state.toggleLeftPanel);
  const toggleRightPanel = useAppStore(state => state.toggleRightPanel);
  const setActiveView = useAppStore(state => state.setActiveView);
  
  return (
    <header className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-4 sticky top-0 z-50">
      {/* Left Section */}
      <div className="flex items-center gap-4">
        {/* Logo */}
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-gradient-to-br from-blue-600 to-blue-800 rounded-lg flex items-center justify-center">
            <span className="text-white font-bold text-sm">AI</span>
          </div>
          <div>
            <h1 className="text-lg font-bold text-gray-900 leading-none">DHG AI Factory</h1>
            <p className="text-[10px] text-gray-500 uppercase tracking-wide">CME Generation System</p>
          </div>
        </div>
        
        {/* Navigation */}
        <nav className="hidden md:flex items-center gap-1 ml-8">
          {[
            { id: 'dashboard', label: 'Dashboard', icon: Home },
            { id: 'generate', label: 'Generate', icon: Plus },
            { id: 'history', label: 'History', icon: History },
            { id: 'settings', label: 'Settings', icon: Settings },
            { id: 'admin', label: 'Admin', icon: Settings }
          ].map(item => (
            <button
              key={item.id}
              onClick={() => setActiveView(item.id as typeof activeView)}
              className={cn(
                'flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                activeView === item.id
                  ? 'bg-blue-50 text-blue-700'
                  : 'text-gray-600 hover:bg-gray-100'
              )}
            >
              <item.icon className="w-4 h-4" />
              {item.label}
            </button>
          ))}
        </nav>
      </div>
      
      {/* Right Section */}
      <div className="flex items-center gap-3">
        {/* Connection Status */}
        <div className={cn(
          'flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium',
          isConnected 
            ? 'bg-green-100 text-green-700' 
            : 'bg-red-100 text-red-700'
        )}>
          {isConnected ? (
            <Wifi className="w-3 h-3" />
          ) : (
            <WifiOff className="w-3 h-3" />
          )}
          {isConnected ? 'Connected' : 'Disconnected'}
        </div>
        
        {/* CME Mode Badge */}
        <div className="px-3 py-1.5 bg-green-100 text-green-800 rounded-full text-xs font-semibold">
          CME MODE
        </div>
        
        {/* Panel Toggles */}
        <div className="flex items-center gap-1 border-l border-gray-200 pl-3">
          <button
            onClick={toggleLeftPanel}
            className={cn(
              'p-2 rounded-lg transition-colors',
              leftPanelOpen ? 'bg-blue-100 text-blue-600' : 'text-gray-400 hover:bg-gray-100'
            )}
            title={leftPanelOpen ? 'Hide left panel' : 'Show left panel'}
          >
            <PanelLeft className="w-5 h-5" />
          </button>
          <button
            onClick={toggleRightPanel}
            className={cn(
              'p-2 rounded-lg transition-colors',
              rightPanelOpen ? 'bg-blue-100 text-blue-600' : 'text-gray-400 hover:bg-gray-100'
            )}
            title={rightPanelOpen ? 'Hide right panel' : 'Show right panel'}
          >
            <PanelRight className="w-5 h-5" />
          </button>
        </div>
        
        {/* User Avatar */}
        <button className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center">
          <span className="text-sm font-medium text-gray-600">SW</span>
        </button>
      </div>
    </header>
  );
};

// ============================================================================
// LEFT PANEL COMPONENT
// ============================================================================

const LeftPanel: React.FC = () => {
  const { leftPanelOpen, leftPanelWidth } = useAppStore(selectUI);
  
  return (
    <AnimatePresence>
      {leftPanelOpen && (
        <motion.aside
          initial={{ width: 0, opacity: 0 }}
          animate={{ width: leftPanelWidth, opacity: 1 }}
          exit={{ width: 0, opacity: 0 }}
          transition={{ duration: 0.2 }}
          className="h-full bg-gray-50 border-r border-gray-200 flex flex-col overflow-hidden"
        >
          {/* Chat Section */}
          <div className="flex-1 min-h-0">
            <ChatPanel className="h-full" />
          </div>
          
          {/* Agent Status Section */}
          <div className="border-t border-gray-200">
            <AgentStatusPanel compact />
          </div>
        </motion.aside>
      )}
    </AnimatePresence>
  );
};

// ============================================================================
// RIGHT PANEL COMPONENT
// ============================================================================

const RightPanel: React.FC = () => {
  const { rightPanelOpen, rightPanelWidth } = useAppStore(selectUI);
  
  return (
    <AnimatePresence>
      {rightPanelOpen && (
        <motion.aside
          initial={{ width: 0, opacity: 0 }}
          animate={{ width: rightPanelWidth, opacity: 1 }}
          exit={{ width: 0, opacity: 0 }}
          transition={{ duration: 0.2 }}
          className="h-full bg-white border-l border-gray-200 overflow-hidden"
        >
          <ContentPreviewPanel className="h-full" />
        </motion.aside>
      )}
    </AnimatePresence>
  );
};

// ============================================================================
// MAIN CONTENT AREA
// ============================================================================

const MainContent: React.FC = () => {
  const { activeView } = useAppStore(selectUI);
  
  return (
    <main className="flex-1 overflow-y-auto bg-white">
      <div className="max-w-4xl mx-auto p-8">
        {activeView === 'dashboard' && <DashboardView />}
        {activeView === 'generate' && <GenerateView />}
        {activeView === 'history' && <HistoryView />}
        {activeView === 'settings' && <UserSettings />}
        {activeView === 'admin' && <AdminSettings />}
      </div>
    </main>
  );
};

// ============================================================================
// VIEW COMPONENTS
// ============================================================================

const DashboardView: React.FC = () => {
  const setActiveView = useAppStore(state => state.setActiveView);
  
  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Welcome back, Stephen</h2>
        <p className="text-gray-600 mt-1">Ready to generate CME content?</p>
      </div>
      
      {/* Quick Stats */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: 'Generated Today', value: '3', color: 'blue' },
          { label: 'Total This Week', value: '12', color: 'green' },
          { label: 'Pending Review', value: '2', color: 'amber' },
          { label: 'Success Rate', value: '98%', color: 'purple' }
        ].map(stat => (
          <div 
            key={stat.label}
            className="p-4 bg-white rounded-xl border border-gray-200 hover:shadow-md transition-shadow"
          >
            <p className="text-sm text-gray-500">{stat.label}</p>
            <p className={cn(
              'text-3xl font-bold mt-1',
              stat.color === 'blue' ? 'text-blue-600' :
              stat.color === 'green' ? 'text-green-600' :
              stat.color === 'amber' ? 'text-amber-600' :
              'text-purple-600'
            )}>
              {stat.value}
            </p>
          </div>
        ))}
      </div>
      
      {/* Quick Actions */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h3>
        <div className="grid grid-cols-3 gap-4">
          {[
            { 
              label: 'Generate Needs Assessment', 
              description: 'Create educational gap analysis',
              icon: '📊'
            },
            { 
              label: 'Create Curriculum', 
              description: 'Build learning objectives',
              icon: '📚'
            },
            { 
              label: 'Grant Development', 
              description: 'Develop grant proposals',
              icon: '📝'
            }
          ].map(action => (
            <button
              key={action.label}
              onClick={() => setActiveView('generate')}
              className="p-6 bg-gray-50 rounded-xl border border-gray-200 text-left hover:bg-blue-50 hover:border-blue-200 transition-colors group"
            >
              <span className="text-3xl mb-3 block">{action.icon}</span>
              <h4 className="font-semibold text-gray-900 group-hover:text-blue-700">
                {action.label}
              </h4>
              <p className="text-sm text-gray-500 mt-1">{action.description}</p>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};

const GenerateView: React.FC = () => (
  <div className="space-y-6">
    <div>
      <h2 className="text-2xl font-bold text-gray-900">Generate CME Content</h2>
      <p className="text-gray-600 mt-1">Fill out the form below to generate compliant medical education content</p>
    </div>
    
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <RequestForm />
    </div>
  </div>
);

const HistoryView: React.FC = () => {
  const history = useAppStore(state => state.history);
  
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Request History</h2>
        <p className="text-gray-600 mt-1">View and manage your previous content requests</p>
      </div>
      
      {history.length === 0 ? (
        <div className="text-center py-12 bg-gray-50 rounded-xl">
          <History className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <p className="text-gray-500">No requests yet. Generate your first content!</p>
        </div>
      ) : (
        <div className="space-y-4">
          {history.map(item => (
            <div 
              key={item.id}
              className="p-4 bg-white rounded-xl border border-gray-200 hover:shadow-md transition-shadow"
            >
              <div className="flex items-start justify-between">
                <div>
                  <h4 className="font-semibold text-gray-900">{item.topic}</h4>
                  <p className="text-sm text-gray-500 mt-1">
                    {item.task_type} • {new Date(item.created_at).toLocaleDateString()}
                  </p>
                </div>
                <span className={cn(
                  'px-2 py-1 rounded text-xs font-medium',
                  item.status === 'complete' ? 'bg-green-100 text-green-700' :
                  item.status === 'failed' ? 'bg-red-100 text-red-700' :
                  'bg-amber-100 text-amber-700'
                )}>
                  {item.status}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

// ============================================================================
// FOOTER COMPONENT
// ============================================================================

const Footer: React.FC = () => {
  const isConnected = useAppStore(selectIsConnected);
  const currentRequest = useAppStore(state => state.currentRequest);
  
  return (
    <footer className="h-12 bg-gray-50 border-t border-gray-200 flex items-center justify-between px-4 text-xs">
      <div className="flex items-center gap-4">
        {/* Connection Status */}
        <div className="flex items-center gap-2">
          <div className={cn(
            'w-2 h-2 rounded-full',
            isConnected ? 'bg-green-500' : 'bg-red-500'
          )} />
          <span className="text-gray-600">
            {isConnected ? 'WebSocket Connected' : 'WebSocket Disconnected'}
          </span>
        </div>
        
        {/* Current Request Status */}
        {currentRequest && (
          <div className="flex items-center gap-2 text-gray-600">
            <Activity className="w-3 h-3" />
            <span>Request: {currentRequest.request_id.slice(0, 8)}...</span>
            <span className="text-blue-600 font-medium">{currentRequest.progress}%</span>
          </div>
        )}
      </div>
      
      <div className="text-gray-400">
        DHG AI Factory v1.0.0 • © 2025 Digital Harmony Group
      </div>
    </footer>
  );
};

// ============================================================================
// APP INNER (with WebSocket connection)
// ============================================================================


const AppInner: React.FC = () => {
  // No longer directly calling useAgentWebSocket - using context instead
  const { connectionState } = useWebSocket();
  
  // Auto-connect happens in WebSocketProvider
  
  return (
    <div className="h-screen flex flex-col bg-gray-100">
      <Header />
      
      <div className="flex-1 flex overflow-hidden">
        <LeftPanel />
        <MainContent />
        <RightPanel />
      </div>
      
      <Footer />
    </div>
  );
};


// ============================================================================
// MAIN APP (with WebSocket handlers)
// ============================================================================

const App: React.FC = () => {
  const setConnected = useAppStore(state => state.setConnected);
  const setSessionId = useAppStore(state => state.setSessionId);
  const updateAgentStatus = useAppStore(state => state.updateAgentStatus);
  const addAgentLog = useAppStore(state => state.addAgentLog);
  const appendContentChunk = useAppStore(state => state.appendContentChunk);
  const setCurrentContent = useAppStore(state => state.setCurrentContent);
  const setValidationResult = useAppStore(state => state.setValidationResult);
  const addMessage = useAppStore(state => state.addMessage);
  const setTyping = useAppStore(state => state.setTyping);
  
  const handlers = {
    onConnected: () => {
      setConnected(true);
      console.log('[App] WebSocket connected');
    },
    onDisconnected: () => {
      setConnected(false);
      console.log('[App] WebSocket disconnected');
    },
    onAgentStatus: (payload) => {
      updateAgentStatus(payload);
    },
    onAgentLog: (payload) => {
      addAgentLog(payload.agent_id, {
        id: `log_${Date.now()}`,
        timestamp: new Date().toISOString(),
        level: payload.level,
        message: payload.message,
        data: payload.data
      });
    },
    onContentChunk: (payload) => {
      appendContentChunk(payload);
    },
    onContentComplete: (payload) => {
      setCurrentContent({
        id: payload.content_id,
        request_id: '',
        title: payload.title,
        content: payload.content,
        format: payload.format,
        sections: [],
        metadata: {
          word_count: payload.metadata.word_count,
          reference_count: payload.metadata.reference_count,
          generation_time_ms: payload.metadata.generation_time_ms,
          compliance_mode: payload.metadata.compliance_mode,
          moore_levels: payload.metadata.moore_levels_addressed,
          target_audience: '',
          topic: ''
        },
        created_at: new Date().toISOString()
      });
    },
    onValidationComplete: (payload) => {
      setValidationResult({
        status: payload.overall_status,
        checks: payload.checks,
        violations: payload.violations,
        warnings: payload.warnings,
        validated_at: new Date().toISOString()
      });
    },
    onChatResponse: (payload) => {
      addMessage({
        id: `msg_${Date.now()}`,
        timestamp: new Date().toISOString(),
        role: 'agent',
        agent_id: payload.agent_id,
        content: payload.content,
        suggestions: payload.suggestions
      });
      setTyping(false);
    },
    onChatTyping: (payload) => {
      setTyping(payload.is_typing);
    }
  };
  
  return (
    <WebSocketProvider authToken="demo-auth-token" handlers={handlers}>
      <AppInner />
    </WebSocketProvider>
  );
};

export default App;
