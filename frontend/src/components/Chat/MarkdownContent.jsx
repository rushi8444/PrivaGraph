import { useState } from 'react';
import { CopyIcon, CheckIcon } from '../Common/Icons';

function CodeBlock({ code, language }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      style={{
        margin: '12px 0',
        borderRadius: '8px',
        overflow: 'hidden',
        border: '1px solid rgba(255, 255, 255, 0.1)',
        background: '#070b14',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '6px 12px',
          background: 'rgba(255, 255, 255, 0.04)',
          borderBottom: '1px solid rgba(255, 255, 255, 0.06)',
          fontSize: '0.72rem',
          color: 'var(--text-muted, #94a3b8)',
          fontFamily: 'var(--font-mono, monospace)',
          textTransform: 'lowercase',
        }}
      >
        <span>{language || 'code'}</span>
        <button
          type="button"
          onClick={handleCopy}
          style={{
            background: 'none',
            border: 'none',
            color: copied ? '#10b981' : 'inherit',
            display: 'flex',
            alignItems: 'center',
            gap: '5px',
            cursor: 'pointer',
            padding: '2px 6px',
            borderRadius: '4px',
            fontSize: '0.72rem',
          }}
          title="Copy code to clipboard"
        >
          {copied ? <CheckIcon size={12} /> : <CopyIcon size={12} />}
          <span>{copied ? 'Copied!' : 'Copy'}</span>
        </button>
      </div>
      <pre
        style={{
          margin: 0,
          padding: '12px 14px',
          overflowX: 'auto',
          fontSize: '0.84rem',
          lineHeight: 1.5,
          color: '#e2e8f0',
          fontFamily: 'var(--font-mono, monospace)',
        }}
      >
        <code>{code}</code>
      </pre>
    </div>
  );
}

export default function MarkdownContent({ text }) {
  if (!text) return null;

  // Split content by fenced code blocks (```lang\n...```)
  const codeBlockRegex = /```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g;
  const parts = [];
  let lastIndex = 0;
  let match;

  while ((match = codeBlockRegex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push({
        type: 'text',
        content: text.substring(lastIndex, match.index),
      });
    }
    parts.push({
      type: 'code',
      language: match[1] || '',
      content: match[2].trimEnd(),
    });
    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < text.length) {
    parts.push({
      type: 'text',
      content: text.substring(lastIndex),
    });
  }

  // Format regular markdown blocks (lists, headers, bold, tables)
  const renderTextSegment = (rawText, segIdx) => {
    const lines = rawText.split('\n');
    const elements = [];
    let listBuffer = [];
    let isTable = false;
    let tableRows = [];

    const flushList = () => {
      if (listBuffer.length > 0) {
        elements.push(
          <ul
            key={`list-${elements.length}`}
            style={{
              paddingLeft: '20px',
              margin: '8px 0',
              lineHeight: 1.6,
            }}
          >
            {listBuffer.map((item, i) => (
              <li key={i}>{formatInline(item)}</li>
            ))}
          </ul>
        );
        listBuffer = [];
      }
    };

    const flushTable = () => {
      if (tableRows.length > 0) {
        const headerRow = tableRows[0];
        const bodyRows = tableRows.slice(1).filter((r) => !r.every((cell) => /^:?-+:?$/.test(cell.trim())));

        elements.push(
          <div
            key={`table-wrapper-${elements.length}`}
            style={{
              overflowX: 'auto',
              margin: '12px 0',
              borderRadius: '6px',
              border: '1px solid rgba(255, 255, 255, 0.1)',
            }}
          >
            <table
              style={{
                width: '100%',
                borderCollapse: 'collapse',
                fontSize: '0.825rem',
                textAlign: 'left',
              }}
            >
              <thead>
                <tr style={{ background: 'rgba(255, 255, 255, 0.05)', borderBottom: '1px solid rgba(255, 255, 255, 0.12)' }}>
                  {headerRow.map((cell, i) => (
                    <th key={i} style={{ padding: '8px 12px', fontWeight: 600 }}>
                      {formatInline(cell.trim())}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {bodyRows.map((row, ri) => (
                  <tr
                    key={ri}
                    style={{
                      borderBottom: ri < bodyRows.length - 1 ? '1px solid rgba(255, 255, 255, 0.06)' : 'none',
                    }}
                  >
                    {row.map((cell, ci) => (
                      <td key={ci} style={{ padding: '7px 12px', color: 'var(--text-secondary)' }}>
                        {formatInline(cell.trim())}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
        tableRows = [];
        isTable = false;
      }
    };

    lines.forEach((line, lineIdx) => {
      const trimmed = line.trim();

      // Table line
      if (trimmed.startsWith('|') && trimmed.endsWith('|')) {
        flushList();
        isTable = true;
        const cells = trimmed
          .slice(1, -1)
          .split('|')
          .map((c) => c.trim());
        tableRows.push(cells);
        return;
      } else if (isTable) {
        flushTable();
      }

      // Headers
      if (trimmed.startsWith('### ')) {
        flushList();
        elements.push(
          <h4 key={lineIdx} style={{ fontSize: '0.98rem', fontWeight: 600, margin: '14px 0 6px', color: 'var(--text-primary)' }}>
            {formatInline(trimmed.slice(4))}
          </h4>
        );
        return;
      }
      if (trimmed.startsWith('## ')) {
        flushList();
        elements.push(
          <h3 key={lineIdx} style={{ fontSize: '1.1rem', fontWeight: 600, margin: '16px 0 8px', color: 'var(--text-primary)' }}>
            {formatInline(trimmed.slice(3))}
          </h3>
        );
        return;
      }
      if (trimmed.startsWith('# ')) {
        flushList();
        elements.push(
          <h2 key={lineIdx} style={{ fontSize: '1.25rem', fontWeight: 700, margin: '18px 0 10px', color: 'var(--text-primary)' }}>
            {formatInline(trimmed.slice(2))}
          </h2>
        );
        return;
      }

      // Bullet points
      if (/^[-*]\s+/.test(trimmed)) {
        listBuffer.push(trimmed.replace(/^[-*]\s+/, ''));
        return;
      } else {
        flushList();
      }

      // Empty line / paragraph
      if (!trimmed) {
        elements.push(<div key={lineIdx} style={{ height: '8px' }} />);
        return;
      }

      elements.push(
        <p key={lineIdx} style={{ margin: '4px 0', lineHeight: 1.6 }}>
          {formatInline(trimmed)}
        </p>
      );
    });

    flushList();
    flushTable();

    return <div key={`seg-${segIdx}`}>{elements}</div>;
  };

  return (
    <div className="markdown-body" style={{ color: 'var(--text-primary)', fontSize: '0.92rem' }}>
      {parts.map((p, idx) =>
        p.type === 'code' ? (
          <CodeBlock key={idx} language={p.language} code={p.content} />
        ) : (
          renderTextSegment(p.content, idx)
        )
      )}
    </div>
  );
}

// Parses inline `code`, **bold**, *italic*, and [links](url)
function formatInline(text) {
  if (!text) return null;

  // Tokenize inline markdown
  const parts = [];
  const regex = /(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*|\[[^\]]+\]\([^)]+\))/g;
  let lastIdx = 0;
  let match;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIdx) {
      parts.push(text.substring(lastIdx, match.index));
    }

    const token = match[0];
    if (token.startsWith('`') && token.endsWith('`')) {
      parts.push(
        <code
          key={match.index}
          style={{
            background: 'rgba(255, 255, 255, 0.08)',
            padding: '2px 5px',
            borderRadius: '4px',
            fontSize: '0.85em',
            fontFamily: 'var(--font-mono, monospace)',
            color: '#a5b4fc',
          }}
        >
          {token.slice(1, -1)}
        </code>
      );
    } else if (token.startsWith('**') && token.endsWith('**')) {
      parts.push(<strong key={match.index}>{token.slice(2, -2)}</strong>);
    } else if (token.startsWith('*') && token.endsWith('*')) {
      parts.push(<em key={match.index}>{token.slice(1, -1)}</em>);
    } else if (token.startsWith('[') && token.includes('](')) {
      const linkMatch = token.match(/\[([^\]]+)\]\(([^)]+)\)/);
      if (linkMatch) {
        parts.push(
          <a
            key={match.index}
            href={linkMatch[2]}
            target="_blank"
            rel="noopener noreferrer"
            style={{ color: 'var(--brand-primary, #6366f1)', textDecoration: 'underline' }}
          >
            {linkMatch[1]}
          </a>
        );
      } else {
        parts.push(token);
      }
    }

    lastIdx = match.index + token.length;
  }

  if (lastIdx < text.length) {
    parts.push(text.substring(lastIdx));
  }

  return parts;
}
