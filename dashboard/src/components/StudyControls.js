import React, { useState } from 'react';
import axios from 'axios';

const API = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const cardStyle = {
  background: '#161b22',
  border: '1px solid #30363d',
  borderRadius: '8px',
  padding: '20px',
};

const btnStyle = (color) => ({
  background: color,
  color: '#fff',
  border: 'none',
  borderRadius: '6px',
  padding: '8px 16px',
  fontSize: '13px',
  cursor: 'pointer',
  fontWeight: 600,
  marginRight: '8px',
});

const inputStyle = {
  background: '#0d1117',
  border: '1px solid #30363d',
  borderRadius: '6px',
  color: '#e1e4e8',
  padding: '6px 10px',
  width: '60px',
  fontSize: '13px',
  marginRight: '8px',
};

export default function StudyControls({ studyName, stats, onRefresh }) {
  const [workerCount, setWorkerCount] = useState(2);
  const [busy, setBusy] = useState(false);

  const handleScale = async () => {
    setBusy(true);
    try {
      await axios.post(`${API}/studies/${studyName}/scale`, {
        num_workers: workerCount,
        n_trials_per_worker: 5,
      });
      if (onRefresh) onRefresh();
    } catch (err) {
      console.error('Failed to scale workers:', err);
    } finally {
      setBusy(false);
    }
  };

  const handleStop = async () => {
    setBusy(true);
    try {
      await axios.post(`${API}/studies/${studyName}/stop`, { cleanup: true });
      if (onRefresh) onRefresh();
    } catch (err) {
      console.error('Failed to stop study:', err);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div style={cardStyle}>
      <h3 style={{ color: '#8b949e', marginBottom: '16px', fontSize: '14px' }}>
        Controls
      </h3>

      <div style={{ marginBottom: '16px' }}>
        <label style={{ color: '#8b949e', fontSize: '13px', marginRight: '8px' }}>
          Workers:
        </label>
        <input
          type="number"
          min="1"
          max="20"
          value={workerCount}
          onChange={(e) => setWorkerCount(parseInt(e.target.value) || 1)}
          style={inputStyle}
        />
        <button onClick={handleScale} style={btnStyle('#1f6feb')} disabled={busy}>
          Scale
        </button>
      </div>

      <div style={{ display: 'flex', gap: '8px' }}>
        <button onClick={handleStop} style={btnStyle('#da3633')} disabled={busy}>
          Stop Study
        </button>
        <button onClick={onRefresh} style={btnStyle('#30363d')} disabled={busy}>
          Refresh
        </button>
      </div>

      {stats && (
        <div style={{ marginTop: '16px', fontSize: '12px', color: '#484f58' }}>
          Total trials: {stats.total_trials} | Active pods: {stats.active_pods}
        </div>
      )}
    </div>
  );
}
