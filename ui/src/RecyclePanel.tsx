import { useState } from 'react'
import type { Resource, TierOptions, Trace } from './api'
import { query, useRequest } from './api'
import { ActionHint, Badge, JsonData, RequestState, ResourceRef } from './Details'
import { ResourcePicker } from './ResourcePicker'
import { LedgerDetails, quantity,UnsupportedFacts } from './AccountingDetails'
import type { Ledger, Rational, Startup } from './AccountingDetails'
import { InputSelections } from './InputSelections'
import type { InputSelectionMap } from './InputSelections'

export interface RecycleAlternative {
  path:Trace['paths'][number];status:'complete'|'unsupported';ledger:Ledger|null;startup:Startup|null
  combined_ledger:Ledger|null;combined_startup:Startup|null
  selected_inputs?:InputSelectionMap
  recovery:{resource_id:string;main_consumed:Rational;side_produced:Rational;side_consumed:Rational;net_returned:Rational;main_input_returned_percent:Rational;usable_returned:Rational;surplus_returned:Rational}|null
  external_inputs:{resource_id:string;amount:Rational}[];unsupported:unknown[]
}
export interface RecyclingPlan {
  snapshot_id:string;status:string;main_path:Trace['paths'][number];byproduct_id:string;return_id:string;yield_mode:'guaranteed'|'expected'
  main_plan:{status:string;ledger:Ledger|null;startup:Startup|null;byproduct_available:Rational|null;return_consumed:Rational|null;unsupported:unknown[];selected_inputs?:InputSelectionMap}
  alternatives:RecycleAlternative[];secondary_trace:Trace;limitations:unknown[]
}
export function RecyclePanel({trace,ownerId,byproductId,tierOptions,onSelect,onOverlay}: {trace:Trace;ownerId:string;byproductId:string;tierOptions?:TierOptions;onSelect:(id:string)=>void;onOverlay:(plan:RecyclingPlan,index:number)=>void}) {
  const owner=trace.processes.find(process=>process.id===ownerId)!
  const firstPath=Math.max(0,trace.paths.findIndex(path=>path.process_ids.includes(ownerId)))
  const [pathIndex,setPathIndex]=useState(firstPath)
  const defaultReturn=owner.inputs.filter(slot=>slot.role==='consume').flatMap(slot=>slot.choices).find(choice=>choice.resource_id!==null)?.resource_id ?? trace.start_id
  const [returnId,setReturnId]=useState(defaultReturn)
  const [resolvedReturn,setResolvedReturn]=useState('')
  const [runs,setRuns]=useState(1)
  const [depth,setDepth]=useState(12)
  const [maxProcesses,setMaxProcesses]=useState(100)
  const [maxPaths,setMaxPaths]=useState(3)
  const [extraSteps,setExtraSteps]=useState(2)
  const [yieldMode,setYieldMode]=useState<'guaranteed'|'expected'>('guaranteed')
  const [selections,setSelections]=useState('{}')
  const [error,setError]=useState('')
  const [submitted,setSubmitted]=useState<Record<string,unknown>|undefined>()
  const request=useRequest<RecyclingPlan>(submitted?query('recycling-plan'):null,submitted)
  const resources=new Map(trace.resources.map(resource=>[resource.id,resource]))
  const [alternative,setAlternative]=useState(0)
  let selectedInputs:InputSelectionMap={}
  let selectionsValid=true
  try{selectedInputs=JSON.parse(selections);if(selectedInputs===null || Array.isArray(selectedInputs) || typeof selectedInputs!=='object')selectionsValid=false}catch{selectionsValid=false}
  const choicesResolved=selectionsValid && Object.values(selectedInputs).every(slots=>slots!==null && typeof slots==='object' && Object.values(slots).every(value=>value!==null && typeof value==='object' && typeof value.resource_id==='string' && value.resource_id.length>0))
  const parameters={main_path:trace.paths[pathIndex],byproduct_id:byproductId,return_id:returnId,main_runs:runs,yield_mode:yieldMode,selections:selectedInputs,max_depth:depth,max_processes:maxProcesses,max_paths:maxPaths,max_extra_steps:extraSteps,...tierOptions}
  const disabledReason=request.loading?'Searching return paths and accounting for the selected recipes.':!returnId?'Select a returned resource from the search results.':resolvedReturn!==returnId?'Wait for the selected returned resource to load.':!choicesResolved?'Resolve the input choices below, or correct the advanced selections JSON.':undefined
  const current=!!submitted && selectionsValid && JSON.stringify(submitted)===JSON.stringify(parameters)
  const inputProcesses=[...new Map([...trace.processes.filter(process=>trace.paths[pathIndex].process_ids.includes(process.id)),...(request.data?.secondary_trace.processes??[])].map(process=>[process.id,process])).values()]
  const inputResources=new Map([...resources,...(request.data?.secondary_trace.resources??[]).map(resource=>[resource.id,resource] as const)])
  const automatic={...(request.data?.main_plan.selected_inputs??{}),...(request.data?.alternatives[alternative]?.selected_inputs??{})}
  const shownSelections:InputSelectionMap={...automatic}
  if(selectionsValid)for(const [id,slots] of Object.entries(selectedInputs))shownSelections[id]={...automatic[id],...slots}
  function changeSelection(processId:string,slot:string,value:{choice_index:number;resource_id:string}){
    const next=selectionsValid?selectedInputs:{}
    setSelections(JSON.stringify({...next,[processId]:{...next[processId],[slot]:value}},null,2))
  }
  function submit(){
    try {
      const selected=JSON.parse(selections)
      if(selected===null || Array.isArray(selected) || typeof selected!=='object')throw new Error('Input selections must be a JSON object')
      const body={...parameters,selections:selected}
      setError('');setAlternative(0);setSubmitted(body)
    }catch(cause){setError(cause instanceof Error?cause.message:String(cause))}
  }
  return <section className="recycle-panel" aria-label="Byproduct recycling plan"><h3>Recycle a recipe output</h3><p className="help">Find a way to turn this output back into an ingredient used by the main path. For example, recover a consumed chemical from a byproduct. Select what should return, then inspect the recovery percentage and any extra supplies needed.</p><p>Output from <strong>{owner.display_name || owner.id}</strong>: <ResourceRef id={byproductId} resources={resources} onSelect={onSelect}/></p>
    <form onSubmit={event=>{event.preventDefault();submit()}}><div className="trace-controls"><label>Main path<select value={pathIndex} onChange={event=>{setPathIndex(Number(event.target.value));setSubmitted(undefined)}}>{trace.paths.map((path,index)=>path.process_ids.includes(ownerId)&&<option key={index} value={index}>Path {index+1} · {path.process_ids.length} steps</option>)}</select></label><ResourcePicker label="Returned resource" selectedId={returnId} onSelect={id=>{setReturnId(id);setSubmitted(undefined)}} onResolve={setResolvedReturn}/><label>Main path runs<input type="number" min="1" step="1" value={runs} onChange={event=>{setRuns(Number(event.target.value));setSubmitted(undefined)}} required/></label><label>Yield accounting<select value={yieldMode} onChange={event=>{setYieldMode(event.target.value as typeof yieldMode);setSubmitted(undefined)}}><option value="guaranteed">Guaranteed yields</option><option value="expected">Expected yields</option></select></label></div>
    <details><summary>Advanced: Secondary path bounds</summary><p className="help">Depth limits recipes in each return path. Process count limits the combined result, path count limits alternatives, and additional steps limit detours beyond the shortest path.</p><div className="trace-controls"><label>Return maximum depth<input type="number" min="1" max="64" value={depth} onChange={event=>setDepth(Number(event.target.value))}/></label><label>Return maximum processes<input type="number" min="1" max="5000" value={maxProcesses} onChange={event=>setMaxProcesses(Number(event.target.value))}/></label><label>Return path count<input type="number" min="1" max="100" value={maxPaths} onChange={event=>setMaxPaths(Number(event.target.value))}/></label><label>Return additional steps<input type="number" min="0" max="64" value={extraSteps} onChange={event=>setExtraSteps(Number(event.target.value))}/></label></div></details>
    <details><summary>Explicit input choices</summary><p className="help">Start with automatic choices. If accounting reports an unresolved slot, open that slot and select the concrete input, then run again.</p><InputSelections processes={inputProcesses} selections={shownSelections} resources={inputResources} onChange={changeSelection}/><details><summary>Advanced selections JSON</summary><label>Input selections JSON<textarea value={selections} onChange={event=>setSelections(event.target.value)} spellCheck={false}/></label></details></details><ActionHint id="recycle-action-hint" reason={disabledReason} ready="Ready to search return paths and inspect recovery."/><button aria-describedby="recycle-action-hint" className="primary" disabled={!!disabledReason}>Inspect return paths and recovery</button></form>
    {error && <p role="alert">{error}</p>}<RequestState {...request} retry={request.reload}/>
    {submitted && !current && <p className="notice">Input choices or plan settings changed. Resubmit before using the quantitative result.</p>}
    {current && request.data && <><div className="detail-title"><h4>Main path accounting</h4><Badge tone={request.data.status==='complete'?'good':'warning'}>{request.data.status}</Badge></div><p>Available byproduct: {quantity(request.data.main_plan.byproduct_available)} · Consumed return resource: {quantity(request.data.main_plan.return_consumed)}</p><UnsupportedFacts items={request.data.main_plan.unsupported} label="Unresolved main inputs or mechanics"/><LedgerDetails ledger={request.data.main_plan.ledger} startup={request.data.main_plan.startup} resources={resources} onSelect={onSelect}/>
      {request.data.alternatives.length===0 ? <div><p>No supported return plan was established within these bounds.</p><p className="help">Check unresolved inputs, try another returned resource, or increase the secondary path bounds. This does not prove recycling is impossible.</p></div> : <><label>Secondary return path<select value={alternative} onChange={event=>setAlternative(Number(event.target.value))}>{request.data.alternatives.map((item,index)=><option key={index} value={index}>Return path {index+1} · {item.path.process_ids.length} steps · {item.status}</option>)}</select></label><button onClick={()=>onOverlay(request.data!,alternative)}>Show connected return path in map</button><RecoveryDetails plan={request.data.alternatives[alternative]} resources={new Map([...resources,...request.data.secondary_trace.resources.map(resource=>[resource.id,resource] as const)])} onSelect={onSelect}/></>}
      <p className="help">Secondary search limits: {request.data.secondary_trace.limit_reasons.join(', ') || 'none reached'}.</p><UnsupportedFacts label="Recycling scope and limitations" items={request.data.limitations}/><JsonData label="Full recycling plan" value={request.data}/></>}
  </section>
}
function RecoveryDetails({plan,resources,onSelect}: {plan:RecycleAlternative;resources:ReadonlyMap<string,Resource>;onSelect:(id:string)=>void}) {
  return <section className="recovery-detail"><h4>Secondary recovery</h4><Badge tone={plan.status==='complete'?'good':'warning'}>{plan.status}</Badge>
    {plan.recovery ? <><ResourceRef id={plan.recovery.resource_id} resources={resources} onSelect={onSelect}/><dl className="metrics"><div><dt>Main input returned</dt><dd>{quantity(plan.recovery.main_input_returned_percent)}%</dd></div><div><dt>Net returned</dt><dd>{quantity(plan.recovery.net_returned)}</dd></div><div><dt>Usable returned</dt><dd>{quantity(plan.recovery.usable_returned)}</dd></div><div><dt>Surplus returned</dt><dd>{quantity(plan.recovery.surplus_returned)}</dd></div></dl></> : <p className="warning-text">Recovery is unknown for this unsupported plan.</p>}
    <h4>Additional external inputs</h4>{plan.external_inputs.length===0?<p>None recorded</p>:<ul>{plan.external_inputs.map(input=><li key={input.resource_id}><ResourceRef id={input.resource_id} resources={resources} onSelect={onSelect}/> {quantity(input.amount)}</li>)}</ul>}
    <LedgerDetails ledger={plan.combined_ledger} startup={plan.combined_startup} resources={resources} onSelect={onSelect}/>
    <UnsupportedFacts label="Unsupported secondary mechanics" items={plan.unsupported}/>
  </section>
}
