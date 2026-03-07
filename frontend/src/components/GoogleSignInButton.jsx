/**
 * Sign in with Google button using Google Identity Services.
 * Requires VITE_GOOGLE_CLIENT_ID. On success, calls onSuccess(idToken).
 */
import { useEffect, useRef } from 'react';

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || '';

export default function GoogleSignInButton({ onSuccess, onError, disabled, className = '' }) {
  const containerRef = useRef(null);
  const cbRef = useRef({ onSuccess, onError });
  cbRef.current = { onSuccess, onError };

  useEffect(() => {
    if (!GOOGLE_CLIENT_ID || !containerRef.current) return;

    const init = () => {
      try {
        window.google.accounts.id.initialize({
          client_id: GOOGLE_CLIENT_ID,
          callback: (response) => {
            const { onSuccess: ok, onError: err } = cbRef.current;
            if (response?.credential) {
              ok?.(response.credential);
            } else {
              err?.(new Error('No credential received'));
            }
          },
        });
        window.google.accounts.id.renderButton(containerRef.current, {
          type: 'standard',
          theme: 'outline',
          size: 'large',
          text: 'continue_with',
          width: 320,
        });
      } catch (e) {
        cbRef.current.onError?.(e);
      }
    };

    if (typeof window.google === 'undefined') {
      const check = setInterval(() => {
        if (typeof window.google !== 'undefined') {
          clearInterval(check);
          init();
        }
      }, 100);
      return () => clearInterval(check);
    }
    init();
  }, []);

  if (!GOOGLE_CLIENT_ID) return null;

  return (
    <div
      ref={containerRef}
      className={className}
      style={{ minHeight: 44 }}
      aria-hidden={disabled}
    />
  );
}
