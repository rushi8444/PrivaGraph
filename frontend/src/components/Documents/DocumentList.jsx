export default function DocumentList({ documents }) {
  if (!documents?.length) {
    return (
      <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '2rem' }}>
        No documents ingested yet.
      </p>
    );
  }

  const classificationClass = (c) => `badge badge-${c.toLowerCase()}`;

  return (
    <div className="doc-list">
      {documents.map((doc, i) => (
        <div
          key={doc.id}
          className="glass-card doc-card"
          style={{ animationDelay: `${i * 60}ms` }}
        >
          <div>
            <div className="doc-card-title">{doc.title}</div>
            <div className="doc-card-meta">
              {doc.department} · {doc.author} · {doc.created}
            </div>
          </div>
          <div className="doc-card-stats">
            <span className="doc-stat">🏷️ {doc.entity_count} entities</span>
            <span className="doc-stat">🔗 {doc.triple_count} triples</span>
          </div>
          <span className={classificationClass(doc.classification)}>
            {doc.classification}
          </span>
        </div>
      ))}
    </div>
  );
}
