import { useCallback, useEffect, useState } from 'react'
import type {Ledger,Rational,Startup,Quantities} from './AccountingDetails'
import type {InputSelectionMap} from './InputSelections'

export interface Resource {
  id: string; kind: string; registry_name: string; display_name: string
  metadata: number | null; nbt: unknown; provenance: unknown
  acquisition_analysis?:AcquisitionAnalysis
  [key: string]: unknown
}
export interface AcquisitionAnalysis {unification:{status:string;preferred_resource_ids:string[];group_ids:string[];evidence:string|null};acquisition:{status:string;source_count:number;eligible_producer_count:number;unresolved_producer_count:number;coverage_complete:boolean;reason:string};provenance?:{world_source:{status:string;evidence_counts:Record<string,number>;evidence:{source_id:string;kind:string;status:string;resource_semantics:string|null;classification:string;confidence:string;environment_ids:string[];environments?:Environment[];conditions?:unknown;parameters?:unknown;[key:string]:unknown}[];inventory_obtainable_proven:false};initial_processing:{status:string;confidence:string;max_steps:number;evidence:unknown[]};renewable:{status:string;reason:string};basic_suggestion:{suggested:boolean;requires_user_selection:true;reason:string}}}
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
export interface Page<T> {
  snapshot_id:string;items:T[];total:number;limit:number;offset:number;matching_complete?:boolean;unresolved_matches?:number
  input_lookup?:{mode:'declared';scope:'literal_captured_resource_references';matching_evaluated:false}
}
export interface Single<T> { snapshot_id: string; item: T }
export interface ProcessInspection extends Single<Process> {
  projection_issue?: {status:'unsupported_accounting';native_model:string;reason:string;voltage_unresolved:boolean}
}
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
interface CutterPathPreference {
  changed:boolean;eligible_paths:number
  classification_visits:{paths:number;recipes:number;slots:number;choices:number;outputs:number}
}
interface AcquisitionClassificationVisits {paths:number;process_references:number;processes:number;manifest_mods:number}
export interface RecipeGroup {id:string;basis:'declared_material_transformation'|'native_process';process_ids:string[];auxiliary_input_indices:Record<string,number[]>}
export interface PathGroup {id:string;representative_path_index:number;path_indices:number[]}
export interface MaterialDetour {
  start_step:number;end_step:number;process_ids:string[];resource_ids:string[]
  status:'zero_net'|'conditional_zero_net';scope:'all_concrete_choices'|'concrete_selection_witness_only'
  cases_checked:number;zero_net_cases:number
  witness:{selections:InputSelectionMap;executions:{process_id:string;runs:Rational}[];required_start_stock:Quantities;presence:Quantities;net:Quantities}
}
export interface Trace {
  recipe_groups:RecipeGroup[]
  path_groups:PathGroup[]
  path_selection: 'diverse' | 'shortest' | 'material'
  group_exclusions?: {group_id:string;name:string;kind:string;member_count:number}[]
  path_ordering?: (CutterPathPreference & {
    policy:'cutter_consumed_item_first';scope:'comparable_retained_final_cutter_paths'
    acquisition_classification_visits?:AcquisitionClassificationVisits
    original_path_indices:number[]
  }) | {
    policy:'native_acquisition_after_retained_alternatives';scope:'retained_material_paths'
    changed:boolean;acquisition_changed:boolean;eligible_paths:number;acquisition_paths:number;unknown_role_paths:number
    source_evidence:{status:'verified'|'unknown';mod_id:'gtnhintergalactic';version:string|null;source:string|null;sha256:string|null}
    acquisition_process_ids:string[];classification_visits:AcquisitionClassificationVisits
    cutter_preference?:CutterPathPreference
    original_path_indices:number[]
  } | {
    policy:'unchanged_material_order';scope:'retained_material_paths';changed:false;eligible_paths:0
    classification_visits:AcquisitionClassificationVisits;original_path_indices:number[]
  }
  path_details?: {
    path_index:number;selection_reason:string;material_continuity:'supported'|'partial'|'discontinuous'
    byproduct_steps:{process_id:string;resource_id:string;basis:'secondary_output_position_hint'}[]
    target_process_id:string|null;target_slot_index:number|null;scope:'dependency_spine_with_external_inputs'
    input_category_hints?: {
      step_index:number;process_id:string;resource_id:string;category:'crafting_tool'
      basis:'exact_captured_ore_dictionary_membership'|'native_ore_dictionary_matching_membership';group_ids:string[];input_role:'consume'
      native_accounting:{tool_accounting:string|null;container_returns:string|null;input_accounting:string|null}
      scope:'selected_resource_category_only'
    }[]
    material_detours?:MaterialDetour[]
  }[]
  material_detour_analysis?: {
    scope:'retained_2_3_recipe_windows';status:'complete'|'partial'
    limits:{windows:number;cases:number;matching_rows:number;cases_per_window:number}
    work:{windows:number;cases:number;matching_rows:number}
    counts:{zero_net:number;conditional_zero_net:number;nonzero:number;unknown:number}
  }
  branch_coverage: {target_process_id:string;slot_index:number;candidate_resources:number;paths:number;path_indices:number[];status:'represented'|'not_discovered'}[]
  snapshot_id: string; start_id: string; target_id: string; resources: Resource[]; processes: Process[]
  edges: { source: string; target: string; role: string; [key: string]: unknown }[]
  leaves: { resource_id: string; status: string; sources: string[]; reason?: string }[]
  cycles: string[][]; truncated: boolean; coverage: Coverage[]
  route: {status: 'found' | 'not_found' | 'incomplete' | 'same_resource'; strategy: 'shortest_known_dependency_path'; resource_ids: string[]; process_ids: string[]}
  paths: {resource_ids: string[]; process_ids: string[]}[]
  search: {
    examined_processes:number;limit:number;truncated:boolean
    terminal_artifacts?: {
      policy:'allow'|'direct_targets_only';basis:'runtime_item_class_hierarchy_or_native_registered_subtype';scope:'selected_consumed_spine_edges'
      recognition_status:'not_requested'|'not_checked'|'captured_for_checked_resources'|'partial'
      endpoint_checks:number;endpoint_compatibility:'not_requested'|'not_checked'|'work_limit'|'unrestricted_start'|'incompatible'|'compatible'
      checked_edges:number;blocked_edges:number;resource_lookups:number;terminal_resources:number
      unknown_resources:number;not_applicable_resources:number;charged_work:number
    }
  }
  limit_reasons: ('depth' | 'search_process_limit' | 'path_limit' | 'path_process_limit' | 'search_state_limit' | 'search_work_limit' | 'search_enumeration_limit' | 'search_variant_limit')[]
  tier_filter?: TierOptions & {active:boolean;excluded_unknown:number;excluded_out_of_range:number}
  recipe_tiers?: {process_id:string;status:'known'|'unknown'|'not_applicable';tier:number|null;name:string|null;scope:string;reason?:string}[]
}
export interface TierOptions {min_tier?:number;max_tier?:number;unknown_tier_policy:'exclude'|'include'}

export interface TraceJob {
  job_id:string;snapshot_id:string;revision:number
  status:'running'|'paused'|'finished'|'failed'|'closed'
  phase:string;elapsed_seconds:number;progress:Record<string,unknown>
  result_revision:number;result?:Trace;request:Record<string,unknown>;error?:string
}

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
