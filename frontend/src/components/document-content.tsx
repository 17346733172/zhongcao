import type { DocumentBlock } from "@/lib/types";

export function DocumentContent({ blocks }: { blocks: DocumentBlock[] }) {
  let tableIndex = 0;
  return blocks.map((block, index) => {
    if (block.type === "heading") {
      const Heading = block.level === 1 ? "h3" : block.level === 2 ? "h4" : "h5";
      return <Heading key={index} id={`document-section-${index}`}>{block.text}</Heading>;
    }
    if (block.type === "table") {
      const number = ++tableIndex;
      return (
        <div key={index} className="source-table-scroll" role="region" aria-label={`原文表格 ${number}`} tabIndex={0}>
          <table aria-label={`原文表格 ${number}`}>
            <thead><tr>{block.rows[0]?.map((cell, cellIndex) => <th key={cellIndex} scope="col">{cell}</th>)}</tr></thead>
            <tbody>{block.rows.slice(1).map((row, rowIndex) => <tr key={rowIndex}>{row.map((cell, cellIndex) => <td key={cellIndex}>{cell}</td>)}</tr>)}</tbody>
          </table>
        </div>
      );
    }
    return <p key={index}>{block.text}</p>;
  });
}
