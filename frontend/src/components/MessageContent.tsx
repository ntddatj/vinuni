import { CitationBadge } from './CitationBadge';

interface Props {
  content: string;
  citationMap?: Record<string, string>; // ordinal → chunk UUID
}

const CITATION_RE = /(\[\d+\])/g;

export function MessageContent({ content, citationMap }: Props) {
  const parts = content.split(CITATION_RE);
  return (
    <>
      {parts.map((part, i) => {
        const match = part.match(/^\[(\d+)\]$/);
        if (match) {
          const ordinal = match[1];
          // Resolve ordinal → UUID nếu có map; fallback ordinal nếu không có (tin nhắn cũ)
          const citationId = citationMap?.[ordinal] ?? ordinal;
          return (
            <CitationBadge
              key={i}
              citationId={citationId}
              label={part}
            />
          );
        }
        return <span key={i}>{part}</span>;
      })}
    </>
  );
}
