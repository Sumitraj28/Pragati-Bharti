import React, { useState, useEffect } from 'react';
import { DocumentGroup, Document } from '../types';
import { api } from '../api/client';
import { Layers, Plus, FileText, AlertCircle, ArrowRight } from 'lucide-react';

interface DocumentGroupsViewProps {
  documents: Document[];
  onSelectDocument: (doc: Document) => void;
  onRefresh: () => void;
}

export const DocumentGroupsView: React.FC<DocumentGroupsViewProps> = ({
  documents,
  onSelectDocument,
  onRefresh,
}) => {
  const [groups, setGroups] = useState<DocumentGroup[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newGroupName, setNewGroupName] = useState('');
  const [creating, setCreating] = useState(false);
  const [selectedGroupId, setSelectedGroupId] = useState<string | null>(null);
  const [selectedDocIdToAdd, setSelectedDocIdToAdd] = useState<string>('');
  const [addingDoc, setAddingDoc] = useState(false);

  const fetchGroups = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getGroups();
      setGroups(data);
      if (data.length > 0 && !selectedGroupId) {
        setSelectedGroupId(data[0].id);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to fetch document groups');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGroups();
  }, []);

  const handleCreateGroup = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newGroupName.trim()) return;
    setCreating(true);
    setError(null);
    try {
      const created = await api.createGroup(newGroupName.trim());
      setNewGroupName('');
      await fetchGroups();
      setSelectedGroupId(created.id);
      onRefresh();
    } catch (err: any) {
      setError(err.message || 'Failed to create group');
    } finally {
      setCreating(false);
    }
  };

  const handleAddDocumentToGroup = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedGroupId || !selectedDocIdToAdd) return;
    setAddingDoc(true);
    setError(null);
    try {
      await api.addDocumentToGroup(selectedGroupId, selectedDocIdToAdd);
      setSelectedDocIdToAdd('');
      await fetchGroups();
      onRefresh();
    } catch (err: any) {
      setError(err.message || 'Failed to link document to group');
    } finally {
      setAddingDoc(false);
    }
  };

  const activeGroup = groups.find((g) => g.id === selectedGroupId);

  // Available documents not already in activeGroup
  const activeGroupDocIds = new Set(activeGroup?.documents?.map((d) => d.id) || []);
  const availableDocs = documents.filter((d) => !activeGroupDocIds.has(d.id));

  return (
    <div className="p-6 md:p-8 space-y-6 max-w-7xl mx-auto">
      {/* Page Title */}
      <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-4 border-b border-paper-border pb-5">
        <div>
          <h2 className="font-display text-2xl font-normal text-ink tracking-tight">
            Document Groups & Associations
          </h2>
          <p className="text-xs text-ink-secondary mt-1">
            Group Question Papers together with their respective Answer Keys for cross-document answer matching.
          </p>
        </div>
      </div>

      {error && (
        <div className="p-3 bg-red-50/80 border-l-2 border-red-700 text-xs text-red-800 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Create New Group Card */}
      <div className="border border-paper-border bg-paper-card p-5 shadow-subtle">
        <h3 className="font-display text-sm font-medium text-ink mb-2">Create New Examination Group</h3>
        <form onSubmit={handleCreateGroup} className="flex gap-3 max-w-xl">
          <input
            type="text"
            required
            value={newGroupName}
            onChange={(e) => setNewGroupName(e.target.value)}
            placeholder="e.g. Physics 2024 Final Examination & Answer Key"
            className="flex-1 px-3 py-2 text-xs bg-paper-subtle border border-paper-border focus:border-terracotta focus:outline-none"
          />
          <button
            type="submit"
            disabled={creating}
            className="px-4 py-2 bg-terracotta hover:bg-terracotta-700 text-paper-card text-xs uppercase font-medium tracking-wider flex items-center gap-1.5 transition-colors disabled:opacity-50"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>{creating ? 'Creating...' : 'Create Group'}</span>
          </button>
        </form>
      </div>

      {/* Groups Layout */}
      {groups.length === 0 && !loading ? (
        <div className="border border-paper-border bg-paper-card p-12 text-center shadow-subtle">
          <Layers className="w-10 h-10 mx-auto text-ink-muted mb-3" />
          <h3 className="font-display text-base text-ink">No document groups established</h3>
          <p className="text-xs text-ink-secondary max-w-md mx-auto mt-1 leading-relaxed">
            Create your first group above to associate question papers with separate answer key PDFs.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Groups List (Left 1 col) */}
          <div className="border border-paper-border bg-paper-card p-4 space-y-2 h-fit shadow-subtle">
            <h4 className="text-[11px] font-mono uppercase tracking-wider text-ink-muted mb-2">
              Active Groups ({groups.length})
            </h4>
            <div className="space-y-1">
              {groups.map((grp) => (
                <button
                  key={grp.id}
                  onClick={() => setSelectedGroupId(grp.id)}
                  className={`w-full text-left p-2.5 text-xs transition-colors border ${
                    selectedGroupId === grp.id
                      ? 'border-terracotta bg-terracotta-50/40 text-ink font-medium'
                      : 'border-transparent hover:bg-paper-hover text-ink-secondary'
                  }`}
                >
                  <p className="truncate font-medium">{grp.name}</p>
                  <div className="flex items-center gap-2 mt-1 text-[10px] font-mono text-ink-muted">
                    <span>{grp.documents?.length || 0} Docs Linked</span>
                    <span>·</span>
                    <span>{grp.id.slice(0, 8)}</span>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Group Details & Member Documents (Right 2 cols) */}
          <div className="md:col-span-2 border border-paper-border bg-paper-card p-6 shadow-subtle">
            {activeGroup ? (
              <div className="space-y-6">
                <div>
                  <h3 className="font-display text-lg text-ink font-medium">
                    {activeGroup.name}
                  </h3>
                  <p className="text-xs font-mono text-ink-muted mt-0.5">
                    Group ID: {activeGroup.id}
                  </p>
                </div>

                {/* Add Document to this Group Form */}
                <div className="p-4 bg-paper-subtle border border-paper-border">
                  <h4 className="text-xs font-medium text-ink mb-2">
                    Link a Document to this Group
                  </h4>
                  <form onSubmit={handleAddDocumentToGroup} className="flex gap-2">
                    <select
                      value={selectedDocIdToAdd}
                      onChange={(e) => setSelectedDocIdToAdd(e.target.value)}
                      className="flex-1 px-3 py-2 text-xs bg-paper-card border border-paper-border focus:outline-none focus:border-terracotta"
                    >
                      <option value="">Select an unlinked document...</option>
                      {availableDocs.map((d) => (
                        <option key={d.id} value={d.id}>
                          {d.filename} ({d.doc_role.replace('_', ' ')})
                        </option>
                      ))}
                    </select>

                    <button
                      type="submit"
                      disabled={addingDoc || !selectedDocIdToAdd}
                      className="px-3 py-2 bg-ink hover:bg-black text-paper-card text-xs font-mono uppercase tracking-wider disabled:opacity-40 flex items-center gap-1.5"
                    >
                      <Plus className="w-3.5 h-3.5" />
                      <span>Link</span>
                    </button>
                  </form>
                </div>

                {/* Linked Documents List */}
                <div>
                  <h4 className="text-[11px] font-mono uppercase tracking-wider text-ink-muted mb-3">
                    Associated Documents ({activeGroup.documents?.length || 0})
                  </h4>

                  {!activeGroup.documents || activeGroup.documents.length === 0 ? (
                    <div className="p-6 text-center border border-dashed border-paper-border text-xs text-ink-muted font-mono">
                      No documents linked to this group yet. Link a Question Paper and an Answer Key above.
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {activeGroup.documents.map((doc) => (
                        <div
                          key={doc.id}
                          className="flex items-center justify-between p-3 border border-paper-border hover:bg-paper-hover/50 transition-colors"
                        >
                          <div className="flex items-center gap-2.5">
                            <FileText className="w-4 h-4 text-terracotta" />
                            <div>
                              <p className="text-xs font-medium text-ink">{doc.filename}</p>
                              <div className="flex items-center gap-2 text-[10px] font-mono text-ink-muted">
                                <span className="uppercase">{doc.doc_role.replace('_', ' ')}</span>
                                <span>·</span>
                                <span>Status: {doc.status}</span>
                              </div>
                            </div>
                          </div>

                          <button
                            onClick={() => onSelectDocument(doc)}
                            className="inline-flex items-center gap-1 text-xs font-mono text-terracotta hover:underline"
                          >
                            <span>Inspect</span>
                            <ArrowRight className="w-3 h-3" />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="p-8 text-center text-xs text-ink-muted font-mono">
                Select a group to view details.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
