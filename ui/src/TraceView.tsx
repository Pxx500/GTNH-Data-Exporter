import { useLayoutEffect, useMemo, useRef, useState } from 'react'
import type { Process, Trace } from './api'
import { Badge, CoverageList, JsonData, ProcessDetail, ResourceRef } from './Details'

const limitDescriptions: Record<Trace['limit_reasons'][number], string> = {
  depth: 'Route search reached Maximum depth. A longer known path may require a higher depth.',
  search_process_limit: 'Route search reached the server search limit. Raising graph limits does not change this fixed search bound.',
  route_process_limit: 'The discovered route exceeds Maximum processes. Increase that bound to include the main route.',
  context_depth: 'Supporting dependency expansion reached its depth bound. Additional context remains outside this graph.',
  context_process_limit: 'Supporting dependencies reached Maximum processes. Additional supporting recipes remain outside this graph.',
}
interface Connection { source: string; target: string; materials: Map<string, Set<string>>; primary: boolean }
interface Box { x: number; y: number; width: number; height: number }

function projectConnections(trace: Trace, processes: ReadonlyMap<string, Process>): Connection[] {
  const result = new Map<string, Connection>()
  const consumers = new Map<string, Trace['edges']>()
  for (const edge of trace.edges) {
    if (!edge.source.startsWith('resource:') || !edge.target.startsWith('process:')) continue
    const entries = consumers.get(edge.source) ?? []
    entries.push(edge)
    consumers.set(edge.source, entries)
  }
  const routeLinks = new Set(trace.route.process_ids.slice(0, -1).map((id, index) => JSON.stringify([id, trace.route.process_ids[index + 1], trace.route.resource_ids[index + 1]])))
  for (const outputEdge of trace.edges) {
    if (!outputEdge.source.startsWith('process:') || !outputEdge.target.startsWith('resource:')) continue
    const source = outputEdge.source.slice(8)
    const resourceId = outputEdge.target.slice(9)
    const producer = processes.get(source)
    if (!producer?.outputs.some(output => output.resource_id === resourceId && output.amount !== 0 && output.chance?.numerator !== 0)) continue
    for (const inputEdge of consumers.get(outputEdge.target) ?? []) {
      if (typeof inputEdge.slot_index !== 'number' || typeof inputEdge.choice_index !== 'number') continue
      const target = inputEdge.target.slice(8)
      const consumer = processes.get(target)
      const slot = consumer?.inputs[inputEdge.slot_index]
      const choice = slot?.choices[inputEdge.choice_index]
      if (!choice || choice.amount === 0 || choice.match.mode === 'native_unknown') continue
      if ((choice.match.mode === 'ore_dict' || choice.match.mode === 'unified') && !choice.match.group_id) continue
      const key = JSON.stringify([source, target])
      let connection = result.get(key)
      if (!connection) { connection = {source, target, materials: new Map(), primary: false}; result.set(key, connection) }
      const roles = connection.materials.get(resourceId) ?? new Set<string>()
      roles.add(slot!.role)
      connection.materials.set(resourceId, roles)
      if (routeLinks.has(JSON.stringify([source, target, resourceId]))) connection.primary = true
    }
  }
  return [...result.values()].sort((a,b) => Number(b.primary) - Number(a.primary))
}

export function TraceView({trace, onSelect}: {trace: Trace; onSelect: (id: string) => void}) {
  const [selection, setSelection] = useState<string | null>(null)
  const [zoom, setZoom] = useState(1)
  const {route} = trace
  const resourceById = useMemo(() => new Map(trace.resources.map(resource => [resource.id, resource])), [trace.resources])
  const processById = useMemo(() => new Map(trace.processes.map(process => [process.id, process])), [trace.processes])
  const connections = useMemo(() => projectConnections(trace, processById), [trace, processById])
  const routeProcesses = new Set(route.process_ids)
  const primary = route.process_ids.flatMap(id => processById.get(id) ? [processById.get(id)!] : [])
  const context = trace.processes.filter(process => !routeProcesses.has(process.id))
  const cyclicIds = new Set(trace.cycles.flat())
  const selectedProcess = selection?.startsWith('process:') ? processById.get(selection.slice(8)) : undefined
  const selectedResource = selection?.startsWith('resource:') ? resourceById.get(selection.slice(9)) : undefined
  const board = useRef<HTMLDivElement>(null)
  const [geometry, setGeometry] = useState<{height: number; boxes: Map<string, Box>}>({height: 600, boxes: new Map()})
  useLayoutEffect(() => {
    const element = board.current
    if (!element) return
    const measure = () => {
      const origin = element.getBoundingClientRect()
      const boxes = new Map<string, Box>()
      element.querySelectorAll<HTMLElement>('[data-recipe-id]').forEach(tile => {
        const rect = tile.getBoundingClientRect()
        boxes.set(tile.dataset.recipeId!, {x:(rect.left-origin.left)/zoom,y:(rect.top-origin.top)/zoom,width:rect.width/zoom,height:rect.height/zoom})
      })
      setGeometry({height: Math.max(300, origin.height/zoom), boxes})
    }
    measure()
    if (typeof ResizeObserver === 'undefined') return
    const observer = new ResizeObserver(measure)
    observer.observe(element)
    element.querySelectorAll('[data-recipe-id]').forEach(tile => observer.observe(tile))
    return () => observer.disconnect()
  }, [trace, zoom])

  const choose = (id: string) => setSelection(id)
  const selectResource = (id: string) => resourceById.has(id) ? choose(`resource:${id}`) : onSelect(id)
  const recipeName = (id: string) => processById.get(id)?.display_name || id
  const resourceName = (id: string) => resourceById.get(id)?.display_name || resourceById.get(id)?.registry_name || id
  const renderTile = (process: Process, index: number, main: boolean) => <li key={process.id}>
    <article data-recipe-id={process.id} aria-label={`Recipe ${recipeName(process.id)}`} className={`recipe-tile ${main ? 'main-recipe' : 'context-recipe'} ${cyclicIds.has(`process:${process.id}`) ? 'cycle-recipe' : ''} ${selection === `process:${process.id}` ? 'selected-recipe' : ''}`}>
      <div className="recipe-tile-toolbar"><Badge tone={main ? 'good' : ''}>{main ? `Step ${index+1} · Selected route` : 'Supporting context'}</Badge>{cyclicIds.has(`process:${process.id}`) && <Badge tone="warning">Cycle member</Badge>}<button type="button" aria-label={`Process ${recipeName(process.id)}`} onClick={() => choose(`process:${process.id}`)}>Inspect details</button></div>
      <ProcessDetail process={process} onSelect={selectResource} resources={resourceById}/>
    </article>
  </li>

  return <>
    <section className={`main-route-panel route-${route.status}`} aria-label="Target-directed route">
      <div className="detail-title">
        <div>
          <p className="eyebrow">Target-directed discovery</p>
          <h3>{route.status === 'found' ? 'Shortest known route found' : route.status === 'not_found' ? 'No known route found' : route.status === 'incomplete' ? 'Route discovery is incomplete' : 'Start and target are the same resource'}</h3>
        </div>
        <Badge tone={route.status === 'found' ? 'good' : route.status === 'same_resource' ? '' : 'warning'}>{route.status.replaceAll('_', ' ')}</Badge>
      </div>
      {route.status === 'found' && <p className="help">Selected known dependency path with the fewest process steps. This does not optimize yield or resource efficiency. Additional ingredients, machine requirements and conditions remain visible below.</p>}
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
    <div className="trace-summary"><Badge>{route.process_ids.length} selected route steps</Badge><Badge>{trace.processes.length} included processes</Badge><Badge>{trace.resources.length} included resources</Badge><Badge tone={trace.cycles.length ? 'warning' : ''}>{trace.cycles.length} cycle groups</Badge><code>Snapshot {trace.snapshot_id}</code></div>

    <div className="graph-toolbar"><div className="graph-legend"><span className="legend-main-route">Whole recipe · Selected route</span><span className="legend-context">Whole recipe · Context</span><span className="legend-cycle">Cycle member</span></div><div><button onClick={() => setZoom(Math.max(.5, zoom-.1))} aria-label="Zoom out">−</button><span>{Math.round(zoom*100)}%</span><button onClick={() => setZoom(Math.min(1.5, zoom+.1))} aria-label="Zoom in">+</button><button onClick={() => setZoom(1)}>Reset zoom</button></div></div>
    <div className={`trace-layout ${selectedProcess || selectedResource ? 'has-inspector' : ''}`}>
      <div className="graph-scroll" tabIndex={0} role="region" aria-label="Whole recipe graph. Selected recipes come first, supporting recipes are secondary.">
        <div className="recipe-canvas" style={{width:1040*zoom,height:geometry.height*zoom}}>
          <div className="recipe-board" ref={board} style={{transform:`scale(${zoom})`}}>
            <svg className="recipe-links" width="1040" height={geometry.height} aria-hidden="true">
              <defs><marker id="recipe-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8" fill="#8297a7"/></marker><marker id="main-recipe-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8" fill="#087c70"/></marker></defs>
              {connections.map((link,index) => {
                const source = geometry.boxes.get(link.source), target = geometry.boxes.get(link.target)
                if (!source || !target) return null
                let d: string, x: number, y: number
                if (link.primary && target.y > source.y) {
                  x=source.x+source.width/2; y=(source.y+source.height+target.y)/2
                  d=`M${x},${source.y+source.height} L${x},${target.y-5}`
                } else {
                  const bend=24+(index%6)*7
                  const startX=source.x<300 ? source.x+source.width : source.x, endX=target.x<300 ? target.x+target.width : target.x
                  const startY=source.y+source.height/2, endY=target.y+target.height/2
                  x=500+bend; y=(startY+endY)/2
                  d=link.source===link.target ? `M${startX},${startY} C${x},${startY-80} ${x},${startY+80} ${startX},${startY+35}` : `M${startX},${startY} C${x},${startY} ${x},${endY} ${endX},${endY}`
                }
                const label=[...link.materials.keys()].map(resourceName).join(' + ')
                return <g key={JSON.stringify([link.source,link.target])}><path className={`recipe-link ${link.primary ? 'main-recipe-link' : 'context-recipe-link'}`} d={d} markerEnd={`url(#${link.primary ? 'main-recipe-arrow' : 'recipe-arrow'})`}/>{link.primary && <text className="recipe-link-label" x={x+12} y={y}>{label.length>34 ? `${label.slice(0,32)}…` : label}</text>}<title>{recipeName(link.source)} → {recipeName(link.target)} · {label}</title></g>
              })}
            </svg>
            <section className="recipe-column"><h3>{route.status==='found' ? 'Selected main route' : 'Partial route evidence'}</h3>{primary.length ? <ol aria-label={route.status==='found' ? 'Selected main route' : 'Partial route evidence'}>{primary.map((process,index) => renderTile(process,index,true))}</ol> : <p className="help">{route.status==='same_resource' ? 'No production recipe is required for the identical resource.' : 'No selected recipe path is established.'}</p>}</section>
            <section className="recipe-column supporting-column"><h3>Supporting recipes and recycling</h3>{context.length ? <ol aria-label="Supporting recipes">{context.map((process,index) => renderTile(process,index,false))}</ol> : <p className="help">No supporting recipe tiles were included.</p>}</section>
          </div>
        </div>
      </div>
      {(selectedProcess || selectedResource) && <aside className="graph-inspector"><h3>Selected record</h3><button className="close-inspector" onClick={() => setSelection(null)} aria-label="Close record inspector">Close</button>{selectedProcess ? <><p className="node-context-label">{routeProcesses.has(selectedProcess.id) ? 'Selected main route recipe' : 'Supporting recipe'}</p><ProcessDetail process={selectedProcess} onSelect={selectResource} resources={resourceById}/></> : selectedResource && <><h3>{selectedResource.display_name || selectedResource.registry_name}</h3><code>{selectedResource.registry_name}</code><p><button onClick={() => onSelect(selectedResource.id)}>Inspect in library</button></p><JsonData label="Full resource record" value={selectedResource}/></>}</aside>}
    </div>
    <section className="direct-recipe-connections"><h3>Direct recipe connections</h3><p className="help">Connections follow supported trace matching. Alternatives within a slot remain OR choices, even when more than one possible supplier is connected. These links do not allocate quantities or prove that all requirements are supplied.</p><ul aria-label="Direct recipe connections">{connections.map(link => <li key={JSON.stringify([link.source,link.target])}><button onClick={() => choose(`process:${link.target}`)}>{recipeName(link.source)} → {recipeName(link.target)}</button><Badge tone={link.primary ? 'good' : ''}>{link.primary ? 'Selected route' : 'Context / recycling'}</Badge><span>{[...link.materials].map(([id,roles]) => `${resourceName(id)} (${[...roles].join(', ')})`).join(' · ')}</span></li>)}</ul>{!connections.length && <p className="help">No confirmed recipe-to-recipe material connections are included. Unresolved anchors and zero outputs remain inspectable in the captured records.</p>}</section>
    <section className="leaves"><h3>Boundary leaves and side inputs</h3><p className="help">A cycle is not a material source. “No known source” is scoped to the captured data.</p><div className="leaf-grid">{trace.leaves.map(leaf => <article key={leaf.resource_id}><ResourceRef id={leaf.resource_id} resources={resourceById} onSelect={selectResource}/><Badge tone={leaf.status==='assumed' ? 'presence' : leaf.status==='available' ? 'good' : 'warning'}>{leaf.status.replaceAll('_',' ')}</Badge>{leaf.reason && <p>{leaf.reason}</p>}<p className="source-ids">{leaf.sources.length ? `Source IDs: ${leaf.sources.join(', ')}` : 'No source references'}</p></article>)}</div></section>
    {trace.cycles.length>0 && <details className="json-data"><summary>Cycle groups ({trace.cycles.length})</summary><p>Groups contain mutually reachable captured records. They do not imply a material source.</p><pre>{JSON.stringify(trace.cycles,null,2)}</pre></details>}
    <details className="coverage"><summary>Trace coverage</summary><CoverageList records={trace.coverage}/></details><JsonData label="Full trace response" value={trace}/>
  </>
}
