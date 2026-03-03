import React, { useMemo } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine,
} from 'recharts';

const cardStyle = {
  background: '#161b22',
  border: '1px solid #30363d',
  borderRadius: '8px',
  padding: '20px',
};

export default function OptimizationChart({ trials }) {
  const data = useMemo(() => {
    let bestSoFar = -Infinity;
    return trials
      .filter((t) => t.state === 'COMPLETE' && t.value != null)
      .map((t) => {
        bestSoFar = Math.max(bestSoFar, t.value);
        return {
          trial: t.number,
          value: t.value,
          best: bestSoFar,
        };
      });
  }, [trials]);

  const bestValue = data.length > 0 ? data[data.length - 1].best : null;

  return (
    <div style={cardStyle}>
      <h3 style={{ color: '#8b949e', marginBottom: '16px', fontSize: '14px' }}>
        Optimization History
      </h3>
      {data.length === 0 ? (
        <p style={{ color: '#484f58', textAlign: 'center', padding: '40px' }}>
          Waiting for completed trials...
        </p>
      ) : (
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#21262d" />
            <XAxis
              dataKey="trial"
              stroke="#484f58"
              label={{ value: 'Trial', position: 'insideBottom', offset: -5, fill: '#8b949e' }}
            />
            <YAxis stroke="#484f58" />
            <Tooltip
              contentStyle={{ background: '#0d1117', border: '1px solid #30363d', borderRadius: '6px' }}
              labelStyle={{ color: '#8b949e' }}
            />
            <Line
              type="monotone"
              dataKey="value"
              stroke="#58a6ff"
              dot={{ fill: '#58a6ff', r: 3 }}
              name="Trial Value"
            />
            <Line
              type="stepAfter"
              dataKey="best"
              stroke="#3fb950"
              strokeDasharray="5 5"
              dot={false}
              name="Best So Far"
            />
            {bestValue && (
              <ReferenceLine y={bestValue} stroke="#3fb950" strokeDasharray="3 3" />
            )}
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
