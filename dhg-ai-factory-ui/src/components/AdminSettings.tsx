// DHG AI Factory - Admin Settings Page
// System configuration, user management, API settings, and agent configuration

import React, { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Settings,
  Users,
  Key,
  Server,
  Database,
  Shield,
  Activity,
  Cpu,
  HardDrive,
  Zap,
  RefreshCw,
  Plus,
  Trash2,
  Edit,
  Check,
  X,
  Copy,
  Eye,
  EyeOff,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Clock,
  Search,
  Filter,
  Download,
  Upload,
  MoreVertical,
  ChevronRight,
  Globe,
  Mail,
  Webhook,
  Terminal,
  FileText,
  BarChart3
} from 'lucide-react';
import { cn } from '../lib/utils';
import { AgentId, AGENT_CONFIGS } from '../types';

// ============================================================================
// TYPES
// ============================================================================

interface SystemUser {
  id: string;
  name: string;
  email: string;
  role: 'admin' | 'editor' | 'viewer';
  status: 'active' | 'inactive' | 'pending';
  lastActive: string;
  createdAt: string;
}

interface APIKey {
  id: string;
  name: string;
  key: string;
  permissions: string[];
  lastUsed: string;
  createdAt: string;
  expiresAt?: string;
}

interface AgentSettings {
  id: AgentId;
  enabled: boolean;
  priority: number;
  timeout: number;
  maxRetries: number;
  rateLimit: number;
  model?: string;
}

interface SystemMetrics {
  cpu: number;
  memory: number;
  storage: number;
  activeConnections: number;
  requestsToday: number;
  avgResponseTime: number;
}

// ============================================================================
// MOCK DATA
// ============================================================================

const mockUsers: SystemUser[] = [
  {
    id: '1',
    name: 'Stephen Webber',
    email: 'swebber@digitalharmonygroup.com',
    role: 'admin',
    status: 'active',
    lastActive: '2025-11-30T10:30:00Z',
    createdAt: '2024-01-15T00:00:00Z'
  },
  {
    id: '2',
    name: 'Sarah Chen',
    email: 'schen@digitalharmonygroup.com',
    role: 'editor',
    status: 'active',
    lastActive: '2025-11-30T09:15:00Z',
    createdAt: '2024-03-20T00:00:00Z'
  },
  {
    id: '3',
    name: 'Mike Johnson',
    email: 'mjohnson@digitalharmonygroup.com',
    role: 'viewer',
    status: 'pending',
    lastActive: '2025-11-28T14:00:00Z',
    createdAt: '2025-11-25T00:00:00Z'
  }
];

const mockAPIKeys: APIKey[] = [
  {
    id: '1',
    name: 'Production API',
    key: 'dhg_prod_sk_1234567890abcdef',
    permissions: ['read', 'write', 'admin'],
    lastUsed: '2025-11-30T10:00:00Z',
    createdAt: '2024-01-01T00:00:00Z'
  },
  {
    id: '2',
    name: 'Development API',
    key: 'dhg_dev_sk_abcdef1234567890',
    permissions: ['read', 'write'],
    lastUsed: '2025-11-29T16:30:00Z',
    createdAt: '2024-06-15T00:00:00Z'
  }
];

const mockMetrics: SystemMetrics = {
  cpu: 45,
  memory: 62,
  storage: 38,
  activeConnections: 23,
  requestsToday: 1247,
  avgResponseTime: 245
};

// ============================================================================
// SUB-COMPONENTS
// ============================================================================

// Tabs Component
interface Tab {
  id: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}

const tabs: Tab[] = [
  { id: 'general', label: 'General', icon: Settings },
  { id: 'users', label: 'Users', icon: Users },
  { id: 'api', label: 'API Keys', icon: Key },
  { id: 'agents', label: 'Agents', icon: Cpu },
  { id: 'integrations', label: 'Integrations', icon: Webhook },
  { id: 'monitoring', label: 'Monitoring', icon: Activity }
];

// Status Badge
const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
  const config = {
    active: { bg: 'bg-green-100', text: 'text-green-800', dot: 'bg-green-500' },
    inactive: { bg: 'bg-gray-100', text: 'text-gray-800', dot: 'bg-gray-500' },
    pending: { bg: 'bg-amber-100', text: 'text-amber-800', dot: 'bg-amber-500' },
    enabled: { bg: 'bg-green-100', text: 'text-green-800', dot: 'bg-green-500' },
    disabled: { bg: 'bg-red-100', text: 'text-red-800', dot: 'bg-red-500' }
  }[status] || { bg: 'bg-gray-100', text: 'text-gray-800', dot: 'bg-gray-500' };

  return (
    <span className={cn('inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium', config.bg, config.text)}>
      <span className={cn('w-1.5 h-1.5 rounded-full', config.dot)} />
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
};

// Metric Card
const MetricCard: React.FC<{
  label: string;
  value: string | number;
  unit?: string;
  icon: React.ComponentType<{ className?: string }>;
  trend?: 'up' | 'down' | 'neutral';
  color?: string;
}> = ({ label, value, unit, icon: Icon, trend, color = 'blue' }) => (
  <div className="bg-white rounded-xl border border-gray-200 p-4">
    <div className="flex items-center justify-between mb-3">
      <div className={cn(
        'p-2 rounded-lg',
        color === 'blue' ? 'bg-blue-100' :
        color === 'green' ? 'bg-green-100' :
        color === 'amber' ? 'bg-amber-100' :
        color === 'purple' ? 'bg-purple-100' : 'bg-gray-100'
      )}>
        <Icon className={cn(
          'w-5 h-5',
          color === 'blue' ? 'text-blue-600' :
          color === 'green' ? 'text-green-600' :
          color === 'amber' ? 'text-amber-600' :
          color === 'purple' ? 'text-purple-600' : 'text-gray-600'
        )} />
      </div>
      {trend && (
        <span className={cn(
          'text-xs font-medium',
          trend === 'up' ? 'text-green-600' :
          trend === 'down' ? 'text-red-600' : 'text-gray-500'
        )}>
          {trend === 'up' ? '↑' : trend === 'down' ? '↓' : '→'}
        </span>
      )}
    </div>
    <p className="text-2xl font-bold text-gray-900">
      {value}
      {unit && <span className="text-sm font-normal text-gray-500 ml-1">{unit}</span>}
    </p>
    <p className="text-sm text-gray-500 mt-1">{label}</p>
  </div>
);

// Progress Bar
const ProgressBar: React.FC<{ value: number; color?: string }> = ({ value, color = 'blue' }) => (
  <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
    <div
      className={cn(
        'h-full rounded-full transition-all duration-300',
        color === 'blue' ? 'bg-blue-600' :
        color === 'green' ? 'bg-green-600' :
        color === 'amber' ? 'bg-amber-600' :
        color === 'red' ? 'bg-red-600' : 'bg-gray-600'
      )}
      style={{ width: `${value}%` }}
    />
  </div>
);

// ============================================================================
// TAB CONTENT COMPONENTS
// ============================================================================

// General Settings Tab
const GeneralSettingsTab: React.FC = () => {
  const [siteName, setSiteName] = useState('DHG AI Factory');
  const [siteUrl, setSiteUrl] = useState('https://aifactory.dhg.ai');
  const [supportEmail, setSupportEmail] = useState('support@digitalharmonygroup.com');
  const [maintenanceMode, setMaintenanceMode] = useState(false);
  const [debugMode, setDebugMode] = useState(false);
  const [logLevel, setLogLevel] = useState('info');

  return (
    <div className="space-y-6">
      {/* Site Settings */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Site Settings</h3>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Site Name</label>
            <input
              type="text"
              value={siteName}
              onChange={(e) => setSiteName(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Site URL</label>
            <input
              type="url"
              value={siteUrl}
              onChange={(e) => setSiteUrl(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Support Email</label>
            <input
              type="email"
              value={supportEmail}
              onChange={(e) => setSupportEmail(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Log Level</label>
            <select
              value={logLevel}
              onChange={(e) => setLogLevel(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="debug">Debug</option>
              <option value="info">Info</option>
              <option value="warning">Warning</option>
              <option value="error">Error</option>
            </select>
          </div>
        </div>
      </div>

      {/* System Toggles */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">System Controls</h3>
        <div className="space-y-4">
          <div className="flex items-center justify-between p-4 bg-amber-50 rounded-lg border border-amber-200">
            <div>
              <p className="text-sm font-medium text-amber-900">Maintenance Mode</p>
              <p className="text-xs text-amber-700 mt-0.5">Disable access for non-admin users</p>
            </div>
            <button
              onClick={() => setMaintenanceMode(!maintenanceMode)}
              className={cn(
                'relative inline-flex h-6 w-11 items-center rounded-full transition-colors',
                maintenanceMode ? 'bg-amber-600' : 'bg-gray-200'
              )}
            >
              <span className={cn(
                'inline-block h-4 w-4 transform rounded-full bg-white transition-transform shadow-sm',
                maintenanceMode ? 'translate-x-6' : 'translate-x-1'
              )} />
            </button>
          </div>

          <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
            <div>
              <p className="text-sm font-medium text-gray-900">Debug Mode</p>
              <p className="text-xs text-gray-500 mt-0.5">Enable verbose logging and error details</p>
            </div>
            <button
              onClick={() => setDebugMode(!debugMode)}
              className={cn(
                'relative inline-flex h-6 w-11 items-center rounded-full transition-colors',
                debugMode ? 'bg-blue-600' : 'bg-gray-200'
              )}
            >
              <span className={cn(
                'inline-block h-4 w-4 transform rounded-full bg-white transition-transform shadow-sm',
                debugMode ? 'translate-x-6' : 'translate-x-1'
              )} />
            </button>
          </div>
        </div>
      </div>

      {/* Database Settings */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Database</h3>
        <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg mb-4">
          <div className="flex items-center gap-3">
            <Database className="w-5 h-5 text-gray-400" />
            <div>
              <p className="text-sm font-medium text-gray-900">PostgreSQL</p>
              <p className="text-xs text-gray-500">Connected • 23 active connections</p>
            </div>
          </div>
          <StatusBadge status="active" />
        </div>
        <div className="flex gap-3">
          <button className="flex items-center gap-2 px-3 py-2 bg-gray-900 text-white rounded-lg text-sm font-medium hover:bg-gray-800">
            <Download className="w-4 h-4" />
            Backup
          </button>
          <button className="flex items-center gap-2 px-3 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50">
            <Upload className="w-4 h-4" />
            Restore
          </button>
        </div>
      </div>
    </div>
  );
};

// Users Tab
const UsersTab: React.FC = () => {
  const [users] = useState<SystemUser[]>(mockUsers);
  const [searchQuery, setSearchQuery] = useState('');
  const [roleFilter, setRoleFilter] = useState<string>('all');

  const filteredUsers = useMemo(() => {
    return users.filter(user => {
      const matchesSearch = user.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                           user.email.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesRole = roleFilter === 'all' || user.role === roleFilter;
      return matchesSearch && matchesRole;
    });
  }, [users, searchQuery, roleFilter]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search users..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-sm w-64 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          <select
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="all">All Roles</option>
            <option value="admin">Admin</option>
            <option value="editor">Editor</option>
            <option value="viewer">Viewer</option>
          </select>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">
          <Plus className="w-4 h-4" />
          Add User
        </button>
      </div>

      {/* Users Table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase">User</th>
              <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Role</th>
              <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Status</th>
              <th className="text-left px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Last Active</th>
              <th className="text-right px-6 py-3 text-xs font-semibold text-gray-500 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {filteredUsers.map((user) => (
              <tr key={user.id} className="hover:bg-gray-50">
                <td className="px-6 py-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-blue-700 flex items-center justify-center text-white font-medium">
                      {user.name.split(' ').map(n => n[0]).join('')}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-900">{user.name}</p>
                      <p className="text-xs text-gray-500">{user.email}</p>
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4">
                  <span className={cn(
                    'px-2 py-1 rounded text-xs font-medium',
                    user.role === 'admin' ? 'bg-purple-100 text-purple-800' :
                    user.role === 'editor' ? 'bg-blue-100 text-blue-800' :
                    'bg-gray-100 text-gray-800'
                  )}>
                    {user.role.charAt(0).toUpperCase() + user.role.slice(1)}
                  </span>
                </td>
                <td className="px-6 py-4">
                  <StatusBadge status={user.status} />
                </td>
                <td className="px-6 py-4">
                  <p className="text-sm text-gray-500">
                    {new Date(user.lastActive).toLocaleDateString()}
                  </p>
                </td>
                <td className="px-6 py-4 text-right">
                  <div className="flex items-center justify-end gap-2">
                    <button className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded">
                      <Edit className="w-4 h-4" />
                    </button>
                    <button className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded">
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

// API Keys Tab
const APIKeysTab: React.FC = () => {
  const [apiKeys] = useState<APIKey[]>(mockAPIKeys);
  const [showKey, setShowKey] = useState<string | null>(null);

  const maskKey = (key: string) => {
    return key.slice(0, 12) + '••••••••••••••••';
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-500">
          Manage API keys for programmatic access to the DHG AI Factory
        </p>
        <button className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">
          <Plus className="w-4 h-4" />
          Create API Key
        </button>
      </div>

      {/* API Keys List */}
      <div className="space-y-4">
        {apiKeys.map((apiKey) => (
          <div key={apiKey.id} className="bg-white rounded-xl border border-gray-200 p-6">
            <div className="flex items-start justify-between mb-4">
              <div>
                <h4 className="text-sm font-semibold text-gray-900">{apiKey.name}</h4>
                <p className="text-xs text-gray-500 mt-0.5">
                  Created {new Date(apiKey.createdAt).toLocaleDateString()}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <button className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded">
                  <Edit className="w-4 h-4" />
                </button>
                <button className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded">
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Key Display */}
            <div className="flex items-center gap-2 p-3 bg-gray-50 rounded-lg font-mono text-sm">
              <span className="flex-1 text-gray-700">
                {showKey === apiKey.id ? apiKey.key : maskKey(apiKey.key)}
              </span>
              <button
                onClick={() => setShowKey(showKey === apiKey.id ? null : apiKey.id)}
                className="p-1.5 text-gray-400 hover:text-gray-600"
              >
                {showKey === apiKey.id ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
              <button
                onClick={() => navigator.clipboard.writeText(apiKey.key)}
                className="p-1.5 text-gray-400 hover:text-gray-600"
              >
                <Copy className="w-4 h-4" />
              </button>
            </div>

            {/* Permissions & Stats */}
            <div className="flex items-center justify-between mt-4">
              <div className="flex items-center gap-2">
                {apiKey.permissions.map((perm) => (
                  <span key={perm} className="px-2 py-0.5 bg-gray-100 rounded text-xs font-medium text-gray-700">
                    {perm}
                  </span>
                ))}
              </div>
              <p className="text-xs text-gray-500">
                Last used: {new Date(apiKey.lastUsed).toLocaleString()}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

// Agents Tab
const AgentsTab: React.FC = () => {
  const [agents, setAgents] = useState<AgentSettings[]>(
    Object.keys(AGENT_CONFIGS).map((id) => ({
      id: id as AgentId,
      enabled: true,
      priority: 5,
      timeout: 30000,
      maxRetries: 3,
      rateLimit: 100,
      model: id === 'medical_llm' ? 'claude-3-opus' : undefined
    }))
  );

  const toggleAgent = (agentId: AgentId) => {
    setAgents(prev => prev.map(a => 
      a.id === agentId ? { ...a, enabled: !a.enabled } : a
    ));
  };

  return (
    <div className="space-y-6">
      <p className="text-sm text-gray-500">
        Configure individual agent settings, timeouts, and rate limits
      </p>

      <div className="grid gap-4">
        {agents.map((agent) => {
          const config = AGENT_CONFIGS[agent.id];
          return (
            <div
              key={agent.id}
              className={cn(
                'bg-white rounded-xl border p-6 transition-all',
                agent.enabled ? 'border-gray-200' : 'border-gray-100 opacity-60'
              )}
            >
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div
                    className="w-10 h-10 rounded-lg flex items-center justify-center text-white text-lg"
                    style={{ backgroundColor: config.color }}
                  >
                    {config.icon}
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-gray-900">{config.name}</h4>
                    <p className="text-xs text-gray-500">{agent.id}</p>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <StatusBadge status={agent.enabled ? 'enabled' : 'disabled'} />
                  <button
                    onClick={() => toggleAgent(agent.id)}
                    className={cn(
                      'relative inline-flex h-6 w-11 items-center rounded-full transition-colors',
                      agent.enabled ? 'bg-green-600' : 'bg-gray-200'
                    )}
                  >
                    <span className={cn(
                      'inline-block h-4 w-4 transform rounded-full bg-white transition-transform shadow-sm',
                      agent.enabled ? 'translate-x-6' : 'translate-x-1'
                    )} />
                  </button>
                </div>
              </div>

              {agent.enabled && (
                <div className="grid grid-cols-4 gap-4 pt-4 border-t border-gray-100">
                  <div>
                    <label className="block text-xs font-medium text-gray-500 mb-1">Timeout (ms)</label>
                    <input
                      type="number"
                      value={agent.timeout}
                      onChange={(e) => setAgents(prev => prev.map(a => 
                        a.id === agent.id ? { ...a, timeout: parseInt(e.target.value) } : a
                      ))}
                      className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-500 mb-1">Max Retries</label>
                    <input
                      type="number"
                      value={agent.maxRetries}
                      onChange={(e) => setAgents(prev => prev.map(a => 
                        a.id === agent.id ? { ...a, maxRetries: parseInt(e.target.value) } : a
                      ))}
                      className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-500 mb-1">Rate Limit</label>
                    <input
                      type="number"
                      value={agent.rateLimit}
                      onChange={(e) => setAgents(prev => prev.map(a => 
                        a.id === agent.id ? { ...a, rateLimit: parseInt(e.target.value) } : a
                      ))}
                      className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-500 mb-1">Priority</label>
                    <input
                      type="number"
                      value={agent.priority}
                      min={1}
                      max={10}
                      onChange={(e) => setAgents(prev => prev.map(a => 
                        a.id === agent.id ? { ...a, priority: parseInt(e.target.value) } : a
                      ))}
                      className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm"
                    />
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

// Integrations Tab
const IntegrationsTab: React.FC = () => {
  const integrations = [
    { id: 'pubmed', name: 'PubMed', icon: '📚', status: 'connected', description: 'Medical literature database' },
    { id: 'openai', name: 'OpenAI', icon: '🤖', status: 'connected', description: 'GPT models for content generation' },
    { id: 'anthropic', name: 'Anthropic', icon: '🧠', status: 'connected', description: 'Claude models for medical LLM' },
    { id: 'slack', name: 'Slack', icon: '💬', status: 'disconnected', description: 'Team notifications' },
    { id: 'gdrive', name: 'Google Drive', icon: '📁', status: 'disconnected', description: 'Document storage' },
    { id: 'webhook', name: 'Webhooks', icon: '🔗', status: 'configured', description: 'Custom HTTP callbacks' }
  ];

  return (
    <div className="space-y-6">
      <p className="text-sm text-gray-500">
        Connect external services and configure webhooks
      </p>

      <div className="grid grid-cols-2 gap-4">
        {integrations.map((integration) => (
          <div key={integration.id} className="bg-white rounded-xl border border-gray-200 p-6">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <span className="text-2xl">{integration.icon}</span>
                <div>
                  <h4 className="text-sm font-semibold text-gray-900">{integration.name}</h4>
                  <p className="text-xs text-gray-500">{integration.description}</p>
                </div>
              </div>
              <StatusBadge status={integration.status === 'connected' ? 'active' : integration.status === 'configured' ? 'pending' : 'inactive'} />
            </div>
            <div className="mt-4">
              <button className={cn(
                'w-full py-2 rounded-lg text-sm font-medium transition-colors',
                integration.status === 'connected'
                  ? 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  : 'bg-blue-600 text-white hover:bg-blue-700'
              )}>
                {integration.status === 'connected' ? 'Configure' : 'Connect'}
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

// Monitoring Tab
const MonitoringTab: React.FC = () => {
  const [metrics] = useState<SystemMetrics>(mockMetrics);

  return (
    <div className="space-y-6">
      {/* Metrics Grid */}
      <div className="grid grid-cols-3 gap-4">
        <MetricCard
          label="CPU Usage"
          value={metrics.cpu}
          unit="%"
          icon={Cpu}
          color="blue"
        />
        <MetricCard
          label="Memory Usage"
          value={metrics.memory}
          unit="%"
          icon={HardDrive}
          color="purple"
        />
        <MetricCard
          label="Storage Used"
          value={metrics.storage}
          unit="%"
          icon={Database}
          color="amber"
        />
        <MetricCard
          label="Active Connections"
          value={metrics.activeConnections}
          icon={Activity}
          color="green"
          trend="up"
        />
        <MetricCard
          label="Requests Today"
          value={metrics.requestsToday.toLocaleString()}
          icon={Zap}
          color="blue"
          trend="up"
        />
        <MetricCard
          label="Avg Response Time"
          value={metrics.avgResponseTime}
          unit="ms"
          icon={Clock}
          color="green"
          trend="down"
        />
      </div>

      {/* System Health */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">System Health</h3>
        <div className="space-y-4">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-600">CPU</span>
              <span className="text-sm font-medium text-gray-900">{metrics.cpu}%</span>
            </div>
            <ProgressBar value={metrics.cpu} color={metrics.cpu > 80 ? 'red' : metrics.cpu > 60 ? 'amber' : 'green'} />
          </div>
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-600">Memory</span>
              <span className="text-sm font-medium text-gray-900">{metrics.memory}%</span>
            </div>
            <ProgressBar value={metrics.memory} color={metrics.memory > 80 ? 'red' : metrics.memory > 60 ? 'amber' : 'green'} />
          </div>
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-600">Storage</span>
              <span className="text-sm font-medium text-gray-900">{metrics.storage}%</span>
            </div>
            <ProgressBar value={metrics.storage} color={metrics.storage > 80 ? 'red' : metrics.storage > 60 ? 'amber' : 'green'} />
          </div>
        </div>
      </div>

      {/* Recent Logs */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">Recent Logs</h3>
          <button className="text-sm text-blue-600 hover:text-blue-800 font-medium">
            View All
          </button>
        </div>
        <div className="space-y-2 font-mono text-xs">
          {[
            { level: 'info', time: '10:45:23', message: 'Request completed: req_abc123 (245ms)' },
            { level: 'info', time: '10:45:20', message: 'Agent research started for request req_abc123' },
            { level: 'warning', time: '10:44:55', message: 'Rate limit approaching for user user_001' },
            { level: 'info', time: '10:44:30', message: 'New WebSocket connection established' },
            { level: 'error', time: '10:43:12', message: 'PubMed API timeout - retrying...' }
          ].map((log, idx) => (
            <div key={idx} className={cn(
              'flex items-start gap-3 px-3 py-2 rounded',
              log.level === 'error' ? 'bg-red-50' :
              log.level === 'warning' ? 'bg-amber-50' : 'bg-gray-50'
            )}>
              <span className="text-gray-400">{log.time}</span>
              <span className={cn(
                'uppercase text-[10px] font-semibold',
                log.level === 'error' ? 'text-red-600' :
                log.level === 'warning' ? 'text-amber-600' : 'text-blue-600'
              )}>
                {log.level}
              </span>
              <span className="text-gray-700">{log.message}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// MAIN COMPONENT
// ============================================================================

const AdminSettings: React.FC = () => {
  const [activeTab, setActiveTab] = useState('general');

  const renderTabContent = () => {
    switch (activeTab) {
      case 'general':
        return <GeneralSettingsTab />;
      case 'users':
        return <UsersTab />;
      case 'api':
        return <APIKeysTab />;
      case 'agents':
        return <AgentsTab />;
      case 'integrations':
        return <IntegrationsTab />;
      case 'monitoring':
        return <MonitoringTab />;
      default:
        return <GeneralSettingsTab />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Admin Settings</h2>
        <p className="text-gray-600 mt-1">
          System configuration, user management, and monitoring
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 p-1 bg-gray-100 rounded-xl">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all',
              activeTab === tab.id
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            )}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <AnimatePresence mode="wait">
        <motion.div
          key={activeTab}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={{ duration: 0.2 }}
        >
          {renderTabContent()}
        </motion.div>
      </AnimatePresence>
    </div>
  );
};

export default AdminSettings;
