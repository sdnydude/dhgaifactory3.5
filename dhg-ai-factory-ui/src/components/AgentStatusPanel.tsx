// DHG AI Factory - Agent Status Panel Component
// Real-time visualization of agent activity during content generation

import React, { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  ChevronDown, 
  ChevronUp, 
  Activity, 
  Clock, 
  CheckCircle, 
  XCircle, 
  Loader, 
  Pause,
  Terminal
} from 'lucide-react';
import { cn } from '../lib/utils';
import { useAppStore, selectAgents, getAgentStatusColor, getAgentConfig } from '../store/useAppStore';
import { AgentId, AgentStatus, AgentState, AgentLogEntry, AGENT_CONFIGS } from '../types';

// ============================================================================
// TYPES
// ============================================================================

interface AgentStatusPanelProps {
  className?: string;
  compact?: boolean;
}

interface AgentRowProps {
  agent: AgentState;
  expanded: boolean;
  onToggle: () => void;
}

interface LogEntryProps {
  log: AgentLogEntry;
}

// ============================================================================
// STATUS ICON COMPONENT
// ============================================================================

const StatusIcon: React.FC<{ status: AgentStatus; className?: string }> = ({ status, className }) => {
  const iconClass = cn('w-4 h-4', className);
  
  switch (status) {
    case 'idle':
      return <Clock className={cn(iconClass, 'text-gray-400')} />;
    case 'working':
      return (
        <Loader className={cn(iconClass, 'text-blue-500 animate-spin')} />
      );
    case 'waiting':
      return <Pause className={cn(iconClass, 'text-amber-500')} />;
    case 'complete':
      return <CheckCircle className={cn(iconClass, 'text-green-500')} />;
    case 'error':
      return <XCircle className={cn(iconClass, 'text-red-500')} />;
    case 'cancelled':
      return <XCircle className={cn(iconClass, 'text-gray-500')} />;
    default:
      return <Activity className={cn(iconClass, 'text-gray-400')} />;
  }
};

// ============================================================================
// LOG ENTRY COMPONENT
// ============================================================================

const LogEntry: React.FC<LogEntryProps> = ({ log }) => {
  const levelColors = {
    debug: 'text-gray-500',
    info: 'text-blue-600',
    warning: 'text-amber-600',
    error: 'text-red-600'
  };
  
  const levelBg = {
    debug: 'bg-gray-100',
    info: 'bg-blue-50',
    warning: 'bg-amber-50',
    error: 'bg-red-50'
  };
  
  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    });
  };
  
  return (
    <div className={cn(
      'px-3 py-1.5 text-xs font-mono border-l-2',
      levelBg[log.level],
      log.level === 'error' ? 'border-red-500' : 
      log.level === 'warning' ? 'border-amber-500' :
      log.level === 'info' ? 'border-blue-500' : 'border-gray-300'
    )}>
      <div className="flex items-start gap-2">
        <span className="text-gray-400 shrink-0">{formatTime(log.timestamp)}</span>
        <span className={cn('uppercase text-[10px] font-semibold shrink-0', levelColors[log.level])}>
          {log.level}
        </span>
        <span className="text-gray-700 break-all">{log.message}</span>
      </div>
      {log.data && (
        <pre className="mt-1 text-[10px] text-gray-500 overflow-x-auto">
          {JSON.stringify(log.data, null, 2)}
        </pre>
      )}
    </div>
  );
};

// ============================================================================
// AGENT ROW COMPONENT
// ============================================================================

const AgentRow: React.FC<AgentRowProps> = ({ agent, expanded, onToggle }) => {
  const config = getAgentConfig(agent.id);
  const statusColor = getAgentStatusColor(agent.status);
  
  const statusText: Record<AgentStatus, string> = {
    idle: 'Ready',
    working: 'Working...',
    waiting: 'Waiting',
    complete: 'Complete',
    error: 'Error',
    cancelled: 'Cancelled'
  };
  
  return (
    <div 
      className="border-b border-gray-100 last:border-b-0"
      style={{ borderLeftColor: config.color, borderLeftWidth: 3 }}
    >
      {/* Agent Header */}
      <button
        onClick={onToggle}
        className={cn(
          'w-full flex items-center justify-between p-3 hover:bg-gray-50 transition-colors',
          'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-inset'
        )}
      >
        <div className="flex items-center gap-3">
          {/* Status Indicator */}
          <div 
            className={cn(
              'w-2.5 h-2.5 rounded-full',
              agent.status === 'working' && 'animate-pulse'
            )}
            style={{ backgroundColor: statusColor }}
          />
          
          {/* Agent Info */}
          <div className="text-left">
            <div className="flex items-center gap-2">
              <span className="text-sm">{config.icon}</span>
              <span className="text-sm font-semibold text-gray-900">{config.name}</span>
            </div>
            <div className="text-xs text-gray-500 mt-0.5">
              {agent.taskDescription || statusText[agent.status]}
            </div>
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          <StatusIcon status={agent.status} />
          {expanded ? (
            <ChevronUp className="w-4 h-4 text-gray-400" />
          ) : (
            <ChevronDown className="w-4 h-4 text-gray-400" />
          )}
        </div>
      </button>
      
      {/* Progress Bar (shown when working) */}
      {agent.status === 'working' && agent.progress > 0 && (
        <div className="px-3 pb-2">
          <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
            <motion.div
              className="h-full rounded-full"
              style={{ backgroundColor: config.color }}
              initial={{ width: 0 }}
              animate={{ width: `${agent.progress}%` }}
              transition={{ duration: 0.3 }}
            />
          </div>
          <div className="flex justify-between mt-1">
            <span className="text-[10px] text-gray-400">Progress</span>
            <span className="text-[10px] font-medium" style={{ color: config.color }}>
              {Math.round(agent.progress)}%
            </span>
          </div>
        </div>
      )}
      
      {/* Expanded Logs Section */}
      <AnimatePresence>
        {expanded && agent.logs.length > 0 && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="bg-gray-50 border-t border-gray-100">
              <div className="flex items-center gap-2 px-3 py-2 border-b border-gray-100">
                <Terminal className="w-3 h-3 text-gray-400" />
                <span className="text-xs font-medium text-gray-600">Agent Logs</span>
                <span className="text-[10px] text-gray-400">({agent.logs.length})</span>
              </div>
              <div className="max-h-48 overflow-y-auto">
                {agent.logs.slice(-20).map((log) => (
                  <LogEntry key={log.id} log={log} />
                ))}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
      
      {/* No logs message */}
      <AnimatePresence>
        {expanded && agent.logs.length === 0 && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="bg-gray-50 border-t border-gray-100 px-3 py-4 text-center">
              <span className="text-xs text-gray-400">No logs yet</span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

// ============================================================================
// MAIN COMPONENT
// ============================================================================

const AgentStatusPanel: React.FC<AgentStatusPanelProps> = ({ className, compact = false }) => {
  const agents = useAppStore(selectAgents);
  const [expandedAgents, setExpandedAgents] = useState<Set<AgentId>>(new Set());
  
  const agentList = useMemo(() => {
    return Object.values(agents).sort((a, b) => {
      // Sort by status priority: working > waiting > error > complete > idle
      const priority: Record<AgentStatus, number> = {
        working: 0,
        waiting: 1,
        error: 2,
        complete: 3,
        cancelled: 4,
        idle: 5
      };
      return priority[a.status] - priority[b.status];
    });
  }, [agents]);
  
  const activeCount = useMemo(() => {
    return Object.values(agents).filter(a => a.status === 'working').length;
  }, [agents]);
  
  const toggleExpanded = (agentId: AgentId) => {
    setExpandedAgents(prev => {
      const next = new Set(prev);
      if (next.has(agentId)) {
        next.delete(agentId);
      } else {
        next.add(agentId);
      }
      return next;
    });
  };
  
  return (
    <div className={cn('bg-white rounded-lg border border-gray-200 overflow-hidden', className)}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-gray-50 border-b border-gray-200">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-gray-600" />
          <h3 className="text-sm font-semibold text-gray-900">Agent Activity</h3>
        </div>
        
        {activeCount > 0 && (
          <div className="flex items-center gap-1.5">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
            <span className="text-xs font-medium text-green-700">
              {activeCount} active
            </span>
          </div>
        )}
      </div>
      
      {/* Agent List */}
      <div className={cn(
        'divide-y divide-gray-100',
        compact ? 'max-h-64' : 'max-h-[calc(100vh-300px)]',
        'overflow-y-auto'
      )}>
        {agentList.map(agent => (
          <AgentRow
            key={agent.id}
            agent={agent}
            expanded={expandedAgents.has(agent.id)}
            onToggle={() => toggleExpanded(agent.id)}
          />
        ))}
      </div>
      
      {/* Footer with overall stats */}
      <div className="flex items-center justify-between px-4 py-2 bg-gray-50 border-t border-gray-200 text-xs text-gray-500">
        <span>
          {Object.values(agents).filter(a => a.status === 'complete').length} / {Object.keys(agents).length} complete
        </span>
        <span>
          {Object.values(agents).reduce((sum, a) => sum + a.logs.length, 0)} log entries
        </span>
      </div>
    </div>
  );
};

export default AgentStatusPanel;
