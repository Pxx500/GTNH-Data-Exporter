import { useCallback, useEffect, useState } from 'react'

export interface Resource {
  id: string; kind: string; registry_name: string; display_name: string
  metadata: number | null; nbt: unknown; provenance: unknown
  [key: string]: unknown
}
export interface Group { id: string; name: string; kind: string; members: string[]; [key: string]: unknown }
export interface Choice {
  resource_id: string | null; amount: number | null
  match: { mode: string; group_id?: string; nbt_sensitive?: boolean; [key: string]: unknown }
  consumption_chance?: { numerator: number; denominator: number } | null
  [key: string]: unknown
}
export interface Output { resource_id: string; amount?: number | null; chance?: { numerator: number; denominator: number } | null; [key: string]: unknown }
export interface Process {
  id: string; family: string; display_name: string
  inputs: { role: string; choices: Choice[]; consumption_chance?: { numerator: number; denominator: number } | null; [key: string]: unknown }[]
  outputs: Output[]; duration_ticks: number | null; eu_per_tick: number | null
  amperage: number | null; executable: boolean | null; conditions: unknown; provenance: unknown
  [key: string]: unknown
}
export interface Source { id: string; kind: string; display_name: string; outputs: Output[]; environment_ids: string[]; status: string; conditions: unknown; parameters: unknown; provenance: unknown; [key: string]: unknown }
export interface Environment { id: string; name: string; dimension_id: number | null; provider: string | null; properties: unknown; provenance: unknown; [key: string]: unknown }
export interface Coverage { id: string; domain: string; status: string; records: number; reason: string | null; provenance: unknown; [key: string]: unknown }
export interface Page<T> { snapshot_id: string; items: T[]; total: number; limit: number; offset: number; matching_complete?: boolean; unresolved_matches?: number }
export interface Single<T> { snapshot_id: string; item: T }
export interface Status { snapshot_id: string; manifest: Record<string, unknown>; counts: Record<string, number>; coverage: Coverage[] }
export interface Trace {
  snapshot_id: string; start_id: string; target_id: string; resources: Resource[]; processes: Process[]
  edges: { source: string; target: string; role: string; [key: string]: unknown }[]
  leaves: { resource_id: string; status: string; sources: string[]; reason?: string }[]
  cycles: string[][]; truncated: boolean; coverage: Coverage[]
  route: {status: 'found' | 'not_found' | 'incomplete' | 'same_resource'; strategy: 'shortest_known_dependency_path'; resource_ids: string[]; process_ids: string[]}
  search: {examined_processes: number; limit: number; truncated: boolean}
  limit_reasons: ('depth' | 'search_process_limit' | 'route_process_limit' | 'context_depth' | 'context_process_limit')[]
}

export function query(path: string, params: Record<string, string | number | undefined> = {}) {
  const search = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => { if (value !== undefined && value !== '') search.set(key, String(value)) })
  return `/api/${path}${search.size ? `?${search}` : ''}`
}

export function useRequest<T>(url: string | null) {
  const [revision, setRevision] = useState(0)
  const [state, setState] = useState<{url: string | null; data?: T; loading: boolean; error?: string}>({url, loading: !!url})
  useEffect(() => {
    if (!url) { setState({url, loading: false}); return }
    const controller = new AbortController()
    setState({url, loading: true})
    fetch(url, {signal: controller.signal})
      .then(async response => {
        const body = await response.json()
        if (!response.ok) throw new Error(typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail ?? body))
        return body as T
      })
      .then(data => { if (!controller.signal.aborted) setState({url, data, loading: false}) })
      .catch(error => { if (!controller.signal.aborted) setState({url, loading: false, error: error instanceof Error ? error.message : String(error)}) })
    return () => controller.abort()
  }, [url, revision])
  const reload = useCallback(() => setRevision(value => value + 1), [])
  return state.url === url ? {...state, reload} : {loading: !!url, data: undefined, error: undefined, reload}
}
