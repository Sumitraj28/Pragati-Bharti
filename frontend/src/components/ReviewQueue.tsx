import React, { useState, useEffect } from 'react';
import { Question } from '../types';
import { api } from '../api/client';
import {
  Check,
  X,
  Edit3,
  ChevronLeft,
  ChevronRight,
  CheckCircle2,
  AlertTriangle,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Save,
  RotateCw
} from 'lucide-react';

interface ReviewQueueProps {
  initialQuestionId?: string | null;
  onRefreshLedger: () => void;
}

export const ReviewQueue: React.FC<ReviewQueueProps> = ({
  initialQuestionId,
  onRefreshLedger,
}) => {
  const [queue, setQueue] = useState<Question[]>([]);
  const [currentIndex, setCurrentIndex] = useState<number>(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Current item state & edit mode
  const [isEditing, setIsEditing] = useState(false);
  const [editedNumber, setEditedNumber] = useState<string>('');
  const [editedText, setEditedText] = useState<string>('');
  const [editedOptions, setEditedOptions] = useState<string>('');
  const [actionLoading, setActionLoading] = useState(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  // Page image state
  const [pageImageUrl, setPageImageUrl] = useState<string | null>(null);
  const [imageLoading, setImageLoading] = useState(false);
  const [zoomLevel, setZoomLevel] = useState<number>(100);

  // Load all questions needing review across all documents
  const fetchQueue = async () => {
    setLoading(true);
    setError(null);
    try {
      const docs = await api.getDocuments();
      let allReviewQuestions: Question[] = [];

      for (const doc of docs) {
        try {
          const items = await api.getDocumentReviewItems(doc.id);
          if (items.review_questions && items.review_questions.length > 0) {
            allReviewQuestions = allReviewQuestions.concat(items.review_questions);
          }
        } catch {
          // If review-items fails for a doc, fallback to getQuestions
          try {
            const qs = await api.getDocumentQuestions(doc.id);
            const needsReview = qs.filter((q) => q.status === 'needs_review');
            allReviewQuestions = allReviewQuestions.concat(needsReview);
          } catch {
            // ignore
          }
        }
      }

      setQueue(allReviewQuestions);

      if (initialQuestionId) {
        const foundIdx = allReviewQuestions.findIndex((q) => q.id === initialQuestionId);
        if (foundIdx !== -1) {
          setCurrentIndex(foundIdx);
        }
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load review queue');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQueue();
  }, [initialQuestionId]);

  const currentQuestion = queue[currentIndex];

  // Sync form inputs when currentQuestion changes
  useEffect(() => {
    if (currentQuestion) {
      setIsEditing(false);
      setEditedNumber(currentQuestion.question_number?.toString() || '');
      setEditedText(currentQuestion.question_text || '');
      setEditedOptions(
        currentQuestion.options
          ? JSON.stringify(currentQuestion.options, null, 2)
          : ''
      );

      // Fetch page image for source page
      const sourcePage = currentQuestion.source_pages?.[0] || 1;
      setImageLoading(true);
      let activeUrl: string | null = null;
      api
        .fetchPageImageBlob(currentQuestion.document_id, sourcePage)
        .then((url) => {
          activeUrl = url;
          setPageImageUrl(url);
        })
        .catch(() => setPageImageUrl(null))
        .finally(() => setImageLoading(false));

      return () => {
        if (activeUrl) URL.revokeObjectURL(activeUrl);
      };
    } else {
      setPageImageUrl(null);
    }
  }, [currentQuestion]);

  const handleApprove = async () => {
    if (!currentQuestion) return;
    setActionLoading(true);
    try {
      await api.updateQuestion(currentQuestion.id, {
        status: 'approved',
      });
      setActionMessage('Item verified and approved.');
      advanceQueue();
      onRefreshLedger();
    } catch (err: any) {
      setError(err.message || 'Failed to approve item');
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async () => {
    if (!currentQuestion) return;
    setActionLoading(true);
    try {
      await api.updateQuestion(currentQuestion.id, {
        status: 'rejected',
      });
      setActionMessage('Item rejected and dismissed.');
      advanceQueue();
      onRefreshLedger();
    } catch (err: any) {
      setError(err.message || 'Failed to reject item');
    } finally {
      setActionLoading(false);
    }
  };

  const handleSaveEdits = async () => {
    if (!currentQuestion) return;
    setActionLoading(true);
    setError(null);
    try {
      let parsedOptions = currentQuestion.options;
      if (editedOptions.trim()) {
        try {
          parsedOptions = JSON.parse(editedOptions);
        } catch {
          throw new Error('Options must be valid JSON (e.g. {"A": "First", "B": "Second"} or ["First", "Second"])');
        }
      }

      await api.updateQuestion(currentQuestion.id, {
        question_number: editedNumber ? parseInt(editedNumber, 10) : undefined,
        question_text: editedText,
        options: parsedOptions || undefined,
        status: 'approved',
      });

      setIsEditing(false);
      setActionMessage('Edits applied and item approved.');
      advanceQueue();
      onRefreshLedger();
    } catch (err: any) {
      setError(err.message || 'Failed to save edits');
    } finally {
      setActionLoading(false);
    }
  };

  const advanceQueue = () => {
    // Remove the current question from local queue
    const updatedQueue = queue.filter((_, idx) => idx !== currentIndex);
    setQueue(updatedQueue);
    if (currentIndex >= updatedQueue.length) {
      setCurrentIndex(Math.max(0, updatedQueue.length - 1));
    }
  };

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center bg-paper text-ink-secondary font-mono text-xs">
        <RotateCw className="w-4 h-4 animate-spin text-terracotta mr-2" />
        <span>Aggregating review queue across documents...</span>
      </div>
    );
  }

  // Cohesive Empty State when no questions need review
  if (queue.length === 0) {
    return (
      <div className="h-screen flex flex-col items-center justify-center p-8 bg-paper text-center select-none">
        <div className="w-12 h-12 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-700 flex items-center justify-center mb-3">
          <CheckCircle2 className="w-6 h-6" />
        </div>
        <h2 className="font-display text-xl text-ink font-normal">Review Queue Clear</h2>
        <p className="text-xs text-ink-secondary max-w-sm mt-1 mb-6 leading-relaxed">
          All extracted questions meet the confidence threshold (≥ 60%) or have already been reviewed and verified by an operator.
        </p>
        <button
          onClick={fetchQueue}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 border border-paper-border text-xs font-mono text-ink hover:bg-paper-card"
        >
          <RotateCcw className="w-3 h-3 text-ink-muted" />
          <span>Recheck Ingestion Queue</span>
        </button>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-paper overflow-hidden select-none">
      {/* Top Review Bar */}
      <header className="h-14 border-b border-paper-border bg-paper-subtle px-6 flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 px-2.5 py-1 bg-terracotta-50 border border-terracotta-200 text-terracotta text-xs font-mono">
            <AlertTriangle className="w-3.5 h-3.5 text-terracotta" />
            <span className="font-semibold">Review Ledger</span>
          </div>
          <span className="text-xs font-mono text-ink-secondary">
            Item <span className="text-ink font-bold">{currentIndex + 1}</span> of {queue.length}
          </span>
        </div>

        {/* Previous / Next buttons */}
        <div className="flex items-center gap-2">
          <button
            disabled={currentIndex <= 0}
            onClick={() => setCurrentIndex((idx) => idx - 1)}
            className="px-2.5 py-1 text-xs font-mono border border-paper-border text-ink hover:bg-paper-card disabled:opacity-30 flex items-center gap-1"
          >
            <ChevronLeft className="w-3.5 h-3.5" />
            <span>Prev</span>
          </button>
          <button
            disabled={currentIndex >= queue.length - 1}
            onClick={() => setCurrentIndex((idx) => idx + 1)}
            className="px-2.5 py-1 text-xs font-mono border border-paper-border text-ink hover:bg-paper-card disabled:opacity-30 flex items-center gap-1"
          >
            <span>Next</span>
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </header>

      {/* Main Reviewer Layout: Source Scan on Left, Verification on Right */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Side: Original Page Scan */}
        <div className="w-1/2 border-r border-paper-border flex flex-col bg-stone-100/40 overflow-hidden">
          {/* Scan Tools Header */}
          <div className="h-10 border-b border-paper-border bg-paper-subtle px-4 flex items-center justify-between text-xs font-mono flex-shrink-0">
            <span className="text-ink-secondary">
              Source Page {currentQuestion.source_pages?.[0] || 1}
            </span>
            <div className="flex items-center gap-1.5">
              <button
                onClick={() => setZoomLevel((z) => Math.max(50, z - 20))}
                className="p-1 border border-paper-border hover:bg-paper-card"
                title="Zoom Out"
              >
                <ZoomOut className="w-3.5 h-3.5" />
              </button>
              <span className="w-10 text-center text-ink-muted text-[11px]">{zoomLevel}%</span>
              <button
                onClick={() => setZoomLevel((z) => Math.min(250, z + 20))}
                className="p-1 border border-paper-border hover:bg-paper-card"
                title="Zoom In"
              >
                <ZoomIn className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => setZoomLevel(100)}
                className="p-1 border border-paper-border hover:bg-paper-card ml-1 text-[10px]"
                title="Reset Zoom"
              >
                <RotateCcw className="w-3 h-3" />
              </button>
            </div>
          </div>

          {/* Render Page Image */}
          <div className="flex-1 overflow-auto p-4 flex items-start justify-center">
            {imageLoading ? (
              <div className="flex flex-col items-center justify-center h-64 text-ink-muted font-mono text-xs">
                <div className="w-6 h-6 border-2 border-terracotta border-t-transparent rounded-full animate-spin mb-2"></div>
                <span>Loading original scan image...</span>
              </div>
            ) : pageImageUrl ? (
              <div
                style={{ width: `${zoomLevel}%` }}
                className="transition-all duration-100 shadow-md border border-paper-border bg-white"
              >
                <img
                  src={pageImageUrl}
                  alt={`Source page ${currentQuestion.source_pages?.[0] || 1}`}
                  className="w-full h-auto block select-none pointer-events-none"
                />
              </div>
            ) : (
              <div className="p-8 text-center text-ink-muted font-mono text-xs">
                Scan preview not available.
              </div>
            )}
          </div>
        </div>

        {/* Right Side: Question Inspector & Action Bar */}
        <div className="w-1/2 flex flex-col bg-paper-card overflow-hidden">
          {/* Reason for Review Banner */}
          <div className="border-b border-paper-border bg-terracotta-50/50 p-4 flex items-start gap-3 flex-shrink-0">
            <AlertTriangle className="w-4 h-4 text-terracotta flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-xs font-semibold text-terracotta">
                Flagged for Human Verification
              </p>
              <p className="text-xs text-ink-secondary mt-0.5">
                Confidence: <span className="font-mono font-bold text-terracotta">{(currentQuestion.confidence_score * 100).toFixed(0)}%</span> (Threshold: 60%). Reason: Ambiguous numbering or OCR extraction artifacts require operator check against original page scan.
              </p>
            </div>
          </div>

          {/* Action Notification Messages */}
          {error && (
            <div className="p-3 bg-red-50 text-xs text-red-800 border-b border-red-200">
              {error}
            </div>
          )}
          {actionMessage && (
            <div className="p-3 bg-emerald-50 text-xs text-emerald-800 border-b border-emerald-200">
              {actionMessage}
            </div>
          )}

          {/* Question Form / Inspector */}
          <div className="flex-1 overflow-y-auto p-6 space-y-5 select-text">
            {isEditing ? (
              /* Editable form */
              <div className="space-y-4 font-mono text-xs">
                <div>
                  <label className="block font-medium text-ink-secondary uppercase text-[10px] tracking-wider mb-1">
                    Question Number
                  </label>
                  <input
                    type="number"
                    value={editedNumber}
                    onChange={(e) => setEditedNumber(e.target.value)}
                    className="w-24 px-2 py-1 bg-paper-subtle border border-paper-border text-ink font-mono"
                    placeholder="e.g. 1"
                  />
                </div>

                <div>
                  <label className="block font-medium text-ink-secondary uppercase text-[10px] tracking-wider mb-1">
                    Question Text
                  </label>
                  <textarea
                    rows={5}
                    value={editedText}
                    onChange={(e) => setEditedText(e.target.value)}
                    className="w-full px-3 py-2 bg-paper-subtle border border-paper-border text-ink font-sans text-xs leading-relaxed"
                  />
                </div>

                <div>
                  <label className="block font-medium text-ink-secondary uppercase text-[10px] tracking-wider mb-1">
                    Options (JSON Format)
                  </label>
                  <textarea
                    rows={4}
                    value={editedOptions}
                    onChange={(e) => setEditedOptions(e.target.value)}
                    className="w-full px-3 py-2 bg-paper-subtle border border-paper-border text-ink font-mono text-xs"
                    placeholder='{"A": "Choice A", "B": "Choice B"}'
                  />
                </div>
              </div>
            ) : (
              /* Read-only view */
              <div className="space-y-4">
                <div className="flex items-center justify-between border-b border-paper-border pb-3">
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-bold text-sm bg-paper-subtle border border-paper-border px-2.5 py-0.5 text-ink">
                      Q{currentQuestion.question_number ?? '—'}
                    </span>
                    <span className="font-mono text-xs text-ink-muted">
                      Type: {currentQuestion.question_type || 'standard'}
                    </span>
                  </div>

                  <button
                    onClick={() => setIsEditing(true)}
                    className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-mono text-ink-secondary hover:text-ink border border-paper-border hover:bg-paper-subtle"
                  >
                    <Edit3 className="w-3 h-3" />
                    <span>Edit Content</span>
                  </button>
                </div>

                <div className="text-sm leading-relaxed text-ink font-normal bg-paper-subtle/40 p-4 border border-paper-border/60">
                  {currentQuestion.question_text}
                </div>

                {currentQuestion.options && (
                  <div>
                    <h4 className="text-[10px] font-mono uppercase tracking-wider text-ink-muted mb-2">
                      Extracted Options
                    </h4>
                    <div className="space-y-1.5">
                      {Array.isArray(currentQuestion.options)
                        ? currentQuestion.options.map((opt, idx) => (
                            <div
                              key={idx}
                              className="text-xs font-mono p-2 bg-paper-subtle border border-paper-border text-ink flex items-start gap-2"
                            >
                              <span className="font-bold text-terracotta">
                                {String.fromCharCode(65 + idx)}.
                              </span>
                              <span>{opt}</span>
                            </div>
                          ))
                        : Object.entries(currentQuestion.options).map(([key, val]) => (
                            <div
                              key={key}
                              className="text-xs font-mono p-2 bg-paper-subtle border border-paper-border text-ink flex items-start gap-2"
                            >
                              <span className="font-bold text-terracotta">{key}.</span>
                              <span>{val}</span>
                            </div>
                          ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Action Footer Bar */}
          <div className="border-t border-paper-border bg-paper-subtle p-4 flex items-center justify-between flex-shrink-0">
            {isEditing ? (
              <div className="flex items-center justify-between w-full">
                <button
                  onClick={() => setIsEditing(false)}
                  className="px-3 py-1.5 text-xs font-mono text-ink-secondary hover:text-ink border border-paper-border bg-paper-card"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSaveEdits}
                  disabled={actionLoading}
                  className="inline-flex items-center gap-1.5 px-4 py-1.5 bg-terracotta hover:bg-terracotta-700 text-paper-card text-xs font-medium uppercase tracking-wider disabled:opacity-50"
                >
                  <Save className="w-3.5 h-3.5" />
                  <span>Save Edits & Approve</span>
                </button>
              </div>
            ) : (
              <div className="flex items-center justify-between w-full">
                <button
                  onClick={handleReject}
                  disabled={actionLoading}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-mono text-red-700 hover:bg-red-50 border border-red-200 bg-paper-card disabled:opacity-50"
                  title="Reject and discard this question"
                >
                  <X className="w-3.5 h-3.5" />
                  <span>Reject</span>
                </button>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setIsEditing(true)}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-mono text-ink hover:bg-paper-hover border border-paper-border bg-paper-card"
                  >
                    <Edit3 className="w-3.5 h-3.5" />
                    <span>Edit</span>
                  </button>

                  <button
                    onClick={handleApprove}
                    disabled={actionLoading}
                    className="inline-flex items-center gap-1.5 px-4 py-1.5 bg-emerald-700 hover:bg-emerald-800 text-white text-xs font-medium uppercase tracking-wider disabled:opacity-50 shadow-subtle"
                  >
                    <Check className="w-3.5 h-3.5" />
                    <span>Approve & Verify</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
