import React, { useState } from 'react';
import { api } from '../api/client';
import { ArrowRight, AlertCircle, CheckCircle2 } from 'lucide-react';

interface AuthViewProps {
  onAuthenticated: (email: string) => void;
}

export const AuthView: React.FC<AuthViewProps> = ({ onAuthenticated }) => {
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccessMsg(null);
    setLoading(true);

    try {
      if (isRegister) {
        await api.register(email, password);
        setSuccessMsg('Account registered successfully. Signing you in...');
        // Auto-login after registration
        await api.login(email, password);
        onAuthenticated(email);
      } else {
        await api.login(email, password);
        onAuthenticated(email);
      }
    } catch (err: any) {
      setError(err.message || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-paper flex flex-col justify-between p-6 md:p-12 selection:bg-terracotta-100 selection:text-terracotta-900">
      {/* Header bar */}
      <header className="flex items-center justify-between border-b border-paper-border pb-6 max-w-4xl mx-auto w-full">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded bg-terracotta text-paper-card flex items-center justify-center font-display font-bold text-lg shadow-subtle">
            D
          </div>
          <span className="font-display text-xl font-medium tracking-tight text-ink">DocIntel</span>
        </div>
        <span className="text-xs font-mono uppercase tracking-widest text-ink-muted">
          Edition 2026 · OCR & QA
        </span>
      </header>

      {/* Main Authentication Box */}
      <main className="max-w-md w-full mx-auto my-8">
        <div className="border border-paper-border bg-paper-card rounded-none p-8 sm:p-10 shadow-subtle">
          <div className="mb-6">
            <h2 className="font-display text-2xl text-ink font-normal tracking-tight">
              {isRegister ? 'Create reviewer ledger' : 'Access document archive'}
            </h2>
            <p className="text-xs text-ink-secondary mt-1.5 leading-relaxed">
              {isRegister
                ? 'Register an operator account to process examination papers and review extractions.'
                : 'Enter your credentials to inspect extractions, manage keys, and verify quality.'}
            </p>
          </div>

          {error && (
            <div className="mb-5 p-3 bg-red-50/70 border-l-2 border-red-700 text-xs text-red-800 flex items-start gap-2.5">
              <AlertCircle className="w-4 h-4 text-red-700 flex-shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {successMsg && (
            <div className="mb-5 p-3 bg-emerald-50/70 border-l-2 border-emerald-700 text-xs text-emerald-800 flex items-start gap-2.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-700 flex-shrink-0 mt-0.5" />
              <span>{successMsg}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium uppercase tracking-wider text-ink-secondary mb-1">
                Email Address
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="operator@institution.edu"
                className="w-full px-3 py-2 text-sm bg-paper-subtle border border-paper-border rounded-none focus:outline-none focus:border-terracotta focus:bg-paper-card text-ink transition-colors font-mono text-xs"
              />
            </div>

            <div>
              <label className="block text-xs font-medium uppercase tracking-wider text-ink-secondary mb-1">
                Password
              </label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full px-3 py-2 text-sm bg-paper-subtle border border-paper-border rounded-none focus:outline-none focus:border-terracotta focus:bg-paper-card text-ink transition-colors font-mono text-xs"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full mt-2 py-2.5 px-4 bg-terracotta hover:bg-terracotta-700 active:bg-terracotta-800 text-paper-card font-medium text-xs tracking-wider uppercase transition-colors flex items-center justify-center gap-2 shadow-subtle disabled:opacity-50"
            >
              <span>{loading ? 'Authenticating...' : isRegister ? 'Register Account' : 'Sign In'}</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </form>

          <div className="mt-6 pt-5 border-t border-paper-border flex items-center justify-between text-xs">
            <span className="text-ink-muted">
              {isRegister ? 'Already registered?' : 'Need an operator login?'}
            </span>
            <button
              type="button"
              onClick={() => {
                setIsRegister(!isRegister);
                setError(null);
                setSuccessMsg(null);
              }}
              className="text-terracotta hover:underline font-medium"
            >
              {isRegister ? 'Sign in to existing account' : 'Create a new account'}
            </button>
          </div>
        </div>

        {/* Quick test credentials helper */}
        <div className="mt-4 text-center">
          <p className="text-[11px] font-mono text-ink-muted">
            Quick demo credentials: <span className="text-ink font-semibold">reviewer@example.com</span> / <span className="text-ink font-semibold">password123</span>
          </p>
        </div>
      </main>

      {/* Editorial footer */}
      <footer className="text-center text-xs text-ink-muted font-mono max-w-4xl mx-auto w-full pt-6 border-t border-paper-border">
        Archival Document Intelligence Pipeline · Deep Text & Vision Extraction
      </footer>
    </div>
  );
};
