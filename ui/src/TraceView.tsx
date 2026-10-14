import { useCallback, useMemo, useState } from 'react'
import type { Trace, TierOptions } from './api'
import { Badge, CoverageList, JsonData, ProcessDetail, ResourceRef } from './Details'
import { pathConnections, recipeGraphForTrace, RecipeGraph } from './RecipeGraph'
import type { AttachedConnection } from './RecipeGraph'
import { RecyclePanel } from './RecyclePanel'
import type { RecyclingPlan } from './RecyclePanel'
import { RecordInspector, ResourceInspector } from './RecordInspector'
import { LoopAuditPanel } from './LoopAuditPanel'

const limitDescriptions: Record<Trace['limit_reasons'][number],string> = {
  depth:'Search reached Maximum depth. Longer paths may require a higher depth.',
  search_process_limit:'Search reached the server process-search bound. Graph controls do not change that server bound.',
  search_state_limit:'Search reached the server state-search bound. More candidate paths remain unexamined.',
  search_work_limit:'Search reached the server work bound. More candidate paths remain unexamined.',
  search_enumeration_limit:'Search reached the server path-enumeration bound. More candidate paths remain unexamined.',
  search_variant_limit:'Search reached its deferred recipe-variant bound while looking for different material routes. Further routes and recipe variants may remain unexamined.',
  path_limit:'Search reached the requested path count. Increase Paths to request additional alternatives.',
  path_process_limit:'An additional complete path exceeded Maximum processes. Increase that bound to include more paths.',
}

export function TraceView({trace,onSelect,onUseStart,onUseTarget,tierOptions}: {trace: Trace;onSelect:(id:string)=>void;onUseStart?:(id:string)=>void;onUseTarget?:(id:string)=>void;tierOptions?:TierOptions}) {
  const [selection,setSelection] = useState<string|null>(null)
  const [highlight,setHighlight] = useState<number|null>(null)
  const [auditOpen,setAuditOpen]=useState(false)
  const [recycle,setRecycle]=useState<{ownerId:string;byproductId:string}|null>(null)
  const [overlay,setOverlay]=useState<{plan:RecyclingPlan;index:number;ownerId:string}|null>(null)
  const graphTrace=useMemo(()=>{
    if(!overlay)return trace
    const secondary=overlay.plan.secondary_trace
    return {...trace,paths:[overlay.plan.main_path,overlay.plan.alternatives[overlay.index].path],
      resources:[...new Map([...trace.resources,...secondary.resources].map(item=>[item.id,item])).values()],
      processes:[...new Map([...trace.processes,...secondary.processes].map(item=>[item.id,item])).values()],
      recipe_tiers:[...new Map([...(trace.recipe_tiers??[]),...(secondary.recipe_tiers??[])].map(item=>[item.process_id,item])).values()]}
  },[trace,overlay])
  const attachments=useMemo(()=>{
    if(!overlay)return []
    const path=overlay.plan.alternatives[overlay.index].path
    if(path.process_ids.length===0)return []
    const links:AttachedConnection[]=[{source:overlay.ownerId,target:path.process_ids[0],resourceId:overlay.plan.byproduct_id,label:'Recycle output'}]
    const {main_plan,main_path,return_id}=overlay.plan
    const consumers=new Set((main_plan.startup?.steps??[]).filter(step=>step.ledger.status==='complete' && (step.ledger.consumed[return_id]?.numerator??0)>0).map(step=>step.process_id))
    for(const id of main_path.process_ids){
      const process=trace.processes.find(item=>item.id===id)
      const selected=main_plan.selected_inputs?.[id]
      if(consumers.has(id) && process?.inputs.some((slot,index)=>slot.role==='consume' && selected?.[String(index)]?.resource_id===return_id))links.push({source:path.process_ids[path.process_ids.length-1],target:id,resourceId:return_id,label:'Returned input'})
    }
    return links
  },[trace,overlay])
  const graph=useMemo(()=>recipeGraphForTrace(graphTrace,attachments),[graphTrace,attachments])
  const {route}=trace
  const resourceById=useMemo(()=>new Map(graphTrace.resources.map(resource=>[resource.id,resource])),[graphTrace.resources])
  const processById=useMemo(()=>new Map(graphTrace.processes.map(process=>[process.id,process])),[graphTrace.processes])
  const connections=useMemo(()=>pathConnections(graphTrace),[graphTrace])
  const selectedProcess=selection?.startsWith('process:') ? processById.get(selection.slice(8)) : undefined
  const selectedTier=graphTrace.recipe_tiers?.find(item=>item.process_id===selectedProcess?.id)
  const selectedResource=selection?.startsWith('resource:') ? resourceById.get(selection.slice(9)) : undefined
  const inspect=useCallback((id:string)=>setSelection(`process:${id}`),[])
  const beginRecycle=useCallback((ownerId:string,byproductId:string)=>{setRecycle({ownerId,byproductId});setSelection(`process:${ownerId}`);setOverlay(null)},[])
  const selectResource=useCallback((id:string)=>setSelection(`resource:${id}`),[])
  const recipeName=(id:string)=>processById.get(id)?.display_name || id
  const resourceName=(id:string)=>resourceById.get(id)?.display_name || resourceById.get(id)?.registry_name || id
  const hasRecipes=trace.paths.some(path=>path.process_ids.length>0)
  return <>
    <section className={`main-route-panel route-${route.status}`} aria-label="Target-directed route">
      <div className="detail-title">
        <div>
          <p className="eyebrow">Target-directed discovery</p>
          <h3>{route.status === 'found' ? 'Known paths found' : route.status === 'not_found' ? 'No known route found' : route.status === 'incomplete' ? 'Route discovery is incomplete' : 'Start and target are the same resource'}</h3>
        </div>
        <Badge tone={route.status === 'found' ? 'good' : route.status === 'same_resource' ? '' : 'warning'}>{route.status.replaceAll('_', ' ')}</Badge>
      </div>
        {route.status === 'found' && <p className="help">{trace.path_selection === 'material' ? 'Results prioritize native material continuity and target ingredient coverage using captured hints. This is a heuristic, not a chemical balance proof.' : trace.path_selection === 'diverse' ? 'Results spread across target ingredient branches, including longer alternatives within the requested bounds. The first path has the fewest known steps.' : 'Results prefer the fewest qualifying process steps within the requested extra-step allowance. The first path has the fewest known steps.'} This does not optimize yield. Every tile retains its additional ingredients, machine requirements and conditions.</p>}
      {route.status === 'not_found' && <p className="help">No connecting dependency path was found in the captured data. Coverage and unresolved mechanics still limit that conclusion. Check the selected resource variants, relax intermediate filters, or raise the Advanced search bounds.</p>}
      {route.status === 'incomplete' && <p className="help">The bounded result does not establish a complete route to the target. Inspect the limits and coverage before using these records.</p>}
      {route.status === 'same_resource' && <p className="help">Zero production steps are required to identify the same resource. This does not establish its availability or quantity.</p>}
      <div className="route-endpoints"><span>Supplied start</span><ResourceRef id={trace.start_id} resources={resourceById} onSelect={selectResource}/><span>Target</span><ResourceRef id={trace.target_id} resources={resourceById} onSelect={selectResource}/></div>
      <p className="route-search-summary">Search examined {trace.search.examined_processes.toLocaleString()} processes · Server search limit {trace.search.limit.toLocaleString()} · {trace.search.truncated ? 'Search truncated' : 'Search finished within its bound'}</p>
    </section>
    {(trace.truncated || trace.limit_reasons.length > 0 || trace.search.truncated) && <div className="notice warning" role="status">
      <strong>Bounded trace has omitted work</strong><p>Returned paths are candidates within this search. Raise the relevant Advanced bound or narrow your endpoints and filters to explore more. Additional recipe requirements still need supplies.</p>
      <ul className="trace-limit-reasons">{trace.limit_reasons.map(reason => <li key={reason}><code>{reason}</code><span>{limitDescriptions[reason]}</span></li>)}</ul>
      {trace.search.truncated && <p>Route search stopped at its server bound. More search work remains unexamined.</p>}
    </div>}
      <div className="trace-summary"><Badge>{trace.paths.length} complete paths</Badge><Badge>{route.process_ids.length} primary path steps</Badge>{trace.branch_coverage.length>0 && <Badge>{trace.branch_coverage.filter(branch=>branch.status==='represented').length}/{trace.branch_coverage.length} target ingredient branches</Badge>}<Badge>{trace.processes.length} included processes</Badge><Badge>{trace.resources.length} included resources</Badge><Badge tone={trace.cycles.length ? 'warning' : ''}>{trace.cycles.length} cycle groups</Badge><code>Snapshot {trace.snapshot_id}</code></div>
      {trace.tier_filter?.active && <div className="notice"><strong>Recipe voltage filter</strong><p>Minimum {trace.tier_filter.min_tier ?? 'any'} · Maximum {trace.tier_filter.max_tier ?? 'any'} · Unknown tiers {trace.tier_filter.unknown_tier_policy} · {trace.tier_filter.excluded_unknown} unknown and {trace.tier_filter.excluded_out_of_range} outside-range recipes excluded.</p></div>}
      {selectedProcess && graphTrace.recipe_tiers && <p className="help">Selected recipe voltage: {selectedTier?.status==='not_applicable'?'No machine voltage requirement':selectedTier?.name??'Unknown'} · This is not a machine capability estimate.</p>}


    <div className="graph-toolbar"><label>Highlight path<select value={highlight===null ? 'all' : highlight} onChange={event=>setHighlight(event.target.value==='all' ? null : Number(event.target.value))}><option value="all">All paths</option>{trace.paths.map((path,index)=><option value={index} key={index}>Path {index+1} · {path.process_ids.length} steps</option>)}</select></label></div>
    <div className={`trace-layout ${selection ? 'has-inspector' : ''}`}>
      <div className="free-recipe-graph" role="region" aria-label="Recipe path graph">{hasRecipes ? <RecipeGraph key={JSON.stringify([graphTrace.snapshot_id,graphTrace.paths])} graph={graph} highlight={highlight} inspect={inspect} inspectResource={selectResource} recycle={beginRecycle} recycleProcesses={overlay?.plan.main_path.process_ids}/> : <div className="empty-state"><h3>No production recipe tiles</h3><p>{route.status==='same_resource' ? 'The endpoints identify the same resource.' : 'No complete recipe path was emitted within this search.'}</p></div>}</div>
      {selection && <RecordInspector onClose={()=>setSelection(null)}>{selectedProcess ? <ProcessDetail process={selectedProcess} resources={resourceById} onSelect={selectResource} onRecycle={trace.paths.some(path=>path.process_ids.includes(selectedProcess.id)) ? id=>beginRecycle(selectedProcess.id,id) : undefined}/> : selection.startsWith('resource:') && <ResourceInspector key={selection} id={selection.slice(9)} resources={resourceById} onInspect={selectResource} onOpenLibrary={onSelect} onUseStart={onUseStart} onUseTarget={onUseTarget}/>}</RecordInspector>}
    </div>
      {overlay && <div className="notice"><strong>Main path and secondary return path</strong><p>The graph now shows the chosen main plan and one return path. Output and return links are presentation connections, not simultaneous execution proof.</p><ul>{attachments.map((link,index)=><li key={index}>{link.label}: {recipeName(link.source)} → {recipeName(link.target)} · {resourceName(link.resourceId)}</li>)}</ul><button onClick={()=>setOverlay(null)}>Show all main paths</button></div>}
      {recycle && <RecyclePanel key={`${trace.snapshot_id}:${recycle.ownerId}:${recycle.byproductId}`} trace={trace} {...recycle} tierOptions={tierOptions} onSelect={selectResource} onOverlay={(plan,index)=>{setHighlight(null);setOverlay({plan,index,ownerId:recycle.ownerId})}}/>}
      <details className="path-list"><summary>Ordered paths and explanations ({trace.paths.length})</summary>{trace.paths.map((path,index)=>{
        const explanation=trace.path_details?.find(item=>item.path_index===index)
        const branch=explanation?.target_process_id!=null && explanation.target_slot_index!=null && processById.has(explanation.target_process_id) ? {processId:explanation.target_process_id,slotIndex:explanation.target_slot_index}:null
        return <section key={index}><h4>Path {index+1} · {path.process_ids.length} steps</h4>{explanation && branch && <>
          <p>{explanation.selection_reason}</p><p>Material continuity hint: {explanation.material_continuity}. Target ingredient branch: <button onClick={()=>inspect(branch.processId)}>{recipeName(branch.processId)}</button>, input {branch.slotIndex+1}.</p>
          <p className="help">This path explains one dependency branch. Other recipe inputs still need external supplies.</p>
          {explanation.byproduct_steps.length>0 && <p className="help">Secondary output positions: {explanation.byproduct_steps.map(step=>`${recipeName(step.process_id)} → ${resourceName(step.resource_id)}`).join(', ')}. Native output order is a hint and does not prove a by-product role.</p>}
        </>}<ol>{path.process_ids.map((id,step)=><li key={id}><button onClick={()=>inspect(id)}>{recipeName(id)}</button><span>→ {resourceName(path.resource_ids[step+1])}</span></li>)}</ol></section>
      })}</details>
    <details className="path-list" open><summary>Direct recipe connections</summary><ul aria-label="Direct recipe connections">{connections.map(link=><li key={link.id}><button onClick={()=>inspect(link.target)}>{recipeName(link.source)} → {recipeName(link.target)}</button><span>{resourceName(link.resourceId)} · Paths {link.paths.map(index=>index+1).join(', ')}</span></li>)}</ul></details>
    <section className="leaves"><h3>Additional recipe requirements</h3><p className="help">Path intermediates are filtered during search. Presence, tools and co-products remain inside each whole recipe and are not intermediate filter matches.</p><div className="leaf-grid">{trace.leaves.map(leaf=><article key={leaf.resource_id}><ResourceRef id={leaf.resource_id} resources={resourceById} onSelect={selectResource}/><Badge tone={leaf.status==='assumed' ? 'presence' : leaf.status==='available' ? 'good' : 'warning'}>{leaf.status.replaceAll('_',' ')}</Badge>{leaf.reason && <p>{leaf.reason}</p>}</article>)}</div></section>
    {trace.cycles.length>0 && <JsonData label="Captured cycle groups" value={trace.cycles}/>}
      <details className="loop-audit-container" onToggle={event=>setAuditOpen(event.currentTarget.open)}><summary>Developer loop audit</summary>{auditOpen && <LoopAuditPanel startId={selectedResource?.id??trace.start_id} resources={resourceById} tierOptions={tierOptions} onSelect={selectResource}/>}</details>
      <details className="coverage"><summary>Trace coverage</summary><CoverageList records={trace.coverage}/></details><JsonData label="Full trace response" value={trace}/>
  </>
}
