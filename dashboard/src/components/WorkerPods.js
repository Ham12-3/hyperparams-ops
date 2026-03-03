import React from 'react';

const cardStyle = {
  background: '#161b22',
  border: '1px solid #30363d',
  borderRadius: '8px',
  padding: '20px',
};

const podStyle = (phase) => ({
  background: '#0d1117',
  border: `1px solid ${phase === 'Running' ? '#238636' : phase === 'Pending' ? '#d29922' : '#30363d'}`,
  borderRadius: '6px',
  padding: '12px',
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  marginBottom: '8px',
});

const phaseColors = {
  Running: '#3fb950',
  Pending: '#d29922',
  Succeeded: '#8b949e',
  Failed: '#f85149',
};

export default function WorkerPods({ stats }) {
  const pods = stats?.pods || [];

  return (
    <div style={cardStyle}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <h3 style={{ color: '#8b949e', fontSize: '14px' }}>
          Worker Pods
        </h3>
        <span style={{ color: '#484f58', fontSize: '13px' }}>
          {stats?.active_pods || 0} active
        </span>
      </div>

      {pods.length === 0 ? (
        <p style={{ color: '#484f58', textAlign: 'center', padding: '20px' }}>
          No worker pods (K8s may not be enabled)
        </p>
      ) : (
        pods.map((pod) => (
          <div key={pod.name} style={podStyle(pod.phase)}>
            <div>
              <div style={{ fontSize: '13px', fontWeight: 600, marginBottom: '2px' }}>
                {pod.name}
              </div>
              <div style={{ fontSize: '11px', color: '#484f58' }}>
                Node: {pod.node || 'N/A'}
                {pod.restart_count > 0 && ` | Restarts: ${pod.restart_count}`}
              </div>
            </div>
            <span style={{
              color: phaseColors[pod.phase] || '#8b949e',
              fontWeight: 600,
              fontSize: '12px',
            }}>
              {pod.phase}
              {pod.reason && ` (${pod.reason})`}
            </span>
          </div>
        ))
      )}

      {stats && (
        <div style={{ marginTop: '16px', display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px' }}>
          {[
            { label: 'Completed', value: stats.completed, color: '#3fb950' },
            { label: 'Running', value: stats.running, color: '#58a6ff' },
            { label: 'Pruned', value: stats.pruned, color: '#d29922' },
            { label: 'Failed', value: stats.failed, color: '#f85149' },
          ].map(({ label, value, color }) => (
            <div key={label} style={{ textAlign: 'center', padding: '8px', background: '#0d1117', borderRadius: '6px' }}>
              <div style={{ fontSize: '20px', fontWeight: 700, color }}>{value || 0}</div>
              <div style={{ fontSize: '11px', color: '#8b949e' }}>{label}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
