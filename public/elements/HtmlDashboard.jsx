import React, { useState } from 'react';

export default function HtmlDashboard(componentProps) {
  const [loading, setLoading] = useState(true);

  // Chainlit은 CustomElement에 props를 다양한 방식으로 주입합니다 (scope.props 또는 component arguments)
  // 모든 경우의 수를 안전하게 병합합니다.
  let scopeProps = {};
  try {
    if (typeof props !== 'undefined' && props) {
      scopeProps = props;
    }
  } catch (e) {}

  const p = {
    ...scopeProps,
    ...(componentProps || {}),
    ...((componentProps && componentProps.props) || {}),
  };

  const url = p.url;
  const title = p.title || '데이터 분석 대시보드';
  const height = p.height || '80vh';

  const containerStyle = {
    width: '100%',
    height: '100%',
    minHeight: '600px',
    display: 'flex',
    flexDirection: 'column',
    borderRadius: '12px',
    overflow: 'hidden',
    boxShadow: '0 4px 20px rgba(0, 0, 0, 0.08)',
    border: '1px solid rgba(226, 232, 240, 0.8)',
    background: '#ffffff',
    margin: '4px 0',
  };

  const headerStyle = {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '12px 18px',
    background: 'linear-gradient(135deg, #1E3A8A 0%, #2563EB 60%, #3B82F6 100%)',
    color: '#ffffff',
    fontSize: '14px',
    fontWeight: '600',
    letterSpacing: '-0.2px',
    fontFamily: "'Pretendard', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
    flexShrink: 0,
  };

  const titleWrapperStyle = {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  };

  const badgeStyle = {
    fontSize: '11px',
    fontWeight: '700',
    background: 'rgba(255, 255, 255, 0.2)',
    padding: '2px 8px',
    borderRadius: '12px',
    letterSpacing: '0.5px',
    textTransform: 'uppercase',
  };

  const btnStyle = {
    padding: '5px 14px',
    borderRadius: '6px',
    border: '1px solid rgba(255, 255, 255, 0.35)',
    background: 'rgba(255, 255, 255, 0.15)',
    color: '#ffffff',
    fontSize: '12px',
    fontWeight: '600',
    cursor: 'pointer',
    textDecoration: 'none',
    transition: 'all 0.2s ease',
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
    flexShrink: 0,
  };

  const iframeContainerStyle = {
    position: 'relative',
    flex: 1,
    width: '100%',
    minHeight: '550px',
    background: '#f8fafc',
  };

  const iframeStyle = {
    width: '100%',
    height: '100%',
    minHeight: '550px',
    border: 'none',
    display: 'block',
  };

  const loaderStyle = {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    display: loading ? 'flex' : 'none',
    alignItems: 'center',
    justifyContent: 'center',
    background: '#ffffff',
    color: '#64748b',
    fontSize: '14px',
    zIndex: 1,
  };

  if (!url) {
    return (
      <div style={{ padding: '24px', color: '#ef4444', textAlign: 'center', background: '#fee2e2', borderRadius: '8px' }}>
        ⚠️ 대시보드 URL이 제공되지 않았습니다. (Props: {JSON.stringify(p)})
      </div>
    );
  }

  return (
    <div style={containerStyle}>
      <div style={headerStyle}>
        <div style={titleWrapperStyle}>
          <span style={badgeStyle}>Interactive</span>
          <span>{title}</span>
        </div>
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          style={btnStyle}
          onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(255, 255, 255, 0.3)')}
          onMouseLeave={(e) => (e.currentTarget.style.background = 'rgba(255, 255, 255, 0.15)')}
        >
          새 탭에서 전체화면 열기 ↗
        </a>
      </div>
      <div style={iframeContainerStyle}>
        {loading && (
          <div style={loaderStyle}>
            ⏳ 대시보드를 불러오는 중입니다...
          </div>
        )}
        <iframe
          src={url}
          style={iframeStyle}
          title={title}
          onLoad={() => setLoading(false)}
          sandbox="allow-scripts allow-same-origin allow-popups allow-forms"
        />
      </div>
    </div>
  );
}
