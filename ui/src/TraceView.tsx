import { useState } from 'react'
import type { Trace } from './api'
import { Badge, CoverageList, JsonData, ProcessDetail, ResourceRef } from './Details'

const limitDescriptions: Record<Trace['limit_reasons'][number], string> = {
  depth: 'Route search reached Maximum depth. A longer known path may require a higher depth.',
  search_process_limit: 'Route search reached the server search limit. Raising graph limits does not change this fixed search bound.',
  route_process_limit: 'The discovered route exceeds Maximum processes. Increase that bound to include the main route.',
  context_depth: 'Supporting dependency expansion reached its depth bound. Additional context remains outside this graph.',
  context_process_limit: 'Supporting dependencies reached Maximum processes. Additional supporting recipes remain outside this graph.',
}

export function TraceView({trace, onSelect}: {trace: Trace; onSelect: (id: string) => void}) {
  const [selection, setSelection] = useState<string | null>(null)
  const [zoom, setZoom] = useState(1)
  const {route} = trace
  const resourceById = new Map(trace.resources.map(resource => [resource.id, resource]))
  const processById = new Map(trace.processes.map(process => [process.id, process]))
  const routeResources = new Set(route.resource_ids)
  const routeProcesses = new Set(route.process_ids)
  const primaryNodes = new Set([
    ...route.resource_ids.map(id => `resource:${id}`),
    ...route.process_ids.map(id => `process:${id}`),
  ])
  const primaryEdges = new Set(route.process_ids.flatMap((id, index) => [
    JSON.stringify([`resource:${route.resource_ids[index]}`, `process:${id}`]),
    JSON.stringify([`process:${id}`, `resource:${route.resource_ids[index + 1]}`]),
  ]))
  const cyclicIds = new Set(trace.cycles.flat())
  const inputIds = new Set(trace.edges.filter(edge => edge.source.startsWith('resource:')).map(edge => edge.source))
  const contextResources = trace.resources.filter(resource => !routeResources.has(resource.id))
  const contextProcesses = trace.processes.filter(process => !routeProcesses.has(process.id))
  const contextLeft = contextResources.filter(resource => inputIds.has(`resource:${resource.id}`))
  const contextRight = contextResources.filter(resource => !inputIds.has(`resource:${resource.id}`))
  const contextY = route.resource_ids.length ? 65 + Math.max(1, route.process_ids.length) * 120 + 80 : 65
  const nodes = [
    ...route.resource_ids.flatMap((id, index) => {
      const resource = resourceById.get(id)
      return resource ? [{id: `resource:${id}`, title: resource.display_name || resource.registry_name, kind: resource.kind, x: index === 0 ? 25 : 715, y: 65 + Math.max(0, index - 1) * 120}] : []
    }),
    ...route.process_ids.flatMap((id, index) => {
      const process = processById.get(id)
      return process ? [{id: `process:${id}`, title: process.display_name || id, kind: process.family, x: 370, y: 65 + index * 120}] : []
    }),
    ...contextLeft.map((resource, index) => ({id: `resource:${resource.id}`, title: resource.display_name || resource.registry_name, kind: resource.kind, x: 25, y: contextY + index * 100})),
    ...contextProcesses.map((process, index) => ({id: `process:${process.id}`, title: process.display_name || process.id, kind: process.family, x: 370, y: contextY + index * 120})),
    ...contextRight.map((resource, index) => ({id: `resource:${resource.id}`, title: resource.display_name || resource.registry_name, kind: resource.kind, x: 715, y: contextY + index * 100})),
  ]
  const positions = new Map(nodes.map(node => [node.id, node]))
  const height = Math.max(420, ...nodes.map(node => node.y + 115))
  const selectedProcess = trace.processes.find(process => `process:${process.id}` === selection)
  const selectedResource = trace.resources.find(resource => `resource:${resource.id}` === selection)
  const hasContext = contextResources.length > 0 || contextProcesses.length > 0
  const choose = (id: string) => setSelection(id)

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
      {route.resource_ids.length > 0 && <>
        <h4>{route.status === 'found' ? 'Selected main route' : route.status === 'same_resource' ? 'Start and target identity' : 'Partial route evidence'}</h4>
        <ol className="main-route-list" aria-label={route.status === 'found' ? 'Selected main route' : route.status === 'same_resource' ? 'Start and target identity' : 'Partial route evidence'}>
          <li>
            <span className="route-step-label">{route.status === 'same_resource' ? 'Start and target' : 'Supplied start'}</span>
            <button type="button" onClick={() => choose(`resource:${route.resource_ids[0]}`)} aria-label={`Inspect resource ${resourceById.get(route.resource_ids[0])?.display_name || route.resource_ids[0]}`}>{resourceById.get(route.resource_ids[0])?.display_name || resourceById.get(route.resource_ids[0])?.registry_name || route.resource_ids[0]}</button>
          </li>
          {route.process_ids.map((id, index) => {
            const process = processById.get(id)
            const resourceId = route.resource_ids[index + 1]
            const resource = resourceById.get(resourceId)
            return <li key={id}>
              <span className="route-step-label">Step {index + 1}</span>
              <button type="button" className="route-process-button" onClick={() => choose(`process:${id}`)} aria-label={`Inspect process ${process?.display_name || id}`}>{process?.display_name || id}</button>
              <span className="route-arrow" aria-hidden="true">→</span>
              <button type="button" onClick={() => choose(`resource:${resourceId}`)} aria-label={`Inspect resource ${resource?.display_name || resourceId}`}>{resource?.display_name || resource?.registry_name || resourceId}</button>
              {resourceId === trace.target_id && <Badge tone="good">Target</Badge>}
            </li>
          })}
        </ol>
      </>}
      <p className="route-search-summary">Search examined {trace.search.examined_processes.toLocaleString()} processes · Server search limit {trace.search.limit.toLocaleString()} · {trace.search.truncated ? 'Search truncated' : 'Search finished within its bound'}</p>
    </section>
    {(trace.truncated || trace.limit_reasons.length > 0 || trace.search.truncated) && <div className="notice warning" role="status">
      <strong>Bounded trace has omitted work</strong>
      <ul className="trace-limit-reasons">{trace.limit_reasons.map(reason => <li key={reason}><code>{reason}</code><span>{limitDescriptions[reason]}</span></li>)}</ul>
      {trace.search.truncated && <p>Route search stopped at its server bound. More search work remains unexamined.</p>}
    </div>}
    <div className="trace-summary"><Badge>{route.process_ids.length} selected route steps</Badge><Badge>{trace.processes.length} included processes</Badge><Badge>{trace.resources.length} included resources</Badge><Badge tone={trace.cycles.length ? 'warning' : ''}>{trace.cycles.length} cycle groups</Badge><code>Snapshot {trace.snapshot_id}</code></div>
    <div className="graph-toolbar">
      <div className="graph-legend"><span className="legend-main-route">Selected route</span><span className="legend-context">Supporting context / co-products</span><span className="legend-cycle">Cycle member</span></div>
      <div><button onClick={() => setZoom(Math.max(.5, zoom - .1))} aria-label="Zoom out">−</button><span>{Math.round(zoom * 100)}%</span><button onClick={() => setZoom(Math.min(1.5, zoom + .1))} aria-label="Zoom in">+</button><button onClick={() => setZoom(1)}>Reset zoom</button></div>
    </div>
    <div className="trace-layout">
      <div className="graph-scroll" tabIndex={0} role="region" aria-label="Dependency graph. Selected route comes first, followed by supporting context.">
        <svg width={1000 * zoom} height={height * zoom} viewBox={`0 0 1000 ${height}`} role="img" aria-label="Target-directed route and supporting dependency graph">
          <defs>
            <marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8" fill="#8b9aac"/></marker>
            <marker id="route-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8" fill="#087c70"/></marker>
          </defs>
          <text className="lane-label" x="25" y="28">{route.resource_ids.length ? 'SELECTED START' : 'CAPTURED RESOURCES'}</text>
          <text className="lane-label" x="370" y="28">PROCESSES</text>
          <text className="lane-label" x="715" y="28">STEP OUTPUTS / TARGET</text>
          {hasContext && route.resource_ids.length > 0 && <><line className="context-divider" x1="25" x2="965" y1={contextY - 40} y2={contextY - 40}/><text className="lane-label" x="25" y={contextY - 20}>SUPPORTING CONTEXT AND CO-PRODUCTS</text></>}
          {trace.edges.map((edge, index) => {
            const source = positions.get(edge.source), target = positions.get(edge.target)
            if (!source || !target) return null
            const primary = primaryEdges.has(JSON.stringify([edge.source, edge.target]))
            const forward = target.x > source.x
            const x1 = source.x + (forward ? 250 : 0), x2 = target.x + (forward ? 0 : 250)
            return <path key={index} className={`graph-edge ${primary ? 'primary-edge' : 'context-edge'}`} d={`M${x1},${source.y + 35} C${x1 + (forward ? 40 : -80)},${source.y + 35} ${x2 + (forward ? -40 : 80)},${target.y + 35} ${x2},${target.y + 35}`} markerEnd={`url(#${primary ? 'route-arrow' : 'arrow'})`}><title>{primary ? 'Selected route' : 'Supporting context'} · {edge.role}: {edge.source} → {edge.target}</title></path>
          })}
          {nodes.map(node => {
            const leaf = trace.leaves.find(leaf => `resource:${leaf.resource_id}` === node.id)
            const primary = primaryNodes.has(node.id)
            const endpoint = node.id === `resource:${trace.start_id}` ? 'Supplied start' : node.id === `resource:${trace.target_id}` ? 'Target' : undefined
            return <g key={node.id} className={`graph-node ${node.id.startsWith('process:') ? 'process-node' : 'resource-node'} ${primary ? 'primary-node' : 'context-node'} ${cyclicIds.has(node.id) ? 'cycle-node' : ''} ${selection === node.id ? 'selected-node' : ''}`} transform={`translate(${node.x},${node.y})`} role="button" tabIndex={0} aria-label={`${node.id.startsWith('process:') ? 'Process' : 'Resource'} ${node.title}${leaf ? `, ${leaf.status}` : ''}`} onClick={() => choose(node.id)} onKeyDown={event => {if (event.key === 'Enter' || event.key === ' ') {event.preventDefault(); choose(node.id)}}}>
              <title>{node.title} · {node.id} · {primary ? 'Selected route' : 'Supporting context'}{leaf ? ` · ${leaf.status}` : ''}</title>
              <rect width="250" height="72" rx="9"/>
              <text x="14" y="23" className="node-title">{node.title.length > 30 ? `${node.title.slice(0, 28)}…` : node.title}</text>
              <text x="14" y="43" className="node-kind">{node.kind}</text>
              <text x="14" y="60" className="node-status">{endpoint || (primary ? 'Selected route step' : 'Supporting context')}{cyclicIds.has(node.id) ? ' · Cycle' : leaf ? ` · ${leaf.status.replaceAll('_', ' ')}` : ''}</text>
            </g>
          })}
        </svg>
      </div>
      <aside className="graph-inspector"><h3>Selected node</h3>
        {selectedProcess ? <><p className="node-context-label">{routeProcesses.has(selectedProcess.id) ? 'Selected main route process' : 'Supporting context process'}</p><ProcessDetail process={selectedProcess} onSelect={onSelect}/></> : selectedResource ? <><p className="node-context-label">{routeResources.has(selectedResource.id) ? 'Selected main route resource' : 'Supporting context / co-product'}</p><p className="eyebrow">{selectedResource.kind}</p><h3>{selectedResource.display_name || selectedResource.registry_name}</h3><code>{selectedResource.registry_name}</code><p><button onClick={() => onSelect(selectedResource.id)}>Inspect in library</button></p><JsonData label="Full resource record" value={selectedResource}/></> : <p className="help">Click a route step or graph node, or focus it and press Enter. Full process details retain every input slot, alternative, quantity and condition.</p>}
      </aside>
    </div>
    <section className="leaves"><h3>Boundary leaves and side inputs</h3><p className="help">A cycle is not a material source. “No known source” is scoped to the captured data.</p><div className="leaf-grid">{trace.leaves.map(leaf => <article key={leaf.resource_id}><ResourceRef id={leaf.resource_id} onSelect={onSelect}/><Badge tone={leaf.status === 'assumed' ? 'presence' : leaf.status === 'available' ? 'good' : 'warning'}>{leaf.status.replaceAll('_', ' ')}</Badge>{leaf.reason && <p>{leaf.reason}</p>}<p className="source-ids">{leaf.sources.length ? `Source IDs: ${leaf.sources.join(', ')}` : 'No source references'}</p></article>)}</div></section>
    {trace.cycles.length > 0 && <details className="json-data"><summary>Cycle groups ({trace.cycles.length})</summary><p>Each group contains mutually reachable nodes. Member order does not describe an execution path.</p><pre>{JSON.stringify(trace.cycles, null, 2)}</pre></details>}
    <details className="coverage"><summary>Trace coverage</summary><CoverageList records={trace.coverage}/></details><JsonData label="Full trace response" value={trace}/>
  </>
}
