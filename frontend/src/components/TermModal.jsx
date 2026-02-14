/**
 * TermModal Component
 * Modal dialog for creating or editing academic terms.
 * Includes form validation and API integration.
 */
import { useState } from 'react';
import { createPortal } from 'react-dom';
import * as api from '../api/client';

export default function TermModal({ onClose, onSaved, editTerm = null }) {
  const [formData, setFormData] = useState({
    term_name: editTerm?.term_name || '',
    start_date: editTerm?.start_date || '',
    end_date: editTerm?.end_date || '',
  });
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  const handleChange = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    setError(''); // Clear error when user types
  };

  const validateForm = () => {
    if (!formData.term_name.trim()) {
      setError('Term name is required');
      return false;
    }
    if (!formData.start_date) {
      setError('Start date is required');
      return false;
    }
    if (!formData.end_date) {
      setError('End date is required');
      return false;
    }
    if (new Date(formData.end_date) <= new Date(formData.start_date)) {
      setError('End date must be after start date');
      return false;
    }
    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    try {
      setSaving(true);
      setError('');

      if (editTerm) {
        await api.updateTerm(editTerm.id, formData);
      } else {
        await api.createTerm(formData);
      }

      onSaved();
      onClose();
    } catch (err) {
      console.error('Failed to save term:', err);
      setError(err.message || 'Failed to save term. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  // Close modal when clicking outside
  const handleBackdropClick = (e) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  return createPortal(
    <div
      className="fixed inset-0 bg-black/30 flex items-center justify-center"
      style={{ zIndex: 99999 }}
      onClick={handleBackdropClick}
    >
      <div className="bg-surface-elevated rounded-card shadow-dropdown border border-border w-full max-w-md mx-4 overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-border">
          <h2 className="text-lg font-semibold text-ink">
            {editTerm ? 'Edit Term' : 'Create New Term'}
          </h2>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          {/* Term Name */}
          <div>
            <label
              htmlFor="term_name"
              className="block text-sm font-medium text-ink mb-1.5"
            >
              Term Name
            </label>
            <input
              id="term_name"
              type="text"
              value={formData.term_name}
              onChange={(e) => handleChange('term_name', e.target.value)}
              placeholder="e.g., Winter 2025"
              className="w-full rounded-input border border-border bg-surface px-3 py-2 text-ink text-sm placeholder:text-ink-subtle focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent transition-colors"
            />
          </div>

          {/* Start Date */}
          <div>
            <label
              htmlFor="start_date"
              className="block text-sm font-medium text-ink mb-1.5"
            >
              Start Date
            </label>
            <input
              id="start_date"
              type="date"
              value={formData.start_date}
              onChange={(e) => handleChange('start_date', e.target.value)}
              className="w-full rounded-input border border-border bg-surface px-3 py-2 text-ink text-sm focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent transition-colors"
            />
          </div>

          {/* End Date */}
          <div>
            <label
              htmlFor="end_date"
              className="block text-sm font-medium text-ink mb-1.5"
            >
              End Date
            </label>
            <input
              id="end_date"
              type="date"
              value={formData.end_date}
              onChange={(e) => handleChange('end_date', e.target.value)}
              className="w-full rounded-input border border-border bg-surface px-3 py-2 text-ink text-sm focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent transition-colors"
            />
          </div>

          {/* Error Message */}
          {error && (
            <div className="rounded-input bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
              {error}
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3 justify-end pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={saving}
              className="rounded-button border border-border bg-surface px-4 py-2 text-sm font-medium text-ink hover:bg-surface-muted disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="rounded-button bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-hover disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {saving ? 'Saving...' : editTerm ? 'Update Term' : 'Create Term'}
            </button>
          </div>
        </form>
      </div>
    </div>,
    document.body
  );
}
