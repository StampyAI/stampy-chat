// const Colours = ["blue", "cyan", "teal", "green", "amber"].map(
//   colour => `bg-${colour}-100 border-${colour}-300 text-${colour}-800`
// );
// this would be nice, but Tailwind needs te actual string of the class to be in
// the source file for it to be included in the build

export const Colours = [
  'bg-red-100    border-red-300   text-red-800',
  'bg-amber-100  border-amber-300  text-amber-800',
  'bg-orange-100 border-orange-300 text-orange-800',
  'bg-lime-100   border-lime-300   text-lime-800',
  'bg-green-100  border-green-300  text-green-800',
  'bg-cyan-100   border-cyan-300   text-cyan-800',
  'bg-blue-100   border-blue-300   text-blue-800',
  'bg-violet-100 border-violet-300 text-violet-800',
  'bg-pink-100   border-pink-300   text-pink-800',
]

export const A: React.FC<{
  href: string
  className?: string
  children: React.ReactNode
}> = ({href, className, children}) => {
  // link element that only populates the href field if the contents are there
  return href && href !== '' ? (
    <a className={className} href={href} target="_blank" rel="noreferrer">
      {children}
    </a>
  ) : (
    <a className={className}>{children}</a>
  )
}
