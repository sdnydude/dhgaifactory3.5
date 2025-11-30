// DHG AI Factory - Zustand Store
// Global state management for agent system

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';
import {
  AppState,
  AppActions,
  AppStore,
  AgentId,
  AgentState,
  AgentStatus,
  AgentLogEntry,
  AgentStatusPayload,
  ChatMessage,
  GeneratedContent,
  RequestStatus,
  RequestHistoryItem,
  ValidationResult,
  ContentChunkPayload,
  UIState,
  AGENT_CONFIGS
} from '../types';

// ============================================================================
// INITIAL STATE
// ============================================================================

const initialAgentState = (id: AgentId): AgentState => ({
  id,
  status: 'idle',
  progress: 0,
  logs: [],
  lastUpdated: new Date().toISOString()
});

const initialAgents: Record<AgentId, AgentState> = {
  orchestrator: initialAgentState('orchestrator'),
  research: initialAgentState('research'),
  medical_llm: initialAgentState('medical_llm'),
  curriculum: initialAgentState('curriculum'),
  outcomes: initialAgentState('outcomes'),
  competitor_intel: initialAgentState('competitor_intel'),
  qa_compliance: initialAgentState('qa_compliance')
};

const initialUIState: UIState = {
  leftPanelOpen: true,
  rightPanelOpen: true,
  leftPanelWidth: 360,
  rightPanelWidth: 360,
  activeView: 'dashboard',
  theme: 'light',
  compactMode: false
};

const initialState: AppState = {
  connected: false,
  sessionId: null,
  agents: initialAgents,
  currentRequest: null,
  currentContent: null,
  messages: [],
  isTyping: false,
  history: [],
  ui: initialUIState
};

// ============================================================================
// STORE CREATION
// ============================================================================

export const useAppStore = create<AppStore>()(
  devtools(
    persist(
      immer((set, get) => ({
        ...initialState,

        // ======================================================================
        // CONNECTION ACTIONS
        // ======================================================================

        setConnected: (connected: boolean) => {
          set((state) => {
            state.connected = connected;
          });
        },

        setSessionId: (sessionId: string) => {
          set((state) => {
            state.sessionId = sessionId;
          });
        },

        // ======================================================================
        // AGENT ACTIONS
        // ======================================================================

        updateAgentStatus: (payload: AgentStatusPayload) => {
          set((state) => {
            const agent = state.agents[payload.agent_id];
            if (agent) {
              agent.status = payload.status;
              agent.taskDescription = payload.task_description;
              if (payload.progress) {
                agent.progress = (payload.progress.current / payload.progress.total) * 100;
              }
              agent.lastUpdated = new Date().toISOString();
            }
          });
        },

        addAgentLog: (agentId: AgentId, log: AgentLogEntry) => {
          set((state) => {
            const agent = state.agents[agentId];
            if (agent) {
              agent.logs.push(log);
              // Keep only last 100 logs per agent
              if (agent.logs.length > 100) {
                agent.logs = agent.logs.slice(-100);
              }
            }
          });
        },

        clearAgentLogs: (agentId: AgentId) => {
          set((state) => {
            const agent = state.agents[agentId];
            if (agent) {
              agent.logs = [];
            }
          });
        },

        // ======================================================================
        // REQUEST ACTIONS
        // ======================================================================

        setCurrentRequest: (request: RequestStatus | null) => {
          set((state) => {
            state.currentRequest = request;
            // Reset agents when starting new request
            if (request && request.status === 'pending') {
              Object.keys(state.agents).forEach((key) => {
                const agent = state.agents[key as AgentId];
                agent.status = 'idle';
                agent.progress = 0;
                agent.taskDescription = undefined;
                agent.logs = [];
              });
            }
          });
        },

        updateRequestProgress: (progress: number) => {
          set((state) => {
            if (state.currentRequest) {
              state.currentRequest.progress = progress;
              state.currentRequest.updated_at = new Date().toISOString();
            }
          });
        },

        // ======================================================================
        // CONTENT ACTIONS
        // ======================================================================

        appendContentChunk: (chunk: ContentChunkPayload) => {
          set((state) => {
            if (!state.currentContent) {
              // Initialize content if not exists
              state.currentContent = {
                id: `content_${Date.now()}`,
                request_id: state.currentRequest?.request_id || '',
                title: '',
                content: chunk.content,
                format: 'markdown',
                sections: [],
                metadata: {
                  word_count: 0,
                  reference_count: 0,
                  generation_time_ms: 0,
                  compliance_mode: 'cme',
                  target_audience: '',
                  topic: ''
                },
                created_at: new Date().toISOString()
              };
            } else {
              state.currentContent.content += chunk.content;
            }
          });
        },

        setCurrentContent: (content: GeneratedContent | null) => {
          set((state) => {
            state.currentContent = content;
          });
        },

        setValidationResult: (result: ValidationResult) => {
          set((state) => {
            if (state.currentContent) {
              state.currentContent.validation = result;
            }
          });
        },

        // ======================================================================
        // CHAT ACTIONS
        // ======================================================================

        addMessage: (message: ChatMessage) => {
          set((state) => {
            state.messages.push(message);
            // Keep only last 200 messages
            if (state.messages.length > 200) {
              state.messages = state.messages.slice(-200);
            }
          });
        },

        setTyping: (isTyping: boolean) => {
          set((state) => {
            state.isTyping = isTyping;
          });
        },

        clearMessages: () => {
          set((state) => {
            state.messages = [];
          });
        },

        // ======================================================================
        // HISTORY ACTIONS
        // ======================================================================

        addToHistory: (item: RequestHistoryItem) => {
          set((state) => {
            // Add to beginning (most recent first)
            state.history.unshift(item);
            // Keep only last 100 items
            if (state.history.length > 100) {
              state.history = state.history.slice(0, 100);
            }
          });
        },

        loadHistory: (items: RequestHistoryItem[]) => {
          set((state) => {
            state.history = items;
          });
        },

        // ======================================================================
        // UI ACTIONS
        // ======================================================================

        toggleLeftPanel: () => {
          set((state) => {
            state.ui.leftPanelOpen = !state.ui.leftPanelOpen;
          });
        },

        toggleRightPanel: () => {
          set((state) => {
            state.ui.rightPanelOpen = !state.ui.rightPanelOpen;
          });
        },

        setLeftPanelWidth: (width: number) => {
          set((state) => {
            state.ui.leftPanelWidth = Math.max(280, Math.min(400, width));
          });
        },

        setRightPanelWidth: (width: number) => {
          set((state) => {
            state.ui.rightPanelWidth = Math.max(280, Math.min(400, width));
          });
        },

        setActiveView: (view: UIState['activeView']) => {
          set((state) => {
            state.ui.activeView = view;
          });
        },

        setTheme: (theme: UIState['theme']) => {
          set((state) => {
            state.ui.theme = theme;
          });
        }
      })),
      {
        name: 'dhg-ai-factory-storage',
        partialize: (state) => ({
          // Only persist UI preferences and history
          ui: state.ui,
          history: state.history
        })
      }
    ),
    { name: 'DHG AI Factory' }
  )
);

// ============================================================================
// SELECTORS
// ============================================================================

export const selectAgents = (state: AppState) => state.agents;
export const selectAgent = (agentId: AgentId) => (state: AppState) => state.agents[agentId];
export const selectActiveAgents = (state: AppState) => 
  Object.values(state.agents).filter(a => a.status === 'working');
export const selectAllAgentLogs = (state: AppState) => 
  Object.values(state.agents).flatMap(a => a.logs).sort((a, b) => 
    new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  );

export const selectCurrentRequest = (state: AppState) => state.currentRequest;
export const selectCurrentContent = (state: AppState) => state.currentContent;
export const selectIsProcessing = (state: AppState) => 
  state.currentRequest?.status === 'processing';

export const selectMessages = (state: AppState) => state.messages;
export const selectHistory = (state: AppState) => state.history;

export const selectUI = (state: AppState) => state.ui;
export const selectIsConnected = (state: AppState) => state.connected;

// ============================================================================
// COMPUTED VALUES
// ============================================================================

export const getOverallProgress = (state: AppState): number => {
  const activeAgents = Object.values(state.agents).filter(
    a => a.status === 'working' || a.status === 'complete'
  );
  
  if (activeAgents.length === 0) return 0;
  
  const totalProgress = activeAgents.reduce((sum, agent) => {
    return sum + (agent.status === 'complete' ? 100 : agent.progress);
  }, 0);
  
  return totalProgress / activeAgents.length;
};

export const getAgentStatusColor = (status: AgentStatus): string => {
  const colors: Record<AgentStatus, string> = {
    idle: '#9CA3AF',
    working: '#0066CC',
    waiting: '#D97706',
    complete: '#059669',
    error: '#DC2626',
    cancelled: '#6B7280'
  };
  return colors[status];
};

export const getAgentConfig = (agentId: AgentId) => AGENT_CONFIGS[agentId];

export default useAppStore;
