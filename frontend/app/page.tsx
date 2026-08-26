'use client';

import { useEffect, useState } from 'react';

interface SystemStatus {
  trading_mode: string;
  kill_switch: boolean;
  market_phase: string;
  broker_provider: string;
  risk_params: Record<string, number>;
}

export default function Home() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [health, setHealth] = useState<any>(null);

  useEffect(() => {
    fetch('/api/v1/status').then(r => r.json()).then(setStatus).catch(() => {});
    fetch('/api/v1/health').then(r => r.json()).then(setHealth).catch(() => {});
  }, []);

  return (
    <main style={{ padding: '2rem', fontFamily: 'system-ui, sans-serif', maxWidth: '1200px', margin: '0 auto' }}>
      <h1 style={{ fontSize: '2rem', marginBottom: '1rem', color: '#1a1a2e' }}>
        📊 A股智能投研平台
      </h1>
      <p style={{ color: '#666', marginBottom: '2rem' }}>
        A-share Intelligent Investment Research & Automated Trading System
      </p>

      {/* System Status Card */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '1rem', marginBottom: '2rem' }}>
        <Card title="系统状态" value={health?.status || 'loading...'} color="#10b981" />
        <Card title="交易模式" value={status?.trading_mode || '...'} color="#3b82f6" />
        <Card title="Kill Switch" value={status?.kill_switch ? '🔴 激活' : '🟢 关闭'} color={status?.kill_switch ? '#ef4444' : '#10b981'} />
        <Card title="市场阶段" value={status?.market_phase || '...'} color="#8b5cf6" />
      </div>

      {/* Quick Actions */}
      <h2 style={{ fontSize: '1.25rem', marginBottom: '1rem' }}>🚀 快速操作</h2>
      <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
        <Button label="📈 市场概览" onClick={() => window.open('/api/v1/market/overview', '_blank')} />
        <Button label="💹 茅台行情" onClick={() => window.open('/api/v1/market/quote/600519.SH', '_blank')} />
        <Button label="🤖 AI 分析茅台" onClick={async () => {
          const r = await fetch('/api/v1/analysis/stock', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({symbol: '600519.SH'})
          });
          const data = await r.json();
          alert(JSON.stringify(data, null, 2).slice(0, 2000));
        }} />
        <Button label="📊 回测 MACD" onClick={async () => {
          const r = await fetch('/api/v1/backtest/run', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({strategy: 'MACD', symbols: ['600519.SH']})
          });
          const data = await r.json();
          alert(JSON.stringify(data.data?.total_return, null, 2));
        }} />
        <Button label="💰 账户" onClick={() => window.open('/api/v1/trading/account', '_blank')} />
        <Button label="📋 持仓" onClick={() => window.open('/api/v1/trading/positions', '_blank')} />
      </div>

      {/* Risk Params */}
      {status?.risk_params && (
        <>
          <h2 style={{ fontSize: '1.25rem', marginTop: '2rem', marginBottom: '1rem' }}>🛡️ 风控参数</h2>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <tbody>
              {Object.entries(status.risk_params).map(([k, v]) => (
                <tr key={k} style={{ borderBottom: '1px solid #eee' }}>
                  <td style={{ padding: '0.5rem', fontWeight: 'bold' }}>{k}</td>
                  <td style={{ padding: '0.5rem' }}>{String(v)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      <footer style={{ marginTop: '3rem', color: '#999', fontSize: '0.875rem' }}>
        A股智能投研平台 v0.1.0 | Phase 1 - 项目骨架 | {new Date().getFullYear()}
      </footer>
    </main>
  );
}

function Card({ title, value, color }: { title: string; value: string; color: string }) {
  return (
    <div style={{ border: '1px solid #e5e7eb', borderRadius: '8px', padding: '1rem', borderTop: `3px solid ${color}` }}>
      <div style={{ fontSize: '0.875rem', color: '#666', marginBottom: '0.25rem' }}>{title}</div>
      <div style={{ fontSize: '1.25rem', fontWeight: 'bold', color }}>{value}</div>
    </div>
  );
}

function Button({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: '0.75rem 1.25rem',
        border: '1px solid #d1d5db',
        borderRadius: '8px',
        background: 'white',
        cursor: 'pointer',
        fontSize: '0.875rem',
        transition: 'all 0.2s',
      }}
      onMouseEnter={(e) => (e.currentTarget.style.background = '#f3f4f6')}
      onMouseLeave={(e) => (e.currentTarget.style.background = 'white')}
    >
      {label}
    </button>
  );
}
