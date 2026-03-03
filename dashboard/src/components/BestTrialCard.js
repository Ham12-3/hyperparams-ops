import React from 'react';

const cardStyle = {
  background: '#161b22',
  border: '1px solid #30363d',
  borderRadius: '8px',
  padding: '20px',
};

const valueStyle = {
  fontSize: '32px',
  fontWeight: 700,
  color: '#3fb950',
  marginBottom: '8px',
};

const paramRow = {
  display: 'flex',
  justifyContent: 'space-between',
  padding: '4px 0',
  borderBottom: '1px solid #21262d',
  fontSize: '13px',
};

export default function BestTrialCard({ best }) {
  if (!best) {
    return (
      <div style={cardStyle}>
        <h3 style={{ color: '#8b949e', marginBottom: '8px' }}>Best Trial</h3>
        <p style={{ color: '#484f58' }}>No completed trials yet</p>
      </div>
    );
  }

  return (
    <div style={cardStyle}>
      <h3 style={{ color: '#8b949e', marginBottom: '8px', fontSize: '14px' }}>
        Best Trial #{best.number}
      </h3>
      <div style={valueStyle}>{best.value?.toFixed(4)}</div>
      <div>
        {best.params && Object.entries(best.params).map(([key, val]) => (
          <div key={key} style={paramRow}>
            <span style={{ color: '#8b949e' }}>{key}</span>
            <span>{typeof val === 'number' ? val.toFixed(6) : String(val)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
