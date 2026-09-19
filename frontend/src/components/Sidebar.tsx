import React from 'react';
import { FileText, CheckSquare, Layers, LogOut, User as UserIcon } from 'lucide-react';

export type ActiveTab = 'documents' | 'review' | 'groups';

interface SidebarProps {
  activeTab: ActiveTab;
  onTabChange: (tab: ActiveTab) => void;
  reviewCount: number;
  userEmail: string | null;
  onLogout: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  onTabChange,
  reviewCount,
  userEmail,
  onLogout,
}) => {
  return (
    <aside className="w-64 flex-shrink-0 bg-paper-subtle border-r border-paper-border flex flex-col justify-between select-none h-screen sticky top-0">
      <div>
        {/* Brand Header */}
        <div className="px-5 py-6 border-b border-paper-border flex items-center gap-3">
          <div className="w-8 h-8 rounded bg-terracotta text-paper-card flex items-center justify-center font-display font-bold text-lg shadow-subtle">
            D
          </div>
          <div>
            <h1 className="font-display font-medium text-lg leading-tight tracking-tight text-ink">
              DocIntel
            </h1>
            <p className="text-[11px] font-mono uppercase tracking-widest text-ink-muted">
              Archival & Review
            </p>
          </div>
        </div>

        {/* Navigation Items */}
        <nav className="p-3 space-y-1">
          <button
            onClick={() => onTabChange('documents')}
            className={`w-full flex items-center justify-between px-3 py-2.5 rounded text-xs font-medium transition-colors ${
              activeTab === 'documents'
                ? 'bg-paper-card text-ink shadow-subtle border border-paper-border font-semibold'
                : 'text-ink-secondary hover:text-ink hover:bg-paper-hover'
            }`}
          >
            <div className="flex items-center gap-2.5">
              <FileText className={`w-4 h-4 ${activeTab === 'documents' ? 'text-terracotta' : 'text-ink-muted'}`} />
              <span>Documents</span>
            </div>
          </button>

          <button
            onClick={() => onTabChange('review')}
            className={`w-full flex items-center justify-between px-3 py-2.5 rounded text-xs font-medium transition-colors ${
              activeTab === 'review'
                ? 'bg-paper-card text-ink shadow-subtle border border-paper-border font-semibold'
                : 'text-ink-secondary hover:text-ink hover:bg-paper-hover'
            }`}
          >
            <div className="flex items-center gap-2.5">
              <CheckSquare className={`w-4 h-4 ${activeTab === 'review' ? 'text-terracotta' : 'text-ink-muted'}`} />
              <span>Review Queue</span>
            </div>
            {reviewCount > 0 && (
              <span className="px-1.5 py-0.5 rounded-full text-[10px] font-mono font-medium bg-terracotta-100 text-terracotta-700 border border-terracotta-200">
                {reviewCount}
              </span>
            )}
          </button>

          <button
            onClick={() => onTabChange('groups')}
            className={`w-full flex items-center justify-between px-3 py-2.5 rounded text-xs font-medium transition-colors ${
              activeTab === 'groups'
                ? 'bg-paper-card text-ink shadow-subtle border border-paper-border font-semibold'
                : 'text-ink-secondary hover:text-ink hover:bg-paper-hover'
            }`}
          >
            <div className="flex items-center gap-2.5">
              <Layers className={`w-4 h-4 ${activeTab === 'groups' ? 'text-terracotta' : 'text-ink-muted'}`} />
              <span>Document Groups</span>
            </div>
          </button>
        </nav>
      </div>

      {/* User & Sign Out Footer */}
      <div className="p-4 border-t border-paper-border bg-paper/60">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-7 h-7 rounded-full bg-paper-border flex items-center justify-center text-ink-secondary">
            <UserIcon className="w-3.5 h-3.5" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium text-ink truncate" title={userEmail || 'User'}>
              {userEmail || 'operator'}
            </p>
            <p className="text-[10px] font-mono text-ink-muted">Authenticated</p>
          </div>
        </div>

        <button
          onClick={onLogout}
          className="w-full flex items-center justify-center gap-2 px-3 py-1.5 rounded text-xs text-ink-secondary hover:text-terracotta hover:bg-paper-hover transition-colors border border-transparent hover:border-paper-border"
        >
          <LogOut className="w-3.5 h-3.5" />
          <span>Sign Out</span>
        </button>
      </div>
    </aside>
  );
};
