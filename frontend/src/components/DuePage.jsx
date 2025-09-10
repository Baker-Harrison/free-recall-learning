import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

export default function DuePage() {
  const [topics, setTopics] = useState([]);

  useEffect(() => {
    fetch('/due')
      .then((r) => r.json())
      .then(setTopics)
      .catch(() => setTopics([]));
  }, []);

  return (
    <div>
      <h2>Due Topics</h2>
      {topics.length === 0 && <p>No topics due.</p>}
      <ul>
        {topics.map((t) => (
          <li key={t}>
            <Link to={`/recall/${encodeURIComponent(t)}`}>{t}</Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
