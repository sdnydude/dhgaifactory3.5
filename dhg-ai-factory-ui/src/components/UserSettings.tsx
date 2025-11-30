// DHG AI Factory - User Settings Page
// Personal preferences, profile, and notification configuration

import React, { useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import {
  User,
  Bell,
  Palette,
  Shield,
  Key,
  Mail,
  Smartphone,
  Globe,
  Moon,
  Sun,
  Monitor,
  Volume2,
  VolumeX,
  Save,
  Check,
  AlertCircle,
  Eye,
  EyeOff,
  Camera,
  Trash2,
  Download,
  LogOut
} from 'lucide-react';
import { cn } from '../lib/utils';
import { useAppStore } from '../store/useAppStore';

// ============================================================================
// TYPES
// ============================================================================

interface UserProfile {
  id: string;
  name: string;
  email: string;
  avatar?: string;
  role: 'admin' | 'editor' | 'viewer';
  organization: string;
  department: string;
  timezone: string;
  createdAt: string;
}

interface UserPreferences {
  theme: 'light' | 'dark' | 'system';
  language: string;
  compactMode: boolean;
  animations: boolean;
  soundEffects: boolean;
  autoSave: boolean;
  defaultComplianceMode: 'auto' | 'cme' | 'non_cme';
  defaultWordCount: number;
  defaultReferenceCount: number;
}

interface NotificationSettings {
  emailNotifications: boolean;
  pushNotifications: boolean;
  generationComplete: boolean;
  validationAlerts: boolean;
  weeklyDigest: boolean;
  marketingEmails: boolean;
}

// ============================================================================
// MOCK DATA
// ============================================================================

const mockProfile: UserProfile = {
  id: 'user_001',
  name: 'Stephen Webber',
  email: 'swebber@digitalharmonygroup.com',
  role: 'admin',
  organization: 'Digital Harmony Group',
  department: 'DHG CME',
  timezone: 'America/New_York',
  createdAt: '2024-01-15T00:00:00Z'
};

const defaultPreferences: UserPreferences = {
  theme: 'light',
  language: 'en-US',
  compactMode: false,
  animations: true,
  soundEffects: true,
  autoSave: true,
  defaultComplianceMode: 'cme',
  defaultWordCount: 1500,
  defaultReferenceCount: 12
};

const defaultNotifications: NotificationSettings = {
  emailNotifications: true,
  pushNotifications: true,
  generationComplete: true,
  validationAlerts: true,
  weeklyDigest: false,
  marketingEmails: false
};

// ============================================================================
// SECTION COMPONENTS
// ============================================================================

interface SettingsSectionProps {
  title: string;
  description?: string;
  icon: React.ComponentType<{ className?: string }>;
  children: React.ReactNode;
}

const SettingsSection: React.FC<SettingsSectionProps> = ({
  title,
  description,
  icon: Icon,
  children
}) => (
  <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
    <div className="px-6 py-4 border-b border-gray-100 bg-gray-50">
      <div className="flex items-center gap-3">
        <div className="p-2 bg-blue-100 rounded-lg">
          <Icon className="w-5 h-5 text-blue-600" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
          {description && (
            <p className="text-sm text-gray-500 mt-0.5">{description}</p>
          )}
        </div>
      </div>
    </div>
    <div className="p-6 space-y-6">{children}</div>
  </div>
);

// ============================================================================
// FORM COMPONENTS
// ============================================================================

interface ToggleProps {
  label: string;
  description?: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
}

const Toggle: React.FC<ToggleProps> = ({
  label,
  description,
  checked,
  onChange,
  disabled
}) => (
  <div className="flex items-center justify-between">
    <div>
      <p className="text-sm font-medium text-gray-900">{label}</p>
      {description && (
        <p className="text-xs text-gray-500 mt-0.5">{description}</p>
      )}
    </div>
    <button
      type="button"
      onClick={() => !disabled && onChange(!checked)}
      disabled={disabled}
      className={cn(
        'relative inline-flex h-6 w-11 items-center rounded-full transition-colors',
        checked ? 'bg-blue-600' : 'bg-gray-200',
        disabled && 'opacity-50 cursor-not-allowed'
      )}
    >
      <span
        className={cn(
          'inline-block h-4 w-4 transform rounded-full bg-white transition-transform shadow-sm',
          checked ? 'translate-x-6' : 'translate-x-1'
        )}
      />
    </button>
  </div>
);

interface SelectFieldProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
  description?: string;
}

const SelectField: React.FC<SelectFieldProps> = ({
  label,
  value,
  onChange,
  options,
  description
}) => (
  <div>
    <label className="block text-sm font-medium text-gray-700 mb-1.5">
      {label}
    </label>
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="w-full px-3 py-2 rounded-lg border border-gray-300 bg-white text-gray-900 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
    >
      {options.map((opt) => (
        <option key={opt.value} value={opt.value}>
          {opt.label}
        </option>
      ))}
    </select>
    {description && (
      <p className="text-xs text-gray-500 mt-1">{description}</p>
    )}
  </div>
);

interface InputFieldProps {
  label: string;
  type?: string;
  value: string | number;
  onChange: (value: string) => void;
  placeholder?: string;
  description?: string;
  disabled?: boolean;
}

const InputField: React.FC<InputFieldProps> = ({
  label,
  type = 'text',
  value,
  onChange,
  placeholder,
  description,
  disabled
}) => (
  <div>
    <label className="block text-sm font-medium text-gray-700 mb-1.5">
      {label}
    </label>
    <input
      type={type}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      disabled={disabled}
      className={cn(
        'w-full px-3 py-2 rounded-lg border border-gray-300 bg-white text-gray-900 text-sm',
        'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
        'disabled:bg-gray-100 disabled:cursor-not-allowed'
      )}
    />
    {description && (
      <p className="text-xs text-gray-500 mt-1">{description}</p>
    )}
  </div>
);

// ============================================================================
// THEME SELECTOR
// ============================================================================

interface ThemeSelectorProps {
  value: 'light' | 'dark' | 'system';
  onChange: (value: 'light' | 'dark' | 'system') => void;
}

const ThemeSelector: React.FC<ThemeSelectorProps> = ({ value, onChange }) => {
  const themes = [
    { id: 'light', label: 'Light', icon: Sun },
    { id: 'dark', label: 'Dark', icon: Moon },
    { id: 'system', label: 'System', icon: Monitor }
  ] as const;

  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-3">
        Theme
      </label>
      <div className="grid grid-cols-3 gap-3">
        {themes.map((theme) => (
          <button
            key={theme.id}
            type="button"
            onClick={() => onChange(theme.id)}
            className={cn(
              'flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all',
              value === theme.id
                ? 'border-blue-500 bg-blue-50'
                : 'border-gray-200 hover:border-gray-300'
            )}
          >
            <theme.icon
              className={cn(
                'w-6 h-6',
                value === theme.id ? 'text-blue-600' : 'text-gray-400'
              )}
            />
            <span
              className={cn(
                'text-sm font-medium',
                value === theme.id ? 'text-blue-700' : 'text-gray-600'
              )}
            >
              {theme.label}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
};

// ============================================================================
// MAIN COMPONENT
// ============================================================================

const UserSettings: React.FC = () => {
  const setTheme = useAppStore((state) => state.setTheme);
  
  // State
  const [profile, setProfile] = useState<UserProfile>(mockProfile);
  const [preferences, setPreferences] = useState<UserPreferences>(defaultPreferences);
  const [notifications, setNotifications] = useState<NotificationSettings>(defaultNotifications);
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  // Handlers
  const updatePreference = useCallback(<K extends keyof UserPreferences>(
    key: K,
    value: UserPreferences[K]
  ) => {
    setPreferences((prev) => ({ ...prev, [key]: value }));
    if (key === 'theme') {
      setTheme(value as 'light' | 'dark' | 'system');
    }
  }, [setTheme]);

  const updateNotification = useCallback(<K extends keyof NotificationSettings>(
    key: K,
    value: NotificationSettings[K]
  ) => {
    setNotifications((prev) => ({ ...prev, [key]: value }));
  }, []);

  const handleSave = async () => {
    setIsSaving(true);
    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 1000));
    setIsSaving(false);
    setSaveSuccess(true);
    setTimeout(() => setSaveSuccess(false), 3000);
  };

  const handleExportData = () => {
    const data = { profile, preferences, notifications };
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'dhg-ai-factory-settings.json';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">User Settings</h2>
          <p className="text-gray-600 mt-1">
            Manage your profile, preferences, and notifications
          </p>
        </div>
        <button
          onClick={handleSave}
          disabled={isSaving}
          className={cn(
            'flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all',
            saveSuccess
              ? 'bg-green-600 text-white'
              : 'bg-blue-600 text-white hover:bg-blue-700'
          )}
        >
          {isSaving ? (
            <>
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
              >
                <Save className="w-4 h-4" />
              </motion.div>
              Saving...
            </>
          ) : saveSuccess ? (
            <>
              <Check className="w-4 h-4" />
              Saved!
            </>
          ) : (
            <>
              <Save className="w-4 h-4" />
              Save Changes
            </>
          )}
        </button>
      </div>

      {/* Profile Section */}
      <SettingsSection
        title="Profile"
        description="Your personal information"
        icon={User}
      >
        {/* Avatar */}
        <div className="flex items-center gap-6">
          <div className="relative">
            <div className="w-24 h-24 rounded-full bg-gradient-to-br from-blue-500 to-blue-700 flex items-center justify-center text-white text-2xl font-bold">
              {profile.name.split(' ').map(n => n[0]).join('')}
            </div>
            <button className="absolute bottom-0 right-0 p-2 bg-white rounded-full shadow-lg border border-gray-200 hover:bg-gray-50">
              <Camera className="w-4 h-4 text-gray-600" />
            </button>
          </div>
          <div>
            <h4 className="text-lg font-semibold text-gray-900">{profile.name}</h4>
            <p className="text-sm text-gray-500">{profile.email}</p>
            <span className={cn(
              'inline-block mt-2 px-2 py-0.5 rounded text-xs font-medium',
              profile.role === 'admin' ? 'bg-purple-100 text-purple-800' :
              profile.role === 'editor' ? 'bg-blue-100 text-blue-800' :
              'bg-gray-100 text-gray-800'
            )}>
              {profile.role.charAt(0).toUpperCase() + profile.role.slice(1)}
            </span>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <InputField
            label="Full Name"
            value={profile.name}
            onChange={(value) => setProfile(p => ({ ...p, name: value }))}
          />
          <InputField
            label="Email"
            type="email"
            value={profile.email}
            onChange={(value) => setProfile(p => ({ ...p, email: value }))}
          />
          <InputField
            label="Organization"
            value={profile.organization}
            onChange={(value) => setProfile(p => ({ ...p, organization: value }))}
          />
          <InputField
            label="Department"
            value={profile.department}
            onChange={(value) => setProfile(p => ({ ...p, department: value }))}
          />
          <SelectField
            label="Timezone"
            value={profile.timezone}
            onChange={(value) => setProfile(p => ({ ...p, timezone: value }))}
            options={[
              { value: 'America/New_York', label: 'Eastern Time (ET)' },
              { value: 'America/Chicago', label: 'Central Time (CT)' },
              { value: 'America/Denver', label: 'Mountain Time (MT)' },
              { value: 'America/Los_Angeles', label: 'Pacific Time (PT)' },
              { value: 'Europe/London', label: 'GMT/BST' },
              { value: 'Europe/Paris', label: 'Central European Time' }
            ]}
          />
        </div>
      </SettingsSection>

      {/* Appearance Section */}
      <SettingsSection
        title="Appearance"
        description="Customize how the app looks and feels"
        icon={Palette}
      >
        <ThemeSelector
          value={preferences.theme}
          onChange={(value) => updatePreference('theme', value)}
        />

        <SelectField
          label="Language"
          value={preferences.language}
          onChange={(value) => updatePreference('language', value)}
          options={[
            { value: 'en-US', label: 'English (US)' },
            { value: 'en-GB', label: 'English (UK)' },
            { value: 'es', label: 'Español' },
            { value: 'fr', label: 'Français' },
            { value: 'de', label: 'Deutsch' }
          ]}
        />

        <Toggle
          label="Compact Mode"
          description="Reduce spacing and padding throughout the interface"
          checked={preferences.compactMode}
          onChange={(value) => updatePreference('compactMode', value)}
        />

        <Toggle
          label="Animations"
          description="Enable smooth transitions and animations"
          checked={preferences.animations}
          onChange={(value) => updatePreference('animations', value)}
        />

        <Toggle
          label="Sound Effects"
          description="Play sounds for notifications and actions"
          checked={preferences.soundEffects}
          onChange={(value) => updatePreference('soundEffects', value)}
        />
      </SettingsSection>

      {/* Defaults Section */}
      <SettingsSection
        title="Content Defaults"
        description="Default values for new content requests"
        icon={Globe}
      >
        <SelectField
          label="Default Compliance Mode"
          value={preferences.defaultComplianceMode}
          onChange={(value) => updatePreference('defaultComplianceMode', value as 'auto' | 'cme' | 'non_cme')}
          options={[
            { value: 'auto', label: 'Auto-detect' },
            { value: 'cme', label: 'CME (ACCME Compliant)' },
            { value: 'non_cme', label: 'Non-CME (Business Content)' }
          ]}
        />

        <div className="grid grid-cols-2 gap-4">
          <InputField
            label="Default Word Count"
            type="number"
            value={preferences.defaultWordCount}
            onChange={(value) => updatePreference('defaultWordCount', parseInt(value) || 1500)}
            description="Target word count for generated content"
          />
          <InputField
            label="Default Reference Count"
            type="number"
            value={preferences.defaultReferenceCount}
            onChange={(value) => updatePreference('defaultReferenceCount', parseInt(value) || 12)}
            description="Number of citations to include"
          />
        </div>

        <Toggle
          label="Auto-Save Drafts"
          description="Automatically save form progress"
          checked={preferences.autoSave}
          onChange={(value) => updatePreference('autoSave', value)}
        />
      </SettingsSection>

      {/* Notifications Section */}
      <SettingsSection
        title="Notifications"
        description="Control how and when you receive notifications"
        icon={Bell}
      >
        <Toggle
          label="Email Notifications"
          description="Receive updates via email"
          checked={notifications.emailNotifications}
          onChange={(value) => updateNotification('emailNotifications', value)}
        />

        <Toggle
          label="Push Notifications"
          description="Receive browser/device notifications"
          checked={notifications.pushNotifications}
          onChange={(value) => updateNotification('pushNotifications', value)}
        />

        <div className="border-t border-gray-100 pt-4 mt-4">
          <p className="text-sm font-medium text-gray-700 mb-4">Notification Types</p>
          
          <div className="space-y-4">
            <Toggle
              label="Generation Complete"
              description="When content generation finishes"
              checked={notifications.generationComplete}
              onChange={(value) => updateNotification('generationComplete', value)}
              disabled={!notifications.emailNotifications && !notifications.pushNotifications}
            />

            <Toggle
              label="Validation Alerts"
              description="When content fails validation checks"
              checked={notifications.validationAlerts}
              onChange={(value) => updateNotification('validationAlerts', value)}
              disabled={!notifications.emailNotifications && !notifications.pushNotifications}
            />

            <Toggle
              label="Weekly Digest"
              description="Summary of activity each week"
              checked={notifications.weeklyDigest}
              onChange={(value) => updateNotification('weeklyDigest', value)}
              disabled={!notifications.emailNotifications}
            />

            <Toggle
              label="Marketing Emails"
              description="Product updates and announcements"
              checked={notifications.marketingEmails}
              onChange={(value) => updateNotification('marketingEmails', value)}
              disabled={!notifications.emailNotifications}
            />
          </div>
        </div>
      </SettingsSection>

      {/* Security Section */}
      <SettingsSection
        title="Security"
        description="Manage your password and security settings"
        icon={Shield}
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">
              Current Password
            </label>
            <div className="relative">
              <input
                type={showPassword ? 'text' : 'password'}
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                className="w-full px-3 py-2 pr-10 rounded-lg border border-gray-300 bg-white text-gray-900 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">
                New Password
              </label>
              <input
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-gray-300 bg-white text-gray-900 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">
                Confirm Password
              </label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-gray-300 bg-white text-gray-900 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <button className="px-4 py-2 bg-gray-900 text-white rounded-lg text-sm font-medium hover:bg-gray-800">
            Update Password
          </button>
        </div>

        <div className="border-t border-gray-100 pt-6 mt-6">
          <h4 className="text-sm font-medium text-gray-900 mb-4">Two-Factor Authentication</h4>
          <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-green-100 rounded-lg">
                <Shield className="w-5 h-5 text-green-600" />
              </div>
              <div>
                <p className="text-sm font-medium text-gray-900">2FA Enabled</p>
                <p className="text-xs text-gray-500">Using authenticator app</p>
              </div>
            </div>
            <button className="text-sm text-blue-600 hover:text-blue-800 font-medium">
              Manage
            </button>
          </div>
        </div>
      </SettingsSection>

      {/* Data & Privacy Section */}
      <SettingsSection
        title="Data & Privacy"
        description="Export your data or delete your account"
        icon={Key}
      >
        <div className="space-y-4">
          <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
            <div>
              <p className="text-sm font-medium text-gray-900">Export Your Data</p>
              <p className="text-xs text-gray-500 mt-0.5">Download all your settings and history</p>
            </div>
            <button
              onClick={handleExportData}
              className="flex items-center gap-2 px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              <Download className="w-4 h-4" />
              Export
            </button>
          </div>

          <div className="flex items-center justify-between p-4 bg-red-50 rounded-lg border border-red-200">
            <div>
              <p className="text-sm font-medium text-red-900">Delete Account</p>
              <p className="text-xs text-red-700 mt-0.5">Permanently delete your account and data</p>
            </div>
            <button className="flex items-center gap-2 px-3 py-2 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700">
              <Trash2 className="w-4 h-4" />
              Delete
            </button>
          </div>
        </div>
      </SettingsSection>

      {/* Sign Out */}
      <div className="flex justify-end">
        <button className="flex items-center gap-2 px-4 py-2 text-gray-600 hover:text-gray-900 font-medium">
          <LogOut className="w-4 h-4" />
          Sign Out
        </button>
      </div>
    </div>
  );
};

export default UserSettings;
