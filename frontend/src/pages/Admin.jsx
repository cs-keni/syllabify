/**
 * Admin page: user management. Distinct admin control-panel aesthetic.
 */
import { useState, useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import {
  getAdminUsers,
  getAdminUserDetails,
  disableUser,
  resetUserSecurity,
  setAdminUser,
  adminSetPassword,
} from '../api/client';
import toast from 'react-hot-toast';

function Badge({ variant, children }) {
  const styles = {
    success: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/50 dark:text-emerald-300',
    danger: 'bg-red-100 text-red-800 dark:bg-red-900/50 dark:text-red-300',
    admin: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900/50 dark:text-indigo-300',
    muted: 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-400',
  };
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${styles[variant] || styles.muted}`}
    >
      {children}
    </span>
  );
}

export default function Admin() {
  const { token, user } = useAuth();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [filterAdmin, setFilterAdmin] = useState('all'); // all | admin | client
  const [filterStatus, setFilterStatus] = useState('all'); // all | active | disabled
  const [filterSecurity, setFilterSecurity] = useState('all'); // all | done | pending
  const [expandedUserId, setExpandedUserId] = useState(null);
  const [expandedDetails, setExpandedDetails] = useState(null);
  const [tempPassword, setTempPassword] = useState('');
  const [settingPassword, setSettingPassword] = useState(false);

  const filteredUsers = useMemo(() => {
    let result = [...users];
    const q = searchQuery.trim().toLowerCase();
    if (q) {
      result = result.filter(
        u =>
          (u.username || '').toLowerCase().includes(q) ||
          (u.email || '').toLowerCase().includes(q)
      );
    }
    if (filterAdmin === 'admin') result = result.filter(u => u.is_admin);
    else if (filterAdmin === 'client') result = result.filter(u => !u.is_admin);
    if (filterStatus === 'active') result = result.filter(u => !u.is_disabled);
    else if (filterStatus === 'disabled') result = result.filter(u => u.is_disabled);
    if (filterSecurity === 'done') result = result.filter(u => u.security_setup_done);
    else if (filterSecurity === 'pending') result = result.filter(u => !u.security_setup_done);
    return result;
  }, [users, searchQuery, filterAdmin, filterStatus, filterSecurity]);

  const PASSWORD_REQS = [
    { key: 'len', test: p => p.length >= 8, label: '8+ chars' },
    { key: 'upper', test: p => /[A-Z]/.test(p), label: 'uppercase' },
    { key: 'lower', test: p => /[a-z]/.test(p), label: 'lowercase' },
    { key: 'num', test: p => /\d/.test(p), label: 'number' },
    { key: 'special', test: p => /[!@#$%^&*()_+\-=[\]{};':"\\|,.<>/?`~]/.test(p), label: 'special' },
  ];
  const tempPasswordOk = PASSWORD_REQS.every(r => r.test(tempPassword));

  const handleSetPassword = async () => {
    if (!expandedUserId || !tempPasswordOk) return;
    setSettingPassword(true);
    try {
      await adminSetPassword(token, expandedUserId, tempPassword);
      toast.success('Password set. User should change it on next login.');
      setTempPassword('');
    } catch (e) {
      toast.error(e.message || 'Failed');
    } finally {
      setSettingPassword(false);
    }
  };

  const toggleUserDetails = async userId => {
    if (expandedUserId === userId) {
      setExpandedUserId(null);
      setExpandedDetails(null);
      setTempPassword('');
      return;
    }
    setExpandedUserId(userId);
    setExpandedDetails(null);
    try {
      const data = await getAdminUserDetails(token, userId);
      setExpandedDetails(data);
    } catch (e) {
      toast.error(e.message || 'Failed to load details');
      setExpandedUserId(null);
      setExpandedDetails(null);
    }
  };

  const load = async () => {
    if (!token) return;
    setLoading(true);
    setError('');
    try {
      const data = await getAdminUsers(token);
      if (!data?.users) {
        setError(data?.error || 'Failed to load users');
        setUsers([]);
      } else {
        setUsers(data.users);
      }
    } catch (e) {
      setError(e.message || 'Failed to load');
      setUsers([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [token]);

  const handleDisable = async (userId, disabled) => {
    try {
      await disableUser(token, userId, disabled);
      toast.success(disabled ? 'User disabled' : 'User enabled');
      load();
    } catch (e) {
      toast.error(e.message || 'Failed');
    }
  };

  const handleResetSecurity = async userId => {
    try {
      await resetUserSecurity(token, userId);
      toast.success('Security reset');
      load();
    } catch (e) {
      toast.error(e.message || 'Failed');
    }
  };

  const handleSetAdmin = async (userId, isAdmin) => {
    try {
      await setAdminUser(token, userId, isAdmin);
      toast.success(isAdmin ? 'Granted admin' : 'Removed admin');
      load();
    } catch (e) {
      toast.error(e.message || 'Failed');
    }
  };

  const totalUsers = users.length;
  const adminCount = users.filter(u => u.is_admin).length;
  const disabledCount = users.filter(u => u.is_disabled).length;
  const hasFilters = searchQuery.trim() || filterAdmin !== 'all' || filterStatus !== 'all' || filterSecurity !== 'all';

  if (loading) {
    return (
      <div className="admin-shell">
        <div className="admin-header">
          <div className="admin-header-inner">
            <span className="admin-title">Control Panel</span>
            <span className="admin-subtitle">User management</span>
          </div>
        </div>
        <div className="admin-body">
          <div className="py-16 text-center text-slate-500 dark:text-slate-400 animate-pulse">
            Loading users…
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="admin-shell">
        <div className="admin-header">
          <div className="admin-header-inner">
            <span className="admin-title">Control Panel</span>
          </div>
        </div>
        <div className="admin-body">
          <div className="rounded-lg border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-950/30 p-4 space-y-4">
            <p className="text-red-700 dark:text-red-300">{error}</p>
            <button
              type="button"
              onClick={load}
              className="rounded-lg bg-slate-800 dark:bg-slate-600 text-white px-4 py-2 text-sm font-medium hover:bg-slate-700 dark:hover:bg-slate-500 transition-colors"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="admin-shell animate-fade-in">
      {/* Admin header bar - distinct from client */}
      <div className="admin-header">
        <div className="admin-header-inner">
          <div className="flex items-center gap-3">
            <span
              className="flex items-center justify-center w-9 h-9 rounded-lg bg-white/10"
              aria-hidden
            >
              <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
            </span>
            <div>
              <span className="admin-title">Control Panel</span>
              <span className="admin-subtitle">User management</span>
            </div>
          </div>
          <Link
            to="/app"
            className="text-sm text-white/80 hover:text-white no-underline transition-colors flex items-center gap-1.5"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            Back to app
          </Link>
        </div>
      </div>

      <div className="admin-body">
        {/* Search & filters */}
        <div className="flex flex-col sm:flex-row gap-3 mb-6">
          <div className="relative flex-1">
            <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              type="search"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              placeholder="Search by username or email..."
              className="w-full pl-9 pr-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-100 text-sm placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-500"
            />
          </div>
          <div className="flex flex-wrap gap-2">
            <select
              value={filterAdmin}
              onChange={e => setFilterAdmin(e.target.value)}
              className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-100 text-sm px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500/30"
            >
              <option value="all">All roles</option>
              <option value="admin">Admins only</option>
              <option value="client">Clients only</option>
            </select>
            <select
              value={filterStatus}
              onChange={e => setFilterStatus(e.target.value)}
              className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-100 text-sm px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500/30"
            >
              <option value="all">All status</option>
              <option value="active">Active</option>
              <option value="disabled">Disabled</option>
            </select>
            <select
              value={filterSecurity}
              onChange={e => setFilterSecurity(e.target.value)}
              className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-100 text-sm px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500/30"
            >
              <option value="all">All security</option>
              <option value="done">Setup done</option>
              <option value="pending">Pending</option>
            </select>
            {hasFilters && (
              <button
                type="button"
                onClick={() => {
                  setSearchQuery('');
                  setFilterAdmin('all');
                  setFilterStatus('all');
                  setFilterSecurity('all');
                }}
                className="text-sm text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
              >
                Clear filters
              </button>
            )}
          </div>
        </div>

        {/* Stats bar */}
        <div className="flex flex-wrap gap-4 mb-6">
          <div className="rounded-lg bg-slate-100 dark:bg-slate-800 px-4 py-2 border border-slate-200 dark:border-slate-700">
            <span className="text-slate-500 dark:text-slate-400 text-xs uppercase tracking-wider">Total users</span>
            <span className="block text-lg font-semibold text-slate-800 dark:text-slate-100 font-mono">{totalUsers}</span>
          </div>
          <div className="rounded-lg bg-indigo-50 dark:bg-indigo-950/40 px-4 py-2 border border-indigo-200 dark:border-indigo-800/60">
            <span className="text-indigo-600 dark:text-indigo-400 text-xs uppercase tracking-wider">Admins</span>
            <span className="block text-lg font-semibold text-indigo-800 dark:text-indigo-200 font-mono">{adminCount}</span>
          </div>
          <div className="rounded-lg bg-red-50 dark:bg-red-950/30 px-4 py-2 border border-red-200 dark:border-red-800/50">
            <span className="text-red-600 dark:text-red-400 text-xs uppercase tracking-wider">Disabled</span>
            <span className="block text-lg font-semibold text-red-800 dark:text-red-200 font-mono">{disabledCount}</span>
          </div>
          {hasFilters && (
            <div className="rounded-lg bg-indigo-100 dark:bg-indigo-900/30 px-4 py-2 border border-indigo-200 dark:border-indigo-700/50">
              <span className="text-indigo-600 dark:text-indigo-400 text-xs uppercase tracking-wider">Showing</span>
              <span className="block text-lg font-semibold text-indigo-800 dark:text-indigo-200 font-mono">{filteredUsers.length}</span>
            </div>
          )}
        </div>

        {/* Users table */}
        <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-slate-50 dark:bg-slate-800/80 border-b border-slate-200 dark:border-slate-700">
                  <th className="text-left p-3 w-10" aria-label="Expand" />
                  <th className="text-left p-3 font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider text-xs w-14">ID</th>
                  <th className="text-left p-3 font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider text-xs">Username</th>
                  <th className="text-left p-3 font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider text-xs hidden sm:table-cell">Email</th>
                  <th className="text-left p-3 font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider text-xs w-20">Security</th>
                  <th className="text-left p-3 font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider text-xs w-16">Admin</th>
                  <th className="text-left p-3 font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider text-xs w-20">Status</th>
                  <th className="text-left p-3 font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider text-xs">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
                {filteredUsers.map(u => (
                  <tr
                    key={u.id}
                    className={`hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors ${u.is_disabled ? 'opacity-70' : ''}`}
                  >
                    <td className="p-3">
                      <button
                        type="button"
                        onClick={() => toggleUserDetails(u.id)}
                        className="inline-flex items-center justify-center w-6 h-6 rounded text-slate-500 hover:text-indigo-600 hover:bg-indigo-50 dark:hover:bg-indigo-900/30 transition-colors"
                        title={expandedUserId === u.id ? 'Hide details' : 'View details'}
                        aria-expanded={expandedUserId === u.id}
                      >
                        <svg
                          className={`w-4 h-4 transition-transform ${expandedUserId === u.id ? 'rotate-90' : ''}`}
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                        >
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                        </svg>
                      </button>
                    </td>
                    <td className="p-3 font-mono text-slate-500 dark:text-slate-400 text-xs">{u.id}</td>
                    <td className="p-3 font-medium text-slate-800 dark:text-slate-100">{u.username}</td>
                    <td className="p-3 text-slate-600 dark:text-slate-400 text-xs hidden sm:table-cell truncate max-w-[180px]" title={u.email || ''}>
                      {u.email || '—'}
                    </td>
                    <td className="p-3">
                      <Badge variant={u.security_setup_done ? 'success' : 'muted'}>
                        {u.security_setup_done ? 'Done' : '—'}
                      </Badge>
                    </td>
                    <td className="p-3">
                      {u.is_admin ? <Badge variant="admin">Admin</Badge> : '—'}
                    </td>
                    <td className="p-3">
                      <Badge variant={u.is_disabled ? 'danger' : 'success'}>
                        {u.is_disabled ? 'Disabled' : 'Active'}
                      </Badge>
                    </td>
                    <td className="p-3">
                      <div className="flex flex-wrap gap-1.5">
                        <button
                          type="button"
                          onClick={() => handleDisable(u.id, !u.is_disabled)}
                          className={`rounded-md px-2 py-1 text-xs font-medium transition-colors ${
                            u.is_disabled
                              ? 'bg-emerald-600 text-white hover:bg-emerald-700'
                              : 'bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300 hover:bg-red-200 dark:hover:bg-red-900/70'
                          }`}
                        >
                          {u.is_disabled ? 'Enable' : 'Disable'}
                        </button>
                        {u.username !== user?.username && (
                          <button
                            type="button"
                            onClick={() => handleSetAdmin(u.id, !u.is_admin)}
                            className="rounded-md px-2 py-1 text-xs font-medium bg-indigo-100 text-indigo-700 dark:bg-indigo-900/50 dark:text-indigo-300 hover:bg-indigo-200 dark:hover:bg-indigo-900/70 transition-colors"
                            title={u.is_admin ? 'Remove admin' : 'Make admin'}
                          >
                            {u.is_admin ? 'Demote' : 'Make admin'}
                          </button>
                        )}
                        <button
                          type="button"
                          onClick={() => handleResetSecurity(u.id)}
                          className="rounded-md px-2 py-1 text-xs font-medium bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors"
                        >
                          Reset security
                        </button>
                      </div>
                    </td>
                  </tr>
                  {expandedUserId === u.id && (
                    <tr className="bg-slate-50/80 dark:bg-slate-800/50">
                      <td colSpan={7} className="p-4 pl-12">
                        {expandedDetails ? (
                        <div className="space-y-4">
                          <div className="flex flex-wrap gap-6 text-sm">
                            <span className="text-slate-600 dark:text-slate-400">
                              <strong className="text-slate-800 dark:text-slate-100">{expandedDetails.terms_count}</strong> terms
                            </span>
                            <span className="text-slate-600 dark:text-slate-400">
                              <strong className="text-slate-800 dark:text-slate-100">{expandedDetails.courses_count}</strong> courses
                            </span>
                            <span className="text-slate-600 dark:text-slate-400">
                              <strong className="text-slate-800 dark:text-slate-100">{expandedDetails.assignments_count}</strong> assignments
                            </span>
                          </div>
                          <div className="pt-2 border-t border-slate-200 dark:border-slate-700">
                            <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">Set temporary password (account recovery)</label>
                            <div className="flex flex-wrap items-end gap-2">
                              <input
                                type="password"
                                value={tempPassword}
                                onChange={e => setTempPassword(e.target.value)}
                                placeholder="New password"
                                className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-1.5 text-sm text-slate-800 dark:text-slate-100 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 w-48"
                              />
                              <button
                                type="button"
                                onClick={handleSetPassword}
                                disabled={!tempPasswordOk || settingPassword}
                                className="rounded-lg px-3 py-1.5 text-xs font-medium bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
                              >
                                {settingPassword ? 'Setting…' : 'Set password'}
                              </button>
                            </div>
                            <div className="flex flex-wrap gap-2 mt-1">
                              {PASSWORD_REQS.map(r => (
                                <span key={r.key} className={`text-xs ${r.test(tempPassword) ? 'text-emerald-600 dark:text-emerald-400' : 'text-slate-400'}`}>
                                  {r.test(tempPassword) ? '✓' : '○'} {r.label}
                                </span>
                              ))}
                            </div>
                          </div>
                        </div>
                        ) : (
                          <span className="text-slate-400 animate-pulse">Loading…</span>
                        )}
                      </td>
                    </tr>
                  )}
                ))}
              </tbody>
            </table>
          </div>
          {filteredUsers.length === 0 && (
            <div className="p-12 text-center text-slate-500 dark:text-slate-400">
              {users.length === 0 ? 'No users found.' : 'No users match your filters.'}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
