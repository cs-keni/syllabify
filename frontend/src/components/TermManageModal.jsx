/**
 * TermManageModal Component
 * Displays a list of all terms with Edit and Delete options.
 * Allows users to manage their academic terms from one place.
 */
import { useState } from 'react';
import * as api from '../api/client';
import TermModal from './TermModal';

export default function TermManageModal({ terms, onClose, onUpdated }) {
  const [editingTerm, setEditingTerm] = useState(null);
  const [deleting, setDeleting] = useState(null);

  const handleEdit = (term) => {
    setEditingTerm(term);
  };

  const handleDelete = async (termId) => {
    if (!window.confirm('Are you sure you want to delete this term? This action cannot be undone.')) {
      return;
    }

    try {
      setDeleting(termId);
      await api.deleteTerm(termId);
      onUpdated();
    } catch (error) {
      console.error('Failed to delete term:', error);
      alert('Failed to delete term. Please try again.');
    } finally {
      setDeleting(null);
    }
  };

  const handleTermSaved = () => {
    setEditingTerm(null);
    onUpdated();
  };

  // Close modal when clicking outside
  const handleBackdropClick = (e) => {
    if (e.target === e.currentTarget && !editingTerm) {
      onClose();
    }
  };

  if (editingTerm) {
    return (
      <TermModal
        editTerm={editingTerm}
        onClose={() => setEditingTerm(null)}
        onSaved={handleTermSaved}
      />
    );
  }

  return (
    <div
      className="fixed inset-0 bg-black/30 flex items-center justify-center z-50"
      onClick={handleBackdropClick}
    >
      <div className="bg-surface-elevated rounded-card shadow-dropdown border border-border w-full max-w-2xl mx-4 overflow-hidden max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-border flex items-center justify-between">
          <h2 className="text-lg font-semibold text-ink">Manage Terms</h2>
          <button
            onClick={onClose}
            className="text-ink-muted hover:text-ink transition-colors"
            aria-label="Close"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* Terms List */}
        <div className="flex-1 overflow-y-auto p-6">
          {terms.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-ink-muted text-sm">No terms yet.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {terms.map((term) => (
                <div
                  key={term.id}
                  className="flex items-center justify-between p-4 rounded-button border border-border bg-surface hover:border-border-hover transition-colors"
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <h3 className="font-medium text-ink">{term.term_name}</h3>
                      {term.is_active && (
                        <span className="text-xs bg-accent/10 text-accent px-2 py-0.5 rounded-button">
                          Active
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-ink-muted mt-1">
                      {new Date(term.start_date).toLocaleDateString()} - {new Date(term.end_date).toLocaleDateString()}
                    </p>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleEdit(term)}
                      className="rounded-button border border-border bg-surface px-3 py-1.5 text-sm font-medium text-ink hover:bg-surface-muted transition-colors"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleDelete(term.id)}
                      disabled={deleting === term.id}
                      className="rounded-button border border-red-200 bg-surface px-3 py-1.5 text-sm font-medium text-red-600 hover:bg-red-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      {deleting === term.id ? 'Deleting...' : 'Delete'}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-border">
          <button
            onClick={onClose}
            className="rounded-button bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-hover transition-colors"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
