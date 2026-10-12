import { useState } from 'react'
import type { Environment, Page, Process, Resource, Single, Source, Status, Trace } from './api'
import { query, useRequest } from './api'
import { Badge, CoverageList, JsonData, ProcessDetail, RequestState, SourceDetail, ResourceRef } from './Details'
import { TraceView } from './TraceView'
import { ResourcePicker } from './ResourcePicker'

function Pagination({page, setOffset}: {page: Page<unknown>; setOffset: (offset: number) => void}) {
  return <div className="pagination"><span>{page.total ? `${page.offset + 1}–${Math.min(page.offset + page.items.length, page.total)} of ${page.total.toLocaleString()}` : '0 results'}</span><button disabled={page.offset === 0} onClick={() => setOffset(Math.max(0, page.offset - page.limit))}>Previous</button><button disabled={page.offset + page.limit >= page.total} onClick={() => setOffset(page.offset + page.limit)}>Next</button></div>
}
function ProcessCard({process, onSelect}: {process: Process; onSelect: (id: string) => void}) {
  const [open, setOpen] = useState(false)
  return <article className="process-card"><button className="process-summary" aria-expanded={open} onClick={() => setOpen(!open)}><span><strong>{process.display_name || process.id}</strong><small>{process.family} · {process.inputs.length} input slots · {process.outputs.length} outputs</small></span><span aria-hidden="true">{open ? '−' : '+'}</span></button>{open && <ProcessDetail process={process} onSelect={onSelect}/>}</article>
}

export default function App() {
  const status = useRequest<Status>(query('status'))
  const [view, setView] = useState<'library' | 'trace' | 'environments'>('library')
  const [search, setSearch] = useState('')
  const [q, setQ] = useState('')
  const [kind, setKind] = useState('')
  const [resourceOffset, setResourceOffset] = useState(0)
  const [selected, setSelected] = useState<string | null>(null)
  const [detailTab, setDetailTab] = useState<'producing' | 'using' | 'sources'>('producing')
  const [detailOffset, setDetailOffset] = useState(0)
  const [startId, setStartId] = useState('')
  const [targetId, setTargetId] = useState('')
  const [environmentSearch, setEnvironmentSearch] = useState('')
  const [environmentQ, setEnvironmentQ] = useState('')
  const [environmentOffset, setEnvironmentOffset] = useState(0)
  const active = !!status.data
  const capture = status.data?.manifest.capture as Record<string, unknown> | undefined
  const pack = status.data?.manifest.pack as Record<string, unknown> | undefined
  const packLabel = pack?.name != null ? `Pack: ${String(pack.name)}`
    : Array.isArray(pack?.mods) ? `Pack identity: ${pack.mods.length.toLocaleString()} captured mods` : 'Pack: Name not captured'
  const captureLabel = capture?.kind != null ? `Capture: ${String(capture.kind)}`
    : capture?.lifecycle != null ? `Capture lifecycle: ${String(capture.lifecycle)}` : 'Capture: Kind not captured'
  const resources = useRequest<Page<Resource>>(active ? query('resources', {q, kind, offset: resourceOffset, limit: 30}) : null)
  const resource = useRequest<Single<Resource>>(active && selected ? query(`resources/${encodeURIComponent(selected)}`) : null)
  const processes = useRequest<Page<Process>>(active && selected && detailTab !== 'sources' ? query('processes', {[detailTab === 'producing' ? 'output_id' : 'input_id']: selected, offset: detailOffset, limit: 10}) : null)
  const sources = useRequest<Page<Source>>(active && selected && detailTab === 'sources' ? query('sources', {resource_id: selected, offset: detailOffset, limit: 10}) : null)
  const environmentCatalog = useRequest<Page<Environment>>(active ? query('environments', {limit: 500}) : null)
  const environments = useRequest<Page<Environment>>(active && view === 'environments' ? query('environments', {q: environmentQ, offset: environmentOffset, limit: 30}) : null)
  const selectResource = (id: string) => { setSelected(id); setDetailOffset(0); setDetailTab('producing'); setView('library') }
  const chooseTab = (tab: typeof detailTab) => { setDetailTab(tab); setDetailOffset(0) }

  return <div className="app">
    <header className="app-header"><a className="brand" href="#" onClick={event => {event.preventDefault(); setView('library')}}><span className="brand-mark">GT</span><span>Dataset Explorer<small>GregTech New Horizons</small></span></a><div className="header-identity">{status.data ? <><span className="live-dot"/><span>Local snapshot</span><code title={status.data.snapshot_id}>{status.data.snapshot_id}</code></> : <span>No snapshot connected</span>}<button className="subtle-button" onClick={status.reload} disabled={status.loading}>Refresh</button></div></header>
    <main>
      <div className="page-heading"><div><p className="eyebrow">Captured data · One shared Dataset</p><h1>Explore the pack’s mechanics</h1><p>Inspect resources, production processes and acquisition context.</p></div><nav className="main-tabs" aria-label="Workspace"><button aria-current={view === 'library' ? 'page' : undefined} onClick={() => setView('library')}>Library</button><button aria-current={view === 'trace' ? 'page' : undefined} onClick={() => setView('trace')}>Trace</button><button aria-current={view === 'environments' ? 'page' : undefined} onClick={() => setView('environments')}>Environments</button></nav></div>
      <RequestState {...status} retry={status.reload}/>
      {!status.data && !status.loading && <section className="empty-state"><h2>Connect a captured snapshot</h2><p>Start the local Dataset HTTP server with an imported snapshot. This interface reads its /api routes.</p><p>No sample production data is loaded.</p></section>}
      {status.data && <>
        <section className="snapshot-panel" aria-label="Dataset identity and coverage"><div className="stats">{Object.entries(status.data.counts).map(([name, count]) => <div key={name}><strong>{count.toLocaleString()}</strong><span>{name}</span></div>)}</div><div className="snapshot-provenance"><strong>{packLabel}</strong><Badge tone={capture?.kind === 'synthetic' ? 'warning' : ''}>{captureLabel}</Badge>{capture?.kind === 'synthetic' && <span>Synthetic verification data</span>}<span>Created: {String(status.data.manifest.created_at ?? 'Unknown')}</span></div><details className="coverage"><summary><span>Coverage and capture evidence</span><span>{status.data.coverage.filter(record => record.status !== 'complete').length} domains need attention</span></summary><p className="help">Completeness belongs to each named domain. Record counts do not prove that every pack mechanic is captured.</p><CoverageList records={status.data.coverage}/><JsonData label="Snapshot manifest and pack identity" value={status.data.manifest}/></details></section>
        {view === 'library' && <div className="library-layout"><aside className="resource-browser"><div className="panel-heading"><h2>Resources</h2><Badge>{resources.data?.total.toLocaleString() ?? '…'}</Badge></div><form className="search-form" onSubmit={event => {event.preventDefault(); setQ(search); setResourceOffset(0)}}><label htmlFor="resource-search">Search name or registry ID</label><div className="input-action"><input id="resource-search" type="search" value={search} onChange={event => setSearch(event.target.value)} placeholder="e.g. iron or gregtech"/><button type="submit">Search</button></div><label htmlFor="resource-kind">Resource kind</label><select id="resource-kind" value={kind} onChange={event => {setKind(event.target.value); setResourceOffset(0)}}><option value="">Items and fluids</option><option value="item">Items</option><option value="fluid">Fluids</option></select></form><RequestState {...resources} retry={resources.reload}/>{resources.data && <><ul className="resource-list">{resources.data.items.map(item => <li key={item.id}><button aria-pressed={selected === item.id} onClick={() => selectResource(item.id)}><span className={`kind-icon ${item.kind}`} aria-hidden="true">{item.kind === 'fluid' ? '◉' : '◇'}</span><span><strong>{item.display_name || item.registry_name}</strong><code>{item.registry_name}</code><small>{item.kind}{item.metadata == null ? '' : ` · metadata ${item.metadata}`}</small></span></button></li>)}</ul>{resources.data.items.length === 0 && <p className="empty-inline">No resources match this search.</p>}<Pagination page={resources.data} setOffset={setResourceOffset}/></>}</aside>
          <section className="resource-detail"><RequestState {...resource} retry={resource.reload}/>{!selected && <div className="empty-state"><span className="empty-symbol">◇</span><h2>Choose a resource</h2><p>Inspect every captured producer, consumer and possible source.</p></div>}{resource.data && <><div className="resource-heading"><div><p className="eyebrow">{resource.data.item.kind} resource</p><h2>{resource.data.item.display_name || resource.data.item.registry_name}</h2><code>{resource.data.item.registry_name}</code><p className="resource-id">Resource ID: {resource.data.item.id}</p></div><div className="button-stack"><button onClick={() => {setStartId(resource.data!.item.id); setView('trace')}}>Use as supplied start</button><button className="primary" onClick={() => {setTargetId(resource.data!.item.id); setView('trace')}}>Trace this target</button></div></div><div className="resource-facts"><span>Metadata: {resource.data.item.metadata ?? 'not captured / not applicable'}</span><Badge>{resource.data.item.nbt == null ? 'No NBT' : 'NBT identity preserved'}</Badge></div><JsonData label="Resource identity and extension fields" value={resource.data.item}/><nav className="detail-tabs" aria-label="Resource relationships"><button aria-pressed={detailTab === 'producing'} onClick={() => chooseTab('producing')}>Producing processes</button><button aria-pressed={detailTab === 'using'} onClick={() => chooseTab('using')}>Using processes</button><button aria-pressed={detailTab === 'sources'} onClick={() => chooseTab('sources')}>Acquisition sources</button></nav>
            {detailTab !== 'sources' && <><RequestState {...processes} retry={processes.reload}/>{processes.data && <>{processes.data.matching_complete === false && <div className="notice warning"><strong>Matching is incomplete</strong><p>{processes.data.unresolved_matches ?? 'Unknown number of'} unresolved matches. Missing results are not an exact negative.</p></div>}{processes.data.items.map(process => <ProcessCard key={process.id} process={process} onSelect={selectResource}/>)}{!processes.data.items.length && <p className="empty-inline">No {detailTab === 'producing' ? 'producing' : 'using'} processes are known in captured data.</p>}<Pagination page={processes.data} setOffset={setDetailOffset}/></>}</>}
            {detailTab === 'sources' && <><p className="help">Generation definitions describe conditional possibility, not observed deposits in a saved world.</p><RequestState {...sources} retry={sources.reload}/><RequestState {...environmentCatalog} retry={environmentCatalog.reload}/>{environmentCatalog.data && environmentCatalog.data.total > environmentCatalog.data.items.length && <p className="warning-text">Only the first 500 environment records are loaded here. Inspect the environment catalog for additional mappings.</p>}{sources.data && <>{sources.data.items.map(source => <SourceDetail key={source.id} source={source} environments={environmentCatalog.data?.items ?? []} onSelect={selectResource}/>)}{!sources.data.items.length && <p className="empty-inline">No acquisition sources are known in captured data. Check coverage before drawing a conclusion.</p>}<Pagination page={sources.data} setOffset={setDetailOffset}/></>}</>}
          </>}</section></div>}
        {view === 'trace' && <TraceWorkspace startId={startId} targetId={targetId} setStartId={setStartId} setTargetId={setTargetId} onSelect={selectResource}/>}
        {view === 'environments' && <section className="environment-workspace"><div className="panel-heading"><div><h2>Environment catalog</h2><p>Registered dimensions and generation context. These are definitions, not world observations.</p></div></div><form className="search-form environment-search" onSubmit={event => {event.preventDefault(); setEnvironmentQ(environmentSearch); setEnvironmentOffset(0)}}><label htmlFor="environment-search">Search environments</label><div className="input-action"><input id="environment-search" value={environmentSearch} onChange={event => setEnvironmentSearch(event.target.value)} placeholder="Name, dimension or provider"/><button>Search</button></div></form><RequestState {...environments} retry={environments.reload}/>{environments.data && <><div className="environment-grid">{environments.data.items.map(environment => <article className="environment-card" key={environment.id}><h3>{environment.name}</h3><code>{environment.id}</code><dl><div><dt>Dimension ID</dt><dd>{environment.dimension_id ?? 'Unknown'}</dd></div><div><dt>Provider</dt><dd>{environment.provider ?? 'Unknown'}</dd></div></dl><JsonData label="Properties and provenance" value={environment}/></article>)}</div>{!environments.data.items.length && <p className="empty-inline">No environments match this search.</p>}<Pagination page={environments.data} setOffset={setEnvironmentOffset}/></>}</section>}
      </>}
    </main><footer>Read-only local explorer · Snapshot-scoped knowledge · Discovery does not prove progression or optimize a whole factory · <a href="/THIRD_PARTY_NOTICES.txt" target="_blank" rel="noreferrer">Third-party licenses</a></footer>
  </div>
}

function IntermediateFilter({label, ids, onChange}: {label:string;ids:string[];onChange:(ids:string[])=>void}) {
  const [draft,setDraft]=useState('')
  const [resolved,setResolved]=useState('')
  const [revision,setRevision]=useState(0)
  return <fieldset className="intermediate-filter"><legend>{label} materials</legend><ResourcePicker key={revision} label={`${label} intermediate`} selectedId={draft} onSelect={setDraft} onResolve={setResolved}/><button type="button" disabled={!draft || resolved!==draft} onClick={()=>{if(!ids.includes(draft))onChange([...ids,draft]);setDraft('');setResolved('');setRevision(value=>value+1)}}>Add {label.toLowerCase()} material</button><ul className="filter-tags">{ids.map(id=><li key={id}><ResourceRef id={id}/><button type="button" aria-label={`Remove ${label.toLowerCase()} material ${id}`} onClick={()=>onChange(ids.filter(value=>value!==id))}>×</button></li>)}</ul></fieldset>
}
function TraceWorkspace({startId,targetId,setStartId,setTargetId,onSelect}: {startId:string;targetId:string;setStartId:(id:string)=>void;setTargetId:(id:string)=>void;onSelect:(id:string)=>void}) {
  const [resolvedStart,setResolvedStart]=useState('')
  const [resolvedTarget,setResolvedTarget]=useState('')
  const [depth,setDepth]=useState(12)
  const [maxProcesses,setMaxProcesses]=useState(50)
  const [maxPaths,setMaxPaths]=useState(8)
  const [extraSteps,setExtraSteps]=useState(2)
  const [required,setRequired]=useState<string[]>([])
  const [excluded,setExcluded]=useState<string[]>([])
  const [url,setUrl]=useState<string|null>(null)
  const trace=useRequest<Trace>(url)
  const ready=!!startId && !!targetId && resolvedStart===startId && resolvedTarget===targetId
  const currentUrl=query('trace',{start_id:startId,target_id:targetId,max_depth:depth,max_processes:maxProcesses,max_paths:maxPaths,max_extra_steps:extraSteps,required_resource_id:required,excluded_resource_id:excluded})
  const current=url===currentUrl
  return <section className="trace-workspace"><div className="panel-heading"><div><h2>Explore concrete production paths</h2><p>Select endpoints, then require or exclude materials that occur between them.</p></div></div><form onSubmit={event=>{event.preventDefault();if(!ready)return;if(current)trace.reload();else setUrl(currentUrl)}}>
    <div className="trace-controls"><ResourcePicker label="Supplied start resource" selectedId={startId} onSelect={setStartId} onResolve={setResolvedStart}/><ResourcePicker label="Target resource" selectedId={targetId} onSelect={setTargetId} onResolve={setResolvedTarget}/><label>Maximum depth<input type="number" min="1" value={depth} onChange={event=>setDepth(Number(event.target.value))} required/></label><label>Maximum processes<input type="number" min="1" max="300" value={maxProcesses} onChange={event=>setMaxProcesses(Number(event.target.value))} required/></label><label>Paths<input type="number" min="1" max="100" value={maxPaths} onChange={event=>setMaxPaths(Number(event.target.value))} required/></label><label>Additional steps<input type="number" min="0" max="64" value={extraSteps} onChange={event=>setExtraSteps(Number(event.target.value))} required/></label></div>
    <p className="help">Additional steps are allowed beyond the shortest qualifying path. Material filters apply to path intermediates, not tools, presence requirements or co-products.</p>
    <div className="intermediate-filters"><IntermediateFilter label="Required" ids={required} onChange={setRequired}/><IntermediateFilter label="Excluded" ids={excluded} onChange={setExcluded}/></div>
    <div className="trace-submit"><button className="primary" disabled={!ready || (trace.loading && current)}>Trace dependencies</button></div>
  </form>
  {current && <RequestState {...trace} retry={trace.reload}/>}
  {url && !current && <p className="notice">Search selections or filters changed. Submit to search the Dataset with these settings.</p>}
  {!url && <div className="empty-state"><h3>Complete paths in one graph</h3><p>Shared recipe tiles are merged. Drag and arrange the graph after the search.</p></div>}
  {current && trace.data && <TraceView trace={trace.data} onSelect={onSelect}/>}
  </section>
}
