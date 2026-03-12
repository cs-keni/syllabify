/**
 * Profile page. Banner, custom avatar (including GIFs), description.
 */
import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Link } from 'react-router-dom';
import {
  getProfile,
  updateProfile,
  uploadAvatar,
  uploadBanner,
} from '../api/client';
import toast from 'react-hot-toast';
import { AVATAR_OPTIONS, getAvatarUrl } from '../lib/avatarOptions';

const imgUrl = getAvatarUrl;

export default function Profile() {
  const { token, user, refreshUser } = useAuth();
  const [bannerUrl, setBannerUrl] = useState('');
  const [avatarUrl, setAvatarUrl] = useState('');
  const [avatar, setAvatar] = useState(null);
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [uploadingBanner, setUploadingBanner] = useState(false);
  const [uploadingAvatar, setUploadingAvatar] = useState(false);

  useEffect(() => {
    if (!token) return;
    setAvatarError(false);
    getProfile(token)
      .then(p => {
        if (p) {
          setBannerUrl(p.banner_url || '');
          setAvatarUrl(p.avatar_url || '');
          setAvatar(p.avatar || null);
          setDescription(p.description || '');
        }
      })
      .finally(() => setLoading(false));
  }, [token]);

  const handleSave = async e => {
    e.preventDefault();
    if (!token) return;
    setSaving(true);
    try {
      await updateProfile(token, {
        banner_url: bannerUrl.trim() || null,
        avatar_url: avatarUrl.trim() || null,
        avatar: avatar || null,
        description: description.trim() || null,
      });
      await refreshUser();
      toast.success('Profile saved');
    } catch (err) {
      toast.error(err.message || 'Failed to save');
    } finally {
      setSaving(false);
    }
  };

  const initials = user?.username
    ? user.username
        .slice(0, 2)
        .toUpperCase()
        .replace(/[^A-Z0-9]/g, '') || '?'
    : '?';

  const [avatarError, setAvatarError] = useState(false);

  const displayAvatar = () => {
    const src = imgUrl(avatarUrl.trim());
    if (src && !avatarError) {
      return (
        <img
          key={avatarUrl}
          src={src}
          alt="Profile"
          className="w-full h-full rounded-full object-cover"
          onError={() => setAvatarError(true)}
        />
      );
    }
    if (avatar && AVATAR_OPTIONS.find(o => o.key === avatar)) {
      const opt = AVATAR_OPTIONS.find(o => o.key === avatar);
      return (
        <img
          src={opt.src}
          alt={opt.label}
          className="w-full h-full rounded-full object-cover"
        />
      );
    }
    return (
      <span className="text-accent text-2xl font-semibold">{initials}</span>
    );
  };

  const handleAvatarUrlChange = v => {
    setAvatarUrl(v);
    setAvatarError(false);
    if (v.trim()) setAvatar(null);
  };

  const handleBannerUpload = async e => {
    const file = e?.target?.files?.[0];
    if (!file || !token) return;
    setUploadingBanner(true);
    try {
      const { url } = await uploadBanner(token, file);
      setBannerUrl(url);
      const p = await updateProfile(token, { banner_url: url });
      if (p?.banner_url != null) setBannerUrl(p.banner_url);
      await refreshUser();
      toast.success('Banner uploaded and saved');
    } catch (err) {
      toast.error(err.message || 'Failed to upload banner');
    } finally {
      setUploadingBanner(false);
      e.target.value = '';
    }
  };

  const handleAvatarUpload = async e => {
    const file = e?.target?.files?.[0];
    if (!file || !token) return;
    setUploadingAvatar(true);
    try {
      const { url } = await uploadAvatar(token, file);
      setAvatarUrl(url);
      setAvatar(null);
      setAvatarError(false);
      const p = await updateProfile(token, { avatar_url: url });
      if (p?.avatar_url != null) setAvatarUrl(p.avatar_url);
      await refreshUser();
      toast.success('Profile picture uploaded and saved');
    } catch (err) {
      toast.error(err.message || 'Failed to upload');
    } finally {
      setUploadingAvatar(false);
      e.target.value = '';
    }
  };

  return (
    <div className="space-y-6">
      <div className="animate-fade-in">
        <Link
          to="/app"
          className="text-sm text-ink-muted hover:text-ink transition-colors no-underline"
        >
          ← Dashboard
        </Link>
        <h1 className="mt-2 text-2xl font-semibold text-ink">Profile</h1>
        <p className="mt-1 text-sm text-ink-muted">
          Customize your banner, profile picture (GIFs supported), and bio.
        </p>
      </div>

      <form
        onSubmit={handleSave}
        className="rounded-xl border border-border bg-surface-elevated overflow-hidden shadow-card animate-fade-in [animation-delay:100ms]"
      >
        {/* Banner */}
        <div className="h-32 overflow-hidden bg-surface-muted">
          {imgUrl(bannerUrl.trim()) ? (
            <img
              key={bannerUrl}
              src={imgUrl(bannerUrl.trim())}
              alt="Banner"
              className="w-full h-full object-cover"
              onError={e => {
                e.target.style.display = 'none';
              }}
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-ink-muted text-sm">
              No banner
            </div>
          )}
        </div>

        <div className="p-6 space-y-6">
          <div>
            <label className="block text-sm font-medium text-ink mb-1">
              Banner
            </label>
            <div className="flex gap-2 flex-wrap">
              <label className="rounded-button bg-accent text-accent-inv px-3 py-2 text-sm font-medium hover:bg-accent-hover cursor-pointer disabled:opacity-50">
                <input
                  type="file"
                  accept="image/jpeg,image/png,image/gif,image/webp"
                  onChange={handleBannerUpload}
                  disabled={loading || uploadingBanner}
                  className="sr-only"
                />
                {uploadingBanner ? 'Uploading…' : 'Upload from computer'}
              </label>
            </div>
            <input
              type="text"
              value={bannerUrl}
              onChange={e => setBannerUrl(e.target.value)}
              placeholder="Or paste image URL (e.g. from Imgur)"
              disabled={loading}
              className="mt-2 w-full rounded-input border border-border bg-surface px-3 py-2 text-ink text-sm placeholder:text-ink-subtle focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent disabled:opacity-60"
            />
          </div>

          <div className="flex flex-col sm:flex-row gap-6">
            <div className="shrink-0">
              <label className="block text-sm font-medium text-ink mb-2">
                Profile picture
              </label>
              <div className="w-24 h-24 rounded-full bg-accent-muted flex items-center justify-center overflow-hidden border-2 border-border">
                {displayAvatar()}
              </div>
              <p className="mt-2 text-xs text-ink-muted font-medium">
                Preset avatars
              </p>
              <div className="flex gap-2 mt-1">
                {AVATAR_OPTIONS.map(opt => (
                  <button
                    key={opt.key}
                    type="button"
                    onClick={() => {
                      setAvatar(opt.key);
                      setAvatarUrl('');
                    }}
                    className={`w-10 h-10 rounded-full border-2 overflow-hidden transition-all ${
                      avatar === opt.key && !avatarUrl
                        ? 'border-accent ring-2 ring-accent/30'
                        : 'border-border hover:border-ink-muted'
                    }`}
                  >
                    <img
                      src={opt.src}
                      alt={opt.label}
                      className="w-full h-full object-cover"
                    />
                  </button>
                ))}
              </div>
            </div>
            <div className="flex-1 min-w-0">
              <label className="block text-sm font-medium text-ink mb-1">
                Custom profile picture
              </label>
              <div className="flex gap-2 mb-2">
                <label className="rounded-button bg-accent text-accent-inv px-3 py-2 text-sm font-medium hover:bg-accent-hover cursor-pointer disabled:opacity-50">
                  <input
                    type="file"
                    accept="image/jpeg,image/png,image/gif,image/webp"
                    onChange={handleAvatarUpload}
                    disabled={loading || uploadingAvatar}
                    className="sr-only"
                  />
                  {uploadingAvatar ? 'Uploading…' : 'Upload from computer'}
                </label>
              </div>
              <input
                type="text"
                value={avatarUrl}
                onChange={e => handleAvatarUrlChange(e.target.value)}
                placeholder="Or paste image URL (GIFs work)"
                disabled={loading}
                className="w-full rounded-input border border-border bg-surface px-3 py-2 text-ink text-sm placeholder:text-ink-subtle focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent disabled:opacity-60"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-ink mb-1">
              Bio / description
            </label>
            <textarea
              value={description}
              onChange={e => setDescription(e.target.value)}
              placeholder="A short bio about yourself..."
              rows={4}
              maxLength={2000}
              disabled={loading}
              className="w-full rounded-input border border-border bg-surface px-3 py-2 text-ink text-sm placeholder:text-ink-subtle focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent disabled:opacity-60 resize-y"
            />
            <p className="mt-1 text-xs text-ink-subtle">
              {description.length}/2000 characters
            </p>
          </div>

          <button
            type="submit"
            disabled={saving || loading}
            className="rounded-button bg-accent text-accent-inv px-4 py-2 text-sm font-medium hover:bg-accent-hover disabled:opacity-50"
          >
            {saving ? 'Saving…' : 'Save profile'}
          </button>
        </div>
      </form>
    </div>
  );
}
