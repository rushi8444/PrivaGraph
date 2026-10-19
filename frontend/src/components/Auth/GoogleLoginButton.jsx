import { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../api/client';

export default function GoogleLoginButton({ disabled = false }) {
  const { loginWithGoogle } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [googleClientId, setGoogleClientId] = useState(
    import.meta.env.VITE_GOOGLE_CLIENT_ID || ''
  );
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);
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

  // 2. Load Google Identity Services (GIS) script and render the official button
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
            width: googleBtnRef.current.offsetWidth || 360,
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

  return (
    <div style={{ width: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
      {/* Official Functional Google Button */}
      <div
        ref={googleBtnRef}
        style={{
          width: '100%',
          display: 'flex',
          justifyContent: 'center',
          minHeight: '44px',
          overflow: 'hidden',
          borderRadius: '8px',
          pointerEvents: disabled || loading ? 'none' : 'auto',
          opacity: disabled || loading ? 0.6 : 1,
        }}
      />

      {loading && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '8px' }}>
          <div className="sidebar-pulse-dot" style={{ width: '6px', height: '6px' }} />
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Signing in with Google...
          </span>
        </div>
      )}

      {errorMsg && (
        <div style={{ marginTop: '8px', color: '#f87171', fontSize: '0.78rem', textAlign: 'center' }}>
          {errorMsg}
        </div>
      )}
    </div>
  );
}
