/**
 * TermSelector Component
 * Displays a dropdown to select/switch between terms and a button to create new terms.
 * Used in Dashboard and other pages to filter data by academic term.
 */
import { useState, useEffect } from 'react';
import toast from 'react-hot-toast';
import * as api from '../api/client';
import TermModal from './TermModal';
import TermManageModal from './TermManageModal';

export default function TermSelector({ onTermChange }) {
  const [terms, setTerms] = useState([]);
  const [currentTermId, setCurrentTermId] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [showManageModal, setShowManageModal] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadTerms();
  }, []);

  const loadTerms = async () => {
    try {
      setLoading(true);
      const data = await api.getTerms();
      const termsList = data.terms || [];
      setTerms(termsList);

      // Find and set active term
      const active = termsList.find(t => t.is_active);
      if (active) {
        setCurrentTermId(active.id);
        if (onTermChange) {
          onTermChange(active.id);
        }
      } else if (termsList.length > 0) {
        // If no active term, use the first one
        setCurrentTermId(termsList[0].id);
        if (onTermChange) {
          onTermChange(termsList[0].id);
        }
      }
    } catch (error) {
      console.error('Failed to load terms:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleChange = async termId => {
    const numericTermId = Number(termId);
    try {
      await api.activateTerm(numericTermId);
      setCurrentTermId(numericTermId);

      // Find term name for toast message
      const selectedTerm = terms.find(t => t.id === numericTermId);
      toast.success(`Switched to ${selectedTerm?.term_name || 'term'}`);

      if (onTermChange) {
        onTermChange(numericTermId);
      }
    } catch (error) {
      console.error('Failed to activate term:', error);
      toast.error('Failed to switch term. Please try again.');
    }
  };

  const handleTermCreated = () => {
    setShowModal(false);
    loadTerms();
  };

  const handleManageUpdated = () => {
    loadTerms();
  };

  if (loading) {
    return (
      <div className="flex items-center gap-3">
        <span className="text-sm text-ink-muted">Loading terms...</span>
      </div>
    );
  }

  if (terms.length === 0) {
    return (
      <div className="flex items-center gap-3">
        <span className="text-sm text-ink-muted">No terms yet.</span>
        <button
          onClick={() => setShowModal(true)}
          className="rounded-button bg-[#0F8A4C] px-3 py-2 text-sm font-medium text-[#F5C30F] hover:bg-[#094728] transition-colors"
        >
          + Create First Term
        </button>
        {showModal && (
          <TermModal
            onClose={() => setShowModal(false)}
            onSaved={handleTermCreated}
          />
        )}
      </div>
    );
  }

  return (
    <div className="flex items-center gap-3">
      <label className="text-sm font-medium text-ink">Term:</label>
      <select
        value={currentTermId || ''}
        onChange={e => handleChange(e.target.value)}
        className="rounded-input border border-border bg-surface px-3 py-2 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
      >
        {terms.map(term => (
          <option key={term.id} value={term.id}>
            {term.term_name}
          </option>
        ))}
      </select>
      <button
        onClick={() => setShowModal(true)}
        className="rounded-button bg-accent px-3 py-2 text-sm font-medium text-white hover:bg-accent-hover transition-colors"
      >
        + New Term
      </button>
      <button
        onClick={() => setShowManageModal(true)}
        className="rounded-button border border-border bg-surface px-3 py-2 text-sm font-medium text-ink hover:bg-surface-muted transition-colors"
      >
        Manage
      </button>
      {showModal && (
        <TermModal
          onClose={() => setShowModal(false)}
          onSaved={handleTermCreated}
        />
      )}
      {showManageModal && (
        <TermManageModal
          terms={terms}
          onClose={() => setShowManageModal(false)}
          onUpdated={handleManageUpdated}
        />
      )}
    </div>
  );
}
