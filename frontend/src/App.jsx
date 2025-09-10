import React from 'react';
import { Routes, Route, Link } from 'react-router-dom';
import UploadPage from './components/UploadPage.jsx';
import DuePage from './components/DuePage.jsx';
import RecallPage from './components/RecallPage.jsx';
import HistoryPage from './components/HistoryPage.jsx';

export default function App() {
  return (
    <div style={{ maxWidth: '800px', margin: '0 auto', padding: '1rem' }}>
      <nav style={{ marginBottom: '1rem' }}>
        <Link to="/upload">Upload</Link> |{' '}
        <Link to="/due">Due Topics</Link> |{' '}
        <Link to="/history">History</Link>
      </nav>
      <Routes>
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/due" element={<DuePage />} />
        <Route path="/recall/:topic" element={<RecallPage />} />
        <Route path="/history" element={<HistoryPage />} />
        <Route path="*" element={<DuePage />} />
      </Routes>
    </div>
  );
}
