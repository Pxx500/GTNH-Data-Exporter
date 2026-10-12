import {useCallback,useState} from 'react'
import type {BoundaryProfile,NetworkReport,Page,Process} from './api'
import {query,useRequest} from './api'
import {BoundaryProfileEditor,BoundaryProfileSelector} from './BoundaryProfileEditor'
import {InputSelections} from './InputSelections'
import type {InputSelectionMap} from './InputSelections'
import {Badge,ProcessDetail,RequestState,ResourceRef} from './Details'
import {ResourcePicker} from './ResourcePicker'
import {ResourceSetEditor} from './ResourceSetEditor'
import {NetworkResult} from './NetworkResult'

const voltageNames=['ULV','LV','MV','HV','EV','IV','LuV','ZPM','UV','UHV','UEV','UIV','UMV','UXV','MAX','MAX+']

export function NetworkAnalysis({snapshotId,profile,onProfileChange,onSelect}:{snapshotId:string;profile?:BoundaryProfile;onProfileChange:(profile:BoundaryProfile|undefined)=>void;onSelect:(id:string)=>void}) {
  const [mode,setMode]=useState<'energy'|'basics'>('energy')
  const [target,setTarget]=useState('')
  const [targetResolved,setTargetResolved]=useState('')
  const [feed,setFeed]=useState('')
  const [feedResolved,setFeedResolved]=useState('')
  const [extraFeeds,setExtraFeeds]=useState<string[]>([])
  const [benchmark,setBenchmark]=useState('')
  const [benchmarkChoices,setBenchmarkChoices]=useState<InputSelectionMap>({})
  const [amount,setAmount]=useState(1)
  const [objective,setObjective]=useState('recipe_runs')
  const [yieldMode,setYieldMode]=useState('guaranteed')
  const [editing,setEditing]=useState(false)
  const [newProfile,setNewProfile]=useState(false)
  const [profileRevision,setProfileRevision]=useState(0)
  const [depth,setDepth]=useState(8)
  const [processes,setProcesses]=useState(200)
  const [variants,setVariants]=useState(128)
  const [resourceLimit,setResourceLimit]=useState(512)
  const [solutions,setSolutions]=useState(8)
  const [solves,setSolves]=useState(24)
  const [seconds,setSeconds]=useState(10)
  const [columns,setColumns]=useState(128)
  const [rows,setRows]=useState(512)
  const [maxTier,setMaxTier]=useState('')
  const [minTier,setMinTier]=useState('')
  const [unknownTier,setUnknownTier]=useState('exclude')
  const [stock,setStock]=useState<Record<string,number>>({})
  const [submitted,setSubmitted]=useState<{mode:string;body:Record<string,unknown>}|null>(null)
  const request=useRequest<NetworkReport>(submitted?query(submitted.mode==='energy'?'energy-audit':'plan-to-bases'):null,submitted?.body)
  const benchmarks=useRequest<Page<Process>>(mode==='energy' && feed && target?query('processes',{input_id:feed,output_id:target,limit:50}):null)
  const chosen=benchmarks.data?.items.find(process=>process.id===benchmark)
  const reset=()=>setSubmitted(null)
  const changeProfile=(value:BoundaryProfile|undefined)=>{onProfileChange(value);reset()}
  const saved=useCallback((value:BoundaryProfile|null)=>{onProfileChange(value??undefined);setProfileRevision(revision=>revision+1);setEditing(false);setSubmitted(null)},[onProfileChange])
  const common={target_id:target,target_amount:amount,yield_mode:yieldMode,max_depth:depth,max_processes:processes,max_variants:variants,max_resources:resourceLimit,max_solutions:solutions,max_solves:solves,max_columns:columns,max_rows:rows,timeout_seconds:seconds,start_stock:Object.keys(stock).length===0?null:stock,min_tier:minTier===''?null:Number(minTier),max_tier:maxTier===''?null:Number(maxTier),unknown_tier_policy:unknownTier}
  const body=mode==='energy'?{...common,primary_feed_id:feed,benchmark_process_id:benchmark,allowed_feed_ids:[...new Set([feed,...extraFeeds])],profile_id:profile?.id??null,benchmark_selections:benchmarkChoices[benchmark]??{}}:{...common,profile_id:profile?.id,objective}
  const current=!!submitted && submitted.mode===mode && JSON.stringify(submitted.body)===JSON.stringify(body)
  return <section className="analysis-workspace"><div className="detail-tabs" role="group" aria-label="Analysis mode"><button aria-pressed={mode==='energy'} onClick={()=>{setMode('energy');reset()}}>Energy benchmark</button><button aria-pressed={mode==='basics'} onClick={()=>{setMode('basics');reset()}}>Target from basics</button></div>
    <h2>{mode==='energy'?'Production energy benchmark':'Target from basic resources'}</h2><p className="help">Solve whole stoichiometric recipe networks, including recycling. Results remain bounded by captured data and selected variants.</p>
    <BoundaryProfileSelector profile={profile} label="Analysis boundary profile" onSelect={changeProfile} revision={profileRevision}/><p className="help">{mode==='energy'?'Profile basics are not implicit energy feeds. This mode uses the profile only for its exclusion scope.':'The selected profile declares which resources may enter as external basic feeds.'}</p>
    {profile && <details open={mode==='basics'}><summary>Declared basic resources ({profile.base_resource_ids.length})</summary><ul className="filter-tags">{profile.base_resource_ids.map(id=><li key={id}><ResourceRef id={id}/><Badge tone="presence">Basic resource</Badge></li>)}</ul></details>}
    <div className="button-stack"><button onClick={()=>{setNewProfile(true);setEditing(true)}}>Create boundary profile</button>{profile && <button onClick={()=>{setNewProfile(false);setEditing(true)}}>Edit boundary profile</button>}</div>
    {editing && <BoundaryProfileEditor key={newProfile?'new':`${profile?.id}:${profile?.revision}`} profile={newProfile?undefined:profile} snapshotId={snapshotId} onSaved={saved}/>}
    <form onSubmit={event=>{event.preventDefault();setSubmitted({mode,body})}}><div className="analysis-controls">
      {mode==='energy' && <ResourcePicker label="Primary feed (e.g. Water)" selectedId={feed} onSelect={id=>{setFeed(id);setBenchmark('');reset()}} onResolve={setFeedResolved} profileId={profile?.id} basicResourceIds={profile?.base_resource_ids}/>}
      <ResourcePicker label={mode==='energy'?'Target product (e.g. Hydrogen)':'Target product'} selectedId={target} onSelect={id=>{setTarget(id);setBenchmark('');reset()}} onResolve={setTargetResolved} profileId={profile?.id} basicResourceIds={profile?.base_resource_ids}/>
      <label>Target quantity<input type="number" min="1" step="1" value={amount} onChange={event=>setAmount(Number(event.target.value))} required/></label><label>Network yield mode<select value={yieldMode} onChange={event=>setYieldMode(event.target.value)}><option value="guaranteed">Guaranteed</option><option value="expected">Expected average</option></select></label>
      {mode==='basics' && <label>Network objective<select value={objective} onChange={event=>setObjective(event.target.value)}><option value="recipe_runs">Fewest recipe runs</option><option value="nominal_eu">Nominal recipe EU</option></select></label>}
    </div>{mode==='energy' && <><ResourceSetEditor label="Additional allowed feeds" ids={extraFeeds} onChange={setExtraFeeds} profileId={profile?.id}/><label>Native benchmark recipe<select value={benchmark} onChange={event=>{setBenchmark(event.target.value);reset()}}><option value="">Choose a captured producer</option>{benchmarks.data?.items.map(process=><option key={process.id} value={process.id}>{process.display_name} · {process.id} · {process.eu_per_tick??'Unknown'} EU/t</option>)}</select></label><p className="help">Benchmark candidates are captured producer records. Dataset validates their matching, energy and selected profile scope.</p><RequestState {...benchmarks} retry={benchmarks.reload}/>{benchmarks.data && benchmarks.data.total>50 && <p className="help">First 50 benchmark candidates shown. Narrow the feed and target identity for others.</p>}{chosen && <details><summary>Benchmark recipe and concrete inputs</summary><ProcessDetail process={chosen}/><InputSelections processes={[chosen]} selections={benchmarkChoices} resources={new Map()} onChange={(pid,slot,value)=>setBenchmarkChoices({...benchmarkChoices,[pid]:{...benchmarkChoices[pid],[slot]:value}})}/></details>}</>}
    <details><summary>Network bounds and initial stock</summary><div className="analysis-controls"><NumberBound label="Candidate maximum depth" value={depth} maximum={20} onChange={setDepth}/><NumberBound label="Candidate maximum processes" value={processes} maximum={1000} onChange={setProcesses}/><NumberBound label="Candidate maximum variants" value={variants} maximum={512} onChange={setVariants}/><NumberBound label="Candidate maximum resources" value={resourceLimit} maximum={2000} onChange={setResourceLimit}/><NumberBound label="Maximum network solutions" value={solutions} maximum={100} onChange={setSolutions}/><NumberBound label="Maximum solver attempts" value={solves} maximum={100} onChange={setSolves}/><NumberBound label="Solver maximum columns" value={columns} maximum={512} onChange={setColumns}/><NumberBound label="Solver maximum rows" value={rows} maximum={4096} onChange={setRows}/><NumberBound label="Solver time limit (seconds)" value={seconds} maximum={30} onChange={setSeconds}/><label>Minimum network recipe voltage<select value={minTier} onChange={event=>setMinTier(event.target.value)}><option value="">Any captured tier</option>{voltageNames.map((name,tier)=><option key={tier} value={tier}>{tier} · {name}</option>)}</select></label><label>Maximum network recipe voltage<select value={maxTier} onChange={event=>setMaxTier(event.target.value)}><option value="">Any captured tier</option>{voltageNames.map((name,tier)=><option key={tier} value={tier}>{tier} · {name}</option>)}</select></label><label>Unknown network recipe voltage<select value={unknownTier} onChange={event=>setUnknownTier(event.target.value)}><option value="exclude">Exclude while tier filter is active</option><option value="include">Include unknown tiers</option></select></label></div>
      <ResourceSetEditor label="Declared initial stocks" ids={Object.keys(stock)} onChange={ids=>setStock(Object.fromEntries(ids.map(id=>[id,stock[id]??1])))}/>{Object.entries(stock).map(([id,value])=><label key={id}>Initial stock quantity for {id}<input type="number" min="0" step="1" value={value} onChange={event=>setStock({...stock,[id]:Number(event.target.value)})}/></label>)}<p className="help">Stock witnesses use a conservative declared batch order. They don't prove minimum scheduling stock or machine readiness. Recipe voltage is not machine capability.</p>
    </details><button className="primary" disabled={request.loading || !target || target!==targetResolved || (mode==='energy'? !chosen || !feed || feed!==feedResolved:!profile)}>Run {mode==='energy'?'energy audit':'basic-resource plan'}</button></form>
    <RequestState {...request} retry={request.reload}/>{submitted && !current && <p className="notice">Settings changed. Run the analysis again before using this result.</p>}{current && request.data && <NetworkResult key={JSON.stringify(submitted)} report={request.data} onSelect={onSelect}/>}
  </section>
}
function NumberBound({label,value,maximum,onChange}:{label:string;value:number;maximum:number;onChange:(value:number)=>void}) {return <label>{label}<input type="number" min="1" max={maximum} value={value} onChange={event=>onChange(Number(event.target.value))}/></label>}
