// The batterie hooks module's state contract (hooks/kg-index.ts). plugin.json
// names this file under "types", and `claude plugin validate` holds every
// $.state key the module uses to it. State is keyed by plugin name, and the
// kit's plugin is `batterie`, so the kg-index keys carry a `kgIndex` prefix.

/** One kg's top index as this thread's system prompt carries it. */
export type KgIndexSection = { id: string; text: string; bytes: number; isRefused: boolean; path: string }

/** The top-index sections, read once per thread so the system prompt stays byte-identical. */
export type KgIndexTop = { isTaken: boolean; sections: KgIndexSection[] }

/** One topic index appended to a loop: which loop, which topic, what happened. */
export type KgIndexEntry = {
  loop: string
  topic: string
  bytes: number
  outcome: 'appended' | 'refused' | 'already-read' | 'failed'
  reason?: string
}

declare module 'claude-code' {
  interface PluginState {
    batterie: {
      kgIndexTop: Shaped<KgIndexTop>
      kgIndexEntered: Shaped<KgIndexEntry[]>
    }
  }
}
