import React from 'react';
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import StudyList from './pages/StudyList';
import StudyDetail from './pages/StudyDetail';

const navStyle = {
  background: '#161b22',
  padding: '12px 24px',
  display: 'flex',
  alignItems: 'center',
  gap: '24px',
  borderBottom: '1px solid #30363d',
};

const logoStyle = {
  fontSize: '18px',
  fontWeight: 700,
  color: '#58a6ff',
  textDecoration: 'none',
};

const containerStyle = {
  maxWidth: '1400px',
  margin: '0 auto',
  padding: '24px',
};

export default function App() {
  return (
    <BrowserRouter>
      <nav style={navStyle}>
        <Link to="/" style={logoStyle}>Hyperparams Ops</Link>
        <Link to="/" style={{ color: '#8b949e', textDecoration: 'none' }}>Studies</Link>
      </nav>
      <div style={containerStyle}>
        <Routes>
          <Route path="/" element={<StudyList />} />
          <Route path="/studies/:name" element={<StudyDetail />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}
