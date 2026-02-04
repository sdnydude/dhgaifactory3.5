/**
 * ReviewPanel - Document Review with Plate JS
 * =============================================
 * Implements Decision R7: Plate JS for Markdown review with inline suggestions.
 * 
 * Features:
 * - Display grant document in rich text editor
 * - Highlight text and add comments
 * - Track all annotations as change list
 * - Submit review decision with annotations
 */

import React, { useState, useCallback, useMemo, useEffect } from 'react';
import { 
  Check, 
  X, 
  MessageSquare, 
  Send, 
  Clock, 
  AlertTriangle,
  FileText,
  ChevronDown,
  ChevronUp,
  Trash2
} from 'lucide-react';

// Note: Plate JS requires installation: npm install @udecode/plate-core slate slate-react
// For now, we'll use a simpler implementation that can be upgraded to Plate later

// Annotation type
const createAnnotation = (id, selection, comment, type = 'comment') => ({
  id,
  selection,
  comment,
  type, // 'comment' | 'suggestion' | 'revision'
  createdAt: new Date().toISOString(),
  resolved: false
});

const ReviewPanel = ({ 
  projectId, 
  projectName,
  documentContent,
  slaDeadline,
  onSubmitReview,
  onClose 
}) => {
  const [annotations, setAnnotations] = useState([]);
  const [selectedText, setSelectedText] = useState('');
  const [selectionRange, setSelectionRange] = useState(null);
  const [commentText, setCommentText] = useState('');
  const [showCommentInput, setShowCommentInput] = useState(false);
  const [reviewNotes, setReviewNotes] = useState('');
  const [showAnnotations, setShowAnnotations] = useState(true);
  const [decision, setDecision] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [hoursRemaining, setHoursRemaining] = useState(null);

  // Calculate SLA hours remaining
  useEffect(() => {
    if (slaDeadline) {
      const updateHours = () => {
        const now = new Date();
        const deadline = new Date(slaDeadline);
        const hours = (deadline - now) / (1000 * 60 * 60);
        setHoursRemaining(Math.max(0, hours));
      };
      updateHours();
      const interval = setInterval(updateHours, 60000);
      return () => clearInterval(interval);
    }
  }, [slaDeadline]);

  // Handle text selection
  const handleTextSelection = useCallback(() => {
    const selection = window.getSelection();
    if (selection && selection.toString().trim()) {
      setSelectedText(selection.toString());
      setSelectionRange({
        start: selection.anchorOffset,
        end: selection.focusOffset,
        text: selection.toString()
      });
      setShowCommentInput(true);
    }
  }, []);

  // Add annotation
  const addAnnotation = useCallback((type) => {
    if (!selectedText || !commentText) return;
    
    const annotation = createAnnotation(
      `ann-${Date.now()}`,
      selectionRange,
      commentText,
      type
    );
    
    setAnnotations(prev => [...prev, annotation]);
    setCommentText('');
    setSelectedText('');
    setSelectionRange(null);
    setShowCommentInput(false);
  }, [selectedText, commentText, selectionRange]);

  // Remove annotation
  const removeAnnotation = useCallback((id) => {
    setAnnotations(prev => prev.filter(a => a.id !== id));
  }, []);

  // Submit review
  const handleSubmitReview = async () => {
    if (!decision) return;
    
    setIsSubmitting(true);
    try {
      await onSubmitReview({
        decision,
        notes: reviewNotes,
        annotations: annotations.map(a => ({
          selection: a.selection,
          comment: a.comment,
          type: a.type,
          createdAt: a.createdAt
        }))
      });
    } catch (error) {
      console.error('Failed to submit review:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  // SLA warning styling
  const getSlaStyle = () => {
    if (!hoursRemaining) return {};
    if (hoursRemaining < 4) return { color: '#ef4444', fontWeight: 600 };
    if (hoursRemaining < 8) return { color: '#f59e0b', fontWeight: 500 };
    return { color: '#22c55e' };
  };

  return (
    <div className="review-panel" style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <div style={styles.headerLeft}>
          <FileText size={20} />
          <span style={styles.title}>Review: {projectName}</span>
        </div>
        <div style={styles.headerRight}>
          {hoursRemaining !== null && (
            <div style={{ ...styles.slaIndicator, ...getSlaStyle() }}>
              <Clock size={16} />
              <span>{hoursRemaining.toFixed(1)}h remaining</span>
            </div>
          )}
          <button onClick={onClose} style={styles.closeButton}>
            <X size={20} />
          </button>
        </div>
      </div>

      {/* Document Content */}
      <div 
        style={styles.documentArea}
        onMouseUp={handleTextSelection}
      >
        <div style={styles.documentContent}>
          {documentContent ? (
            <div 
              style={styles.markdownContent}
              dangerouslySetInnerHTML={{ __html: documentContent }}
            />
          ) : (
            <div style={styles.placeholder}>
              <FileText size={48} opacity={0.3} />
              <p>Loading document...</p>
            </div>
          )}
        </div>
      </div>

      {/* Comment Input (shows when text selected) */}
      {showCommentInput && selectedText && (
        <div style={styles.commentInput}>
          <div style={styles.selectedTextPreview}>
            <strong>Selected:</strong> "{selectedText.substring(0, 100)}..."
          </div>
          <textarea
            value={commentText}
            onChange={(e) => setCommentText(e.target.value)}
            placeholder="Add your comment or suggestion..."
            style={styles.textarea}
            rows={3}
          />
          <div style={styles.commentActions}>
            <button
              onClick={() => addAnnotation('comment')}
              style={styles.commentButton}
              disabled={!commentText}
            >
              <MessageSquare size={16} />
              Comment
            </button>
            <button
              onClick={() => addAnnotation('suggestion')}
              style={{ ...styles.commentButton, ...styles.suggestionButton }}
              disabled={!commentText}
            >
              <AlertTriangle size={16} />
              Suggest Change
            </button>
            <button
              onClick={() => {
                setShowCommentInput(false);
                setSelectedText('');
                setCommentText('');
              }}
              style={styles.cancelButton}
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Annotations List */}
      <div style={styles.annotationsSection}>
        <button 
          onClick={() => setShowAnnotations(!showAnnotations)}
          style={styles.annotationsToggle}
        >
          <span>Annotations ({annotations.length})</span>
          {showAnnotations ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>
        
        {showAnnotations && (
          <div style={styles.annotationsList}>
            {annotations.length === 0 ? (
              <p style={styles.noAnnotations}>
                Select text in the document to add comments or suggestions.
              </p>
            ) : (
              annotations.map((ann) => (
                <div key={ann.id} style={styles.annotationItem}>
                  <div style={styles.annotationHeader}>
                    <span style={{
                      ...styles.annotationType,
                      backgroundColor: ann.type === 'suggestion' ? '#fef3c7' : '#dbeafe'
                    }}>
                      {ann.type === 'suggestion' ? 'Suggestion' : 'Comment'}
                    </span>
                    <button 
                      onClick={() => removeAnnotation(ann.id)}
                      style={styles.deleteButton}
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                  <div style={styles.annotationText}>"{ann.selection.text}"</div>
                  <div style={styles.annotationComment}>{ann.comment}</div>
                </div>
              ))
            )}
          </div>
        )}
      </div>

      {/* Review Notes */}
      <div style={styles.reviewNotes}>
        <label style={styles.label}>Overall Review Notes</label>
        <textarea
          value={reviewNotes}
          onChange={(e) => setReviewNotes(e.target.value)}
          placeholder="Add any overall notes for the author..."
          style={styles.textarea}
          rows={3}
        />
      </div>

      {/* Decision Buttons */}
      <div style={styles.decisionSection}>
        <label style={styles.label}>Decision</label>
        <div style={styles.decisionButtons}>
          <button
            onClick={() => setDecision('approved')}
            style={{
              ...styles.decisionButton,
              ...(decision === 'approved' ? styles.approvedSelected : {})
            }}
          >
            <Check size={20} />
            Approve
          </button>
          <button
            onClick={() => setDecision('revision_requested')}
            style={{
              ...styles.decisionButton,
              ...(decision === 'revision_requested' ? styles.revisionSelected : {})
            }}
          >
            <AlertTriangle size={20} />
            Request Revision
          </button>
        </div>
      </div>

      {/* Submit */}
      <div style={styles.submitSection}>
        <button
          onClick={handleSubmitReview}
          disabled={!decision || isSubmitting}
          style={{
            ...styles.submitButton,
            opacity: (!decision || isSubmitting) ? 0.5 : 1
          }}
        >
          <Send size={18} />
          {isSubmitting ? 'Submitting...' : 'Submit Review'}
        </button>
      </div>
    </div>
  );
};

// Styles
const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    backgroundColor: '#1a1a1a',
    color: '#e5e5e5',
    borderRadius: '8px',
    overflow: 'hidden'
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '12px 16px',
    borderBottom: '1px solid #333',
    backgroundColor: '#252525'
  },
  headerLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px'
  },
  headerRight: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px'
  },
  title: {
    fontSize: '14px',
    fontWeight: 600
  },
  slaIndicator: {
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
    fontSize: '12px'
  },
  closeButton: {
    background: 'none',
    border: 'none',
    color: '#888',
    cursor: 'pointer',
    padding: '4px'
  },
  documentArea: {
    flex: 1,
    overflow: 'auto',
    padding: '16px',
    backgroundColor: '#0d0d0d'
  },
  documentContent: {
    maxWidth: '800px',
    margin: '0 auto'
  },
  markdownContent: {
    lineHeight: 1.7,
    fontSize: '14px',
    '& h1, & h2, & h3': {
      marginTop: '24px',
      marginBottom: '12px'
    },
    '& p': {
      marginBottom: '12px'
    }
  },
  placeholder: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    height: '200px',
    color: '#666'
  },
  commentInput: {
    padding: '12px 16px',
    borderTop: '1px solid #333',
    backgroundColor: '#252525'
  },
  selectedTextPreview: {
    fontSize: '12px',
    color: '#888',
    marginBottom: '8px',
    fontStyle: 'italic'
  },
  textarea: {
    width: '100%',
    padding: '8px 12px',
    backgroundColor: '#1a1a1a',
    border: '1px solid #333',
    borderRadius: '6px',
    color: '#e5e5e5',
    fontSize: '13px',
    resize: 'none',
    outline: 'none'
  },
  commentActions: {
    display: 'flex',
    gap: '8px',
    marginTop: '8px'
  },
  commentButton: {
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
    padding: '6px 12px',
    backgroundColor: '#3b82f6',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    fontSize: '12px',
    cursor: 'pointer'
  },
  suggestionButton: {
    backgroundColor: '#f59e0b'
  },
  cancelButton: {
    padding: '6px 12px',
    backgroundColor: 'transparent',
    color: '#888',
    border: '1px solid #444',
    borderRadius: '4px',
    fontSize: '12px',
    cursor: 'pointer'
  },
  annotationsSection: {
    borderTop: '1px solid #333'
  },
  annotationsToggle: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    width: '100%',
    padding: '12px 16px',
    backgroundColor: '#252525',
    border: 'none',
    color: '#e5e5e5',
    cursor: 'pointer',
    fontSize: '13px',
    fontWeight: 500
  },
  annotationsList: {
    maxHeight: '200px',
    overflow: 'auto',
    padding: '8px 16px'
  },
  noAnnotations: {
    fontSize: '12px',
    color: '#666',
    textAlign: 'center',
    padding: '16px'
  },
  annotationItem: {
    padding: '8px 12px',
    backgroundColor: '#1a1a1a',
    borderRadius: '6px',
    marginBottom: '8px'
  },
  annotationHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '4px'
  },
  annotationType: {
    fontSize: '10px',
    padding: '2px 6px',
    borderRadius: '3px',
    fontWeight: 500,
    color: '#1a1a1a'
  },
  deleteButton: {
    background: 'none',
    border: 'none',
    color: '#666',
    cursor: 'pointer',
    padding: '2px'
  },
  annotationText: {
    fontSize: '12px',
    color: '#888',
    marginBottom: '4px',
    fontStyle: 'italic'
  },
  annotationComment: {
    fontSize: '13px'
  },
  reviewNotes: {
    padding: '12px 16px',
    borderTop: '1px solid #333'
  },
  label: {
    display: 'block',
    fontSize: '12px',
    fontWeight: 500,
    marginBottom: '8px',
    color: '#888'
  },
  decisionSection: {
    padding: '12px 16px',
    borderTop: '1px solid #333'
  },
  decisionButtons: {
    display: 'flex',
    gap: '12px'
  },
  decisionButton: {
    flex: 1,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '8px',
    padding: '12px',
    backgroundColor: '#252525',
    border: '2px solid #333',
    borderRadius: '8px',
    color: '#888',
    fontSize: '14px',
    cursor: 'pointer',
    transition: 'all 0.2s'
  },
  approvedSelected: {
    backgroundColor: '#166534',
    borderColor: '#22c55e',
    color: 'white'
  },
  revisionSelected: {
    backgroundColor: '#92400e',
    borderColor: '#f59e0b',
    color: 'white'
  },
  submitSection: {
    padding: '12px 16px',
    borderTop: '1px solid #333',
    backgroundColor: '#252525'
  },
  submitButton: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '8px',
    width: '100%',
    padding: '12px',
    backgroundColor: '#3b82f6',
    border: 'none',
    borderRadius: '8px',
    color: 'white',
    fontSize: '14px',
    fontWeight: 500,
    cursor: 'pointer'
  }
};

export default ReviewPanel;
