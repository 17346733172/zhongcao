import Markdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";

const components: Components = {
  h1: ({ children }) => <h4>{children}</h4>,
  h2: ({ children }) => <h4>{children}</h4>,
  h3: ({ children }) => <h4>{children}</h4>,
  table: ({ children }) => <div className="answer-table-scroll" role="region" aria-label="回答表格" tabIndex={0}><table>{children}</table></div>,
  a: ({ children, href }) => <a href={href} target="_blank" rel="noreferrer">{children}</a>,
};

export function AnswerMarkdown({ content }: { content: string }) {
  return <div className="answer-markdown"><Markdown remarkPlugins={[remarkGfm]} components={components} skipHtml disallowedElements={["img", "input"]}>{content}</Markdown></div>;
}
