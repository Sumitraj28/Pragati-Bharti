import React, { useState, useEffect } from 'react';
import { Document, Page, Question, Answer } from '../types';
import { api } from '../api/client';
import {
  ArrowLeft,
  ChevronLeft,
  ChevronRight,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  AlertCircle,
  ExternalLink,
  FileText
} from 'lucide-react';

interface DocumentDetailProps {
  document: Document;
  onBack: () => void;
  onReviewQuestion?: (questionId: string) => void;
}

export const DocumentDetail: React.FC<DocumentDetailProps> = ({
  document,
  onBack,
  onReviewQuestion,
}) => {
  const [pages, setPages] = useState<Page[]>([]);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [answersMap, setAnswersMap] = useState<Record<string, Answer | null>>({});
  const [activePageNum, setActivePageNum] = useState<number>(1);
  const [pageImageUrl, setPageImageUrl] = useState<string | null>(null);
  const [imageLoading, setImageLoading] = useState(false);
  const [zoomLevel, setZoomLevel] = useState<number>(100);
  const [filterCurrentPageOnly, setFilterCurrentPageOnly] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load pages and questions
  useEffect(() => {
    let isMounted = true;
    const loadData = async () => {
      setLoading(true);
      setError(null);
      try {
        const [pagesData, questionsData] = await Promise.all([
          api.getDocumentPages(document.id),
          api.getDocumentQuestions(document.id),
        ]);

        if (!isMounted) return;
        setPages(pagesData);
        setQuestions(questionsData);

        if (pagesData.length > 0) {
          setActivePageNum(pagesData[0].page_number);
        }

        // Fetch answers for all questions in parallel
        const ansPromises = questionsData.map(async (q) => {
          try {
            const ans = await api.getQuestionAnswer(q.id);
            return { qid: q.id, ans };
          } catch {
            return { qid: q.id, ans: null };
          }
        });
        const ansResults = await Promise.all(ansPromises);
        if (!isMounted) return;
        const newMap: Record<string, Answer | null> = {};
        ansResults.forEach((r) => {
          newMap[r.qid] = r.ans;
        });
        setAnswersMap(newMap);
      } catch (err: any) {
        if (isMounted) setError(err.message || 'Failed to load document details');
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    loadData();
    return () => {
      isMounted = false;
    };
  }, [document.id]);

  // Load page image whenever activePageNum changes
  useEffect(() => {
    let activeUrl: string | null = null;
    const loadImage = async () => {
      if (pages.length === 0) return;
      setImageLoading(true);
      try {
        const url = await api.fetchPageImageBlob(document.id, activePageNum);
        activeUrl = url;
        setPageImageUrl(url);
      } catch (err) {
        setPageImageUrl(null);
      } finally {
        setImageLoading(false);
      }
    };

    loadImage();
    return () => {
      if (activeUrl) {
        URL.revokeObjectURL(activeUrl);
      }
    };
  }, [document.id, activePageNum, pages.length]);

  const currentPage = pages.find((p) => p.page_number === activePageNum);

  // Filter questions for current page if toggled
  const displayedQuestions = filterCurrentPageOnly
    ? questions.filter((q) => q.source_pages && q.source_pages.includes(activePageNum))
    : questions;

  const renderConfidence = (score: number) => {
    const pct = Math.round(score * 100);
    let dotColor = 'bg-emerald-600';
    let textColor = 'text-ink-secondary';

    if (score < 0.6) {
      dotColor = 'bg-terracotta';
      textColor = 'text-terracotta-700 font-semibold';
    } else if (score < 0.8) {
      dotColor = 'bg-amber-500';
    }

    return (
      <span className="inline-flex items-center gap-1.5 font-mono text-[11px]" title={`Confidence: ${(score * 100).toFixed(0)}%`}>
        <span className={`w-1.5 h-1.5 rounded-full ${dotColor}`}></span>
        <span className={textColor}>{pct}%</span>
      </span>
    );
  };

  const renderStatusPill = (status: string) => {
    switch (status) {
      case 'needs_review':
        return (
          <span className="px-1.5 py-0.5 text-[10px] font-mono uppercase tracking-wider bg-terracotta-50 text-terracotta-700 border border-terracotta-200">
            Needs Review
          </span>
        );
      case 'approved':
        return (
          <span className="px-1.5 py-0.5 text-[10px] font-mono uppercase tracking-wider bg-emerald-50 text-emerald-800 border border-emerald-200">
            Verified
          </span>
        );
      case 'rejected':
        return (
          <span className="px-1.5 py-0.5 text-[10px] font-mono uppercase tracking-wider bg-zinc-100 text-zinc-600 border border-zinc-200">
            Rejected
          </span>
        );
      default:
        return (
          <span className="px-1.5 py-0.5 text-[10px] font-mono uppercase tracking-wider bg-paper-subtle text-ink-muted border border-paper-border">
            Extracted
          </span>
        );
    }
  };

  return (
    <div className="h-screen flex flex-col bg-paper overflow-hidden select-none">
      {/* Top Header Bar */}
      <header className="h-14 border-b border-paper-border bg-paper-subtle px-5 flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-3">
          <button
            onClick={onBack}
            className="p-1.5 rounded-none text-ink-secondary hover:text-ink hover:bg-paper-hover border border-paper-border transition-colors flex items-center gap-1 text-xs font-mono"
            title="Return to Documents"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Archive</span>
          </button>

          <div className="h-4 w-[1px] bg-paper-borderStrong"></div>

          <div>
            <h2 className="font-display text-base font-normal text-ink leading-none truncate max-w-md">
              {document.filename}
            </h2>
            <div className="flex items-center gap-2 mt-1 text-[11px] font-mono text-ink-muted">
              <span>Doc ID: {document.id.slice(0, 8)}</span>
              <span>·</span>
              <span className="uppercase">{document.doc_role.replace('_', ' ')}</span>
              <span>·</span>
              <span>{pages.length} Pages</span>
              <span>·</span>
              <span>{questions.length} Items Extracted</span>
            </div>
          </div>
        </div>

        {/* Action / Quick Stats */}
        <div className="flex items-center gap-3">
          {questions.some((q) => q.status === 'needs_review') && (
            <span className="text-xs font-mono text-terracotta flex items-center gap-1.5 bg-terracotta-50 px-2 py-1 border border-terracotta-200">
              <AlertCircle className="w-3.5 h-3.5" />
              <span>Review items present</span>
            </span>
          )}
        </div>
      </header>

      {/* Main Split-Pane Content Area */}
      <div className="flex-1 flex overflow-hidden">
        {/* LEFT PANE: Original Page Render & Viewer */}
        <div className="w-1/2 border-r border-paper-border flex flex-col bg-paper-subtle/40 overflow-hidden">
          {/* Viewer Toolbar */}
          <div className="h-10 border-b border-paper-border bg-paper-subtle px-4 flex items-center justify-between text-xs font-mono flex-shrink-0">
            {/* Page Navigation */}
            <div className="flex items-center gap-2">
              <button
                disabled={activePageNum <= 1}
                onClick={() => setActivePageNum((prev) => Math.max(1, prev - 1))}
                className="p-1 border border-paper-border hover:bg-paper-card disabled:opacity-30 disabled:hover:bg-transparent"
                title="Previous Page"
              >
                <ChevronLeft className="w-3.5 h-3.5" />
              </button>
              <span className="text-ink-secondary">
                Page <span className="text-ink font-semibold">{activePageNum}</span> of {pages.length || 1}
              </span>
              <button
                disabled={activePageNum >= (pages.length || 1)}
                onClick={() => setActivePageNum((prev) => Math.min(pages.length, prev + 1))}
                className="p-1 border border-paper-border hover:bg-paper-card disabled:opacity-30 disabled:hover:bg-transparent"
                title="Next Page"
              >
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* Zoom Controls */}
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

          {/* Page Image Display Canvas */}
          <div className="flex-1 overflow-auto p-4 flex items-start justify-center bg-stone-100/50">
            {imageLoading ? (
              <div className="flex flex-col items-center justify-center h-64 text-ink-muted font-mono text-xs">
                <div className="w-6 h-6 border-2 border-terracotta border-t-transparent rounded-full animate-spin mb-2"></div>
                <span>Rendering high-resolution scan...</span>
              </div>
            ) : pageImageUrl ? (
              <div
                style={{ width: `${zoomLevel}%` }}
                className="transition-all duration-100 shadow-md border border-paper-border bg-white"
              >
                <img
                  src={pageImageUrl}
                  alt={`Source page ${activePageNum}`}
                  className="w-full h-auto block select-none pointer-events-none"
                />
              </div>
            ) : (
              <div className="p-8 text-center text-ink-muted">
                <FileText className="w-8 h-8 mx-auto mb-2 text-ink-faint" />
                <p className="text-xs font-mono">No rendered page image available for page {activePageNum}</p>
              </div>
            )}
          </div>

          {/* Extracted Raw OCR Snippet Tray (Collapsible/Footer) */}
          {currentPage?.raw_text && (
            <div className="border-t border-paper-border bg-paper-subtle p-3 max-h-36 overflow-y-auto font-mono text-[11px] text-ink-secondary">
              <span className="text-[10px] font-semibold text-ink uppercase tracking-wider block mb-1">
                Raw Page OCR Stream ({currentPage.raw_text.length} chars)
              </span>
              <p className="whitespace-pre-wrap leading-relaxed select-text">
                {currentPage.raw_text.slice(0, 300)}...
              </p>
            </div>
          )}
        </div>

        {/* RIGHT PANE: Structured Extracted Questions & Review Indicators */}
        <div className="w-1/2 flex flex-col bg-paper overflow-hidden">
          {/* Right Pane Controls */}
          <div className="h-10 border-b border-paper-border bg-paper-subtle px-4 flex items-center justify-between text-xs flex-shrink-0">
            <span className="font-mono text-xs text-ink-secondary">
              Extracted Questions ({displayedQuestions.length})
            </span>

            <label className="flex items-center gap-2 cursor-pointer text-xs text-ink-secondary hover:text-ink font-mono">
              <input
                type="checkbox"
                checked={filterCurrentPageOnly}
                onChange={(e) => setFilterCurrentPageOnly(e.target.checked)}
                className="accent-terracotta rounded-none w-3.5 h-3.5"
              />
              <span>Page {activePageNum} only</span>
            </label>
          </div>

          {/* Questions Scrollable List */}
          <div className="flex-1 overflow-y-auto p-5 space-y-4 select-text">
            {error && (
              <div className="p-3 bg-red-50 text-xs text-red-800 border-l-2 border-red-700 flex items-center gap-2">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}
            {loading ? (
              <div className="p-8 text-center text-ink-muted font-mono text-xs">
                <span>Loading structured extraction data...</span>
              </div>
            ) : displayedQuestions.length === 0 ? (
              <div className="p-12 text-center border border-dashed border-paper-border">
                <p className="font-display text-sm text-ink">No questions extracted for this selection.</p>
                <p className="text-xs text-ink-muted mt-1 font-mono">
                  {filterCurrentPageOnly
                    ? `No questions sourced from page ${activePageNum}. Try toggling page filter.`
                    : 'The document processing pipeline did not detect questions.'}
                </p>
              </div>
            ) : (
              displayedQuestions.map((q) => {
                const answer = answersMap[q.id];
                return (
                  <div
                    key={q.id}
                    className={`border transition-colors p-4 ${
                      q.status === 'needs_review'
                        ? 'border-terracotta-300 bg-terracotta-50/20'
                        : 'border-paper-border bg-paper-card'
                    }`}
                  >
                    {/* Question Header Card */}
                    <div className="flex items-start justify-between gap-3 mb-2.5">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-xs bg-paper-subtle border border-paper-border px-2 py-0.5 text-ink">
                          Q{q.question_number ?? '—'}
                        </span>
                        {renderStatusPill(q.status)}
                      </div>

                      <div className="flex items-center gap-3">
                        <div className="flex items-center gap-1.5">
                          <span className="text-[10px] uppercase font-mono text-ink-muted">Confidence:</span>
                          {renderConfidence(q.confidence_score)}
                        </div>

                        {onReviewQuestion && q.status === 'needs_review' && (
                          <button
                            onClick={() => onReviewQuestion(q.id)}
                            className="text-[11px] font-mono text-terracotta hover:underline inline-flex items-center gap-1"
                            title="Open in focused Review Queue"
                          >
                            <span>Verify</span>
                            <ExternalLink className="w-3 h-3" />
                          </button>
                        )}
                      </div>
                    </div>

                    {/* Question Text */}
                    <div className="text-xs leading-relaxed text-ink font-normal mb-3">
                      {q.question_text}
                    </div>

                    {/* Options (if present) */}
                    {q.options && (
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5 my-2.5 pt-2 border-t border-paper-border/60">
                        {Array.isArray(q.options)
                          ? q.options.map((opt, idx) => (
                              <div
                                key={idx}
                                className="text-[11px] font-mono px-2 py-1 bg-paper-subtle border border-paper-border/70 text-ink-secondary"
                              >
                                <span className="font-semibold text-ink mr-1">
                                  {String.fromCharCode(65 + idx)}.
                                </span>
                                <span>{opt}</span>
                              </div>
                            ))
                          : Object.entries(q.options).map(([key, val]) => (
                              <div
                                key={key}
                                className="text-[11px] font-mono px-2 py-1 bg-paper-subtle border border-paper-border/70 text-ink-secondary"
                              >
                                <span className="font-semibold text-ink mr-1">{key}.</span>
                                <span>{val}</span>
                              </div>
                            ))}
                      </div>
                    )}

                    {/* Linked Answer / Solution Box */}
                    {answer && (
                      <div className="mt-3 pt-2.5 border-t border-paper-border flex items-start justify-between text-xs bg-paper-subtle/60 p-2.5">
                        <div>
                          <span className="text-[10px] font-mono uppercase tracking-wider text-ink-muted block mb-0.5">
                            Matched Answer Key
                          </span>
                          <span className="font-mono text-ink font-medium">
                            {answer.raw_answer_text}
                          </span>
                        </div>
                        <div className="text-right">
                          <span className="text-[10px] font-mono text-ink-muted block">Match Conf</span>
                          <span className="font-mono text-[11px] text-ink-secondary">
                            {(answer.confidence_score * 100).toFixed(0)}%
                          </span>
                        </div>
                      </div>
                    )}

                    {/* Metadata Footer */}
                    <div className="mt-2.5 pt-2 border-t border-paper-border/40 flex items-center justify-between text-[10px] font-mono text-ink-muted">
                      <span>Source Pages: [{(q.source_pages || []).join(', ')}]</span>
                      <span>Type: {q.question_type || 'standard'}</span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
