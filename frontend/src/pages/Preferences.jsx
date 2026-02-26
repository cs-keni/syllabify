/**
 * Preferences: Account (email), work hours, preferred days.
 * Backend integration: Phase 4 (Account), Phase 6 (study prefs).
 */
import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { getProfile, updateProfile, getPreferences, updatePreferences } from '../api/client';
import toast from 'react-hot-toast';

const DAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const DAY_TO_CODE = { Mon: 'MO', Tue: 'TU', Wed: 'WE', Thu: 'TH', Fri: 'FR', Sat: 'SA', Sun: 'SU' };

function parsePreferredDays(csv) {
  if (!csv || typeof csv !== 'string') return [];
  return csv.split(',').map(s => s.trim().toUpperCase()).filter(Boolean);
}

export default function Preferences() {
  const { token } = useAuth();
  const [email, setEmail] = useState('');
  const [workStart, setWorkStart] = useState('09:00');
  const [workEnd, setWorkEnd] = useState('17:00');
  const [selectedDays, setSelectedDays] = useState([true, true, true, true, true, false, false]);
  const [maxHours, setMaxHours] = useState(8);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!token) return;
    Promise.all([getProfile(token), getPreferences(token)])
      .then(([p, prefs]) => {
        if (p?.email != null) setEmail(p.email);
        if (prefs) {
          setWorkStart(prefs.work_start || '09:00');
          setWorkEnd(prefs.work_end || '17:00');
          const codes = parsePreferredDays(prefs.preferred_days);
          setSelectedDays(DAY_LABELS.map(d => codes.includes(DAY_TO_CODE[d])));
          const h = prefs.max_hours_per_day;
          setMaxHours(typeof h === 'number' ? h : parseInt(h, 10) || 8);
        }
      })
      .finally(() => setLoading(false));
  }, [token]);

  const handleSaveAccount = async e => {
    e.preventDefault();
    if (!token) return;
    setSaving(true);
    try {
      await updateProfile(token, { email: email.trim() || null });
      toast.success('Profile saved');
    } catch (err) {
      toast.error(err.message || 'Failed to save');
    } finally {
      setSaving(false);
    }
  };

  const handleSavePreferences = async e => {
    e.preventDefault();
    if (!token) return;
    setSaving(true);
    try {
      const codes = DAY_LABELS.filter((_, i) => selectedDays[i]).map(d => DAY_TO_CODE[d]);
      await updatePreferences(token, {
        work_start: workStart,
        work_end: workEnd,
        preferred_days: codes.join(','),
        max_hours_per_day: maxHours,
      });
      toast.success('Preferences saved');
    } catch (err) {
      toast.error(err.message || 'Failed to save preferences');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-8">
      <div className="animate-fade-in">
        <Link
          to="/app"
          className="text-sm text-ink-muted hover:text-ink transition-colors no-underline"
        >
          ← Dashboard
        </Link>
        <h1 className="mt-2 text-2xl font-semibold text-ink">Preferences</h1>
        <p className="mt-1 text-sm text-ink-muted">
          Manage your account and study preferences.
        </p>
      </div>

      <div className="rounded-card bg-surface-elevated border border-border p-6 shadow-card animate-fade-in-up [animation-delay:200ms]">
        <div className="grid gap-8 lg:grid-cols-2">
        <section>
          <h2 className="text-sm font-medium text-ink mb-3">Account</h2>
          <form onSubmit={handleSaveAccount} className="flex flex-col gap-3">
            <div>
              <label htmlFor="email" className="block text-sm text-ink-muted mb-1">
                Email (optional)
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="you@example.com"
                disabled={loading}
                className="w-full max-w-md rounded-input border border-border bg-surface px-3 py-2 text-ink text-sm placeholder:text-ink-subtle focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent disabled:opacity-60"
              />
            </div>
            <button
              type="submit"
              disabled={saving || loading}
              className="rounded-button bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-hover disabled:opacity-60 w-fit"
            >
              {saving ? 'Saving…' : 'Save'}
            </button>
          </form>
        </section>

        <form onSubmit={handleSavePreferences} className="space-y-8">
          <section>
            <h2 className="text-sm font-medium text-ink mb-3">Work hours</h2>
            <div className="flex items-center gap-4">
              <label className="text-sm text-ink-muted">Start</label>
              <input
                type="time"
                value={workStart}
                onChange={e => setWorkStart(e.target.value)}
                disabled={loading}
                className="rounded-input border border-border bg-surface px-3 py-2 text-ink text-sm focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent disabled:opacity-60"
              />
              <label className="text-sm text-ink-muted">End</label>
              <input
                type="time"
                value={workEnd}
                onChange={e => setWorkEnd(e.target.value)}
                disabled={loading}
                className="rounded-input border border-border bg-surface px-3 py-2 text-ink text-sm focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent disabled:opacity-60"
              />
            </div>
          </section>

          <section>
            <h2 className="text-sm font-medium text-ink mb-3">Preferred days</h2>
            <div className="flex flex-wrap gap-2">
              {DAY_LABELS.map((day, i) => (
                <label
                  key={day}
                  className="inline-flex items-center gap-2 rounded-button border border-border bg-surface px-3 py-2 text-sm text-ink cursor-pointer hover:bg-surface-muted has-[:checked]:border-accent has-[:checked]:bg-accent-muted"
                >
                  <input
                    type="checkbox"
                    checked={selectedDays[i]}
                    onChange={e => {
                      const next = [...selectedDays];
                      next[i] = e.target.checked;
                      setSelectedDays(next);
                    }}
                    disabled={loading}
                    className="rounded border-border text-accent focus:ring-accent"
                  />
                  {day}
                </label>
              ))}
            </div>
          </section>

          <section>
            <h2 className="text-sm font-medium text-ink mb-3">
              Max hours per day
            </h2>
            <div className="flex items-center gap-4">
              <input
                type="range"
                min="2"
                max="12"
                value={maxHours}
                onChange={e => setMaxHours(parseInt(e.target.value, 10))}
                disabled={loading}
                className="w-48 h-2 rounded-full appearance-none bg-border accent-accent disabled:opacity-60"
              />
              <span className="text-sm text-ink-muted">{maxHours} hours</span>
            </div>
          </section>

          <button
            type="submit"
            disabled={saving || loading}
            className="mt-4 rounded-button bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-hover disabled:opacity-60 w-fit"
          >
            {saving ? 'Saving…' : 'Save preferences'}
          </button>
        </form>
        </div>

        <p className="mt-8 pt-6 border-t border-border text-xs text-ink-subtle">
          Calendar theme, dark mode, and per-course colors will be available in
          a future update.
        </p>
      </div>
    </div>
  );
}
