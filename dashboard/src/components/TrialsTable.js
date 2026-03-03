import React, { useState, useMemo } from 'react';

const cardStyle = {
  background: '#161b22',
  border: '1px solid #30363d',
  borderRadius: '8px',
  padding: '20px',
  overflow: 'auto',
};

const thStyle = {
  textAlign: 'left',
  padding: '10px 12px',
  borderBottom: '2px solid #30363d',
  color: '#8b949e',
  fontSize: '12px',
  fontWeight: 600,
  textTransform: 'uppercase',
  cursor: 'pointer',
  userSelect: 'none',
  whiteSpace: 'nowrap',
};

const tdStyle = {
  padding: '8px 12px',
  borderBottom: '1px solid #21262d',
  fontSize: '13px',
  whiteSpace: 'nowrap',
};

const stateColors = {
  COMPLETE: '#3fb950',
  RUNNING: '#58a6ff',
  PRUNED: '#d29922',
  FAIL: '#f85149',
};

export default function TrialsTable({ trials }) {
  const [sortKey, setSortKey] = useState('number');
  const [sortAsc, setSortAsc] = useState(true);

  const handleSort = (key) => {
    if (sortKey === key) {
      setSortAsc(!sortAsc);
    } else {
      setSortKey(key);
      setSortAsc(true);
    }
  };

  const sorted = useMemo(() => {
    return [...trials].sort((a, b) => {
      let aVal = a[sortKey];
      let bVal = b[sortKey];
      if (aVal == null) return 1;
      if (bVal == null) return -1;
      if (typeof aVal === 'string') return sortAsc ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
      return sortAsc ? aVal - bVal : bVal - aVal;
    });
  }, [trials, sortKey, sortAsc]);

  const paramKeys = useMemo(() => {
    if (trials.length === 0) return [];
    const keys = new Set();
    trials.forEach((t) => Object.keys(t.params || {}).forEach((k) => keys.add(k)));
    return Array.from(keys);
  }, [trials]);

  const arrow = (key) => sortKey === key ? (sortAsc ? ' \u25B2' : ' \u25BC') : '';

  return (
    <div style={cardStyle}>
      <h3 style={{ color: '#8b949e', marginBottom: '16px', fontSize: '14px' }}>
        All Trials ({trials.length})
      </h3>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            <th style={thStyle} onClick={() => handleSort('number')}>#{ arrow('number')}</th>
            <th style={thStyle} onClick={() => handleSort('state')}>Status{arrow('state')}</th>
            <th style={thStyle} onClick={() => handleSort('value')}>Value{arrow('value')}</th>
            <th style={thStyle} onClick={() => handleSort('duration')}>Duration{arrow('duration')}</th>
            {paramKeys.map((k) => (
              <th key={k} style={thStyle}>{k}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((trial) => (
            <tr key={trial.number}>
              <td style={tdStyle}>{trial.number}</td>
              <td style={tdStyle}>
                <span style={{
                  color: stateColors[trial.state] || '#8b949e',
                  fontWeight: 600,
                  fontSize: '12px',
                }}>
                  {trial.state}
                </span>
              </td>
              <td style={tdStyle}>{trial.value != null ? trial.value.toFixed(4) : '-'}</td>
              <td style={tdStyle}>{trial.duration != null ? `${trial.duration.toFixed(1)}s` : '-'}</td>
              {paramKeys.map((k) => (
                <td key={k} style={tdStyle}>
                  {trial.params?.[k] != null
                    ? (typeof trial.params[k] === 'number'
                      ? trial.params[k].toFixed(4)
                      : String(trial.params[k]))
                    : '-'}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
