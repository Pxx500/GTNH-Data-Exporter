import { useEffect, useMemo, useRef, useState } from 'react'
import {useTraceJob} from './useTraceJob'
import type { Environment, Group, Page, Process, Resource, Single, Source, Status, Trace } from './api'
import { query, useRequest } from './api'
import { ActionHint, Badge, CoverageList, JsonData, RequestState, SourceDetail, ResourceRef, ProcessInputSummary } from './Details'
import { ProcessInspector } from './RecordInspector'
import { TraceActivity, TraceView } from './TraceView'
import type {TraceActivityState} from './TraceView'
import { ResourcePicker } from './ResourcePicker'
import { ChemicalFacts } from './ChemicalFacts'
import {AcquisitionBadges,AcquisitionDetails} from './AcquisitionDetails'
import {NetworkAnalysis} from './NetworkAnalysis'
import {StatisticsPanel} from './StatisticsPanel'
import {BoundaryProfileSelector} from './BoundaryProfileEditor'
import type {BoundaryProfile} from './api'

function Pagination({page, setOffset}: {page: Page<unknown>; setOffset: (offset: number) => void}) {
  return <div className="pagination"><span>{page.total ? `${page.offset + 1}–${Math.min(page.offset + page.items.length, page.total)} of ${page.total.toLocaleString()}` : '0 results'}</span><button disabled={page.offset === 0} onClick={() => setOffset(Math.max(0, page.offset - page.limit))}>Previous</button><button disabled={page.offset + page.limit >= page.total} onClick={() => setOffset(page.offset + page.limit)}>Next</button>{page.total===0?<small>No pages available for this search.</small>:<>{page.offset===0 && <small>First page: no previous results.</small>}{page.offset+page.limit>=page.total && <small>Last page: no more results.</small>}</>}</div>
}
function ProcessCard({process, onSelect}: {process: Process; onSelect: (id: string) => void}) {
  const [open, setOpen] = useState(false)
  return <article className="process-card"><button className="process-summary" aria-expanded={open} onClick={() => setOpen(!open)}><span><strong>{process.display_name || process.id}</strong><small>{process.family} · <ProcessInputSummary process={process}/> · {process.outputs.length} outputs</small></span><span aria-hidden="true">{open ? '−' : '+'}</span></button>{open && <ProcessInspector process={process} onSelect={onSelect}/>}</article>
}

export default function App() {
  const status = useRequest<Status>(query('status'))
  const [view, setView] = useState<'library' | 'trace' | 'environments' | 'analysis' | 'statistics'>('library')
  const [visited,setVisited]=useState<string[]>([])
  useEffect(()=>{setVisited(current=>current.includes(view)?current:[...current,view])},[view])
  const [boundaryProfile,setBoundaryProfile]=useState<BoundaryProfile|undefined>()
  const [libraryScopeOpen,setLibraryScopeOpen]=useState(false)
  const [search, setSearch] = useState('')
  const [q, setQ] = useState('')
  const [kind, setKind] = useState('')
  const [resourceOffset, setResourceOffset] = useState(0)
  const [selected, setSelected] = useState<string | null>(null)
  const [detailTab, setDetailTab] = useState<'producing' | 'using' | 'sources'>('producing')
  const [inputMode,setInputMode] = useState<'matched'|'declared'>('matched')
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
  const resources = useRequest<Page<Resource>>(active ? query('resources', {q, kind, offset: resourceOffset, limit: 30,profile_id:boundaryProfile?.id}) : null)
  const resource = useRequest<Single<Resource>>(active && selected ? query(`resources/${encodeURIComponent(selected)}`) : null)
  const processes = useRequest<Page<Process>>(active && selected && detailTab !== 'sources' ? query('processes', {[detailTab === 'producing' ? 'output_id' : 'input_id']: selected, input_mode:detailTab==='using'?inputMode:undefined, offset: detailOffset, limit: 10}) : null)
  const sources = useRequest<Page<Source>>(active && selected && detailTab === 'sources' ? query('sources', {resource_id: selected, offset: detailOffset, limit: 10}) : null)
  const environmentCatalog = useRequest<Page<Environment>>(active ? query('environments', {limit: 500}) : null)
  const environments = useRequest<Page<Environment>>(active && view === 'environments' ? query('environments', {q: environmentQ, offset: environmentOffset, limit: 30}) : null)
  const selectResource = (id: string) => { setSelected(id); setDetailOffset(0); setDetailTab('producing'); setView('library') }
  const chooseTab = (tab: typeof detailTab) => { setDetailTab(tab); setDetailOffset(0) }
  const SnapshotPanel=view==='trace'?'details':'section'

  return <div className="app">
    <header className="app-header"><a className="brand" href="#" onClick={event => {event.preventDefault(); setView('library')}}><span className="brand-mark">GT</span><span>Dataset Explorer<small>GregTech New Horizons</small></span></a><div className="header-identity">{status.data ? <><span className="live-dot"/><span>Local snapshot</span><code title={status.data.snapshot_id}>{status.data.snapshot_id}</code></> : <span>No snapshot connected</span>}<button className="subtle-button" onClick={status.reload} disabled={status.loading}>Refresh</button>{status.loading && <small>Snapshot request in progress.</small>}</div></header>
    <main>
      <div className="page-heading"><div><p className="eyebrow">Captured data · One shared Dataset</p><h1>Explore the pack’s mechanics</h1><p>Use Library to inspect a resource, Trace to compare production paths, Analysis to calculate supplies or energy, and Statistics to compare the captured catalog.</p></div><nav className="main-tabs" aria-label="Workspace"><button aria-current={view === 'library' ? 'page' : undefined} onClick={() => setView('library')}>Library</button><button aria-current={view === 'trace' ? 'page' : undefined} onClick={() => setView('trace')}>Trace</button><button aria-current={view === 'environments' ? 'page' : undefined} onClick={() => setView('environments')}>Environments</button><button aria-current={view==='analysis'?'page':undefined} onClick={()=>setView('analysis')}>Analysis</button><button aria-current={view==='statistics'?'page':undefined} onClick={()=>setView('statistics')}>Statistics</button></nav></div>
      <RequestState {...status} retry={status.reload}/>
      {!status.data && !status.loading && <section className="empty-state"><h2>Connect a captured snapshot</h2><p>Start the local Dataset HTTP server with an imported snapshot. This interface reads its /api routes.</p><p>No sample production data is loaded.</p></section>}
      {status.data && <>
        <SnapshotPanel className="snapshot-panel" aria-label="Dataset identity and coverage">{view==='trace' && <summary className="trace-dataset-summary">Dataset details</summary>}<div className="stats">{Object.entries(status.data.counts).map(([name, count]) => <div key={name}><strong>{count.toLocaleString()}</strong><span>{name}</span></div>)}</div><div className="snapshot-provenance"><strong>{packLabel}</strong><Badge tone={capture?.kind === 'synthetic' ? 'warning' : ''}>{captureLabel}</Badge>{capture?.kind === 'synthetic' && <span>Synthetic verification data</span>}<span>Created: {String(status.data.manifest.created_at ?? 'Unknown')}</span></div><details className="coverage"><summary><span>Coverage and capture evidence</span><span>{status.data.coverage.filter(record => record.status !== 'complete').length} domains need attention</span></summary><p className="help">Completeness belongs to each named domain. Record counts do not prove that every pack mechanic is captured.</p><CoverageList records={status.data.coverage}/><JsonData label="Snapshot manifest and pack identity" value={status.data.manifest}/></details></SnapshotPanel>
        {view === 'library' && <div className="library-layout"><aside className="resource-browser"><div className="panel-heading"><h2>Resources</h2><Badge>{resources.data?.total.toLocaleString() ?? '…'}</Badge></div><p className="help">Search an item or fluid, then click a row to inspect its recipes and sources. Resource variants can have different metadata or NBT. Prefer a canonical identity when the captured unification evidence identifies one.</p><p className="help">Library search scope: {boundaryProfile?.name??'All captured resources'}. This profile does not filter the historical Trace workspace.</p><details onToggle={event=>setLibraryScopeOpen(event.currentTarget.open)}><summary>Library search profile</summary>{libraryScopeOpen && <BoundaryProfileSelector profile={boundaryProfile} label="Library search scope" onSelect={value=>{setBoundaryProfile(value);setResourceOffset(0)}}/>}</details><form className="search-form" onSubmit={event => {event.preventDefault(); setQ(search); setResourceOffset(0)}}><label htmlFor="resource-search">Search name or registry ID</label><div className="input-action"><input id="resource-search" type="search" value={search} onChange={event => setSearch(event.target.value)} placeholder="e.g. iron or gregtech"/><button type="submit">Search</button></div><label htmlFor="resource-kind">Resource kind</label><select id="resource-kind" value={kind} onChange={event => {setKind(event.target.value); setResourceOffset(0)}}><option value="">Items and fluids</option><option value="item">Items</option><option value="fluid">Fluids</option></select></form><RequestState {...resources} retry={resources.reload}/>{resources.data && <><ul className="resource-list">{resources.data.items.map(item => <li key={item.id}><button aria-pressed={selected === item.id} onClick={() => selectResource(item.id)}><span className={`kind-icon ${item.kind}`} aria-hidden="true">{item.kind === 'fluid' ? '◉' : '◇'}</span><span><strong>{item.display_name || item.registry_name}</strong><AcquisitionBadges resource={item} basic={boundaryProfile?.base_resource_ids.includes(item.id)}/><code>{item.registry_name}</code><small>{item.kind}{item.metadata == null ? '' : ` · metadata ${item.metadata}`}</small></span></button></li>)}</ul>{resources.data.items.length === 0 && <p className="empty-inline">No resources match this search.</p>}<Pagination page={resources.data} setOffset={setResourceOffset}/></>}</aside>
          <section className="resource-detail"><RequestState {...resource} retry={resource.reload}/>{!selected && <div className="empty-state"><span className="empty-symbol">◇</span><h2>Choose a resource</h2><p>Inspect every captured producer, consumer and possible source.</p></div>}{resource.data && <><div className="resource-heading"><div><p className="eyebrow">{resource.data.item.kind} resource</p><h2>{resource.data.item.display_name || resource.data.item.registry_name}</h2><code>{resource.data.item.registry_name}</code><p className="resource-id">Resource ID: {resource.data.item.id}</p></div><div className="button-stack"><button onClick={() => {setStartId(resource.data!.item.id); setView('trace')}}>Use as supplied start</button><button className="primary" onClick={() => {setTargetId(resource.data!.item.id); setView('trace')}}>Trace this target</button></div></div><div className="resource-facts"><span>Metadata: {resource.data.item.metadata ?? 'not captured / not applicable'}</span><Badge>{resource.data.item.nbt == null ? 'No NBT' : 'NBT identity preserved'}</Badge></div><AcquisitionDetails resourceId={resource.data.item.id} profileId={boundaryProfile?.id}/><ChemicalFacts resourceId={resource.data.item.id}/><JsonData label="Resource identity and extension fields" value={resource.data.item}/><nav className="detail-tabs" aria-label="Resource relationships"><button aria-pressed={detailTab === 'producing'} onClick={() => chooseTab('producing')}>Producing processes</button><button aria-pressed={detailTab === 'using'} onClick={() => chooseTab('using')}>Using processes</button><button aria-pressed={detailTab === 'sources'} onClick={() => chooseTab('sources')}>Acquisition sources</button></nav>
            {detailTab==='using' && <><label>Input lookup<select value={inputMode} onChange={event=>{setInputMode(event.target.value as typeof inputMode);setDetailOffset(0)}}><option value="matched">Known input matches</option><option value="declared">Captured references</option></select></label><p className="help">{inputMode==='declared'?'Only references to this exact variant are listed. Groups and wildcard matches are not expanded.':'Uses captured input predicates. Unresolved native matches may be missing.'}</p></>}
            {detailTab !== 'sources' && <><RequestState {...processes} retry={processes.reload}/>{processes.data && <>{processes.data.input_lookup?.mode==='declared' && <p className="help">Captured ingredient references. Native acceptance is not evaluated.</p>}{processes.data.matching_complete === false && <div className="notice warning"><strong>Matching is incomplete</strong><p>{processes.data.unresolved_matches ?? 'Unknown number of'} unresolved matches. Missing results are not an exact negative.</p></div>}{processes.data.items.map(process => <ProcessCard key={process.id} process={process} onSelect={selectResource}/>)}{!processes.data.items.length && <p className="empty-inline">{processes.data.input_lookup?.mode==='declared'?'No captured references to this exact resource ID were found.':`No ${detailTab==='producing'?'producing':'using'} processes are known in captured data.`}</p>}<Pagination page={processes.data} setOffset={setDetailOffset}/></>}</>}
            {detailTab === 'sources' && <><p className="help">Generation definitions describe conditional possibility, not observed deposits in a saved world.</p><RequestState {...sources} retry={sources.reload}/><RequestState {...environmentCatalog} retry={environmentCatalog.reload}/>{environmentCatalog.data && environmentCatalog.data.total > environmentCatalog.data.items.length && <p className="warning-text">Only the first 500 environment records are loaded here. Inspect the environment catalog for additional mappings.</p>}{sources.data && <>{sources.data.items.map(source => <SourceDetail key={source.id} source={source} environments={environmentCatalog.data?.items ?? []} onSelect={selectResource}/>)}{!sources.data.items.length && <p className="empty-inline">No acquisition sources are known in captured data. Check coverage before drawing a conclusion.</p>}<Pagination page={sources.data} setOffset={setDetailOffset}/></>}</>}
          </>}</section></div>}
        {view === 'statistics' && <StatisticsPanel profile={boundaryProfile} onProfileChange={setBoundaryProfile} onSelect={selectResource}/>}
          {(view === 'analysis' || visited.includes('analysis')) && <div hidden={view!=='analysis'}><NetworkAnalysis key={status.data.snapshot_id} snapshotId={status.data.snapshot_id} profile={boundaryProfile} onProfileChange={setBoundaryProfile} onSelect={selectResource}/></div>}
          {(view === 'trace' || visited.includes('trace')) && <div hidden={view!=='trace'}><TraceWorkspace key={status.data.snapshot_id} snapshotId={status.data.snapshot_id} startId={startId} targetId={targetId} setStartId={setStartId} setTargetId={setTargetId} onSelect={selectResource}/></div>}
        {view === 'environments' && <section className="environment-workspace"><div className="panel-heading"><div><h2>Environment catalog</h2><p>Registered dimensions and generation context. These are definitions, not world observations.</p></div></div><form className="search-form environment-search" onSubmit={event => {event.preventDefault(); setEnvironmentQ(environmentSearch); setEnvironmentOffset(0)}}><label htmlFor="environment-search">Search environments</label><div className="input-action"><input id="environment-search" value={environmentSearch} onChange={event => setEnvironmentSearch(event.target.value)} placeholder="Name, dimension or provider"/><button>Search</button></div></form><RequestState {...environments} retry={environments.reload}/>{environments.data && <><div className="environment-grid">{environments.data.items.map(environment => <article className="environment-card" key={environment.id}><h3>{environment.name}</h3><code>{environment.id}</code><dl><div><dt>Dimension ID</dt><dd>{environment.dimension_id ?? 'Unknown'}</dd></div><div><dt>Provider</dt><dd>{environment.provider ?? 'Unknown'}</dd></div></dl><JsonData label="Properties and provenance" value={environment}/></article>)}</div>{!environments.data.items.length && <p className="empty-inline">No environments match this search.</p>}<Pagination page={environments.data} setOffset={setEnvironmentOffset}/></>}</section>}
      </>}
    </main><footer>Immutable capture · User-controlled analysis profiles · Bounded results do not certify machine execution · <a href="/THIRD_PARTY_NOTICES.txt" target="_blank" rel="noreferrer">Third-party licenses</a></footer>
  </div>
}

function IntermediateFilter({label, ids, onChange}: {label:string;ids:string[];onChange:(ids:string[])=>void}) {
  const [draft,setDraft]=useState('')
  const [resolved,setResolved]=useState('')
  const [revision,setRevision]=useState(0)
  const disabledReason=!draft?'Select a search result before adding this material.':resolved!==draft?'Wait for the selected material to load.':undefined
  return <fieldset className="intermediate-filter"><legend>{label} materials</legend><ResourcePicker key={revision} label={`${label} intermediate`} selectedId={draft} onSelect={setDraft} onResolve={setResolved}/><ActionHint reason={disabledReason} ready="Ready to add this material."/><button type="button" disabled={!!disabledReason} onClick={()=>{if(!ids.includes(draft))onChange([...ids,draft]);setDraft('');setResolved('');setRevision(value=>value+1)}}>Add {label.toLowerCase()} material</button><ul className="filter-tags">{ids.map(id=><li key={id}><ResourceRef id={id}/><button type="button" aria-label={`Remove ${label.toLowerCase()} material ${id}`} onClick={()=>onChange(ids.filter(value=>value!==id))}>×</button></li>)}</ul></fieldset>
}
function ExcludedGroupFilter({ids,onChange}:{ids:string[];onChange:(ids:string[])=>void}) {
  const [text,setText]=useState('')
  const [search,setSearch]=useState<string|null>(null)
  const groups=useRequest<Page<Group & {member_count:number}>>(search===null?null:query('resource-groups',{q:search,limit:20}))
  const toggle=(id:string)=>onChange(ids.includes(id)?ids.filter(value=>value!==id):[...ids,id])
  return <fieldset className="intermediate-filter"><legend>Excluded groups on paths</legend><p className="help">Exclude members of selected captured groups from paths. Other recipe inputs remain visible.</p>
    <div className="input-action"><label>Search captured groups<input value={text} placeholder="e.g. nuggetIron" onChange={event=>setText(event.target.value)}/></label><button type="button" onClick={()=>setSearch(text.trim())}>Find groups</button></div><RequestState {...groups} retry={groups.reload}/>
    {groups.data && <><p className="help">{groups.data.items.length} of {groups.data.total.toLocaleString()} matching groups shown.</p><ul className="scope-options">{groups.data.items.map(group=><li key={group.id}><label title={group.id}><input type="checkbox" checked={ids.includes(group.id)} onChange={()=>toggle(group.id)}/>{group.name} <span>{group.member_count.toLocaleString()} members · {group.kind}</span></label></li>)}</ul></>}
    {ids.length>0 && <ul className="filter-tags">{ids.map(id=><SelectedTraceGroup key={id} id={id} remove={()=>toggle(id)}/>)}</ul>}
  </fieldset>
}
function SelectedTraceGroup({id,remove}:{id:string;remove:()=>void}) {
  const group=useRequest<Single<Group>>(query(`groups/${encodeURIComponent(id)}`))
  return <li title={id}>{group.data ? <span>{group.data.item.name} · {group.data.item.members.length.toLocaleString()} members · {group.data.item.kind}</span>:id}<button type="button" onClick={remove} aria-label={`Remove group ${id}`}>Remove</button><RequestState {...group} retry={group.reload}/></li>
}

function TraceWorkspace({snapshotId,startId,targetId,setStartId,setTargetId,onSelect}: {snapshotId:string;startId:string;targetId:string;setStartId:(id:string)=>void;setTargetId:(id:string)=>void;onSelect:(id:string)=>void}) {
  const [resolvedStart,setResolvedStart]=useState('')
  const [resolvedTarget,setResolvedTarget]=useState('')
  const [depth,setDepth]=useState('12')
  const [maxProcesses,setMaxProcesses]=useState('150')
  const [maxPaths,setMaxPaths]=useState('8')
  const [extraSteps,setExtraSteps]=useState('6')
  const [pathSelection,setPathSelection]=useState('material')
  const [terminalArtifactPolicy,setTerminalArtifactPolicy]=useState('allow')
  const [minTier,setMinTier]=useState('')
  const [maxTier,setMaxTier]=useState('')
  const [tierBadInput,setTierBadInput]=useState({minTier:false,maxTier:false})
  const readTierValidity=(field:'minTier'|'maxTier',input:HTMLInputElement)=>{
    const badInput=input.validity.badInput
    setTierBadInput(value=>({...value,[field]:badInput}))
  }
  const [unknownTierPolicy,setUnknownTierPolicy]=useState('exclude')
  const [required,setRequired]=useState<string[]>([])
  const [excluded,setExcluded]=useState<string[]>([])
  const [excludedGroups,setExcludedGroups]=useState<string[]>([])
  const [timeBudget,setTimeBudget]=useState('5')
  const [budgetMultiplier,setBudgetMultiplier]=useState(1)
  const [submitted,setSubmitted]=useState<{url:string;kind:'job'|'sync'}>()
  const [requestClock,setRequestClock]=useState<{id:string;sampledAt:number;elapsedSeconds:number;pending:boolean;kind:'job'|'sync';failed?:boolean}>()
  const requestSequence=useRef(0)
  const beginRequestClock=(kind:'job'|'sync')=>setRequestClock({id:`${snapshotId}:request:${++requestSequence.current}`,sampledAt:Date.now(),elapsedSeconds:0,pending:true,kind})
  const finishRequestClock=(failed=false)=>setRequestClock(value=>value?.pending?{...value,elapsedSeconds:Math.max(0,Date.now()-value.sampledAt)/1000,pending:false,failed}:value)
  const jobs=useTraceJob(snapshotId)
  const synchronous=useRequest<Trace>(submitted?.kind==='sync'?submitted.url:null)
  const trace=submitted?.kind==='job'?{data:jobs.result,loading:jobs.busy,error:jobs.error,reload:jobs.retry}:synchronous
  const url=submitted?.url??null
  const activeJob=submitted?.kind==='job'?jobs.job:undefined
  useEffect(()=>{
    if(submitted?.kind==='sync' && !synchronous.loading)finishRequestClock()
  },[submitted?.kind,synchronous.loading,synchronous.data,synchronous.error])
  const activeSampledAt=useMemo(()=>Date.now(),[activeJob?.job_id,activeJob?.status,activeJob?.elapsed_seconds])
  const requestActivity:TraceActivityState|undefined=requestClock?{
    id:requestClock.id,status:requestClock.failed || trace.error?'failed':requestClock.kind==='sync'?(requestClock.pending?'running':'finished'):(requestClock.pending?'starting':'closed'),
    elapsedSeconds:requestClock.elapsedSeconds,sampledAt:requestClock.sampledAt,timing:'request',error:trace.error,
  }:undefined
  const activity:TraceActivityState|undefined=requestClock?.pending || requestClock?.failed?requestActivity:activeJob?{
    id:activeJob.job_id,status:activeJob.status,phase:activeJob.phase,elapsedSeconds:activeJob.elapsed_seconds,sampledAt:activeSampledAt,timing:'active',error:trace.error??activeJob.error,
  }:requestActivity
  const terminalArtifacts=trace.data?.search.terminal_artifacts
  const pathOrdering=trace.data?.path_ordering
  const ready=!!startId && !!targetId && resolvedStart===startId && resolvedTarget===targetId
  const currentUrl=query('trace',{start_id:startId,target_id:targetId,max_depth:Number(depth),max_processes:Number(maxProcesses),max_paths:Number(maxPaths),max_extra_steps:Number(extraSteps),path_selection:pathSelection,terminal_artifact_policy:terminalArtifactPolicy,required_resource_id:required,excluded_resource_id:excluded,excluded_group_id:excludedGroups,min_tier:minTier===''?undefined:Number(minTier),max_tier:maxTier===''?undefined:Number(maxTier),unknown_tier_policy:unknownTierPolicy,view:'compact',time_budget_seconds:pathSelection==='material'?Number(timeBudget):undefined,budget_multiplier:pathSelection==='material'?budgetMultiplier:undefined})
  const current=url===currentUrl
  const numberError=(value:string|number,label:string,min:number,max:number,integer=true)=>{
    const number=Number(value)
    return String(value).trim()==='' || !Number.isFinite(number) || (integer && !Number.isInteger(number)) || number<min || number>max?`${label} must be ${integer?'a whole number':'a finite number'} from ${min} to ${max}.`:undefined
  }
  const fieldErrors={
    depth:numberError(depth,'Maximum depth',1,64),
    maxProcesses:numberError(maxProcesses,'Included recipe limit',1,5000),
    maxPaths:numberError(maxPaths,'Paths',1,100),
    extraSteps:numberError(extraSteps,'Additional steps',0,64),
    minTier:tierBadInput.minTier?'Minimum recipe voltage tier must be a whole number from 0 to 15.':minTier===''?undefined:numberError(minTier,'Minimum recipe voltage tier',0,15),
    maxTier:tierBadInput.maxTier?'Maximum recipe voltage tier must be a whole number from 0 to 15.':maxTier===''?undefined:numberError(maxTier,'Maximum recipe voltage tier',0,15),
    timeBudget:pathSelection==='material'?numberError(timeBudget,'Search time per run (seconds)',.05,60,false):undefined,
    budgetMultiplier:pathSelection==='material'?numberError(budgetMultiplier,'Search work budget',1,10):undefined,
  }
  if(minTier!=='' && maxTier!=='' && !fieldErrors.minTier && !fieldErrors.maxTier && Number(minTier)>Number(maxTier)){
    fieldErrors.minTier='Minimum recipe voltage tier must not exceed the maximum tier.'
    fieldErrors.maxTier='Maximum recipe voltage tier must not be below the minimum tier.'
  }
  const validationErrors=Object.values(fieldErrors).filter(message=>message!==undefined)
  const validationProps=(field:keyof typeof fieldErrors,helpId?:string)=>({'aria-invalid':!!fieldErrors[field],'aria-describedby':[helpId,fieldErrors[field]?`trace-${field}-error`:undefined].filter(Boolean).join(' ') || undefined})
  const fieldError=(field:keyof typeof fieldErrors)=>fieldErrors[field] && <p id={`trace-${field}-error`} className="warning-text">{fieldErrors[field]}</p>
  const validTime=!numberError(timeBudget,'Search time per run (seconds)',.05,60,false)
  const activityActions=<>
    {jobs.closing && <p className="help">Closing the previous search before starting a new one.</p>}
    {submitted?.kind==='job' && !trace.data && (jobs.busy || activeJob?.status==='running') && <p className="help">Preparing the first retained result.</p>}
    {activeJob && <><button type="button" disabled={jobs.busy || activeJob.status!=='running'} onClick={()=>void jobs.pause()}>Stop search</button>
      <button type="button" disabled={jobs.busy || activeJob.status!=='paused' || !validTime} onClick={()=>void jobs.continueSearch(Number(timeBudget))}>Continue search</button>
      {activeJob.status==='paused' && <small>Results and unfinished work retained.</small>}
      {activeJob.status==='finished' && <small>Continue is unavailable. Submit a new search to change bounds or work budget.</small>}
    </>}
    {trace.error && (activeJob || submitted?.kind==='sync') && <button type="button" onClick={()=>{if(submitted?.kind==='sync')beginRequestClock('sync');trace.reload()}}>Try again</button>}
  </>
  const disabledReason=validationErrors.length>0?'Fix the highlighted Trace settings before searching.':jobs.busy || ((trace.loading || activeJob?.status==='running') && current)?'Searching paths. Wait for this request to finish.':!startId && !targetId?'Select a supplied start and a target from the search results.':!startId?'Select a supplied start from the search results.':!targetId?'Select a target from the search results.':!ready?'Wait for both selected resources to load.':undefined
  const routeLabel=pathSelection==='material'?'Main material flow':pathSelection==='diverse'?'Diverse routes':'Fewest steps first'
  const customSearchLimits=[Number(depth)!==12,Number(maxProcesses)!==150,Number(maxPaths)!==8,Number(extraSteps)!==6,pathSelection==='material' && Number(timeBudget)!==5,pathSelection==='material' && budgetMultiplier!==1].filter(Boolean).length
  const materialSummary=[required.length>0?`${required.length} required`:null,excluded.length>0?`${excluded.length} excluded`:null,excludedGroups.length>0?`${excludedGroups.length} excluded groups`:null,terminalArtifactPolicy==='direct_targets_only'?'Tools: direct targets only':null].filter(Boolean).join(' · ') || 'No material filters'
  const voltageSummary=minTier!=='' || maxTier!==''?`Tiers ${minTier || '0'}–${maxTier || '15'} · Unknown ${unknownTierPolicy==='include'?'included':'excluded'}`:unknownTierPolicy==='include'?'Any tier · Unknown included':'Any tier'
  return <section className="trace-workspace"><div className="panel-heading"><div><h2>Trace production paths</h2><p>Find recipe paths from a supplied resource to a target.</p></div></div><form noValidate onSubmit={event=>{event.preventDefault()
      const minBad=(event.currentTarget.elements.namedItem('minTier') as HTMLInputElement).validity.badInput
      const maxBad=(event.currentTarget.elements.namedItem('maxTier') as HTMLInputElement).validity.badInput
      setTierBadInput({minTier:minBad,maxTier:maxBad})
      if(minBad || maxBad || !ready || disabledReason)return
      beginRequestClock(pathSelection==='material'?'job':'sync')
      if(pathSelection==='material'){
        if(submitted?.kind!=='job')setSubmitted({url:currentUrl,kind:'job'})
        void jobs.start({start_id:startId,target_id:targetId,max_depth:Number(depth),max_processes:Number(maxProcesses),max_paths:Number(maxPaths),max_extra_steps:Number(extraSteps),path_selection:'material',terminal_artifact_policy:terminalArtifactPolicy,required_resource_ids:required,excluded_resource_ids:excluded,excluded_group_ids:excludedGroups,min_tier:minTier===''?undefined:Number(minTier),max_tier:maxTier===''?undefined:Number(maxTier),unknown_tier_policy:unknownTierPolicy,view:'compact',time_budget_seconds:Number(timeBudget),budget_multiplier:budgetMultiplier}).then(accepted=>{finishRequestClock(!accepted);if(accepted)setSubmitted({url:currentUrl,kind:'job'})})
      }else{
        void jobs.close().then(closed=>{if(!closed)return;if(current && submitted?.kind==='sync')synchronous.reload();else setSubmitted({url:currentUrl,kind:'sync'})})
      }
    }}>
    <div className="trace-endpoints"><ResourcePicker label="Supplied start resource" selectedId={startId} onSelect={setStartId} onResolve={setResolvedStart}/><ResourcePicker label="Target resource" selectedId={targetId} onSelect={setTargetId} onResolve={setResolvedTarget}/></div>
    {validationErrors.length>0 && <section className="notice error" role="region" aria-label="Trace setting errors" aria-live="polite"><strong>Check {validationErrors.length} Trace {validationErrors.length===1?'setting':'settings'}</strong><ul>{validationErrors.map(message=><li key={message}>{message}</li>)}</ul></section>}
    <div className="trace-search-action"><ActionHint id="trace-action-hint" reason={disabledReason} ready="Ready to find paths between the selected resources."/><button aria-describedby="trace-action-hint" className="primary" disabled={!!disabledReason}>Trace dependencies</button></div>
    <details className="trace-settings"><summary><span>Materials and intermediates</span><small>{materialSummary}</small></summary>
      <p className="help">Select a material, then Add. Filters apply to intermediates, not tools, presence requirements or co-products.</p>
      <div className="intermediate-filters"><IntermediateFilter label="Required" ids={required} onChange={setRequired}/><IntermediateFilter label="Excluded" ids={excluded} onChange={setExcluded}/></div>
      <ExcludedGroupFilter ids={excludedGroups} onChange={setExcludedGroups}/>
      <div className="trace-setting"><label title="Recognizes captured Tinkers and GT tools and parts, including turbine rotors and GGFab single-use tools.">Tools and parts in paths<select aria-describedby="trace-tools-help" value={terminalArtifactPolicy} onChange={event=>setTerminalArtifactPolicy(event.target.value)}><option value="allow">Allow intermediates</option><option value="direct_targets_only">Direct targets only</option></select></label><p id="trace-tools-help" className="help">Direct targets only blocks paths through recognized tools and parts, including single-use tools. Direct crafting and required cofeeds remain available.</p></div>
    </details>
    <details className="trace-settings"><summary><span>Recipe voltage limits</span><small>{voltageSummary}</small></summary>
      <p className="help">Filter by recipe voltage tier, not full machine capability.</p>
      <div className="tier-controls"><div><label>Minimum recipe voltage tier<input {...validationProps('minTier')} name="minTier" type="number" min="0" max="15" value={minTier} placeholder="Any" onInput={event=>readTierValidity('minTier',event.currentTarget)} onChange={event=>{setMinTier(event.target.value);readTierValidity('minTier',event.target)}}/></label>{fieldError('minTier')}</div><div><label>Maximum recipe voltage tier<input {...validationProps('maxTier')} name="maxTier" type="number" min="0" max="15" value={maxTier} placeholder="Any" onInput={event=>readTierValidity('maxTier',event.currentTarget)} onChange={event=>{setMaxTier(event.target.value);readTierValidity('maxTier',event.target)}}/></label>{fieldError('maxTier')}</div><label>Unknown recipe voltage<select value={unknownTierPolicy} onChange={event=>setUnknownTierPolicy(event.target.value)}><option value="exclude">Exclude when filtering tiers</option><option value="include">Include unresolved tiers</option></select></label></div>
    </details>
    <details className="trace-settings"><summary><span>Search strategy and budgets</span><small>{routeLabel}{customSearchLimits>0?` · ${customSearchLimits} custom ${customSearchLimits===1?'limit':'limits'}`:''}</small></summary>
      <div className="trace-setting"><label>Route selection<select aria-describedby="trace-strategy-help" value={pathSelection} onChange={event=>setPathSelection(event.target.value)}><option value="diverse">Diverse routes</option><option value="material">Main material flow</option><option value="shortest">Fewest steps first</option></select></label><p id="trace-strategy-help" className="help">{pathSelection==='material'?'Follow native material continuity and target ingredient branches. Recipe variants are representative. Side inputs need external supplies.':pathSelection==='diverse'?'Spread routes across target ingredients, including longer alternatives.':'Show the shortest qualifying paths first.'}</p></div>
      <div className="trace-settings-grid">
        <div><label>Maximum depth<input {...validationProps('depth','trace-depth-help')} type="number" min="1" max="64" value={depth} onChange={event=>setDepth(event.target.value)} required/></label>{fieldError('depth')}<p id="trace-depth-help" className="help">Recipes per path.</p></div>
        <div><label>Included recipe limit<input {...validationProps('maxProcesses','trace-recipes-help')} type="number" min="1" max="5000" value={maxProcesses} onChange={event=>setMaxProcesses(event.target.value)} required/></label>{fieldError('maxProcesses')}<p id="trace-recipes-help" className="help">Unique recipes in the combined map.</p></div>
        <div><label>Paths<input {...validationProps('maxPaths','trace-paths-help')} type="number" min="1" max="100" value={maxPaths} onChange={event=>setMaxPaths(event.target.value)} required/></label>{fieldError('maxPaths')}<p id="trace-paths-help" className="help">Maximum alternatives to retain.</p></div>
        <div><label>Additional steps<input {...validationProps('extraSteps','trace-detour-help')} type="number" min="0" max="64" value={extraSteps} onChange={event=>setExtraSteps(event.target.value)} required/></label>{fieldError('extraSteps')}<p id="trace-detour-help" className="help">Detour beyond the shortest qualifying path.</p></div>
      </div>
      {pathSelection==='material' && <><div className="trace-settings-grid">
        <div><label>Search time per run (seconds)<input {...validationProps('timeBudget','trace-time-help')} type="number" min=".05" max="60" step="any" value={timeBudget} onChange={event=>setTimeBudget(event.target.value)} required/></label>{fieldError('timeBudget')}<p id="trace-time-help" className="help">Time allowed for each run or continuation.</p></div>
        <div><label>Search work budget<select {...validationProps('budgetMultiplier','trace-work-help')} value={budgetMultiplier} onChange={event=>setBudgetMultiplier(Number(event.target.value))}>{Array.from({length:10},(_,index)=><option key={index+1} value={index+1}>{index+1}×</option>)}</select></label>{fieldError('budgetMultiplier')}<p id="trace-work-help" className="help">Choose before starting a new search.</p></div>
      </div><p className="help">Results appear while searching. Stop retains results and unfinished work. Continue resumes the same search.</p></>}
    </details>
  </form>
  {current && pathOrdering?.changed && (pathOrdering.policy==='cutter_consumed_item_first' || (!pathOrdering.acquisition_changed && pathOrdering.cutter_preference?.changed)) && <p className="help">For comparable Cutter recipes, paths through the consumed item are shown first. Fluid routes remain available.</p>}
  {current && pathOrdering?.policy==='native_acquisition_after_retained_alternatives' && pathOrdering.changed && pathOrdering.acquisition_changed && <p className="help">Space Mining acquisition paths are shown after alternatives already found in this search.</p>}
  {current && terminalArtifacts?.policy==='direct_targets_only' && terminalArtifacts.endpoint_compatibility==='incompatible' && <p className="notice" role="status">The selected start is a tool or part. Direct targets only won't use it to make other products. Select Allow intermediates for unrestricted path inspection.</p>}
  {current && terminalArtifacts?.policy==='direct_targets_only' && terminalArtifacts.recognition_status==='partial' && <p className="notice" role="status">Tool and part recognition is incomplete for this search: {terminalArtifacts.unknown_resources.toLocaleString()} inspected resources lack usable captured class evidence. Direct-target restrictions apply only to recognized tools and parts.</p>}
  {url && !current && <p className="notice">Settings changed. The displayed result uses the submitted settings. Submit a new search to apply these changes.</p>}
  {!trace.data && activity && <TraceActivity activity={activity}>{activityActions}</TraceActivity>}
  {trace.data && <TraceView key={activeJob?.job_id??url??undefined} activity={activity} activityActions={activityActions} boardId={activeJob?.job_id} jobStatus={activeJob?.status} resultRevision={activeJob?.result_revision} trace={trace.data} onSelect={onSelect} onUseStart={setStartId} onUseTarget={setTargetId} tierOptions={trace.data.tier_filter??{unknown_tier_policy:'exclude'}}/>}
  </section>
}
