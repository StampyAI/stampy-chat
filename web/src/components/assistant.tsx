import { ShowCitation, CitationsBlock } from "./citations";
import { GlossarySpan } from "./glossary";
import type { AssistantEntry as AssistantType, ContentBlock } from "../types";

const TOOL_DISPLAY_NAMES: Record<string, string> = {
  lw_af_arxivsafety_search: "Searched articles",
  lw_af_arxivsafety_recent: "Searched recent articles",
  lw_af_arxivsafety_get_doc: "Viewed full article",
  lw_af_posts_sorted: "Listed article names",
  lw_af_authors: "Listed authors",
  lw_af_tags: "Listed tags",
};

const toolDisplayName = (name: string) => TOOL_DISPLAY_NAMES[name] || name;

const ToolAction: React.FC<{
  name: string;
  input: Record<string, any>;
  model_output?: string;
}> = ({ name, input, model_output }) => (
  <details className="phase-message">
    <summary className="grey">{toolDisplayName(name)}</summary>
    <div style={{ fontSize: "0.85em", paddingTop: "4px", maxHeight: "300px", overflow: "auto" }}>
      <div style={{ fontWeight: "bold", marginBottom: "4px" }}>Request</div>
      <pre style={{ whiteSpace: "pre-wrap" }}>{JSON.stringify(input, null, 2)}</pre>
      {model_output && (
        <>
          <div style={{ fontWeight: "bold", marginTop: "8px", marginBottom: "4px" }}>Response</div>
          <pre style={{ whiteSpace: "pre-wrap" }}>{model_output}</pre>
        </>
      )}
    </div>
  </details>
);

const Thinking: React.FC<{ thinking: string }> = ({ thinking }) => (
  <details className="phase-message">
    <summary className="grey">
      Thinking ›
    </summary>
    <div style={{ whiteSpace: "pre-wrap", fontSize: "0.85em" }}>{thinking}</div>
  </details>
);

export const AssistantEntry: React.FC<{ entry: AssistantType }> = ({
  entry,
}) => (
  <div className="mt-3 mb-8">
    {/* Render blocks with tool_use+tool_result merged */}
    {(() => {
      const blocks = entry.blocks || [];
      const elements: React.ReactNode[] = [];
      for (let i = 0; i < blocks.length; i++) {
        const block = blocks[i];
        if (block.type === "thinking") {
          elements.push(<Thinking key={i} thinking={block.thinking} />);
        } else if (block.type === "tool_use") {
          const next = blocks[i + 1];
          const result = next?.type === "tool_result" ? next : undefined;
          elements.push(
            <ToolAction key={i} name={block.name} input={block.input} model_output={result?.model_output} />
          );
          if (result) i++;
        } else if (block.type === "tool_result") {
          elements.push(<ToolAction key={i} name={block.tool} input={{}} model_output={block.model_output} />);
        } else if (block.type === "text") {
          elements.push(
            ...block.text.split("\n").map((paragraph, j) => (
              <CitationsBlock
                key={`${i}-${j}`}
                text={paragraph}
                citations={entry.citationsMap || new Map()}
                textRenderer={(t) => <GlossarySpan content={t} />}
              />
            ))
          );
        }
      }
      return elements;
    })()}
    {/* Fallback: if no blocks, render content directly (backward compat) */}
    {(!entry.blocks || entry.blocks.length === 0) &&
      entry.content &&
      entry.content.split("\n").map((paragraph, i) => (
        <CitationsBlock
          key={i}
          text={paragraph}
          citations={entry.citationsMap || new Map()}
          textRenderer={(t) => <GlossarySpan content={t} />}
        />
      ))}
    <ul className="mt-5">
      {entry.citationsMap &&
        Array.from(entry.citationsMap.values()).map((citation) => (
          <li key={citation.index}>
            <ShowCitation citation={citation} />
          </li>
        ))}
    </ul>
    <details className="prompt">
      <summary>Full prompt details</summary>
      <div className="prompt-container">
        {entry.timings && entry.timings.length > 0 && (
          <div className="prompt-section">
            <h4>Timings</h4>
            <div className="timings">
              {entry.timings.map((timing, i) => (
                <div key={i} className="timing-entry">
                  {(timing.time / 1000).toFixed(2)}s: {timing.name}
                </div>
              ))}
            </div>
          </div>
        )}
        {entry.settings && (
          <div className="prompt-section">
            <h4>Settings</h4>
            <pre className="settings-json">
              {JSON.stringify(entry.settings, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </details>
  </div>
);
