/**
 * Preferences: Account (email), work hours, preferred days.
 * Backend integration: Phase 4 (Account), Phase 6 (study prefs).
 */
import { useState, useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import {
  getProfile,
  updateProfile,
  getPreferences,
  updatePreferences,
  changePassword,
} from '../api/client';
import { useAccent } from '../contexts/AccentContext';
import toast from 'react-hot-toast';

const DAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const DAY_TO_CODE = {
  Mon: 'MO',
  Tue: 'TU',
  Wed: 'WE',
  Thu: 'TH',
  Fri: 'FR',
  Sat: 'SA',
  Sun: 'SU',
};

function parsePreferredDays(csv) {
  if (!csv || typeof csv !== 'string') return [];
  return csv
    .split(',')
    .map(s => s.trim().toUpperCase())
    .filter(Boolean);
}

const PASSWORD_REQUIREMENTS = [
  { key: 'length', test: p => p.length >= 8, label: 'At least 8 characters' },
  { key: 'upper', test: p => /[A-Z]/.test(p), label: 'One uppercase letter' },
  { key: 'lower', test: p => /[a-z]/.test(p), label: 'One lowercase letter' },
  { key: 'number', test: p => /\d/.test(p), label: 'One number' },
  { key: 'special', test: p => /[!@#$%^&*()_+\-=[\]{};':"\\|,.<>/?`~]/.test(p), label: 'One special character' },
];

export default function Preferences() {
  const { token } = useAuth();
  const { accent, setAccent, palettes } = useAccent();
  const [email, setEmail] = useState('');
  const [workStart, setWorkStart] = useState('09:00');
  const [workEnd, setWorkEnd] = useState('17:00');
  const [selectedDays, setSelectedDays] = useState([
    true,
    true,
    true,
    true,
    true,
    false,
    false,
  ]);
  const [maxHours, setMaxHours] = useState(8);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [timezone, setTimezone] = useState('');
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmNewPassword, setConfirmNewPassword] = useState('');
  const [passwordError, setPasswordError] = useState('');
  const [passwordSaving, setPasswordSaving] = useState(false);

  const passwordReqStatus = useMemo(
    () => PASSWORD_REQUIREMENTS.map(r => ({ ...r, met: r.test(newPassword) })),
    [newPassword]
  );
  const passwordAllMet = passwordReqStatus.every(r => r.met);

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
          setTimezone(prefs.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone || '');
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

  const handleChangePassword = async e => {
    e.preventDefault();
    if (!token) return;
    setPasswordError('');
    if (newPassword !== confirmNewPassword) {
      setPasswordError('New passwords do not match');
      return;
    }
    if (!passwordAllMet) {
      setPasswordError('New password does not meet all requirements');
      return;
    }
    setPasswordSaving(true);
    try {
      await changePassword(token, {
        currentPassword,
        newPassword,
      });
      toast.success('Password changed');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmNewPassword('');
    } catch (err) {
      setPasswordError(err.message || 'Failed to change password');
    } finally {
      setPasswordSaving(false);
    }
  };

  const handleSavePreferences = async e => {
    e.preventDefault();
    if (!token) return;
    setSaving(true);
    try {
      const codes = DAY_LABELS.filter((_, i) => selectedDays[i]).map(
        d => DAY_TO_CODE[d]
      );
      await updatePreferences(token, {
        work_start: workStart,
        work_end: workEnd,
        preferred_days: codes.join(','),
        max_hours_per_day: maxHours,
        timezone: timezone || null,
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
                <label
                  htmlFor="email"
                  className="block text-sm text-ink-muted mb-1"
                >
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
                className="rounded-button bg-[#0F8A4C] px-4 py-2 text-sm font-medium text-[#F5C30F] hover:bg-[#094728] disabled:opacity-60 w-fit"
              >
                {saving ? 'Saving…' : 'Save'}
              </button>
            </form>

            <div className="mt-6 pt-6 border-t border-border">
              <h3 className="text-sm font-medium text-ink mb-3">Change password</h3>
              <form onSubmit={handleChangePassword} className="flex flex-col gap-3 max-w-md">
                {passwordError && (
                  <p className="text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800/60 rounded-input px-3 py-2">
                    {passwordError}
                  </p>
                )}
                <div>
                  <label htmlFor="currentPassword" className="block text-sm text-ink-muted mb-1">
                    Current password
                  </label>
                  <input
                    id="currentPassword"
                    type="password"
                    value={currentPassword}
                    onChange={e => setCurrentPassword(e.target.value)}
                    required
                    autoComplete="current-password"
                    disabled={loading}
                    className="w-full rounded-input border border-border bg-surface px-3 py-2 text-ink text-sm focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent disabled:opacity-60"
                  />
                </div>
                <div>
                  <label htmlFor="newPassword" className="block text-sm text-ink-muted mb-1">
                    New password
                  </label>
                  <input
                    id="newPassword"
                    type="password"
                    value={newPassword}
                    onChange={e => setNewPassword(e.target.value)}
                    required
                    autoComplete="new-password"
                    disabled={loading}
                    className="w-full rounded-input border border-border bg-surface px-3 py-2 text-ink text-sm focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent disabled:opacity-60"
                  />
                  <div className="mt-1.5 flex flex-wrap gap-x-3 gap-y-1">
                    {passwordReqStatus.map(r => (
                      <span
                        key={r.key}
                        className={`inline-flex items-center gap-1.5 text-xs transition-all duration-200 ${
                          r.met ? 'text-green-600 dark:text-green-400' : 'text-ink-muted'
                        }`}
                      >
                        <span
                          className={`inline-block w-3.5 h-3.5 rounded-full border-2 flex items-center justify-center shrink-0 transition-all duration-200 ${
                            r.met ? 'border-green-600 dark:border-green-400 bg-green-600 dark:bg-green-400' : 'border-ink-muted/60'
                          }`}
                        >
                          {r.met && (
                            <svg className="w-2 h-2 text-white" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                            </svg>
                          )}
                        </span>
                        {r.label}
                      </span>
                    ))}
                  </div>
                </div>
                <div>
                  <label htmlFor="confirmNewPassword" className="block text-sm text-ink-muted mb-1">
                    Confirm new password
                  </label>
                  <input
                    id="confirmNewPassword"
                    type="password"
                    value={confirmNewPassword}
                    onChange={e => setConfirmNewPassword(e.target.value)}
                    required
                    autoComplete="new-password"
                    disabled={loading}
                    className="w-full rounded-input border border-border bg-surface px-3 py-2 text-ink text-sm focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent disabled:opacity-60"
                  />
                </div>
                <button
                  type="submit"
                  disabled={passwordSaving || loading || !passwordAllMet}
                  className="rounded-button bg-[#0F8A4C] px-4 py-2 text-sm font-medium text-[#F5C30F] hover:bg-[#094728] disabled:opacity-60 w-fit"
                >
                  {passwordSaving ? 'Changing…' : 'Change password'}
                </button>
              </form>
            </div>
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
              <h2 className="text-sm font-medium text-ink mb-3">
                Preferred days
              </h2>
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
                      className="rounded border-border accent-accent focus:ring-accent"
                    />
                    {day}
                  </label>
                ))}
              </div>
            </section>

            <section>
              <h2 className="text-sm font-medium text-ink mb-3">Timezone</h2>
              <select
                value={timezone}
                onChange={e => setTimezone(e.target.value)}
                disabled={loading}
                className="w-full max-w-md rounded-input border border-border bg-surface px-3 py-2 text-ink text-sm focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent disabled:opacity-60"
              >
                <option value="">
                  {typeof Intl !== 'undefined'
                    ? `Browser default (${Intl.DateTimeFormat().resolvedOptions().timeZone})`
                    : 'Browser default'}
                </option>
                <option value="America/New_York">Eastern (America/New_York)</option>
                <option value="America/Chicago">Central (America/Chicago)</option>
                <option value="America/Denver">Mountain (America/Denver)</option>
                <option value="America/Los_Angeles">Pacific (America/Los_Angeles)</option>
                <option value="UTC">UTC</option>
              </select>
              <p className="mt-1 text-xs text-ink-subtle">
                Used for due dates and scheduling. Defaults to your browser
                timezone.
              </p>
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
              className="mt-4 rounded-button bg-[#0F8A4C] px-4 py-2 text-sm font-medium text-[#F5C30F] hover:bg-[#094728] disabled:opacity-60 w-fit"
            >
              {saving ? 'Saving…' : 'Save preferences'}
            </button>
          </form>
        </div>

        <section className="mt-8 pt-6 border-t border-border">
          <h2 className="text-sm font-medium text-ink mb-3">Accent color</h2>
          <div className="flex flex-wrap gap-2">
            {palettes.map(key => {
              const colors = {
                green: '#0f8a4c',
                blue: '#2563eb',
                purple: '#7c3aed',
                indigo: '#4f46e5',
              }[key];
              return (
                <button
                  key={key}
                  type="button"
                  onClick={() => setAccent(key)}
                  title={`Use ${key} accent`}
                  className={`w-9 h-9 rounded-full border-2 transition-all ${
                    accent === key
                      ? 'border-accent ring-2 ring-accent/30'
                      : 'border-border hover:border-ink-muted'
                  }`}
                  style={{ backgroundColor: colors }}
                  aria-pressed={accent === key}
                  aria-label={`${key} accent`}
                />
              );
            })}
          </div>
          <p className="mt-2 text-xs text-ink-subtle">
            Choose an accent color for buttons and links.
          </p>
        </section>
      </div>
    </div>
  );
}
