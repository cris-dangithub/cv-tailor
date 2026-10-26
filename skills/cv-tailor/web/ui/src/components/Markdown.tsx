import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { cx } from "../lib/format";

export function Markdown({ text, className }: { text: string; className?: string }) {
  return (
    <div className={cx("prose", className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ href, children }) => (
            <a href={href} target="_blank" rel="noreferrer noopener">
              {children}
            </a>
          ),
        }}
      >
        {text}
      </ReactMarkdown>
    </div>
  );
}
