import { useMemo, isValidElement, cloneElement } from 'react';
import type { ReactElement, ReactNode } from 'react';
import ReactMarkdown from 'react-markdown';
import type { Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeSanitize from 'rehype-sanitize';
import { CitationBadge } from './CitationBadge';
import styles from './MessageContent.module.css';

interface Props {
  content: string;
  citationMap?: Record<string, string>;
}

const CITATION_RE = /(\[\d+\])/g;

// Không inject citation vào trong code (inline `code` / fenced ```pre```):
// trong code, `[N]` phải giữ nguyên văn.
const SKIP_ELEMENTS = new Set(['code', 'pre']);

function processStringForCitations(
  text: string,
  citationMap: Record<string, string> | undefined,
  keyPrefix: string,
): React.ReactNode[] {
  const parts = text.split(CITATION_RE);
  return parts.map((part, i) => {
    const match = part.match(/^\[(\d+)\]$/);
    if (match) {
      const citationId = citationMap?.[match[1]] ?? match[1];
      return <CitationBadge key={`${keyPrefix}-${i}`} citationId={citationId} label={part} />;
    }
    return part;
  });
}

// Duyệt đệ quy children của block element và thay `[N]` thành <CitationBadge>.
// Hỗ trợ cả citation nằm trong inline formatting (bold/italic/link) — đệ quy vào
// React element con — trừ code/pre. (AC#3)
export function injectCitations(
  children: React.ReactNode,
  citationMap: Record<string, string> | undefined,
  keyPrefix = 'c',
): React.ReactNode {
  if (typeof children === 'string') {
    return processStringForCitations(children, citationMap, keyPrefix);
  }
  if (Array.isArray(children)) {
    return children.flatMap((child, i) =>
      injectCitations(child, citationMap, `${keyPrefix}-${i}`),
    );
  }
  if (isValidElement(children)) {
    const el = children as ReactElement<{ children?: ReactNode }>;
    if (typeof el.type === 'string' && SKIP_ELEMENTS.has(el.type)) {
      return el;
    }
    if (el.props?.children == null) {
      return el;
    }
    return cloneElement(
      el,
      undefined,
      injectCitations(el.props.children, citationMap, `${keyPrefix}e`),
    );
  }
  return children;
}

export function MessageContent({ content, citationMap }: Props) {
  const components: Components = useMemo(() => {
    const inject = (children: React.ReactNode) => injectCitations(children, citationMap);
    return {
      p: ({ children }) => <p>{inject(children)}</p>,
      li: ({ children }) => <li>{inject(children)}</li>,
      td: ({ children }) => <td>{inject(children)}</td>,
      th: ({ children }) => <th>{inject(children)}</th>,
      h1: ({ children }) => <h1>{inject(children)}</h1>,
      h2: ({ children }) => <h2>{inject(children)}</h2>,
      h3: ({ children }) => <h3>{inject(children)}</h3>,
      h4: ({ children }) => <h4>{inject(children)}</h4>,
      h5: ({ children }) => <h5>{inject(children)}</h5>,
      h6: ({ children }) => <h6>{inject(children)}</h6>,
    };
  }, [citationMap]);

  return (
    <div className={styles.markdown}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeSanitize]}
        components={components}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
