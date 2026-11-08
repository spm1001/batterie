import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { KgIndexEntry, KgIndexSection, KgIndexTop } from '../types'

// kg-index: a knowledge graph's top index rides the system prompt from the
// thread's first request; a topic's index arrives as a new user row the first
// time a loop reads, edits or writes a note inside that topic's folder.
//
// OFF UNLESS CONFIGURED, AND SILENT WHEN OFF. The roots come from the plugin's
// own setting, `kg_index_roots`, which `register` receives before any hook
// exists. Blank (the default), it registers no hook at all. That matters: a
// machine with managed settings seats a security plugin above every
// person-installed hooks module, and Claude Code tells the person each
// session that a plugin's prompt.compose hook "was skipped" merely because
// the hook is registered, before any of its code runs (measured on 2.1.319,
// 7 Nov 2026). An environment variable could not gate that: `register` has
// no `$`, and a hook may not register hooks later (the engine refuses
// `on()` after `register` returns). A person turns it on with
//   claude plugin configure batterie@batterie   (or /plugin configure)
// or in ~/.claude/settings.json:
//   "pluginConfigs": { "batterie@batterie": { "options": {
//     "kg_index_roots": "~/repos/me/my-kg:~/repos/team/team-kg" } } }
// Changing the setting reloads the module with the new value.
//
// `kg_index_system_prompt` (default true) picks how the top index travels.
// Set it false on a machine whose managed settings fence prompt changes from
// person-installed plugins (the atelier): there Claude Code's built-in security
// plugin passes over a person's prompt.compose hook and says it "was skipped".
// False registers no prompt.compose hook; the top index arrives instead as a
// <system-reminder> row just before the first prompt of each thread, the way
// topic indexes arrive. The security plugin passes over a person's hooks on
// prompt.compose, prompt.section, prompt.context, prompt.attachment,
// skill.prompt, attribution.text, session.compact and settings.read, and on
// session.append only for attachment, hook-context and compaction rows; it
// leaves prompt.submit and a plugin's own appended rows alone (read from the
// 2.1.319 binary, 8 Nov 2026). Because session.compact never reaches this
// module there, the row's absence from the conversation is what says a
// compaction or /clear happened.
//
// A kg is a folder holding an index file (INDEX_NAMES, first found wins). A
// note's topic is the nearest folder above it, below the kg's root, that holds
// one too, at any depth. An absent root is skipped, which is what makes one
// list machine-aware. KG_INDEX_CAP_BYTES in the environment moves the size cap.
//
// First built as a standalone prototype and then as its own plugin (7 Nov
// 2026); folded into batterie@batterie the same night. Engine tests:
// `claude plugin test .` from the batterie-de-savoir root.

const INDEX_NAMES = ['MEMORY.md', '_index.md', 'index.md']
// Every top-index section, loaded or refused, opens with `# ${TOP_TITLE}`; the
// message route finds its own row in the conversation by that heading.
const TOP_TITLE = 'Knowledge graph index'
const DEFAULT_CAP = 25_000

// Tags change when the stored shape changes: an older value then reads as the
// initial one instead of being misread.
const top = atom({ plugin: 'batterie', key: 'kgIndexTop' } as const, { isTaken: false, sections: [] } as KgIndexTop, {
  shape: 'top-1',
})
const entered = atom({ plugin: 'batterie', key: 'kgIndexEntered' } as const, [] as KgIndexEntry[], {
  shape: 'entered-1',
})

const bytesOf = (text: string) => new TextEncoder().encode(text).length
const trimSlash = (path: string) => (path.length > 1 ? path.replace(/\/+$/, '') : path)
const baseName = (path: string) => path.split('/').filter(Boolean).pop() ?? path

/** The colon-separated roots as written, blanks dropped; `~` is expanded later, where `$` can read HOME. */
function parseRoots(raw: unknown): string[] {
  if (typeof raw !== 'string') return []
  return raw
    .split(':')
    .map(part => part.trim())
    .filter(part => part.length > 0)
}

async function expandRoots($: EngineInterface, written: string[]): Promise<string[]> {
  const home = await $.env.get('HOME')
  return written
    .map(part => ((part === '~' || part.startsWith('~/')) && home !== undefined ? home + part.slice(1) : part))
    .map(trimSlash)
}

async function capOf($: EngineInterface): Promise<number> {
  const fromEnv = Number(await $.env.get('KG_INDEX_CAP_BYTES'))
  return Number.isFinite(fromEnv) && fromEnv > 0 ? fromEnv : DEFAULT_CAP
}

async function indexIn($: EngineInterface, dir: string): Promise<string | undefined> {
  for (const name of INDEX_NAMES) {
    const path = `${dir}/${name}`
    if (await $.fs.exists(path)) return path
  }
  return undefined
}

function refusal(what: string, path: string, bytes: number, cap: number): string {
  return [
    `# ${what}: not loaded`,
    `The kg-index mod refused ${path}: ${bytes.toLocaleString('en-GB')} bytes, over its ${cap.toLocaleString('en-GB')}-byte cap.`,
    'Read that file with the Read tool if the task needs it, and tell the person the index needs splitting into topics.',
  ].join('\n')
}

async function readTop($: EngineInterface, roots: string[]): Promise<KgIndexSection[]> {
  const cap = await capOf($)
  const sections: KgIndexSection[] = []
  for (const root of roots) {
    const path = await indexIn($, root)
    if (path === undefined) {
      $.ui.log(`kg-index skipped ${root} (no ${INDEX_NAMES.join(' or ')} there)`, { to: 'debug' })
      continue
    }
    const body = await $.fs.read(path)
    const bytes = bytesOf(body)
    const name = baseName(root)
    const id = `kg-index:${name}`
    if (bytes > cap) {
      $.ui.log(`kg-index refused ${path}, ${bytes} bytes over the ${cap}-byte cap`)
      sections.push({ id, path, bytes, isRefused: true, text: refusal(`${TOP_TITLE} ${name}`, path, bytes, cap) })
      continue
    }
    const text = [
      `# ${TOP_TITLE}: ${name}`,
      `The top index of the kg at ${root}, loaded by the kg-index mod when this thread started. Each line points at a note or a topic under that folder: read one with the Read tool when it bears on the task. The first time you read a note inside a topic folder, that topic's own index arrives as a message, unless you have already read that index file yourself.`,
      '',
      body.trim(),
    ].join('\n')
    sections.push({ id, path, bytes, isRefused: false, text })
  }
  return sections
}

// Which kg topic a file is in, if any: its root, the nearest folder above the
// file (below the root) that holds an index, and that index's path.
async function topicOf(
  $: EngineInterface,
  roots: string[],
  file: string,
): Promise<{ root: string; topicDir: string; index: string } | undefined> {
  const root = roots.find(candidate => file.startsWith(`${candidate}/`))
  if (root === undefined) return undefined
  const parts = file.slice(root.length + 1).split('/').slice(0, -1)
  for (let depth = parts.length; depth > 0; depth--) {
    const topicDir = `${root}/${parts.slice(0, depth).join('/')}`
    const index = await indexIn($, topicDir)
    if (index !== undefined) return { root, topicDir, index }
  }
  return undefined
}

// The thread's top-index snapshot, read on first use and then kept.
async function topOf($: EngineInterface, roots: string[]): Promise<KgIndexTop> {
  const snapshot = await read($, top)
  if (snapshot.isTaken) return snapshot
  const taken: KgIndexTop = { isTaken: true, sections: await readTop($, roots) }
  await update($, top, () => taken)
  return taken
}

// Injected rows wear the harness's own wrapper, so the model can tell them
// from the person's typing. A kg page may be team-writable, so a closing tag
// inside one must not end the wrapper early.
const reminder = (text: string) =>
  `<system-reminder>\n${text.replaceAll('</system-reminder>', '<\\/system-reminder>')}\n</system-reminder>`

const TOP_ROW_MARK = `<system-reminder>\n# ${TOP_TITLE}`
const holdsTopRow = (rows: readonly { role: string; text: string }[]) =>
  rows.some(row => row.role === 'user' && row.text.includes(TOP_ROW_MARK))

export const register: Register = (on, options) => {
  const written = parseRoots(options.kg_index_roots)
  // Nothing configured: register nothing, so nothing can run, say or be skipped.
  if (written.length === 0) return

  // The top index: read once per thread, kept in state, so every later compose
  // in the thread answers byte-identically (a changed section costs the cache).
  if (options.kg_index_system_prompt !== false) {
    on('prompt.compose', async ($, e, next) => {
      const composed = await next(e)
      if (e.traits.includes('bare')) return composed
      const snapshot = await topOf($, await expandRoots($, written))
      if (snapshot.sections.length === 0) return composed
      const ours = new Set(snapshot.sections.map(section => section.id))
      return {
        sections: [
          ...composed.sections.filter(section => !ours.has(section.id)),
          ...snapshot.sections.map(section => ({ id: section.id, text: section.text, scope: 'session' as const })),
        ],
      }
    })
  }

  // The message route: where the system prompt is fenced, the top index rides
  // a row of its own, appended just before the prompt that starts a thread, so
  // the model reads it with the person's first words. Checked against the
  // conversation itself each time the person submits at an idle prompt: that
  // covers a fresh thread, a resumed one (the row is already there), and a
  // compaction or /clear (the row is gone, and so is every topic row).
  if (options.kg_index_system_prompt === false) {
    on('prompt.submit', async ($, e, next) => {
      // Folded into a running turn: a row here could land between a tool call
      // and its result. The thread's first prompt is never one of these.
      if (e.turnId !== undefined) return next(e)
      if (holdsTopRow(await $.session.messages())) return next(e)
      if ((await read($, entered)).some(entry => entry.loop === 'main')) {
        await update($, entered, list => list.filter(entry => entry.loop !== 'main'))
      }
      const { sections } = await topOf($, await expandRoots($, written))
      if (sections.length === 0) return next(e)
      await $.session.append({
        message: { type: 'user', content: [{ type: 'text', text: reminder(sections.map(s => s.text).join('\n\n')) }] },
      })
      return next(e)
    }).catch(($, e, next) => {
      $.ui.log(`kg-index could not add the top index before this prompt (${next.error.kind}: ${next.error.message ?? 'no message'}); the prompt goes on without it`)
      return next(e)
    })
  }

  // A topic's index on entry: after a file tool touches a note in a topic
  // folder, once per loop and topic.
  on('tool.call', { tool: ['Read', 'Edit', 'Write'] }, async ($, e, next) => {
    const ran = await next(e)
    if (ran.deny !== undefined || ran.isError === true) return ran
    const file = 'file_path' in e && typeof e.file_path === 'string' ? e.file_path : undefined
    if (file === undefined) return ran
    const roots = await expandRoots($, written)
    const where = await topicOf($, roots, file)
    if (where === undefined) return ran
    const loop = e.agentId ?? 'main'
    const seen = await read($, entered)
    if (seen.some(entry => entry.loop === loop && entry.topic === where.topicDir)) return ran
    const index = where.index

    const record = async (entry: KgIndexEntry) => update($, entered, list => [...list, entry])
    if (index === file) {
      await record({ loop, topic: where.topicDir, bytes: 0, outcome: 'already-read' })
      return ran
    }
    const body = await $.fs.read(index)
    const bytes = bytesOf(body)
    const cap = await capOf($)
    const name = `${baseName(where.root)}/${where.topicDir.slice(where.root.length + 1)}`
    const isRefused = bytes > cap
    const text = isRefused
      ? refusal(`Topic index ${name}`, index, bytes, cap)
      : [
          `# Topic index: ${name}`,
          `You just opened a note in this topic, so the kg-index mod has added the topic's index (${index}). Each line points at a note in the topic: read one when it bears on the task.`,
          '',
          body.trim(),
        ].join('\n')
    try {
      await $.session.append({
        message: { type: 'user', content: [{ type: 'text', text: reminder(text) }] },
        ...(e.agentId === undefined ? {} : { agentId: e.agentId }),
      })
      await record({ loop, topic: where.topicDir, bytes, outcome: isRefused ? 'refused' : 'appended' })
      if (isRefused) $.ui.log(`kg-index refused ${index}, ${bytes} bytes over the ${cap}-byte cap`)
    } catch (error) {
      const reason = error instanceof Error ? error.message : String(error)
      await record({ loop, topic: where.topicDir, bytes, outcome: 'failed', reason })
      $.ui.log(`kg-index could not append ${index}: ${reason}`)
    }
    return ran
  }).catch(($, e, next) => next(e)) // never refuses: after next, replays the call's own result

  // A subagent's system prompt is not composed through prompt.compose, so the
  // top index rides in front of its task prompt. A fork inherits the parent's
  // context already; a resumed run's prompt is fixed.
  on('agent.spawn', async ($, e, next) => {
    if (e.fork || e.resume !== undefined) return next(e)
    const { sections } = await topOf($, await expandRoots($, written))
    if (sections.length === 0) return next(e)
    const preface = reminder(sections.map(section => section.text).join('\n\n'))
    return next({ ...e, prompt: `${preface}\n\n${e.prompt}` })
  }).catch(($, e, next) => next(e)) // a failure here spawns the subagent unchanged

  // /kg-index says what this thread loaded.
  on('session.start', async ($, e, next) => {
    await $.command.register({ name: 'kg-index', description: 'Show which kg indexes this thread loaded' })
    return next(e)
  })

  on('command.run', { command: 'kg-index' }, async $ => {
    const snapshot = await read($, top)
    const list = await read($, entered)
    const lines = [
      `Roots: ${(await expandRoots($, written)).join(', ')}`,
      ...(options.kg_index_system_prompt === false
        ? [
            `Top index: sent as a message, not in the system prompt (kg_index_system_prompt is false); in this conversation now: ${holdsTopRow(await $.session.messages()) ? 'yes' : 'no, it comes with the next prompt'}`,
          ]
        : []),
      ...(!snapshot.isTaken
        ? ['Top index: not read yet in this thread']
        : snapshot.sections.length === 0
          ? ['Top index: none (no root held an index)']
          : snapshot.sections.map(s => `Top index ${s.id}: ${s.isRefused ? 'REFUSED' : 'loaded'}, ${s.bytes} bytes, ${s.path}`)),
      ...list.map(t => `Topic ${t.topic} in ${t.loop}: ${t.outcome}, ${t.bytes} bytes${t.reason ? ` (${t.reason})` : ''}`),
    ]
    return { text: lines.join('\n') }
  })

  // A compaction summarises the topic rows away, so that loop's topics count as
  // unentered again: the next read in one brings its index back. The system
  // prompt survives compaction, so the top index needs nothing.
  on('session.compact', async ($, e, next) => {
    const compacted = await next(e)
    if ((await read($, entered)).length === 0) return compacted
    const loop = e.agentId ?? 'main'
    await update($, entered, list => list.filter(entry => entry.loop !== loop))
    return compacted
  }).catch(($, e, next) => next(e)) // never blocks a compaction

  // A /clear starts a new thread: read the kg afresh for it.
  on('session.end', async ($, e, next) => {
    if (e.reason === 'clear' && (await read($, top)).isTaken) {
      await update($, top, () => ({ isTaken: false, sections: [] }))
      await update($, entered, () => [])
    }
    return next(e)
  })
}
