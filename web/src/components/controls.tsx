import type { Mode } from "../types";

const MODES = {
  rookie:
    "For people who are new to the field of AI alignment. The " +
    "answer might be longer, since technical terms will be " +
    "explained in more detail and less background will be assumed.",
  concise:
    "Quick and to the point. Followup questions may need to be " +
    "asked to get the full picture of what's going on.",
  default: "A balanced default mode.",
};

type ControlsType = {
  mode: Mode;
  setMode: (m: any) => void;
};
export const Controls = ({ mode, setMode }: ControlsType) => {
  {
    /* three buttons for the three modes, place far right, 1rem between each */
  }
  return (
    <div className="ml-auto mr-0 mb-5 flex w-fit flex-row justify-center gap-2">
      {Object.entries(MODES).map(([modeType, title]) => (
        <button
          className={
            "border border-gray-300 px-1 " +
            (mode === modeType ? "bg-gray-200" : "")
          }
          onClick={() => setMode(modeType)}
          title={title}
          key={modeType}
        >
          {modeType}
        </button>
      ))}
    </div>
  );
};
