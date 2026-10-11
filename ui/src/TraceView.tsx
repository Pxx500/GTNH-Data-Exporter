import { useCallback, useMemo, useState } from 'react'
import type { Trace } from './api'
import { Badge, CoverageList, JsonData, ProcessDetail, ResourceRef } from './Details'
import { pathConnections, RecipeGraph } from './RecipeGraph'

const limitDescriptions: Record<Trace['limit_reasons'][number],string> = {
  depth:'Search reached Maximum depth. Longer paths may require a higher depth.',
  search_process_limit:'Search reached the server process-search bound. Graph controls do not change that server bound.',
  search_state_limit:'Search reached the server state-search bound. More candidate paths remain unexamined.',
  search_work_limit:'Search reached the server work bound. More candidate paths remain unexamined.',
  search_enumeration_limit:'Search reached the server path-enumeration bound. More candidate paths remain unexamined.',
  path_limit:'Search reached the requested path count. Increase Paths to request additional alternatives.',
  path_process_limit:'An additional complete path exceeded Maximum processes. Increase that bound to include more paths.',
}

export function TraceView({trace,onSelect}: {trace: Trace;onSelect:(id:string)=>void}) {
  const [selection,setSelection] = useState<string|null>(null)
  const [highlight,setHighlight] = useState<number|null>(null)
  const {route}=trace
  const resourceById=useMemo(()=>new Map(trace.resources.map(resource=>[resource.id,resource])),[trace.resources])
  const processById=useMemo(()=>new Map(trace.processes.map(process=>[process.id,process])),[trace.processes])
  const connections=useMemo(()=>pathConnections(trace),[trace])
  const selectedProcess=selection?.startsWith('process:') ? processById.get(selection.slice(8)) : undefined
  const selectedResource=selection?.startsWith('resource:') ? resourceById.get(selection.slice(9)) : undefined
  const inspect=useCallback((id:string)=>setSelection(`process:${id}`),[])
  const selectResource=useCallback((id:string)=>{if(resourceById.has(id))setSelection(`resource:${id}`);else onSelect(id)},[resourceById,onSelect])
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
      {route.status === 'found' && <p className="help">Paths are searched by fewest qualifying process steps, within the requested extra-step allowance. This does not optimize yield. Every tile retains its additional ingredients, machine requirements and conditions.</p>}
      {route.status === 'not_found' && <p className="help">No connecting dependency path was found in the captured data. Coverage and unresolved mechanics still limit that conclusion.</p>}
      {route.status === 'incomplete' && <p className="help">The bounded result does not establish a complete route to the target. Inspect the limits and coverage before using these records.</p>}
      {route.status === 'same_resource' && <p className="help">Zero production steps are required to identify the same resource. This does not establish its availability or quantity.</p>}
      <div className="route-endpoints"><span>Supplied start</span><ResourceRef id={trace.start_id} resources={resourceById} onSelect={selectResource}/><span>Target</span><ResourceRef id={trace.target_id} resources={resourceById} onSelect={selectResource}/></div>
      <p className="route-search-summary">Search examined {trace.search.examined_processes.toLocaleString()} processes · Server search limit {trace.search.limit.toLocaleString()} · {trace.search.truncated ? 'Search truncated' : 'Search finished within its bound'}</p>
    </section>
    {(trace.truncated || trace.limit_reasons.length > 0 || trace.search.truncated) && <div className="notice warning" role="status">
      <strong>Bounded trace has omitted work</strong>
      <ul className="trace-limit-reasons">{trace.limit_reasons.map(reason => <li key={reason}><code>{reason}</code><span>{limitDescriptions[reason]}</span></li>)}</ul>
      {trace.search.truncated && <p>Route search stopped at its server bound. More search work remains unexamined.</p>}
    </div>}
    <div className="trace-summary"><Badge>{trace.paths.length} complete paths</Badge><Badge>{route.process_ids.length} primary path steps</Badge><Badge>{trace.processes.length} included processes</Badge><Badge>{trace.resources.length} included resources</Badge><Badge tone={trace.cycles.length ? 'warning' : ''}>{trace.cycles.length} cycle groups</Badge><code>Snapshot {trace.snapshot_id}</code></div>


    <div className="graph-toolbar"><p className="help">Drag a tile by its header. Pan the canvas, scroll to zoom, or use the graph controls.</p><label>Highlight path<select value={highlight===null ? 'all' : highlight} onChange={event=>setHighlight(event.target.value==='all' ? null : Number(event.target.value))}><option value="all">All paths</option>{trace.paths.map((path,index)=><option value={index} key={index}>Path {index+1} · {path.process_ids.length} steps</option>)}</select></label></div>
    <div className={`trace-layout ${selectedProcess || selectedResource ? 'has-inspector' : ''}`}>
      <div className="free-recipe-graph" role="region" aria-label="Recipe path graph">{hasRecipes ? <RecipeGraph key={JSON.stringify([trace.snapshot_id,trace.paths])} trace={trace} highlight={highlight} inspect={inspect} inspectResource={selectResource}/> : <div className="empty-state"><h3>No production recipe tiles</h3><p>{route.status==='same_resource' ? 'The endpoints identify the same resource.' : 'No complete recipe path was emitted within this search.'}</p></div>}</div>
      {(selectedProcess || selectedResource) && <aside className="graph-inspector"><h3>Selected record</h3><button className="close-inspector" onClick={()=>setSelection(null)} aria-label="Close record inspector">Close</button>{selectedProcess ? <ProcessDetail process={selectedProcess} resources={resourceById} onSelect={selectResource}/> : selectedResource && <><h3>{selectedResource.display_name || selectedResource.registry_name}</h3><code>{selectedResource.registry_name}</code><p><button onClick={()=>onSelect(selectedResource.id)}>Inspect in library</button></p><JsonData label="Full resource record" value={selectedResource}/></>}</aside>}
    </div>
    <details className="path-list"><summary>Ordered paths ({trace.paths.length})</summary>{trace.paths.map((path,index)=><section key={index}><h4>Path {index+1} · {path.process_ids.length} steps</h4><ol>{path.process_ids.map((id,step)=><li key={id}><button onClick={()=>inspect(id)}>{recipeName(id)}</button><span>→ {resourceName(path.resource_ids[step+1])}</span></li>)}</ol></section>)}</details>
    <details className="path-list" open><summary>Direct recipe connections</summary><ul aria-label="Direct recipe connections">{connections.map(link=><li key={link.id}><button onClick={()=>inspect(link.target)}>{recipeName(link.source)} → {recipeName(link.target)}</button><span>{resourceName(link.resourceId)} · Paths {link.paths.map(index=>index+1).join(', ')}</span></li>)}</ul></details>
    <section className="leaves"><h3>Additional recipe requirements</h3><p className="help">Path intermediates are filtered during search. Presence, tools and co-products remain inside each whole recipe and are not intermediate filter matches.</p><div className="leaf-grid">{trace.leaves.map(leaf=><article key={leaf.resource_id}><ResourceRef id={leaf.resource_id} resources={resourceById} onSelect={selectResource}/><Badge tone={leaf.status==='assumed' ? 'presence' : leaf.status==='available' ? 'good' : 'warning'}>{leaf.status.replaceAll('_',' ')}</Badge>{leaf.reason && <p>{leaf.reason}</p>}</article>)}</div></section>
    {trace.cycles.length>0 && <JsonData label="Captured cycle groups" value={trace.cycles}/>}
    <details className="coverage"><summary>Trace coverage</summary><CoverageList records={trace.coverage}/></details><JsonData label="Full trace response" value={trace}/>
  </>
}
