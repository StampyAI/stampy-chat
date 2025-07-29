import { ShowCitation, CitationsBlock } from "./citations";
import { GlossarySpan } from "./glossary";
import type { AssistantEntry as AssistantType } from "../types";

const roles = {
  assistant: "Assistant",
  user: "User",
  system: "System",
};

export const AssistantEntry: React.FC<{ entry: AssistantType }> = ({
  entry,
}) => (
  <div className="mt-3 mb-8">
    {entry.content.split("\n").map((paragraph, i) => (
      <CitationsBlock
        key={i}
        text={paragraph}
        citations={entry.citationsMap || new Map()}
        textRenderer={(t) => <GlossarySpan content={t} />}
      />
    ))}
    <ul className="mt-5">
      {entry.citationsMap &&
        // show citations
        Array.from(entry.citationsMap.values()).map((citation) => (
          <li key={citation.index}>
            <ShowCitation citation={citation} />
          </li>
        ))}
    </ul>
    <details className="prompt">
      <summary>Full prompt</summary>
      <div className="prompt-container">
        {entry.promptedHistory?.map((entry, i) => (
          <div className="prompt-block" key={i}>
            <div className="prompt-role">
              {"\n\n"}
              {roles[entry.role as keyof typeof roles]}:
            </div>
            <div className="prompt-line">{entry.content}</div>
          </div>
        ))}
      </div>
    </details>
  </div>
);
