import React, { useState } from 'react';

export default function UploadPage() {
  const [topic, setTopic] = useState('');
  const [content, setContent] = useState('');
  const [message, setMessage] = useState('');

  const submit = async (e) => {
    e.preventDefault();
    setMessage('');
    const res = await fetch('/upload', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ topic, content })
    });
    if (res.ok) {
      setMessage('Uploaded!');
      setTopic('');
      setContent('');
    } else {
      setMessage('Upload failed');
    }
  };

  return (
    <div>
      <h2>Upload Study Material</h2>
      <form onSubmit={submit}>
        <div>
          <input
            type="text"
            placeholder="Topic"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            required
          />
        </div>
        <div>
          <textarea
            placeholder="Content"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            rows={10}
            required
          />
        </div>
        <button type="submit">Upload</button>
      </form>
      {message && <p>{message}</p>}
    </div>
  );
}
