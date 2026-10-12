import { useState } from 'react'
import type { Process,Resource,Single,TierOptions } from './api'
import { query,useRequest } from './api'
import { Badge,JsonData,ProcessDetail,RequestState,ResourceRef } from './Details'
import { ResourcePicker } from './ResourcePicker'
import { LedgerDetails,QuantityList,quantity } from './AccountingDetails'
import type { Ledger,Quantities,Rational } from './AccountingDetails'

interface LoopWitness {
  steps:{process_id:string;runs:Rational}[];resource_ids:string[];classification:string;return_ratio:Rational
  ledger:Ledger;required_start_stock:Quantities;external_consumption:Quantities;autonomous:boolean
  chemical_balance:{status:string;element_inputs:Quantities;element_outputs:Quantities;element_delta:Quantities;classification:string;unsupported:unknown[]}
}
interface LoopReport {snapshot_id:string;status:string;yield_mode:'guaranteed'|'expected';search:unknown;limit_reasons:string[];unsupported:unknown[];witnesses:LoopWitness[]}
export function LoopAuditPanel({startId,tierOptions,resources,onSelect}: {startId:string;tierOptions?:TierOptions;resources:ReadonlyMap<string,Resource>;onSelect:(id:string)=>void}) {
  const [start,setStart]=useState(startId)
  const [resolved,setResolved]=useState('')
  const [kind,setKind]=useState('any')
  const [chemicalKind,setChemicalKind]=useState('any')
  const [yieldMode,setYieldMode]=useState('guaranteed')
  const [depth,setDepth]=useState(6)
  const [paths,setPaths]=useState(5)
  const [url,setUrl]=useState<string|null>(null)
  const [selected,setSelected]=useState(0)
  const [processId,setProcessId]=useState<string|null>(null)
  const request=useRequest<LoopReport>(url)
  const process=useRequest<Single<Process>>(processId?query(`processes/${encodeURIComponent(processId)}`):null)
  const currentUrl=query('loops',{start_id:start,kind,chemical_kind:chemicalKind,yield_mode:yieldMode,max_depth:depth,max_processes:200,max_paths:paths,max_states:5000,...tierOptions})
  const current=url===currentUrl
  const witness=current?request.data?.witnesses[selected]:undefined
  return <section className="loop-audit" aria-label="Bounded loop audit"><h3>Audit material return and chemical balance</h3><p className="help">A gaining material return can consume external reagents. Chemical balance is a separate source-backed check. Material autonomy does not mean self-powered or machine-condition-free execution.</p>
    <form onSubmit={event=>{event.preventDefault();setSelected(0);setProcessId(null);if(current)request.reload();else setUrl(currentUrl)}}><div className="trace-controls"><ResourcePicker label="Loop start resource" selectedId={start} onSelect={setStart} onResolve={setResolved}/><label>Material return<select value={kind} onChange={event=>setKind(event.target.value)}>{['any','gaining','lossy','conserving'].map(value=><option key={value} value={value}>{value}</option>)}</select></label><label>Chemical balance<select value={chemicalKind} onChange={event=>setChemicalKind(event.target.value)}>{['any','balanced','gaining','lossy','mixed','unsupported'].map(value=><option key={value} value={value}>{value}</option>)}</select></label><label>Loop yield mode<select value={yieldMode} onChange={event=>setYieldMode(event.target.value)}><option value="guaranteed">Guaranteed</option><option value="expected">Expected average</option></select></label><label>Loop maximum depth<input type="number" min="1" max="20" value={depth} onChange={event=>setDepth(Number(event.target.value))}/></label><label>Loop witnesses<input type="number" min="1" max="100" value={paths} onChange={event=>setPaths(Number(event.target.value))}/></label></div><button disabled={!start || start!==resolved || request.loading}>Run bounded loop audit</button></form>
    {url && !current && <p className="notice">Loop selections changed. Run the audit again to use these settings.</p>}{current && <RequestState {...request} retry={request.reload}/>}
    {current && request.data && <><Badge tone={request.data.status==='complete'?'good':'warning'}>{request.data.status}</Badge><Badge>{request.data.yield_mode} yields</Badge>{request.data.limit_reasons.length>0 && <p className="warning-text">Bounded audit: {request.data.limit_reasons.join(', ')}</p>}
      {request.data.witnesses.length===0 ? <p>No matching loop witness was established within this scope.</p> : <label>Loop witness<select value={selected} onChange={event=>{setSelected(Number(event.target.value));setProcessId(null)}}>{request.data.witnesses.map((item,index)=><option key={index} value={index}>Loop {index+1} · Material {item.classification} · Chemistry {item.chemical_balance.classification}</option>)}</select></label>}
      {witness && <section className="loop-witness"><h4>Selected loop witness</h4><dl className="metrics"><div><dt>Material return</dt><dd>{witness.classification}</dd></div><div><dt>Return ratio</dt><dd>{quantity(witness.return_ratio)}</dd></div><div><dt>Material net closure</dt><dd>{witness.autonomous?'autonomous':Object.values(witness.external_consumption).some(amount=>amount.numerator>0)?'external consumption required':Object.values(witness.ledger.net).some(amount=>amount.numerator<0)?'net resource replenishment required':'autonomy unverified'}</dd></div><div><dt>Chemical balance</dt><dd>{witness.chemical_balance.classification} · {witness.chemical_balance.status}</dd></div></dl><ol>{witness.steps.map((step,index)=><li key={index}><button onClick={()=>setProcessId(step.process_id)}>{step.process_id}</button> · Runs {quantity(step.runs)}{witness.resource_ids[index+1] && <span> → <ResourceRef id={witness.resource_ids[index+1]} resources={resources} onSelect={onSelect}/></span>}</li>)}</ol>
        <QuantityList values={witness.required_start_stock} label="Loop starting stock" resources={resources} onSelect={onSelect}/><QuantityList values={witness.external_consumption} label="Loop external consumption" resources={resources} onSelect={onSelect}/><LedgerDetails ledger={witness.ledger} resources={resources} onSelect={onSelect}/><JsonData label="Chemical element balance and unsupported scope" value={witness.chemical_balance}/>
        {processId && <><RequestState {...process} retry={process.reload}/>{process.data && <ProcessDetail process={process.data.item} resources={resources} onSelect={onSelect}/>}</>}
      </section>}
      <JsonData label="Loop search bounds and unsupported mechanics" value={{search:request.data.search,unsupported:request.data.unsupported}}/>
    </>}
  </section>
}
