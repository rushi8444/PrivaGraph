export default function AuditTable({ entries }) {
  if (!entries?.length) {
    return (
      <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '2rem' }}>
        No audit entries yet.
      </p>
    );
  }

  return (
    <div className="audit-table-wrap glass-card">
      <table className="audit-table">
        <thead>
          <tr>
            <th>Timestamp</th>
            <th>Event</th>
            <th>Details</th>
            <th>Hash Chain</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((entry, i) => (
            <tr key={i} style={{ animationDelay: `${i * 30}ms` }} className="animate-in">
              <td>{new Date(entry.timestamp).toLocaleString()}</td>
              <td><span className="audit-event-type">{entry.event_type}</span></td>
              <td>{JSON.stringify(entry.details).slice(0, 80)}...</td>
              <td>
                <span className={`audit-hash ${entry.chain_valid ? 'audit-chain-ok' : 'audit-chain-broken'}`}>
                  {entry.chain_valid ? '✓' : '✗'} {entry.entry_hash?.slice(0, 12)}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
