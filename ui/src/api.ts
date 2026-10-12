import { useCallback, useEffect, useState } from 'react'
import type {Ledger,Rational,Startup,Quantities} from './AccountingDetails'
import type {InputSelectionMap} from './InputSelections'

export interface Resource {
  id: string; kind: string; registry_name: string; display_name: string
  metadata: number | null; nbt: unknown; provenance: unknown
  acquisition_analysis?:AcquisitionAnalysis
  [key: string]: unknown
}
export interface AcquisitionAnalysis {unification:{status:string;preferred_resource_ids:string[];group_ids:string[];evidence:string};acquisition:{status:string;source_count:number;eligible_producer_count:number;unresolved_producer_count:number;coverage_complete:boolean;reason:string}}
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
export interface QueryScope {excluded_resource_ids?:string[];excluded_group_ids?:string[];excluded_namespaces?:string[];excluded_family_ids?:string[]}
export interface BoundaryProfile {id:string;name:string;revision:number;base_resource_ids:string[];scope:QueryScope;semantics:string}
export interface ProfileList {snapshot_id:string;items:BoundaryProfile[]}
export interface ScopeCatalog {snapshot_id:string;namespaces:{id:string;resources:number}[];families:{id:string;processes:number}[];unknown_namespace_count:number}
export interface NetworkVariant {variant_id:string;process_id:string;process:Process;selections:InputSelectionMap[string]}
export interface NetworkExecution {variant_id:string;process_id:string;runs:Rational;selections:InputSelectionMap[string];ledger:Ledger}
export interface NominalEnergy {status:string;total_eu:Rational|null;eu_per_target:Rational|null;unknown_processes:unknown[]}
export interface NetworkSolution {executions:NetworkExecution[];ledger:Ledger;net_imports:Quantities;net_coproducts:Quantities;nominal_energy:NominalEnergy;integer_batch_scale:number;startup:Startup;witness_verified:boolean;savings?:{status:string;eu?:Rational;percent?:Rational};base_boundary?:{status:string;unresolved_startup:Quantities;semantics:string}}
export interface NetworkDiscovery {resources:Resource[];processes:Record<string,Process>;groups:Group[];variants:NetworkVariant[];search:unknown;exclusions:unknown;limit_reasons:string[];coverage_complete:boolean}
export interface NetworkWitnessReport {snapshot_id:string;status:string;discovery:NetworkDiscovery;solutions:NetworkSolution[];search:{complete:boolean;limit_reasons:string[];[key:string]:unknown};limit_reasons?:string[];unsupported?:unknown[];benchmark?:{process:Process;selections:InputSelectionMap[string];runs:Rational;ledger:Ledger;energy:{total_eu:Rational;eu_per_target:Rational};cofeeds:Quantities;coproducts:Quantities;comparison_scope:string}}
export interface NetworkBoundaryReport {snapshot_id:string;status:string;boundary:{resource_id:string;amount:Rational};base_requirements:Quantities;solutions:[];profile:BoundaryProfile;execution_scope:'assumed_external_feed_boundary';coverage_complete:true}
export type NetworkReport=NetworkWitnessReport|NetworkBoundaryReport
export interface StatisticsSummary {count:number;min:Rational|null;q1:Rational|null;median:Rational|null;q3:Rational|null;max:Rational|null;iqr:Rational|null}
export interface StatisticsTier {status:string;tier:number|null;name:string|null;reason?:string}
export interface StatisticsReport {snapshot_id:string;overview:{resources:{count:number;by_kind:Record<string,number>;by_namespace:Record<string,number>};groups:{count:number;by_kind:Record<string,number>;member_counts:StatisticsSummary};processes:{count:number;by_family:Record<string,number>;by_tier:{recipe_tier:StatisticsTier;count:number}[];by_executability:Record<string,number>;gates:Record<string,number>;energy_status:Record<string,number>}};distributions:(StatisticsSummary&{family:string;recipe_tier:StatisticsTier;metric:string;comparison:string})[];findings:{kind:string;comparison_scope:string;process_ids:string[];normalized_signature:unknown;batch_scales:unknown;normalized_costs:unknown;cost_ratio:Rational;count:number}[];exclusions:Record<string,number>;search:{complete:boolean;truncated:boolean;limit_reasons:string[];[key:string]:unknown};processes:Record<string,Process>}
export interface Trace {
  path_selection: 'diverse' | 'shortest'
  branch_coverage: {target_process_id:string;slot_index:number;candidate_resources:number;paths:number;path_indices:number[];status:'represented'|'not_discovered'}[]
  snapshot_id: string; start_id: string; target_id: string; resources: Resource[]; processes: Process[]
  edges: { source: string; target: string; role: string; [key: string]: unknown }[]
  leaves: { resource_id: string; status: string; sources: string[]; reason?: string }[]
  cycles: string[][]; truncated: boolean; coverage: Coverage[]
  route: {status: 'found' | 'not_found' | 'incomplete' | 'same_resource'; strategy: 'shortest_known_dependency_path'; resource_ids: string[]; process_ids: string[]}
  paths: {resource_ids: string[]; process_ids: string[]}[]
  search: {examined_processes: number; limit: number; truncated: boolean}
  limit_reasons: ('depth' | 'search_process_limit' | 'path_limit' | 'path_process_limit' | 'search_state_limit' | 'search_work_limit' | 'search_enumeration_limit' | 'search_variant_limit')[]
  tier_filter?: TierOptions & {active:boolean;excluded_unknown:number;excluded_out_of_range:number}
  recipe_tiers?: {process_id:string;status:'known'|'unknown';tier:number|null;name:string|null;scope:string;reason?:string}[]
}
export interface TierOptions {min_tier?:number;max_tier?:number;unknown_tier_policy:'exclude'|'include'}

export function query(path: string, params: Record<string, string | number | string[] | undefined> = {}) {
  const search = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => { if (Array.isArray(value)) value.forEach(item => search.append(key, item)); else if (value !== undefined && value !== '') search.set(key, String(value)) })
  return `/api/${path}${search.size ? `?${search}` : ''}`
}

export function useRequest<T>(url: string | null, body?: unknown, method?:'POST'|'DELETE') {
  const payload = body === undefined ? undefined : JSON.stringify(body)
  const [revision, setRevision] = useState(0)
  const [state, setState] = useState<{url: string | null; payload?:string;method?:string; data?: T; loading: boolean; error?: string}>({url, payload,method, loading: !!url})
  useEffect(() => {
    if (!url) { setState({url, payload,method, loading: false}); return }
    const controller = new AbortController()
    setState({url, payload,method, loading: true})
    fetch(url, {signal: controller.signal, ...(payload === undefined ? {} : {method:method??'POST',headers:{'Content-Type':'application/json'},body:payload})})
      .then(async response => {
        const body = await response.json()
        if (!response.ok) throw new Error(typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail ?? body))
        return body as T
      })
      .then(data => { if (!controller.signal.aborted) setState({url, payload,method, data, loading: false}) })
      .catch(error => { if (!controller.signal.aborted) setState({url, payload,method, loading: false, error: error instanceof Error ? error.message : String(error)}) })
    return () => controller.abort()
  }, [url, payload,method, revision])
  const reload = useCallback(() => setRevision(value => value + 1), [])
  return state.url === url && state.payload === payload && state.method===method ? {...state, reload} : {loading: !!url, data: undefined, error: undefined, reload}
}
