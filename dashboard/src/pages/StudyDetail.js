import React, { useEffect, useState, useMemo } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';
import useWebSocket from '../hooks/useWebSocket';
import BestTrialCard from '../components/BestTrialCard';
import OptimizationChart from '../components/OptimizationChart';
import ParallelCoordinatePlot from '../components/ParallelCoordinatePlot';
import TrialsTable from '../components/TrialsTable';
import WorkerPods from '../components/WorkerPods';
import StudyControls from '../components/StudyControls';

const API = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const sectionStyle = {
  marginBottom: '24px',
};

const gridStyle = {
  display: 'grid',
  gridTemplateColumns: '1fr 1fr',
  gap: '16px',
  marginBottom: '24px',
};

export default function StudyDetail() {
  const { name } = useParams();
  const [trials, setTrials] = useState([]);
  const [best, setBest] = useState(null);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const { messages, connected } = useWebSocket(name);

  const fetchData = () => {
    Promise.all([
      axios.get(`${API}/studies/${name}/trials`),
      axios.get(`${API}/studies/${name}/best`).catch(() => null),
      axios.get(`${API}/studies/${name}/stats`).catch(() => null),
    ]).then(([trialsRes, bestRes, statsRes]) => {
      setTrials(trialsRes.data);
      if (bestRes) setBest(bestRes.data);
      if (statsRes) setStats(statsRes.data);
    }).catch((err) => {
      console.error('Failed to fetch study data:', err);
    }).finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, [name]);

  // Merge WebSocket updates into trials
  const mergedTrials = useMemo(() => {
    const trialMap = new Map();
    trials.forEach((t) => trialMap.set(t.number, t));

    messages.forEach((msg) => {
      const existing = trialMap.get(msg.trial_number);
      if (existing) {
        trialMap.set(msg.trial_number, {
          ...existing,
          state: msg.status === 'complete' ? 'COMPLETE' : msg.status === 'pruned' ? 'PRUNED' : 'RUNNING',
          value: msg.value ?? existing.value,
          params: msg.params ?? existing.params,
        });
      } else {
        trialMap.set(msg.trial_number, {
          number: msg.trial_number,
          state: msg.status === 'complete' ? 'COMPLETE' : msg.status === 'pruned' ? 'PRUNED' : 'RUNNING',
          value: msg.value,
          params: msg.params || {},
          duration: null,
          datetime_start: null,
          datetime_complete: null,
          intermediate_values: {},
        });
      }
    });

    return Array.from(trialMap.values()).sort((a, b) => a.number - b.number);
  }, [trials, messages]);

  if (loading) {
    return <p style={{ color: '#8b949e' }}>Loading study data...</p>;
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <h1 style={{ fontSize: '24px' }}>{name}</h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{
            width: '8px', height: '8px', borderRadius: '50%',
            background: connected ? '#3fb950' : '#f85149',
            display: 'inline-block',
          }} />
          <span style={{ color: '#8b949e', fontSize: '13px' }}>
            {connected ? 'Live' : 'Disconnected'}
          </span>
        </div>
      </div>

      <div style={gridStyle}>
        <BestTrialCard best={best} />
        <StudyControls studyName={name} stats={stats} onRefresh={fetchData} />
      </div>

      <div style={sectionStyle}>
        <OptimizationChart trials={mergedTrials} />
      </div>

      <div style={sectionStyle}>
        <ParallelCoordinatePlot trials={mergedTrials} />
      </div>

      <div style={sectionStyle}>
        <WorkerPods stats={stats} />
      </div>

      <div style={sectionStyle}>
        <TrialsTable trials={mergedTrials} />
      </div>
    </div>
  );
}
