import {useState} from 'react'
import type {Resource,Single} from './api'
import {query,useRequest} from './api'
import {Badge,JsonData,RequestState} from './Details'

export function AcquisitionBadges({resource,basic=false}:{resource:Resource;basic?:boolean}) {
  const analysis=resource.acquisition_analysis
  const noncanonical=analysis?.unification.status==='noncanonical_unification_variant'
  const preferred=noncanonical?analysis?.unification.preferred_resource_ids[0]:undefined
  const anchor=useRequest<Single<Resource>>(preferred?query(`resources/${encodeURIComponent(preferred)}`):null)
  const labels:Record<string,string>={known_source:'Known source',eligible_producer:'Captured producer',unresolved_producer_only:'Unresolved producer',no_known_acquisition:'No known acquisition'}
  return <span className="acquisition-badges">{basic && <Badge tone="presence">Basic resource</Badge>}{noncanonical && <span title={`Captured preferred identity: ${anchor.data?.item.display_name??preferred??'none captured'} · ${anchor.data?.item.registry_name??''}. Native unification evidence, not an absence proof.`}><Badge tone="danger">Noncanonical variant</Badge></span>}
    {analysis && labels[analysis.acquisition.status] && <span title={`${analysis.acquisition.reason} Captured coverage is partial. This is not an unobtainability claim.`}><Badge tone={analysis.acquisition.status==='no_known_acquisition'||analysis.acquisition.status==='unresolved_producer_only'?'warning':'good'}>{labels[analysis.acquisition.status]}</Badge></span>}
  </span>
}
export function AcquisitionDetails({resourceId,profileId}:{resourceId:string;profileId?:string}) {
  const [open,setOpen]=useState(false)
  const request=useRequest<{snapshot_id:string;item:unknown;grounding:{status:string;[key:string]:unknown};discovery:unknown}>(open?query(`acquisition/${encodeURIComponent(resourceId)}`,{profile_id:profileId}):null)
  const grounding:Record<string,string>={structural_reachable:'A structurally grounded dependency path is known',no_known_grounded_path:'No grounded path is known within this captured scope',incomplete:'Grounding discovery is incomplete'}
  return <details className="chemical-facts" onToggle={event=>setOpen(event.currentTarget.open)}><summary>Acquisition evidence</summary>{open && <><p className="help">Unification replacements are native identity facts. Missing captured acquisition or grounding is a scoped suspicion. It does not prove a resource is unobtainable.</p><RequestState {...request} retry={request.reload}/>{request.data && <><strong>{grounding[request.data.grounding.status]??request.data.grounding.status}</strong><JsonData label="Native unification and acquisition evidence" value={request.data.item}/><JsonData label="Grounding and unseeded components" value={request.data.grounding}/><JsonData label="Acquisition discovery scope" value={request.data.discovery}/></>}</>}</details>
}
