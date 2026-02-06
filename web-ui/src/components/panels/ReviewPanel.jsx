/**
 * ReviewPanel - Document Review with Inline Annotations
 * ======================================================
 * Two-column layout: 80% document, 20% controls
 * Inline highlighting of comments and suggestions
 */

import React, { useState, useCallback, useEffect, useRef } from 'react';
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
  Trash2,
  Edit3
} from 'lucide-react';

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
  const [decision, setDecision] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [hoursRemaining, setHoursRemaining] = useState(null);
  const [activeAnnotation, setActiveAnnotation] = useState(null);
  const documentRef = useRef(null);

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

  // Handle text selection in document
  const handleTextSelection = useCallback(() => {
    const selection = window.getSelection();
    if (selection && selection.toString().trim() && documentRef.current) {
      const range = selection.getRangeAt(0);
      
      // Check if selection is within document area
      if (documentRef.current.contains(range.commonAncestorContainer)) {
        setSelectedText(selection.toString());
        setSelectionRange({
          text: selection.toString(),
          startOffset: range.startOffset,
          endOffset: range.endOffset
        });
        setShowCommentInput(true);
      }
    }
  }, []);

  // Add annotation with inline highlight
  const addAnnotation = useCallback((type) => {
    if (!selectedText || !commentText) return;
    
    const annotation = {
      id: `ann-${Date.now()}`,
      selection: selectionRange,
      comment: commentText,
      type,
      createdAt: new Date().toISOString(),
      resolved: false
    };
    
    setAnnotations(prev => [...prev, annotation]);
    setCommentText('');
    setSelectedText('');
    setSelectionRange(null);
    setShowCommentInput(false);
    
    // Clear browser selection
    window.getSelection()?.removeAllRanges();
  }, [selectedText, commentText, selectionRange]);

  // Remove annotation
  const removeAnnotation = useCallback((id) => {
    setAnnotations(prev => prev.filter(a => a.id !== id));
    if (activeAnnotation === id) setActiveAnnotation(null);
  }, [activeAnnotation]);

  // Render document with inline highlights
  const renderDocumentWithHighlights = () => {
    if (!documentContent) {
      return (
        <div style={styles.placeholder}>
          <FileText size={48} opacity={0.3} />
          <p>Loading document...</p>
        </div>
      );
    }

    // Create a temporary div to parse HTML
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = documentContent;
    let textContent = tempDiv.textContent || tempDiv.innerText || '';
    
    // If no annotations, return plain content
    if (annotations.length === 0) {
      return (
        <div 
          style={styles.markdownContent}
          dangerouslySetInnerHTML={{ __html: documentContent }}
        />
      );
    }

    // Build highlighted version
    // Sort annotations by their position in text
    const sortedAnnotations = [...annotations].sort((a, b) => {
      const posA = textContent.indexOf(a.selection.text);
      const posB = textContent.indexOf(b.selection.text);
      return posB - posA; // Reverse to replace from end first
    });

    let highlightedContent = documentContent;
    
    sortedAnnotations.forEach(ann => {
      const escapedText = ann.selection.text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      const regex = new RegExp(`(${escapedText})`, 'g');
      const highlightColor = ann.type === 'suggestion' ? '#fef3c7' : '#dbeafe';
      const borderColor = ann.type === 'suggestion' ? '#f59e0b' : '#3b82f6';
      const isActive = activeAnnotation === ann.id;
      
      highlightedContent = highlightedContent.replace(regex, 
        `<mark data-annotation-id="${ann.id}" style="background-color: ${highlightColor}; border-bottom: 2px solid ${borderColor}; padding: 2px 4px; border-radius: 2px; cursor: pointer; ${isActive ? 'box-shadow: 0 0 0 2px ' + borderColor + ';' : ''}">$1</mark>`
      );
    });

    return (
      <div 
        style={styles.markdownContent}
        dangerouslySetInnerHTML={{ __html: highlightedContent }}
        onClick={(e) => {
          const annId = e.target.dataset?.annotationId;
          if (annId) setActiveAnnotation(annId);
        }}
      />
    );
  };

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

  // SLA styling
  const getSlaStyle = () => {
    if (!hoursRemaining) return {};
    if (hoursRemaining < 4) return { color: '#ef4444', fontWeight: 600 };
    if (hoursRemaining < 8) return { color: '#f59e0b', fontWeight: 500 };
    return { color: '#22c55e' };
  };

  return (
    <div style={styles.container}>
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

      {/* Main Layout - 80/20 split */}
      <div style={styles.mainLayout}>
        {/* Document Area - 80% */}
        <div style={styles.documentColumn}>
          <div 
            ref={documentRef}
            style={styles.documentArea}
            onMouseUp={handleTextSelection}
          >
            {renderDocumentWithHighlights()}
          </div>

          {/* Comment Input (floating at bottom of document) */}
          {showCommentInput && selectedText && (
            <div style={styles.commentInput}>
              <div style={styles.selectedTextPreview}>
                <strong>Selected:</strong> "{selectedText.substring(0, 80)}{selectedText.length > 80 ? '...' : ''}"
              </div>
              <textarea
                value={commentText}
                onChange={(e) => setCommentText(e.target.value)}
                placeholder="Add your comment or suggestion..."
                style={styles.textarea}
                rows={2}
                autoFocus
              />
              <div style={styles.commentActions}>
                <button
                  onClick={() => addAnnotation('comment')}
                  style={{
                    ...styles.actionButton,
                    ...styles.commentButton,
                    opacity: commentText ? 1 : 0.5
                  }}
                  disabled={!commentText}
                >
                  <MessageSquare size={14} />
                  Comment
                </button>
                <button
                  onClick={() => addAnnotation('suggestion')}
                  style={{
                    ...styles.actionButton,
                    ...styles.suggestionButton,
                    opacity: commentText ? 1 : 0.5
                  }}
                  disabled={!commentText}
                >
                  <Edit3 size={14} />
                  Suggest Change
                </button>
                <button
                  onClick={() => {
                    setShowCommentInput(false);
                    setSelectedText('');
                    setCommentText('');
                    window.getSelection()?.removeAllRanges();
                  }}
                  style={styles.cancelButton}
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Controls Panel - 20% */}
        <div style={styles.controlsColumn}>
          {/* Annotations List */}
          <div style={styles.section}>
            <div style={styles.sectionHeader}>
              <MessageSquare size={16} />
              <span>Annotations ({annotations.length})</span>
            </div>
            <div style={styles.annotationsList}>
              {annotations.length === 0 ? (
                <p style={styles.emptyText}>
                  Select text to add comments
                </p>
              ) : (
                annotations.map((ann) => (
                  <div 
                    key={ann.id} 
                    style={{
                      ...styles.annotationItem,
                      borderLeft: `3px solid ${ann.type === 'suggestion' ? '#f59e0b' : '#3b82f6'}`,
                      backgroundColor: activeAnnotation === ann.id ? '#2a2a2a' : '#1a1a1a'
                    }}
                    onClick={() => setActiveAnnotation(ann.id)}
                  >
                    <div style={styles.annotationHeader}>
                      <span style={{
                        ...styles.annotationType,
                        backgroundColor: ann.type === 'suggestion' ? '#fef3c7' : '#dbeafe',
                        color: '#1a1a1a'
                      }}>
                        {ann.type === 'suggestion' ? 'Suggestion' : 'Comment'}
                      </span>
                      <button 
                        onClick={(e) => { e.stopPropagation(); removeAnnotation(ann.id); }}
                        style={styles.deleteButton}
                      >
                        <Trash2 size={12} />
                      </button>
                    </div>
                    <div style={styles.annotationQuote}>"{ann.selection.text.substring(0, 40)}..."</div>
                    <div style={styles.annotationComment}>{ann.comment}</div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Review Notes */}
          <div style={styles.section}>
            <div style={styles.sectionHeader}>
              <FileText size={16} />
              <span>Review Notes</span>
            </div>
            <textarea
              value={reviewNotes}
              onChange={(e) => setReviewNotes(e.target.value)}
              placeholder="Overall notes..."
              style={styles.notesTextarea}
              rows={3}
            />
          </div>

          {/* Decision */}
          <div style={styles.section}>
            <div style={styles.sectionHeader}>
              <Check size={16} />
              <span>Decision</span>
            </div>
            <div style={styles.decisionButtons}>
              <button
                onClick={() => setDecision('approved')}
                style={{
                  ...styles.decisionButton,
                  ...(decision === 'approved' ? styles.approvedSelected : {})
                }}
              >
                <Check size={16} />
                Approve
              </button>
              <button
                onClick={() => setDecision('revision_requested')}
                style={{
                  ...styles.decisionButton,
                  ...(decision === 'revision_requested' ? styles.revisionSelected : {})
                }}
              >
                <AlertTriangle size={16} />
                Revise
              </button>
            </div>
          </div>

          {/* Submit */}
          <button
            onClick={handleSubmitReview}
            disabled={!decision || isSubmitting}
            style={{
              ...styles.submitButton,
              opacity: (!decision || isSubmitting) ? 0.5 : 1
            }}
          >
            <Send size={16} />
            {isSubmitting ? 'Submitting...' : 'Submit Review'}
          </button>
        </div>
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
    backgroundColor: '#0a0a0a',
    color: '#e5e5e5',
    overflow: 'hidden'
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '12px 20px',
    borderBottom: '1px solid #333',
    backgroundColor: '#1a1a1a',
    flexShrink: 0
  },
  headerLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px'
  },
  headerRight: {
    display: 'flex',
    alignItems: 'center',
    gap: '16px'
  },
  title: {
    fontSize: '15px',
    fontWeight: 600
  },
  slaIndicator: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    fontSize: '13px'
  },
  closeButton: {
    background: 'none',
    border: 'none',
    color: '#666',
    cursor: 'pointer',
    padding: '4px'
  },
  
  // Main 80/20 layout
  mainLayout: {
    display: 'flex',
    flex: 1,
    overflow: 'hidden'
  },
  documentColumn: {
    width: '80%',
    display: 'flex',
    flexDirection: 'column',
    borderRight: '1px solid #333',
    position: 'relative'
  },
  controlsColumn: {
    width: '20%',
    minWidth: '280px',
    display: 'flex',
    flexDirection: 'column',
    backgroundColor: '#141414',
    overflow: 'auto'
  },
  
  // Document area
  documentArea: {
    flex: 1,
    overflow: 'auto',
    padding: '32px 48px',
    backgroundColor: '#0d0d0d'
  },
  markdownContent: {
    maxWidth: '900px',
    lineHeight: 1.8,
    fontSize: '15px',
    color: '#e0e0e0'
  },
  placeholder: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    height: '300px',
    color: '#555'
  },
  
  // Comment input (floating)
  commentInput: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    padding: '12px 20px',
    backgroundColor: '#1a1a1a',
    borderTop: '1px solid #333',
    boxShadow: '0 -4px 20px rgba(0,0,0,0.3)'
  },
  selectedTextPreview: {
    fontSize: '12px',
    color: '#888',
    marginBottom: '8px'
  },
  textarea: {
    width: '100%',
    padding: '10px 12px',
    backgroundColor: '#252525',
    border: '1px solid #444',
    borderRadius: '6px',
    color: '#e5e5e5',
    fontSize: '13px',
    resize: 'none',
    outline: 'none'
  },
  commentActions: {
    display: 'flex',
    gap: '8px',
    marginTop: '10px'
  },
  actionButton: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    padding: '8px 14px',
    border: 'none',
    borderRadius: '6px',
    fontSize: '12px',
    fontWeight: 500,
    cursor: 'pointer'
  },
  commentButton: {
    backgroundColor: '#3b82f6',
    color: 'white'
  },
  suggestionButton: {
    backgroundColor: '#f59e0b',
    color: 'white'
  },
  cancelButton: {
    padding: '8px 14px',
    backgroundColor: 'transparent',
    color: '#888',
    border: '1px solid #444',
    borderRadius: '6px',
    fontSize: '12px',
    cursor: 'pointer'
  },
  
  // Controls panel sections
  section: {
    padding: '16px',
    borderBottom: '1px solid #252525'
  },
  sectionHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    fontSize: '12px',
    fontWeight: 600,
    color: '#888',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
    marginBottom: '12px'
  },
  annotationsList: {
    maxHeight: '250px',
    overflow: 'auto'
  },
  emptyText: {
    fontSize: '12px',
    color: '#555',
    textAlign: 'center',
    padding: '20px 0'
  },
  annotationItem: {
    padding: '10px',
    backgroundColor: '#1a1a1a',
    borderRadius: '6px',
    marginBottom: '8px',
    cursor: 'pointer'
  },
  annotationHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '6px'
  },
  annotationType: {
    fontSize: '9px',
    padding: '2px 6px',
    borderRadius: '3px',
    fontWeight: 600,
    textTransform: 'uppercase'
  },
  deleteButton: {
    background: 'none',
    border: 'none',
    color: '#555',
    cursor: 'pointer',
    padding: '2px'
  },
  annotationQuote: {
    fontSize: '11px',
    color: '#666',
    fontStyle: 'italic',
    marginBottom: '4px'
  },
  annotationComment: {
    fontSize: '12px',
    color: '#ccc'
  },
  
  // Notes
  notesTextarea: {
    width: '100%',
    padding: '10px',
    backgroundColor: '#1a1a1a',
    border: '1px solid #333',
    borderRadius: '6px',
    color: '#e5e5e5',
    fontSize: '12px',
    resize: 'none',
    outline: 'none'
  },
  
  // Decision buttons
  decisionButtons: {
    display: 'flex',
    gap: '8px'
  },
  decisionButton: {
    flex: 1,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '6px',
    padding: '10px',
    backgroundColor: '#1a1a1a',
    border: '2px solid #333',
    borderRadius: '6px',
    color: '#888',
    fontSize: '12px',
    cursor: 'pointer'
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
  
  // Submit
  submitButton: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '8px',
    margin: '16px',
    padding: '14px',
    backgroundColor: '#3b82f6',
    border: 'none',
    borderRadius: '8px',
    color: 'white',
    fontSize: '14px',
    fontWeight: 600,
    cursor: 'pointer'
  }
};

export default ReviewPanel;
