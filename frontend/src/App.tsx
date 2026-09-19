import React, { useState, useEffect, useCallback } from 'react';
import { Sidebar, ActiveTab } from './components/Sidebar';
import { DocumentList } from './components/DocumentList';
import { DocumentDetail } from './components/DocumentDetail';
import { ReviewQueue } from './components/ReviewQueue';
import { DocumentGroupsView } from './components/DocumentGroupsView';
import { AuthView } from './components/AuthView';
import { Document } from './types';
import { api } from './api/client';

export const App: React.FC = () => {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(api.isAuthenticated());
  const [userEmail, setUserEmail] = useState<string | null>(api.getUserEmail());
  const [activeTab, setActiveTab] = useState<ActiveTab>('documents');
  const [selectedDocument, setSelectedDocument] = useState<Document | null>(null);
  const [targetReviewQuestionId, setTargetReviewQuestionId] = useState<string | null>(null);

  const [documents, setDocuments] = useState<Document[]>([]);
  const [reviewCount, setReviewCount] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(false);

  // Sync auth state on logout event
  useEffect(() => {
    const handleLogout = () => {
      setIsAuthenticated(false);
      setUserEmail(null);
      setSelectedDocument(null);
    };
    window.addEventListener('docintel-auth-logout', handleLogout);
    return () => window.removeEventListener('docintel-auth-logout', handleLogout);
  }, []);

  // Fetch documents and review queue count
  const fetchData = useCallback(async () => {
    if (!api.isAuthenticated()) return;
    try {
      const docs = await api.getDocuments();
      setDocuments(docs);

      // Fetch review items count across docs
      let totalReview = 0;
      for (const doc of docs) {
        if (doc.status === 'done') {
          try {
            const items = await api.getDocumentReviewItems(doc.id);
            totalReview += items.review_questions?.length || 0;
          } catch {
            // fallback
          }
        }
      }
      setReviewCount(totalReview);
    } catch (err) {
      console.error('Error fetching data:', err);
    }
  }, []);

  useEffect(() => {
    if (isAuthenticated) {
      setLoading(true);
      fetchData().finally(() => setLoading(false));
    }
  }, [isAuthenticated, fetchData]);

  // Polling: if any document is in 'pending' or 'processing' status, poll every 3 seconds
  useEffect(() => {
    if (!isAuthenticated) return;
    const hasActiveDocs = documents.some(
      (d) => d.status === 'pending' || d.status === 'processing'
    );

    if (!hasActiveDocs) return;

    const interval = setInterval(() => {
      fetchData();
    }, 3000);

    return () => clearInterval(interval);
  }, [isAuthenticated, documents, fetchData]);

  const handleAuthenticated = (email: string) => {
    setIsAuthenticated(true);
    setUserEmail(email);
    fetchData();
  };

  const handleLogout = () => {
    api.clearToken();
    setIsAuthenticated(false);
    setUserEmail(null);
    setSelectedDocument(null);
  };

  // Navigating to review question directly from DocumentDetail
  const handleReviewQuestion = (questionId: string) => {
    setSelectedDocument(null);
    setTargetReviewQuestionId(questionId);
    setActiveTab('review');
  };

  if (!isAuthenticated) {
    return <AuthView onAuthenticated={handleAuthenticated} />;
  }

  return (
    <div className="flex h-screen bg-paper text-ink overflow-hidden font-sans">
      {/* Persistent Left Sidebar */}
      <Sidebar
        activeTab={activeTab}
        onTabChange={(tab) => {
          setSelectedDocument(null);
          setTargetReviewQuestionId(null);
          setActiveTab(tab);
        }}
        reviewCount={reviewCount}
        userEmail={userEmail}
        onLogout={handleLogout}
      />

      {/* Main Content Area */}
      <main className="flex-1 overflow-y-auto bg-paper">
        {selectedDocument ? (
          <DocumentDetail
            document={selectedDocument}
            onBack={() => setSelectedDocument(null)}
            onReviewQuestion={handleReviewQuestion}
          />
        ) : activeTab === 'documents' ? (
          <DocumentList
            documents={documents}
            loading={loading}
            onSelectDocument={(doc) => setSelectedDocument(doc)}
            onRefresh={fetchData}
          />
        ) : activeTab === 'review' ? (
          <ReviewQueue
            initialQuestionId={targetReviewQuestionId}
            onRefreshLedger={fetchData}
          />
        ) : activeTab === 'groups' ? (
          <DocumentGroupsView
            documents={documents}
            onSelectDocument={(doc) => setSelectedDocument(doc)}
            onRefresh={fetchData}
          />
        ) : null}
      </main>
    </div>
  );
};

export default App;
