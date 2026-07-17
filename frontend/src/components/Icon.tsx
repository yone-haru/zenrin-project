export type IconName =
  | 'shield'
  | 'search'
  | 'swap'
  | 'walk'
  | 'clock'
  | 'pin'
  | 'warning'
  | 'camera'
  | 'close'
  | 'chevronDown'
  | 'refresh'
  | 'locate'
  | 'share'
  | 'lock'
  | 'check'
  | 'help'
  | 'mail'

const paths: Record<IconName, string> = {
  shield: 'M12 3l7 3v5c0 4.5-2.8 8.4-7 10-4.2-1.6-7-5.5-7-10V6l7-3zm-3 9l2 2 4-5',
  search: 'M10.5 18a7.5 7.5 0 1 1 5.3-12.8A7.5 7.5 0 0 1 10.5 18zm5.2-2.3L21 21',
  swap: 'M8 4v14m0 0l-4-4m4 4l4-4m8 6V6m0 0l-4 4m4-4l4 4',
  walk: 'M13 4a2 2 0 1 1-4 0 2 2 0 0 1 4 0zm-2 4l-2 5 4 2 1 5m-5-7l-3 6m5-10l4 3',
  clock: 'M12 21a9 9 0 1 1 0-18 9 9 0 0 1 0 18zm0-13v5l3 2',
  pin: 'M12 21s7-5.1 7-11a7 7 0 1 0-14 0c0 5.9 7 11 7 11zm0-8.5a2.5 2.5 0 1 1 0-5 2.5 2.5 0 0 1 0 5z',
  warning: 'M12 3l10 18H2L12 3zm0 6v5m0 3h.01',
  camera: 'M4 8h3l1.7-2.2A1 1 0 0 1 9.5 5h5a1 1 0 0 1 .8.4L17 8h3a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V9a1 1 0 0 1 1-1zm8 3a3.5 3.5 0 1 0 0 7 3.5 3.5 0 0 0 0-7z',
  close: 'M6 6l12 12M18 6L6 18',
  chevronDown: 'M6 9l6 6 6-6',
  refresh: 'M4 4v6h6M20 20v-6h-6M5 13a7 7 0 0 0 12.5 3.5M19 11A7 7 0 0 0 6.5 7.5',
  locate: 'M12 2v3m0 14v3m8-10h-3M7 12H4m13 0a5 5 0 1 1-10 0 5 5 0 0 1 10 0z',
  share: 'M4 12v7a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-7M16 6l-4-4-4 4M12 2v13',
  lock: 'M6 11V8a6 6 0 1 1 12 0v3m-13 0h14a1 1 0 0 1 1 1v8a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1v-8a1 1 0 0 1 1-1z',
  check: 'M4 12l5 5L20 6',
  help: 'M12 21a9 9 0 1 1 0-18 9 9 0 0 1 0 18zm-2.8-9.3a2.8 2.8 0 1 1 3.9 2.6c-.7.3-1.1.8-1.1 1.5v.4M12 17h.01',
  mail: 'M4 6h16v12H4V6zm0 0l8 7 8-7',
}

export function Icon({ name }: { name: IconName }) {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d={paths[name]} />
    </svg>
  )
}
