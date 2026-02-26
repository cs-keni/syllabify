/**
 * Admin page: list users, disable/enable, reset security.
 */
import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { getAdminUsers, disableUser, resetUserSecurity } from '../api/client';
import toast from 'react-hot-toast';

export default function Admin() {
  const { token } = useAuth();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

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

  if (loading) {
    return (
      <div className="py-12 text-center text-ink-muted animate-pulse">Loading users…</div>
    );
  }

  if (error) {
    return (
      <div className="space-y-4">
        <p className="text-red-600">{error}</p>
        <button
          type="button"
          onClick={load}
          className="rounded-button bg-accent px-4 py-2 text-sm text-white"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-fade-in">
      <h1 className="text-2xl font-semibold text-ink">Admin — User management</h1>
      <div className="rounded-card bg-surface-elevated border border-border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-surface-muted border-b border-border">
            <tr>
              <th className="text-left p-3 font-medium text-ink">ID</th>
              <th className="text-left p-3 font-medium text-ink">Username</th>
              <th className="text-left p-3 font-medium text-ink">Email</th>
              <th className="text-left p-3 font-medium text-ink">Security</th>
              <th className="text-left p-3 font-medium text-ink">Admin</th>
              <th className="text-left p-3 font-medium text-ink">Disabled</th>
              <th className="text-left p-3 font-medium text-ink">Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.map(u => (
              <tr key={u.id} className="border-t border-border-subtle hover:bg-surface-muted/50">
                <td className="p-3 text-ink-muted">{u.id}</td>
                <td className="p-3 font-medium">{u.username}</td>
                <td className="p-3 text-ink-muted">{u.email || '—'}</td>
                <td className="p-3">{u.security_setup_done ? 'Yes' : 'No'}</td>
                <td className="p-3">{u.is_admin ? 'Yes' : '—'}</td>
                <td className="p-3">{u.is_disabled ? 'Yes' : 'No'}</td>
                <td className="p-3">
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => handleDisable(u.id, !u.is_disabled)}
                      className="rounded-button border border-border px-2 py-1 text-xs hover:bg-surface-muted"
                    >
                      {u.is_disabled ? 'Enable' : 'Disable'}
                    </button>
                    <button
                      type="button"
                      onClick={() => handleResetSecurity(u.id)}
                      className="rounded-button border border-border px-2 py-1 text-xs hover:bg-surface-muted"
                    >
                      Reset security
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {users.length === 0 && (
          <p className="p-6 text-center text-ink-muted">No users found.</p>
        )}
      </div>
    </div>
  );
}
