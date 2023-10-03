import type {Mode} from '../types'

export const Controls = ({mode, setMode}: {mode: [Mode, boolean]; setMode: (m: any) => void}) => {
  {
    /* three buttons for the three modes, place far right, 1rem between each */
  }
  return (
    <div className="ml-auto mr-0 mb-5 flex w-fit flex-row justify-center gap-2">
      <button
        className={
          'border border-gray-300 px-1 ' + (mode[1] && mode[0] === 'rookie' ? 'bg-gray-200' : '')
        }
        onClick={() => {
          setMode(['rookie', true])
        }}
        title="For people who are new to the field of AI alignment. The
                              answer might be longer, since technical terms will be
                              explained in more detail and less background will be
                              assumed."
      >
        rookie
      </button>
      <button
        className={
          'border border-gray-300 px-1 ' + (mode[1] && mode[0] === 'concise' ? 'bg-gray-200' : '')
        }
        onClick={() => {
          setMode(['concise', true])
        }}
        title="Quick and to the point. Followup questions may need to be
                              asked to get the full picture of what's going on."
      >
        concise
      </button>
      <button
        className={
          'border border-gray-300 px-1 ' + (mode[1] && mode[0] === 'default' ? 'bg-gray-200' : '')
        }
        onClick={() => {
          setMode(['default', true])
        }}
        title="A balanced default mode."
      >
        default
      </button>
    </div>
  )
}
