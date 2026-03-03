import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';

const API = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const cardStyle = {
  background: '#161b22',
  border: '1px solid #30363d',
  borderRadius: '8px',
  padding: '20px',
  marginBottom: '12px',
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  textDecoration: 'none',
  color: 'inherit',
  transition: 'border-color 0.2s',
};

const badgeStyle = (color) => ({
  background: color,
  color: '#fff',
  padding: '4px 10px',
  borderRadius: '12px',
  fontSize: '12px',
  fontWeight: 600,
});

const formStyle = {
  background: '#161b22',
  border: '1px solid #30363d',
  borderRadius: '8px',
  padding: '20px',
  marginBottom: '24px',
};

const inputStyle = {
  background: '#0d1117',
  border: '1px solid #30363d',
  borderRadius: '6px',
  color: '#e1e4e8',
  padding: '8px 12px',
  marginRight: '8px',
  fontSize: '14px',
};

const btnStyle = {
  background: '#238636',
  color: '#fff',
  border: 'none',
  borderRadius: '6px',
  padding: '8px 16px',
  fontSize: '14px',
  cursor: 'pointer',
  fontWeight: 600,
};

export default function StudyList() {
  const [studies, setStudies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [newName, setNewName] = useState('');
  const [creating, setCreating] = useState(false);

  const fetchStudies = () => {
    axios.get(`${API}/studies`)
      .then((res) => setStudies(res.data))
      .catch((err) => console.error('Failed to fetch studies:', err))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchStudies();
    const interval = setInterval(fetchStudies, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!newName.trim()) return;
    setCreating(true);
    try {
      await axios.post(`${API}/studies`, {
        name: newName.trim(),
        direction: 'maximize',
        pruner_type: 'hyperband',
        num_workers: 2,
        n_trials_per_worker: 10,
      });
      setNewName('');
      fetchStudies();
    } catch (err) {
      console.error('Failed to create study:', err);
    } finally {
      setCreating(false);
    }
  };

  return (
    <div>
      <h1 style={{ marginBottom: '24px', fontSize: '24px' }}>Studies</h1>

      <form onSubmit={handleCreate} style={formStyle}>
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <input
            style={inputStyle}
            placeholder="New study name..."
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
          />
          <select
            style={{ ...inputStyle, marginRight: '8px' }}
            defaultValue="maximize"
          >
            <option value="maximize">Maximize</option>
            <option value="minimize">Minimize</option>
          </select>
          <button type="submit" style={btnStyle} disabled={creating}>
            {creating ? 'Creating...' : 'Create Study'}
          </button>
        </div>
      </form>

      {loading ? (
        <p style={{ color: '#8b949e' }}>Loading studies...</p>
      ) : studies.length === 0 ? (
        <p style={{ color: '#8b949e' }}>No studies yet. Create one above.</p>
      ) : (
        studies.map((study) => (
          <Link to={`/studies/${study.name}`} key={study.name} style={cardStyle}>
            <div>
              <h3 style={{ fontSize: '16px', marginBottom: '4px' }}>{study.name}</h3>
              <span style={{ color: '#8b949e', fontSize: '13px' }}>
                {study.n_trials} trials | Started{' '}
                {study.datetime_start
                  ? new Date(study.datetime_start).toLocaleDateString()
                  : 'N/A'}
              </span>
            </div>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <span style={badgeStyle('#1f6feb')}>{study.direction}</span>
              {study.best_value != null && (
                <span style={badgeStyle('#238636')}>
                  Best: {study.best_value.toFixed(4)}
                </span>
              )}
            </div>
          </Link>
        ))
      )}
    </div>
  );
}
