import { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../api/client';
import { GoogleIcon } from '../Common/Icons';

export default function GoogleLoginButton({ disabled = false }) {
  const { loginWithGoogle } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [googleClientId, setGoogleClientId] = useState(
    import.meta.env.VITE_GOOGLE_CLIENT_ID || ''
  );
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);
  const [showConfigNotice, setShowConfigNotice] = useState(false);
  const googleBtnRef = useRef(null);

  const from = location.state?.from?.pathname || '/query';

  // 1. Fetch server-side configured Google Client ID if not supplied in env
  useEffect(() => {
    let active = true;
    api
      .getGoogleConfig()
      .then((cfg) => {
        if (active && cfg?.client_id) {
          setGoogleClientId(cfg.client_id);
        }
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, []);

  // 2. Load Google Identity Services (GIS) script
  useEffect(() => {
    if (!googleClientId) return;

    const scriptId = 'google-gis-client';
    if (!document.getElementById(scriptId)) {
      const script = document.createElement('script');
      script.id = scriptId;
      script.src = 'https://accounts.google.com/gsi/client';
      script.async = true;
      script.defer = true;
      script.onload = initGis;
      document.body.appendChild(script);
    } else if (window.google?.accounts?.id) {
      initGis();
    }

    function initGis() {
      if (!window.google?.accounts?.id || !googleClientId) return;

      try {
        window.google.accounts.id.initialize({
          client_id: googleClientId,
          callback: handleCredentialResponse,
          auto_select: false,
          cancel_on_tap_outside: true,
        });

        if (googleBtnRef.current) {
          window.google.accounts.id.renderButton(googleBtnRef.current, {
            theme: 'filled_black',
            size: 'large',
            width: '100%',
            text: 'continue_with',
            shape: 'rectangular',
          });
        }
      } catch (err) {
        console.warn('Google Identity initialization failed:', err);
      }
    }
  }, [googleClientId]);

  const handleCredentialResponse = async (response) => {
    if (!response?.credential) return;
    setLoading(true);
    setErrorMsg(null);
    try {
      await loginWithGoogle(response.credential);
      navigate(from, { replace: true });
    } catch (err) {
      setErrorMsg(err.message || 'Google authentication failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleManualClick = async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      let clientId = googleClientId;
      if (!clientId) {
        const cfg = await api.getGoogleConfig().catch(() => null);
        if (cfg?.client_id) {
          clientId = cfg.client_id;
          setGoogleClientId(cfg.client_id);
        }
      }

      if (clientId) {
        // Direct browser to Google OAuth redirect endpoint
        window.location.href = 'http://localhost:8000/api/v1/auth/google/login';
      } else {
        setShowConfigNotice(true);
      }
    } catch {
      window.location.href = 'http://localhost:8000/api/v1/auth/google/login';
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ width: '100%' }}>
      {/* Hidden GIS native button container if GIS rendered it */}
      <div
        ref={googleBtnRef}
        style={{
          display: googleClientId ? 'block' : 'none',
          width: '100%',
          overflow: 'hidden',
          borderRadius: '8px',
        }}
      />

      {/* Styled PrivaGraph Google Button fallback / manual trigger */}
      {(!googleClientId || !window.google?.accounts?.id) && (
        <button
          type="button"
          onClick={handleManualClick}
          disabled={disabled || loading}
          className="btn btn-ghost"
          style={{
            width: '100%',
            padding: '10px 16px',
            borderRadius: '8px',
            border: '1px solid rgba(255, 255, 255, 0.15)',
            background: 'rgba(255, 255, 255, 0.04)',
            color: 'var(--text-primary)',
            fontSize: '0.875rem',
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '10px',
            cursor: 'pointer',
            transition: 'all 0.2s ease',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = 'rgba(255, 255, 255, 0.08)';
            e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.25)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = 'rgba(255, 255, 255, 0.04)';
            e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.15)';
          }}
        >
          {loading ? (
            <div className="sidebar-pulse-dot" style={{ width: '8px', height: '8px' }} />
          ) : (
            <GoogleIcon size={18} />
          )}
          <span>Continue with Google</span>
        </button>
      )}

      {errorMsg && (
        <div style={{ marginTop: '8px', color: '#f87171', fontSize: '0.78rem', textAlign: 'center' }}>
          {errorMsg}
        </div>
      )}

      {/* Helpful developer modal if Google OAuth Client ID is not configured yet in .env */}
      {showConfigNotice && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0, 0, 0, 0.75)',
            backdropFilter: 'blur(6px)',
            zIndex: 1000,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '20px',
          }}
          onClick={() => setShowConfigNotice(false)}
        >
          <div
            className="card animate-in"
            style={{
              maxWidth: '440px',
              width: '100%',
              background: '#0d131f',
              border: '1px solid rgba(99, 102, 241, 0.3)',
              borderRadius: '14px',
              padding: '24px',
              boxShadow: '0 20px 40px rgba(0, 0, 0, 0.8)',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '14px' }}>
              <GoogleIcon size={24} />
              <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
                Google OAuth Setup
              </h3>
            </div>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.5, marginBottom: '14px' }}>
              Google OAuth backend endpoints are active. To enable live one-click Google Sign-In with your Google Cloud project, add your client ID to <code>.env</code>:
            </p>
            <div
              style={{
                background: 'rgba(0, 0, 0, 0.5)',
                padding: '10px 12px',
                borderRadius: '6px',
                fontFamily: 'var(--font-mono)',
                fontSize: '0.8rem',
                color: '#818cf8',
                marginBottom: '18px',
                border: '1px solid rgba(255, 255, 255, 0.08)',
              }}
            >
              GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com<br />
              GOOGLE_CLIENT_SECRET=your-client-secret
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={() => setShowConfigNotice(false)}
              >
                Understood
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
