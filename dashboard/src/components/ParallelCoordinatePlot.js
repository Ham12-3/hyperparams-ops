import React, { useMemo } from 'react';
import {
  ScatterChart, Scatter, XAxis, YAxis, ZAxis, Tooltip,
  ResponsiveContainer, CartesianGrid,
} from 'recharts';

const cardStyle = {
  background: '#161b22',
  border: '1px solid #30363d',
  borderRadius: '8px',
  padding: '20px',
};

/**
 * Simplified parallel coordinate visualization using scatter plots.
 * Shows parameter relationships via scatter chart facets.
 */
export default function ParallelCoordinatePlot({ trials }) {
  const completedTrials = useMemo(
    () => trials.filter((t) => t.state === 'COMPLETE' && t.value != null),
    [trials]
  );

  const paramKeys = useMemo(() => {
    if (completedTrials.length === 0) return [];
    return Object.keys(completedTrials[0].params || {}).filter(
      (k) => typeof completedTrials[0].params[k] === 'number'
    );
  }, [completedTrials]);

  const scatterData = useMemo(() => {
    return completedTrials.map((t) => ({
      ...t.params,
      value: t.value,
      trial: t.number,
    }));
  }, [completedTrials]);

  if (completedTrials.length === 0 || paramKeys.length === 0) {
    return (
      <div style={cardStyle}>
        <h3 style={{ color: '#8b949e', marginBottom: '16px', fontSize: '14px' }}>
          Parameter Relationships
        </h3>
        <p style={{ color: '#484f58', textAlign: 'center', padding: '40px' }}>
          Waiting for completed trials with numeric parameters...
        </p>
      </div>
    );
  }

  return (
    <div style={cardStyle}>
      <h3 style={{ color: '#8b949e', marginBottom: '16px', fontSize: '14px' }}>
        Parameter Relationships
      </h3>
      <div style={{ display: 'grid', gridTemplateColumns: `repeat(${Math.min(paramKeys.length, 3)}, 1fr)`, gap: '12px' }}>
        {paramKeys.slice(0, 6).map((param) => (
          <div key={param}>
            <p style={{ color: '#8b949e', fontSize: '12px', marginBottom: '4px', textAlign: 'center' }}>
              {param} vs value
            </p>
            <ResponsiveContainer width="100%" height={180}>
              <ScatterChart margin={{ top: 5, right: 5, bottom: 5, left: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#21262d" />
                <XAxis
                  dataKey={param}
                  type="number"
                  stroke="#484f58"
                  tick={{ fontSize: 10 }}
                  name={param}
                />
                <YAxis
                  dataKey="value"
                  type="number"
                  stroke="#484f58"
                  tick={{ fontSize: 10 }}
                  name="value"
                />
                <ZAxis range={[30, 30]} />
                <Tooltip
                  contentStyle={{ background: '#0d1117', border: '1px solid #30363d', borderRadius: '6px', fontSize: '12px' }}
                  cursor={{ strokeDasharray: '3 3' }}
                />
                <Scatter data={scatterData} fill="#58a6ff" />
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        ))}
      </div>
    </div>
  );
}
