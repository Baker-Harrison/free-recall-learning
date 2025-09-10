import React, { useState } from 'react';

export default function HistoryPage() {
  const [topic, setTopic] = useState('');
  const [items, setItems] = useState([]);

  const fetchHistory = async () => {
    const res = await fetch(`/history/${encodeURIComponent(topic)}`);
    if (res.ok) {
      setItems(await res.json());
    } else {
      setItems([]);
    }
  };

  return (
    <div>
      <h2>History</h2>
      <div>
        <input
          type="text"
          placeholder="Topic"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
        />
        <button onClick={fetchHistory}>Load</button>
      </div>
      <ul>
        {items.map((h, idx) => (
          <li key={idx}>
            <strong>{h.created_at}</strong> - Score {h.score}
            <details>
              <summary>Feedback</summary>
              <p>{h.feedback}</p>
              <p><em>Your recall:</em> {h.recall_text}</p>
            </details>
          </li>
        ))}
      </ul>
    </div>
  );
}
