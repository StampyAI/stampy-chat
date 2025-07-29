import { ChangeEvent } from "react";
import type { Parseable } from "../types";

// const Colours = ["blue", "cyan", "teal", "green", "amber"].map(
//   colour => `bg-${colour}-100 border-${colour}-300 text-${colour}-800`
// );
// this would be nice, but Tailwind needs te actual string of the class to be in
// the source file for it to be included in the build
type NumberParser = (v: Parseable) => number;
type InputFields = {
  field: string;
  label: string;
  value?: Parseable;
  min?: string | number;
  max?: string | number;
  step?: string | number;
  parser?: NumberParser;
  updater: (v: any) => any;
};

export const Colours = [
  "bg-red-100    border-red-300   text-red-800",
  "bg-amber-100  border-amber-300  text-amber-800",
  "bg-orange-100 border-orange-300 text-orange-800",
  "bg-lime-100   border-lime-300   text-lime-800",
  "bg-green-100  border-green-300  text-green-800",
  "bg-cyan-100   border-cyan-300   text-cyan-800",
  "bg-blue-100   border-blue-300   text-blue-800",
  "bg-violet-100 border-violet-300 text-violet-800",
  "bg-pink-100   border-pink-300   text-pink-800",
];

export const A: React.FC<{
  href: string;
  className?: string;
  children: React.ReactNode;
}> = ({ href, className, children }) => {
  // link element that only populates the href field if the contents are there
  return href && href !== "" ? (
    <a className={className} href={href} target="_blank" rel="noreferrer">
      {children}
    </a>
  ) : (
    <a className={className}>{children}</a>
  );
};

const between =
  (
    min: Parseable,
    max: Parseable,
    parser: NumberParser,
    updater: (v: any) => any
  ) =>
  (event: ChangeEvent) => {
    let num = parser((event.target as HTMLInputElement).value);
    if (isNaN(num)) {
      return;
    } else if (min !== undefined && num < parser(min)) {
      num = parser(min);
    } else if (max !== undefined && num > parser(max)) {
      num = parser(max);
    }
    updater(num);
  };

export const SectionHeader = ({ text }: { text: string }) => (
  <h4 className="col-span-4 text-lg font-semibold">{text}</h4>
);

export const NumberInput = ({
  field,
  value,
  label,
  min,
  max,
  updater,
  // this cast is just to satisfy typescript - it can handle numbers, strings and undefined just fine
  parser = (v) => parseInt(v as string, 10),
}: InputFields) => (
  <>
    <label htmlFor={field} className="col-span-3 inline-block">
      {label}:{" "}
    </label>
    <input
      name={field}
      value={value}
      className="w-20"
      onChange={between(min, max, parser, updater)}
      type="number"
    />
  </>
);

export const Slider = ({
  field,
  value,
  label,
  min = 0,
  max = 1,
  step = 0.01,
  // this cast is just to satisfy typescript - it can handle numbers, strings and undefined just fine
  parser = (v) => parseFloat(v as string),
  updater,
}: InputFields) => (
  <>
    <label htmlFor={field} className="col-span-2">
      {label}:
    </label>
    <input
      name={field}
      className="col-span-2"
      value={value}
      onChange={between(min, max, parser, updater)}
      type="range"
      min={min}
      max={max}
      step={step}
    />
  </>
);

export const Checkbox = ({
  field,
  value,
  label = "",
  updater,
}: InputFields) => (
  <>
    <label htmlFor={field} className="col-span-2">
      {label}:
    </label>
    <input
      name={field}
      className="col-span-2"
      value={value}
      onChange={(event: ChangeEvent) =>
        updater((event.target as HTMLInputElement).checked)
      }
      type="checkbox"
    />
  </>
);

export const Select = ({
  name,
  value,
  options,
  updater,
}: {
  name: string;
  value: string;
  options: string[];
  updater: (v: any) => any;
}) => (
  <select name={name} value={value} onChange={updater} className="col-span-2">
    {options.map((option: string) => (
      <option key={option} value={option}>
        {option}
      </option>
    ))}
  </select>
);
