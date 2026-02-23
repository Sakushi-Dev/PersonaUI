// ── Error Boundary ──

import { Component } from 'react';

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({ errorInfo });
    console.error('[ErrorBoundary]', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          padding: '40px',
          maxWidth: '600px',
          margin: '60px auto',
          background: 'rgba(255,255,255,0.9)',
          borderRadius: '12px',
          fontFamily: 'system-ui, sans-serif',
          color: '#1a1a1a',
        }}>
          <h2 style={{ color: '#ef4444', marginTop: 0 }}>Etwas ist schiefgelaufen</h2>
          <p style={{ color: '#666' }}>{this.state.error?.message}</p>
          <details style={{ marginTop: '16px' }}>
            <summary style={{ cursor: 'pointer', color: '#4f78e6' }}>Stack Trace</summary>
            <pre style={{
              fontSize: '12px',
              overflow: 'auto',
              background: '#f0f0f0',
              padding: '12px',
              borderRadius: '8px',
              marginTop: '8px',
            }}>
              {this.state.error?.stack}
              {this.state.errorInfo?.componentStack}
            </pre>
          </details>
          <button
            onClick={() => window.location.reload()}
            style={{
              marginTop: '20px',
              padding: '10px 24px',
              background: '#4f78e6',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              cursor: 'pointer',
              fontSize: '14px',
            }}
          >
            Seite neu laden
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
