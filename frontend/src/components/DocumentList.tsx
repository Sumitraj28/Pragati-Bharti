import React, { useState, useRef, useEffect } from 'react';
import { Document } from '../types';
import { api } from '../api/client';
import { UploadCloud, FileText, ArrowUpRight, AlertCircle, RefreshCw, CheckCircle2, FileUp } from 'lucide-react';

interface DocumentListProps {
  documents: Document[];
  loading: boolean;
  onSelectDocument: (document: Document) => void;
  onRefresh: () => void;
}

export const DocumentList: React.FC<DocumentListProps> = ({
  documents,
  loading,
  onSelectDocument,
  onRefresh,
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Clear upload success after 4s
  useEffect(() => {
    if (uploadSuccess) {
      const t = setTimeout(() => setUploadSuccess(null), 4000);
      return () => clearTimeout(t);
    }
  }, [uploadSuccess]);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      await processFileUpload(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      await processFileUpload(e.target.files[0]);
      e.target.value = '';
    }
  };

  const processFileUpload = async (file: File) => {
    setUploadError(null);
    setUploadSuccess(null);

    // Validate extension
    const validExtensions = ['.pdf', '.jpg', '.jpeg', '.png'];
    const hasValidExt = validExtensions.some((ext) => file.name.toLowerCase().endsWith(ext));
    if (!hasValidExt) {
      setUploadError('Invalid file type. Only PDF, JPG, and PNG documents are supported.');
      return;
    }

    if (file.size > 20 * 1024 * 1024) {
      setUploadError('File size exceeds the 20MB limit.');
      return;
    }

    setIsUploading(true);
    try {
      const res = await api.uploadDocument(file);
      setUploadSuccess(`"${file.name}" ingested successfully (ID: ${res.id.slice(0, 8)}). Processing pipeline triggered.`);
      onRefresh();
    } catch (err: any) {
      setUploadError(err.message || 'Failed to upload document');
    } finally {
      setIsUploading(false);
    }
  };

  const formatRole = (role: string) => {
    switch (role) {
      case 'question_paper':
        return 'Question Paper';
      case 'answer_key':
        return 'Answer Key';
      default:
        return 'Standard Document';
    }
  };

  const renderStatus = (status: string) => {
    switch (status) {
      case 'pending':
        return (
          <div className="inline-flex items-center gap-1.5 text-xs text-amber-700 font-mono">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse"></span>
            <span>Queued</span>
          </div>
        );
      case 'processing':
        return (
          <div className="inline-flex items-center gap-1.5 text-xs text-terracotta font-mono font-medium">
            <span className="w-1.5 h-1.5 rounded-full bg-terracotta animate-ping"></span>
            <span className="animate-pulse">Processing...</span>
          </div>
        );
      case 'done':
        return (
          <div className="inline-flex items-center gap-1.5 text-xs text-ink-secondary font-mono">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-600"></span>
            <span>Completed</span>
          </div>
        );
      case 'failed':
        return (
          <div className="inline-flex items-center gap-1.5 text-xs text-red-700 font-mono">
            <span className="w-1.5 h-1.5 rounded-full bg-red-600"></span>
            <span>Failed</span>
          </div>
        );
      default:
        return <span className="text-xs text-ink-muted font-mono">{status}</span>;
    }
  };

  const formatDate = (dateStr: string) => {
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="p-6 md:p-8 space-y-6 max-w-7xl mx-auto">
      {/* Top Header with title and refresh */}
      <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-4 border-b border-paper-border pb-5">
        <div>
          <h2 className="font-display text-2xl font-normal text-ink tracking-tight">
            Document Repository
          </h2>
          <p className="text-xs text-ink-secondary mt-1">
            Archival records, OCR extractions, and structured examination items.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={onRefresh}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-mono text-ink-secondary hover:text-ink border border-paper-border hover:bg-paper-hover rounded-none transition-colors"
            title="Poll / Refresh Ledger"
          >
            <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin text-terracotta' : ''}`} />
            <span>Sync Ledger</span>
          </button>
        </div>
      </div>

      {/* Integrated Drag & Drop Upload Zone (NOT a modal) */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`border border-dashed transition-all duration-150 cursor-pointer p-5 text-center select-none ${
          isDragging
            ? 'border-terracotta bg-terracotta-50/50'
            : 'border-paper-borderStrong bg-paper-subtle/50 hover:bg-paper-hover/40 hover:border-ink-muted'
        }`}
      >
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileChange}
          accept=".pdf,.jpg,.jpeg,.png"
          className="hidden"
        />
        <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
          <div className="w-8 h-8 rounded-full bg-paper-card border border-paper-border flex items-center justify-center text-terracotta shadow-subtle">
            {isUploading ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <FileUp className="w-4 h-4" />
            )}
          </div>
          <div className="text-left">
            <p className="text-xs text-ink font-medium">
              {isUploading
                ? 'Uploading document to ingestion pipeline...'
                : 'Drop PDF or scanned question paper here, or click to browse'}
            </p>
            <p className="text-[11px] text-ink-muted font-mono mt-0.5">
              Supports PDF, PNG, JPG up to 20MB · Auto-triggers OCR & Vision extraction
            </p>
          </div>
        </div>
      </div>

      {/* Notifications */}
      {uploadError && (
        <div className="p-3 bg-red-50/80 border-l-2 border-red-700 text-xs text-red-800 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{uploadError}</span>
        </div>
      )}

      {uploadSuccess && (
        <div className="p-3 bg-emerald-50/80 border-l-2 border-emerald-700 text-xs text-emerald-800 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
          <span>{uploadSuccess}</span>
        </div>
      )}

      {/* Dense Document Table */}
      <div className="border border-paper-border bg-paper-card shadow-subtle overflow-hidden">
        {documents.length === 0 && !loading ? (
          <div className="p-12 text-center">
            <div className="w-12 h-12 mx-auto rounded-full bg-paper-subtle border border-paper-border flex items-center justify-center text-ink-muted mb-3">
              <UploadCloud className="w-5 h-5" />
            </div>
            <h3 className="font-display text-lg text-ink font-normal">No archival documents found</h3>
            <p className="text-xs text-ink-secondary max-w-sm mx-auto mt-1 mb-4 leading-relaxed">
              Ingest a question paper or answer key PDF to begin OCR text extraction, layout parsing, and human review.
            </p>
            <button
              onClick={() => fileInputRef.current?.click()}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-terracotta hover:bg-terracotta-700 text-paper-card text-xs uppercase tracking-wider font-medium transition-colors"
            >
              <FileUp className="w-3.5 h-3.5" />
              <span>Upload First Document</span>
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-paper-border bg-paper-subtle/80 text-ink-secondary font-medium font-mono text-[11px] uppercase tracking-wider">
                  <th className="py-2.5 px-4">Document / Identifier</th>
                  <th className="py-2.5 px-4">Classification</th>
                  <th className="py-2.5 px-4">Status</th>
                  <th className="py-2.5 px-4 text-center">Pages</th>
                  <th className="py-2.5 px-4 text-center">Questions</th>
                  <th className="py-2.5 px-4">Ingested At</th>
                  <th className="py-2.5 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-paper-border">
                {documents.map((doc) => (
                  <tr
                    key={doc.id}
                    onClick={() => onSelectDocument(doc)}
                    className="hover:bg-paper-hover/50 cursor-pointer transition-colors group"
                  >
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2.5">
                        <FileText className="w-4 h-4 text-ink-muted group-hover:text-terracotta transition-colors flex-shrink-0" />
                        <div>
                          <p className="font-medium text-ink group-hover:text-terracotta transition-colors truncate max-w-xs">
                            {doc.filename}
                          </p>
                          <p className="font-mono text-[10px] text-ink-muted">
                            {doc.id.slice(0, 12)}…
                          </p>
                        </div>
                      </div>
                    </td>

                    <td className="py-3 px-4">
                      <span className="inline-block px-2 py-0.5 text-[11px] font-mono bg-paper-subtle border border-paper-border text-ink-secondary">
                        {formatRole(doc.doc_role)}
                      </span>
                    </td>

                    <td className="py-3 px-4">
                      {renderStatus(doc.status)}
                    </td>

                    <td className="py-3 px-4 text-center font-mono text-ink-secondary">
                      {doc.pages_count ?? '—'}
                    </td>

                    <td className="py-3 px-4 text-center font-mono">
                      {doc.questions_count !== undefined && doc.questions_count > 0 ? (
                        <span className="text-ink font-semibold">{doc.questions_count}</span>
                      ) : (
                        <span className="text-ink-muted">—</span>
                      )}
                    </td>

                    <td className="py-3 px-4 font-mono text-ink-muted text-[11px]">
                      {formatDate(doc.created_at)}
                    </td>

                    <td className="py-3 px-4 text-right">
                      <span className="inline-flex items-center gap-1 text-[11px] text-terracotta hover:underline font-medium">
                        <span>Inspect</span>
                        <ArrowUpRight className="w-3 h-3" />
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
