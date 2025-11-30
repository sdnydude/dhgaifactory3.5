// DHG AI Factory - Content Preview Panel Component
// Real-time display of generated content with validation status

import React, { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import { 
  Download, 
  Copy, 
  Check, 
  X, 
  AlertTriangle, 
  FileText, 
  Code, 
  BookOpen,
  CheckCircle,
  XCircle,
  AlertCircle,
  Loader,
  ExternalLink
} from 'lucide-react';
import { cn } from '../lib/utils';
import { useAppStore, selectCurrentContent } from '../store/useAppStore';
import { GeneratedContent, ValidationResult, ValidationIssue, ComplianceMode } from '../types';

// ============================================================================
// TYPES
// ============================================================================

interface ContentPreviewPanelProps {
  className?: string;
}

type TabId = 'preview' | 'markdown' | 'json' | 'references';

interface TabConfig {
  id: TabId;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}

// ============================================================================
// CONSTANTS
// ============================================================================

const TABS: TabConfig[] = [
  { id: 'preview', label: 'Preview', icon: FileText },
  { id: 'markdown', label: 'Markdown', icon: Code },
  { id: 'json', label: 'JSON', icon: BookOpen },
  { id: 'references', label: 'References', icon: ExternalLink }
];

// ============================================================================
// VALIDATION BADGE COMPONENT
// ============================================================================

const ValidationBadge: React.FC<{ status: ValidationResult['status'] }> = ({ status }) => {
  const config = {
    passed: {
      bg: 'bg-green-50',
      border: 'border-green-200',
      text: 'text-green-700',
      icon: CheckCircle,
      label: 'Validation Passed'
    },
    failed: {
      bg: 'bg-red-50',
      border: 'border-red-200',
      text: 'text-red-700',
      icon: XCircle,
      label: 'Validation Failed'
    },
    warning: {
      bg: 'bg-amber-50',
      border: 'border-amber-200',
      text: 'text-amber-700',
      icon: AlertCircle,
      label: 'Validation Warnings'
    }
  };
  
  const { bg, border, text, icon: Icon, label } = config[status];
  
  return (
    <div className={cn(
      'flex items-center gap-2 px-3 py-2 rounded-lg border',
      bg, border, text
    )}>
      <Icon className="w-4 h-4" />
      <span className="text-sm font-medium">{label}</span>
    </div>
  );
};

// ============================================================================
// VALIDATION DETAILS COMPONENT
// ============================================================================

const ValidationDetails: React.FC<{ validation: ValidationResult }> = ({ validation }) => {
  const [expanded, setExpanded] = useState(false);
  
  const checkOrder = [
    'source_verification',
    'reference_validation', 
    'word_count',
    'accme_compliance',
    'fair_balance',
    'hallucination_detection'
  ];
  
  const checkLabels: Record<string, string> = {
    source_verification: 'Source Verification',
    reference_validation: 'Reference Validation',
    word_count: 'Word Count Check',
    accme_compliance: 'ACCME Compliance',
    fair_balance: 'Fair Balance',
    hallucination_detection: 'Hallucination Detection'
  };
  
  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-3 bg-gray-50 hover:bg-gray-100 transition-colors"
      >
        <ValidationBadge status={validation.status} />
        <span className="text-sm text-gray-500">
          {expanded ? 'Hide details' : 'Show details'}
        </span>
      </button>
      
      {/* Details */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            <div className="p-4 space-y-3 border-t border-gray-200">
              {/* Check Results */}
              <div className="space-y-2">
                {checkOrder.map(checkId => {
                  const check = validation.checks[checkId];
                  if (!check) return null;
                  
                  return (
                    <div key={checkId} className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        {check.status === 'passed' ? (
                          <CheckCircle className="w-4 h-4 text-green-500" />
                        ) : check.status === 'warning' ? (
                          <AlertCircle className="w-4 h-4 text-amber-500" />
                        ) : (
                          <XCircle className="w-4 h-4 text-red-500" />
                        )}
                        <span className="text-sm text-gray-700">
                          {checkLabels[checkId] || checkId}
                        </span>
                      </div>
                      <span className={cn(
                        'text-xs font-medium px-2 py-0.5 rounded',
                        check.status === 'passed' ? 'bg-green-100 text-green-700' :
                        check.status === 'warning' ? 'bg-amber-100 text-amber-700' :
                        'bg-red-100 text-red-700'
                      )}>
                        {check.score}%
                      </span>
                    </div>
                  );
                })}
              </div>
              
              {/* Violations */}
              {validation.violations.length > 0 && (
                <div className="mt-4">
                  <h4 className="text-xs font-semibold text-red-700 uppercase mb-2">
                    Violations ({validation.violations.length})
                  </h4>
                  <div className="space-y-2">
                    {validation.violations.map((issue, idx) => (
                      <IssueCard key={idx} issue={issue} type="violation" />
                    ))}
                  </div>
                </div>
              )}
              
              {/* Warnings */}
              {validation.warnings.length > 0 && (
                <div className="mt-4">
                  <h4 className="text-xs font-semibold text-amber-700 uppercase mb-2">
                    Warnings ({validation.warnings.length})
                  </h4>
                  <div className="space-y-2">
                    {validation.warnings.map((issue, idx) => (
                      <IssueCard key={idx} issue={issue} type="warning" />
                    ))}
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

// ============================================================================
// ISSUE CARD COMPONENT
// ============================================================================

const IssueCard: React.FC<{ issue: ValidationIssue; type: 'violation' | 'warning' }> = ({ issue, type }) => (
  <div className={cn(
    'p-3 rounded-lg border text-sm',
    type === 'violation' 
      ? 'bg-red-50 border-red-200' 
      : 'bg-amber-50 border-amber-200'
  )}>
    <div className="flex items-start gap-2">
      {type === 'violation' ? (
        <X className="w-4 h-4 text-red-500 mt-0.5" />
      ) : (
        <AlertTriangle className="w-4 h-4 text-amber-500 mt-0.5" />
      )}
      <div>
        <p className={cn(
          'font-medium',
          type === 'violation' ? 'text-red-800' : 'text-amber-800'
        )}>
          {issue.message}
        </p>
        {issue.section && (
          <p className={cn(
            'text-xs mt-1',
            type === 'violation' ? 'text-red-600' : 'text-amber-600'
          )}>
            Section: {issue.section}
          </p>
        )}
      </div>
    </div>
  </div>
);

// ============================================================================
// METADATA CARD COMPONENT
// ============================================================================

const MetadataCard: React.FC<{ content: GeneratedContent }> = ({ content }) => {
  const complianceBadge: Record<ComplianceMode, { bg: string; text: string; label: string }> = {
    cme: { bg: 'bg-green-100', text: 'text-green-800', label: 'CME' },
    non_cme: { bg: 'bg-cyan-100', text: 'text-cyan-800', label: 'Non-CME' },
    auto: { bg: 'bg-blue-100', text: 'text-blue-800', label: 'Auto' }
  };
  
  const badge = complianceBadge[content.metadata.compliance_mode];
  
  return (
    <div className="flex flex-wrap items-center gap-3 p-3 bg-gray-50 rounded-lg border border-gray-200">
      <span className={cn(
        'px-2 py-0.5 rounded text-xs font-semibold',
        badge.bg, badge.text
      )}>
        {badge.label}
      </span>
      
      <div className="flex items-center gap-1 text-xs text-gray-600">
        <FileText className="w-3 h-3" />
        <span>{content.metadata.word_count.toLocaleString()} words</span>
      </div>
      
      <div className="flex items-center gap-1 text-xs text-gray-600">
        <BookOpen className="w-3 h-3" />
        <span>{content.metadata.reference_count} references</span>
      </div>
      
      {content.metadata.moore_levels && content.metadata.moore_levels.length > 0 && (
        <div className="flex items-center gap-1 text-xs text-gray-600">
          <span>Moore Levels:</span>
          <span className="font-medium">{content.metadata.moore_levels.join(', ')}</span>
        </div>
      )}
    </div>
  );
};

// ============================================================================
// MAIN COMPONENT
// ============================================================================

const ContentPreviewPanel: React.FC<ContentPreviewPanelProps> = ({ className }) => {
  const content = useAppStore(selectCurrentContent);
  const [activeTab, setActiveTab] = useState<TabId>('preview');
  const [copied, setCopied] = useState(false);
  
  // Extract references from content (basic regex)
  const references = useMemo(() => {
    if (!content) return [];
    const refMatch = content.content.match(/\[\d+\]\s+.+/g);
    return refMatch || [];
  }, [content]);
  
  const handleCopy = async () => {
    if (!content) return;
    
    const textToCopy = activeTab === 'json' 
      ? JSON.stringify(content, null, 2)
      : content.content;
    
    await navigator.clipboard.writeText(textToCopy);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  
  const handleDownload = () => {
    if (!content) return;
    
    const filename = `${content.title.replace(/\s+/g, '_')}_${new Date().toISOString().split('T')[0]}`;
    let downloadContent: string;
    let mimeType: string;
    let extension: string;
    
    switch (activeTab) {
      case 'json':
        downloadContent = JSON.stringify(content, null, 2);
        mimeType = 'application/json';
        extension = 'json';
        break;
      case 'markdown':
      case 'preview':
      default:
        downloadContent = content.content;
        mimeType = 'text/markdown';
        extension = 'md';
        break;
    }
    
    const blob = new Blob([downloadContent], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${filename}.${extension}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };
  
  // Empty State
  if (!content) {
    return (
      <div className={cn('flex flex-col h-full bg-white', className)}>
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
          <h3 className="text-sm font-semibold text-gray-900">Generated Content</h3>
        </div>
        <div className="flex-1 flex flex-col items-center justify-center p-8 text-center">
          <div className="w-16 h-16 rounded-full bg-gray-100 flex items-center justify-center mb-4">
            <FileText className="w-8 h-8 text-gray-400" />
          </div>
          <h4 className="text-sm font-medium text-gray-900 mb-1">
            No content generated yet
          </h4>
          <p className="text-xs text-gray-500 max-w-[200px]">
            Submit a request to see the generated content here
          </p>
        </div>
      </div>
    );
  }
  
  return (
    <div className={cn('flex flex-col h-full bg-white', className)}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
        <h3 className="text-sm font-semibold text-gray-900 truncate max-w-[200px]">
          {content.title || 'Generated Content'}
        </h3>
        <div className="flex items-center gap-2">
          <button
            onClick={handleCopy}
            className={cn(
              'p-2 rounded-lg transition-colors',
              'hover:bg-gray-100 text-gray-600'
            )}
            title="Copy to clipboard"
          >
            {copied ? (
              <Check className="w-4 h-4 text-green-500" />
            ) : (
              <Copy className="w-4 h-4" />
            )}
          </button>
          <button
            onClick={handleDownload}
            className={cn(
              'p-2 rounded-lg transition-colors',
              'hover:bg-gray-100 text-gray-600'
            )}
            title="Download"
          >
            <Download className="w-4 h-4" />
          </button>
        </div>
      </div>
      
      {/* Tabs */}
      <div className="flex border-b border-gray-200">
        {TABS.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              'flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium transition-colors',
              activeTab === tab.id
                ? 'text-blue-600 border-b-2 border-blue-600 -mb-px'
                : 'text-gray-500 hover:text-gray-700'
            )}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>
      
      {/* Content Area */}
      <div className="flex-1 overflow-y-auto p-4">
        {/* Metadata */}
        <MetadataCard content={content} />
        
        {/* Validation (if available) */}
        {content.validation && (
          <div className="mt-4">
            <ValidationDetails validation={content.validation} />
          </div>
        )}
        
        {/* Tab Content */}
        <div className="mt-4">
          {activeTab === 'preview' && (
            <div className="prose prose-sm max-w-none">
              <ReactMarkdown>{content.content}</ReactMarkdown>
            </div>
          )}
          
          {activeTab === 'markdown' && (
            <pre className="p-4 bg-gray-900 text-gray-100 rounded-lg overflow-x-auto text-xs font-mono">
              {content.content}
            </pre>
          )}
          
          {activeTab === 'json' && (
            <pre className="p-4 bg-gray-900 text-gray-100 rounded-lg overflow-x-auto text-xs font-mono">
              {JSON.stringify(content, null, 2)}
            </pre>
          )}
          
          {activeTab === 'references' && (
            <div className="space-y-2">
              {references.length > 0 ? (
                references.map((ref, idx) => (
                  <div key={idx} className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                    <p className="text-sm text-gray-700">{ref}</p>
                  </div>
                ))
              ) : (
                <p className="text-sm text-gray-500 text-center py-8">
                  No references found in content
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ContentPreviewPanel;
