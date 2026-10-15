import {useState} from 'react'
import type {AcquisitionAnalysis,Resource,Single} from './api'
import {query,useRequest} from './api'
import {Badge,ConditionFacts,EnvironmentFacts,JsonData,RequestState} from './Details'

const sourceLabels:Record<string,string>={captured_inventory_source:'Captured world source',mining_rule_candidate_only:'Mining drop candidate',generated_block_only:'Generated ore block'}

export function AcquisitionBadges({resource,basic=false}:{resource:Resource;basic?:boolean}) {
  const analysis=resource.acquisition_analysis
  const noncanonical=analysis?.unification.status==='noncanonical_unification_variant'
  const preferred=noncanonical?analysis?.unification.preferred_resource_ids[0]:undefined
  const anchor=useRequest<Single<Resource>>(preferred?query(`resources/${encodeURIComponent(preferred)}`):null)
  const origin=analysis?.provenance?.world_source
  const labels:Record<string,string>={known_source:'Captured source definition',unresolved_producer_only:'Unresolved production recipes',no_known_acquisition:'No captured acquisition evidence'}
  return <span className="acquisition-badges">{basic && <Badge tone="presence">Basic resource</Badge>}{noncanonical && <span title={`Captured preferred identity: ${anchor.data?.item.display_name??preferred??'none captured'} · ${anchor.data?.item.registry_name??''}. Native unification evidence, not an absence proof.`}><Badge tone="danger">Noncanonical variant</Badge></span>}
    {origin && sourceLabels[origin.status] && <span title="Captured definitions describe world origin. Candidate mining drops are inferred. These labels do not establish inventory or a complete acquisition plan."><Badge tone={origin.status==='captured_inventory_source'?'good':'warning'}>{sourceLabels[origin.status]}</Badge></span>}
    {analysis?.provenance?.initial_processing.status==='inferred' && <span title="A bounded chain from a world source supports this initial-processing inference. It is a heuristic, not a declared basic resource."><Badge>Initial processing (inferred)</Badge></span>}
    {analysis && labels[analysis.acquisition.status] && !(analysis.acquisition.status==='known_source' && origin && sourceLabels[origin.status]) && <span title={`${analysis.acquisition.reason} Captured coverage may be partial. This is not an unobtainability claim.`}><Badge tone={analysis.acquisition.status==='no_known_acquisition'||analysis.acquisition.status==='unresolved_producer_only'?'warning':'good'}>{labels[analysis.acquisition.status]}</Badge></span>}
  </span>
}
export function AcquisitionDetails({resourceId,profileId}:{resourceId:string;profileId?:string}) {
  const [open,setOpen]=useState(false)
  const request=useRequest<{snapshot_id:string;item:AcquisitionAnalysis;grounding:{status:string;[key:string]:unknown};discovery:unknown}>(open?query(`acquisition/${encodeURIComponent(resourceId)}`,{profile_id:profileId}):null)
  const grounding:Record<string,string>={structural_reachable:'A structurally grounded dependency path is known',no_known_grounded_path:'No grounded path is known within this captured scope',incomplete:'Grounding discovery is incomplete'}
  const analysis=request.data?.item
  const provenance=analysis?.provenance
  return <details className="chemical-facts" onToggle={event=>setOpen(event.currentTarget.open)}><summary>Acquisition evidence</summary>{open && <><p className="help">A production recipe, a world source definition and a complete acquisition plan are different evidence. Missing records in this captured scope do not prove a resource is unobtainable.</p><RequestState {...request} retry={request.reload}/>{request.data && analysis && <>
    <p><strong>Production recipes in dump: {analysis.acquisition.eligible_producer_count.toLocaleString()}</strong></p><p>{analysis.acquisition.unresolved_producer_count.toLocaleString()} unresolved production recipes · {analysis.acquisition.source_count.toLocaleString()} source definitions</p><p>{analysis.acquisition.reason}</p>
    <p className="help">Production recipes still require their ingredients and conditions. Open Production recipes to inspect them.</p>
    {provenance && <section><h4>World origin and initial processing</h4><strong>{sourceLabels[provenance.world_source.status]??'No active world source evidence'}</strong><p className="help">A generated ore block is separate from its mining output. Mining-rule candidates are inferred. Captured source definitions do not prove available inventory.</p>
      <EnvironmentFacts environments={provenance.world_source.evidence.flatMap(evidence=>evidence.environments??[])}/>
      <ul>{provenance.world_source.evidence.map((evidence,index)=><li key={`${evidence.source_id}:${index}`}><strong>{(evidence.resource_semantics??evidence.classification??evidence.kind).replaceAll('_',' ')}</strong> · {evidence.status} · {evidence.confidence.replaceAll('_',' ')}<p>{evidence.kind}</p>{evidence.environments?.length ? <p>Environments: {evidence.environments.map(environment=>`${environment.name} (dimension ${environment.dimension_id??'unknown'})`).join(', ')}</p>:evidence.environment_ids.length>0 && <p>Environment IDs: {evidence.environment_ids.join(', ')}</p>}<ConditionFacts value={evidence.conditions??{}} label="Source conditions"/></li>)}</ul>
      <p>Initial processing: {provenance.initial_processing.status==='inferred'?`inferred within ${provenance.initial_processing.max_steps} steps (${provenance.initial_processing.confidence})`:'no bounded evidence'}</p><p>Renewability: {provenance.renewable.status}. {provenance.renewable.reason}</p>
      {provenance.basic_suggestion.suggested && <p className="help">Suggested basic resource: {provenance.basic_suggestion.reason} Add it to a profile only if you want to assume its supply as your planning boundary.</p>}
    </section>}
    <strong>{grounding[request.data.grounding.status]??request.data.grounding.status}</strong><JsonData label="Technical data: native unification and acquisition evidence" value={analysis}/><JsonData label="Grounding and unseeded components" value={request.data.grounding}/><JsonData label="Acquisition discovery scope" value={request.data.discovery}/>
  </>}</>}</details>
}
