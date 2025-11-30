// DHG AI Factory - Request Form Component
// Form for submitting CME content generation requests

import React, { useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { 
  FileText, 
  Users, 
  Building2, 
  Target, 
  Hash, 
  BookOpen,
  Loader,
  Sparkles,
  ChevronDown,
  ChevronUp,
  AlertCircle,
  CheckCircle
} from 'lucide-react';
import { cn } from '../lib/utils';
import { useWebSocket } from '../hooks/useAgentWebSocket';
import { useAppStore } from '../store/useAppStore';
import { 
  TaskType, 
  ComplianceMode, 
  MooreLevel, 
  RequestFormData, 
  RequestFormErrors,
  TASK_TYPES 
} from '../types';

// ============================================================================
// TYPES
// ============================================================================

interface RequestFormProps {
  className?: string;
  onSubmitSuccess?: (requestId: string) => void;
}

// ============================================================================
// CONSTANTS
// ============================================================================

const MOORE_LEVELS: { value: MooreLevel; label: string; description: string }[] = [
  { value: '1', label: 'Level 1', description: 'Participation' },
  { value: '2', label: 'Level 2', description: 'Satisfaction' },
  { value: '3a', label: 'Level 3A', description: 'Declarative Knowledge' },
  { value: '3b', label: 'Level 3B', description: 'Procedural Knowledge' },
  { value: '4', label: 'Level 4', description: 'Competence' },
  { value: '5', label: 'Level 5', description: 'Performance' },
  { value: '6', label: 'Level 6', description: 'Patient Health' },
  { value: '7', label: 'Level 7', description: 'Community Health' }
];

const TARGET_AUDIENCES = [
  'Primary Care Physicians',
  'Cardiologists',
  'Endocrinologists',
  'Oncologists',
  'Nurse Practitioners',
  'Physician Assistants',
  'Pharmacists',
  'Nurses',
  'Medical Students',
  'Residents',
  'Other Healthcare Professionals'
];

const FUNDERS = [
  'Novo Nordisk',
  'Eli Lilly',
  'Pfizer',
  'Merck',
  'AstraZeneca',
  'Bristol-Myers Squibb',
  'Johnson & Johnson',
  'Roche',
  'Amgen',
  'AbbVie',
  'Other'
];

const DEFAULT_FORM_VALUES: RequestFormData = {
  task_type: 'needs_assessment',
  topic: '',
  compliance_mode: 'cme',
  target_audience: 'Primary Care Physicians',
  funder: '',
  moore_levels: ['3a', '4'],
  word_count_target: 1500,
  reference_count: 12,
  additional_context: ''
};

// ============================================================================
// FORM FIELD COMPONENTS
// ============================================================================

interface FormFieldProps {
  label: string;
  required?: boolean;
  error?: string;
  hint?: string;
  children: React.ReactNode;
  icon?: React.ComponentType<{ className?: string }>;
}

const FormField: React.FC<FormFieldProps> = ({ 
  label, 
  required, 
  error, 
  hint, 
  children,
  icon: Icon 
}) => (
  <div className="space-y-1.5">
    <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
      {Icon && <Icon className="w-4 h-4 text-gray-400" />}
      {label}
      {required && <span className="text-red-500">*</span>}
    </label>
    {children}
    {hint && !error && (
      <p className="text-xs text-gray-500">{hint}</p>
    )}
    {error && (
      <p className="flex items-center gap-1 text-xs text-red-600">
        <AlertCircle className="w-3 h-3" />
        {error}
      </p>
    )}
  </div>
);

// ============================================================================
// COMPLIANCE MODE TOGGLE
// ============================================================================

interface ComplianceToggleProps {
  value: ComplianceMode;
  onChange: (value: ComplianceMode) => void;
}

const ComplianceToggle: React.FC<ComplianceToggleProps> = ({ value, onChange }) => {
  const options: { value: ComplianceMode; label: string; color: string }[] = [
    { value: 'auto', label: 'AUTO', color: 'blue' },
    { value: 'cme', label: 'CME', color: 'green' },
    { value: 'non_cme', label: 'NON-CME', color: 'cyan' }
  ];
  
  return (
    <div className="flex bg-gray-100 rounded-lg p-1">
      {options.map(option => (
        <button
          key={option.value}
          type="button"
          onClick={() => onChange(option.value)}
          className={cn(
            'flex-1 px-4 py-2 text-sm font-medium rounded-md transition-all duration-200',
            value === option.value
              ? option.color === 'blue' ? 'bg-blue-600 text-white shadow-sm' :
                option.color === 'green' ? 'bg-green-600 text-white shadow-sm' :
                'bg-cyan-600 text-white shadow-sm'
              : 'text-gray-600 hover:text-gray-900'
          )}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
};

// ============================================================================
// MOORE LEVEL SELECTOR
// ============================================================================

interface MooreLevelSelectorProps {
  value: MooreLevel[];
  onChange: (value: MooreLevel[]) => void;
  error?: string;
}

const MooreLevelSelector: React.FC<MooreLevelSelectorProps> = ({ value, onChange, error }) => {
  const toggleLevel = (level: MooreLevel) => {
    if (value.includes(level)) {
      onChange(value.filter(l => l !== level));
    } else {
      onChange([...value, level]);
    }
  };
  
  return (
    <FormField 
      label="Moore Levels" 
      hint="Select outcome levels to address"
      error={error}
      icon={Target}
    >
      <div className="grid grid-cols-4 gap-2">
        {MOORE_LEVELS.map(level => (
          <button
            key={level.value}
            type="button"
            onClick={() => toggleLevel(level.value)}
            className={cn(
              'p-2 rounded-lg border text-center transition-all duration-200',
              value.includes(level.value)
                ? 'bg-blue-50 border-blue-300 text-blue-700'
                : 'bg-white border-gray-200 text-gray-600 hover:border-gray-300'
            )}
          >
            <div className="text-xs font-semibold">{level.label}</div>
            <div className="text-[10px] text-gray-500 truncate">{level.description}</div>
          </button>
        ))}
      </div>
    </FormField>
  );
};

// ============================================================================
// MAIN FORM COMPONENT
// ============================================================================

const RequestForm: React.FC<RequestFormProps> = ({ className, onSubmitSuccess }) => {
  const { submitRequest, isConnected } = useWebSocket();
  const setCurrentRequest = useAppStore(state => state.setCurrentRequest);
  
  const [formData, setFormData] = useState<RequestFormData>(DEFAULT_FORM_VALUES);
  const [errors, setErrors] = useState<RequestFormErrors>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [submitSuccess, setSubmitSuccess] = useState(false);
  
  // Update form field
  const updateField = useCallback(<K extends keyof RequestFormData>(
    field: K, 
    value: RequestFormData[K]
  ) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    // Clear error when field is updated
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: undefined }));
    }
  }, [errors]);
  
  // Validate form
  const validate = useCallback((): boolean => {
    const newErrors: RequestFormErrors = {};
    
    if (!formData.topic.trim()) {
      newErrors.topic = 'Topic is required';
    } else if (formData.topic.length < 10) {
      newErrors.topic = 'Topic must be at least 10 characters';
    }
    
    if (!formData.target_audience) {
      newErrors.target_audience = 'Target audience is required';
    }
    
    if (formData.word_count_target < 500) {
      newErrors.word_count_target = 'Minimum word count is 500';
    } else if (formData.word_count_target > 10000) {
      newErrors.word_count_target = 'Maximum word count is 10,000';
    }
    
    if (formData.reference_count < 3) {
      newErrors.reference_count = 'Minimum 3 references required';
    } else if (formData.reference_count > 50) {
      newErrors.reference_count = 'Maximum 50 references';
    }
    
    if (formData.additional_context) {
      try {
        JSON.parse(formData.additional_context);
      } catch {
        newErrors.additional_context = 'Invalid JSON format';
      }
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [formData]);
  
  // Handle form submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validate() || !isConnected) return;
    
    setIsSubmitting(true);
    setSubmitSuccess(false);
    
    try {
      // Build request payload
      const request = {
        task_type: formData.task_type,
        topic: formData.topic.trim(),
        compliance_mode: formData.compliance_mode,
        target_audience: formData.target_audience,
        funder: formData.funder || undefined,
        moore_levels: formData.moore_levels.length > 0 ? formData.moore_levels : undefined,
        word_count_target: formData.word_count_target,
        reference_count: formData.reference_count,
        additional_context: formData.additional_context 
          ? JSON.parse(formData.additional_context) 
          : undefined
      };
      
      // Submit via WebSocket
      const requestId = await submitRequest(request);
      
      // Update store
      setCurrentRequest({
        request_id: requestId,
        status: 'processing',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        progress: 0
      });
      
      setSubmitSuccess(true);
      onSubmitSuccess?.(requestId);
      
      // Reset form after short delay
      setTimeout(() => {
        setSubmitSuccess(false);
      }, 3000);
      
    } catch (error) {
      console.error('Failed to submit request:', error);
      setErrors(prev => ({
        ...prev,
        topic: error instanceof Error ? error.message : 'Failed to submit request'
      }));
    } finally {
      setIsSubmitting(false);
    }
  };
  
  const taskConfig = TASK_TYPES[formData.task_type];
  
  return (
    <form onSubmit={handleSubmit} className={cn('space-y-6', className)}>
      {/* Task Type Selection */}
      <FormField 
        label="Task Type" 
        required 
        icon={FileText}
        hint={taskConfig?.description}
      >
        <select
          value={formData.task_type}
          onChange={e => updateField('task_type', e.target.value as TaskType)}
          className={cn(
            'w-full px-3 py-2.5 rounded-lg border border-gray-300',
            'bg-white text-gray-900 text-sm',
            'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
          )}
        >
          {Object.values(TASK_TYPES).map(type => (
            <option key={type.id} value={type.id}>
              {type.name}
            </option>
          ))}
        </select>
      </FormField>
      
      {/* Topic Input */}
      <FormField 
        label="Topic" 
        required 
        error={errors.topic}
        icon={BookOpen}
        hint="Be specific about the clinical topic or educational focus"
      >
        <textarea
          value={formData.topic}
          onChange={e => updateField('topic', e.target.value)}
          placeholder="e.g., Type 2 Diabetes Management with SGLT2 Inhibitors in Patients with Heart Failure"
          rows={3}
          className={cn(
            'w-full px-3 py-2.5 rounded-lg border text-sm',
            errors.topic 
              ? 'border-red-300 focus:ring-red-500 focus:border-red-500' 
              : 'border-gray-300 focus:ring-blue-500 focus:border-blue-500',
            'bg-white text-gray-900',
            'focus:outline-none focus:ring-2 resize-none'
          )}
        />
      </FormField>
      
      {/* Compliance Mode */}
      <FormField 
        label="Compliance Mode" 
        required
        hint={
          formData.compliance_mode === 'cme' 
            ? 'ACCME-compliant with fair balance and source verification' 
            : formData.compliance_mode === 'non_cme'
            ? 'Business content without CME compliance requirements'
            : 'Automatically detect based on topic and context'
        }
      >
        <ComplianceToggle 
          value={formData.compliance_mode}
          onChange={value => updateField('compliance_mode', value)}
        />
      </FormField>
      
      {/* Target Audience */}
      <FormField 
        label="Target Audience" 
        required 
        error={errors.target_audience}
        icon={Users}
      >
        <select
          value={formData.target_audience}
          onChange={e => updateField('target_audience', e.target.value)}
          className={cn(
            'w-full px-3 py-2.5 rounded-lg border border-gray-300',
            'bg-white text-gray-900 text-sm',
            'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
          )}
        >
          {TARGET_AUDIENCES.map(audience => (
            <option key={audience} value={audience}>
              {audience}
            </option>
          ))}
        </select>
      </FormField>
      
      {/* Funder (Optional) */}
      <FormField 
        label="Funder" 
        icon={Building2}
        hint="Select pharmaceutical/industry funder if applicable"
      >
        <select
          value={formData.funder}
          onChange={e => updateField('funder', e.target.value)}
          className={cn(
            'w-full px-3 py-2.5 rounded-lg border border-gray-300',
            'bg-white text-gray-900 text-sm',
            'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
          )}
        >
          <option value="">No funder selected</option>
          {FUNDERS.map(funder => (
            <option key={funder} value={funder}>
              {funder}
            </option>
          ))}
        </select>
      </FormField>
      
      {/* Moore Levels */}
      <MooreLevelSelector
        value={formData.moore_levels}
        onChange={value => updateField('moore_levels', value)}
        error={errors.moore_levels}
      />
      
      {/* Advanced Options Toggle */}
      <button
        type="button"
        onClick={() => setShowAdvanced(!showAdvanced)}
        className="flex items-center gap-2 text-sm font-medium text-gray-600 hover:text-gray-900"
      >
        {showAdvanced ? (
          <ChevronUp className="w-4 h-4" />
        ) : (
          <ChevronDown className="w-4 h-4" />
        )}
        Advanced Options
      </button>
      
      {/* Advanced Options */}
      {showAdvanced && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          className="space-y-4 pl-4 border-l-2 border-gray-200"
        >
          {/* Word Count */}
          <FormField 
            label="Word Count Target" 
            error={errors.word_count_target}
            icon={Hash}
          >
            <input
              type="number"
              value={formData.word_count_target}
              onChange={e => updateField('word_count_target', parseInt(e.target.value) || 0)}
              min={500}
              max={10000}
              step={100}
              className={cn(
                'w-full px-3 py-2.5 rounded-lg border text-sm',
                errors.word_count_target 
                  ? 'border-red-300 focus:ring-red-500' 
                  : 'border-gray-300 focus:ring-blue-500',
                'bg-white text-gray-900',
                'focus:outline-none focus:ring-2'
              )}
            />
          </FormField>
          
          {/* Reference Count */}
          <FormField 
            label="Reference Count" 
            error={errors.reference_count}
            icon={BookOpen}
          >
            <input
              type="number"
              value={formData.reference_count}
              onChange={e => updateField('reference_count', parseInt(e.target.value) || 0)}
              min={3}
              max={50}
              className={cn(
                'w-full px-3 py-2.5 rounded-lg border text-sm',
                errors.reference_count 
                  ? 'border-red-300 focus:ring-red-500' 
                  : 'border-gray-300 focus:ring-blue-500',
                'bg-white text-gray-900',
                'focus:outline-none focus:ring-2'
              )}
            />
          </FormField>
          
          {/* Additional Context (JSON) */}
          <FormField 
            label="Additional Context (JSON)" 
            error={errors.additional_context}
            hint="Optional JSON object with extra parameters"
          >
            <textarea
              value={formData.additional_context}
              onChange={e => updateField('additional_context', e.target.value)}
              placeholder='{"therapeutic_area": "Endocrinology", "prior_content_ids": ["req_abc123"]}'
              rows={3}
              className={cn(
                'w-full px-3 py-2.5 rounded-lg border text-sm font-mono',
                errors.additional_context 
                  ? 'border-red-300 focus:ring-red-500' 
                  : 'border-gray-300 focus:ring-blue-500',
                'bg-white text-gray-900',
                'focus:outline-none focus:ring-2 resize-none'
              )}
            />
          </FormField>
        </motion.div>
      )}
      
      {/* Estimated Duration */}
      <div className="flex items-center gap-2 p-3 bg-gray-50 rounded-lg">
        <Sparkles className="w-4 h-4 text-blue-500" />
        <span className="text-sm text-gray-600">
          Estimated generation time: 
          <span className="font-medium text-gray-900 ml-1">
            ~{Math.ceil(taskConfig?.estimatedDuration / 60) || 1} minute(s)
          </span>
        </span>
      </div>
      
      {/* Submit Button */}
      <button
        type="submit"
        disabled={isSubmitting || !isConnected}
        className={cn(
          'w-full flex items-center justify-center gap-2',
          'px-6 py-3 rounded-xl font-semibold text-white',
          'transition-all duration-200',
          isSubmitting || !isConnected
            ? 'bg-gray-400 cursor-not-allowed'
            : submitSuccess
            ? 'bg-green-600 hover:bg-green-700'
            : 'bg-blue-600 hover:bg-blue-700 shadow-lg shadow-blue-600/25 hover:shadow-blue-600/40'
        )}
      >
        {isSubmitting ? (
          <>
            <Loader className="w-5 h-5 animate-spin" />
            Generating...
          </>
        ) : submitSuccess ? (
          <>
            <CheckCircle className="w-5 h-5" />
            Request Submitted!
          </>
        ) : (
          <>
            <Sparkles className="w-5 h-5" />
            Generate Content
          </>
        )}
      </button>
      
      {!isConnected && (
        <p className="text-center text-sm text-amber-600">
          ⚠️ Not connected to server. Please wait...
        </p>
      )}
    </form>
  );
};

export default RequestForm;
