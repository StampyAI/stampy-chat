import { useState } from "react";
import { ShowCitation, CitationsBlock } from "./citations";
import { GlossarySpan } from "./glossary";
import type { Citation, AssistantEntry as AssistantType } from "../types";

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
  </div>
);
