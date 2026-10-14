import {useCallback,useMemo,useState} from 'react'
import type {NetworkReport,NetworkWitnessReport} from './api'
import {Badge,JsonData,ProcessDetail,ResourceRef} from './Details'
import {LedgerDetails,QuantityList,quantity,UnsupportedFacts} from './AccountingDetails'
import {RecipeGraph} from './RecipeGraph'
import type {RecipeGraphData} from './RecipeGraph'
import {RecordInspector,ResourceInspector} from './RecordInspector'

export function NetworkResult({report,onSelect}:{report:NetworkReport;onSelect:(id:string)=>void}) {
  if('boundary' in report)return <section className="network-result" aria-label="Basic-resource boundary"><h3>Target is already a declared basic resource</h3><Badge tone="good">{report.status}</Badge><p>No production steps are needed inside this profile. Supply is assumed at the selected external boundary, not proven by captured acquisition.</p><QuantityList values={report.base_requirements} label="Required basic supplies" onSelect={onSelect}/><JsonData label="Declared basic boundary" value={report}/></section>
  return <NetworkWitness report={report} onSelect={onSelect}/>
}
function NetworkWitness({report,onSelect}:{report:NetworkWitnessReport;onSelect:(id:string)=>void}) {
  const [index,setIndex]=useState(0)
  const [inspected,setInspected]=useState<string|null>(null)
  const [resourceId,setResourceId]=useState<string|null>(null)
  const solution=report.solutions[index]
  const resources=useMemo(()=>new Map(report.discovery.resources.map(resource=>[resource.id,resource])),[report.discovery.resources])
  const graph=useMemo<RecipeGraphData>(()=>{
    const executions=solution?.executions??[]
    const connections:RecipeGraphData['connections']=[]
    for(const producer of executions)for(const consumer of executions)for(const [resourceId,amount] of Object.entries(producer.ledger.produced)){
      if(amount.numerator>0 && (consumer.ledger.consumed[resourceId]?.numerator??0)>0)connections.push({id:JSON.stringify([producer.variant_id,consumer.variant_id,resourceId]),source:producer.variant_id,target:consumer.variant_id,resourceId})
    }
    return {resources:report.discovery.resources,recipes:executions.map(execution=>({id:execution.variant_id,process:report.discovery.processes[execution.process_id],runs:execution.runs})),connections}
  },[solution,report.discovery])
  const inspect=useCallback((id:string)=>{setInspected(id);setResourceId(null)},[])
  const inspectResource=useCallback((id:string)=>{setResourceId(id);setInspected(null)},[])
  const execution=solution?.executions.find(item=>item.variant_id===inspected)
  return <section className="network-result" aria-label="Stoichiometric network result"><div className="detail-title"><h3>Bounded network result</h3><Badge tone={report.status==='complete'?'good':'warning'}>{report.status.replaceAll('_',' ')}</Badge></div>
    <p className="help">Optimization applies to discovered candidate variants. It does not establish a global optimum, machine execution or an inventory schedule. Graph links show shared consumed and produced resources, not allocated transport flows.</p>
    {(!report.discovery.coverage_complete || !report.search.complete) && <div className="notice warning"><strong>{report.solutions.length>0?'Candidate networks found, search is partial':'Search is partial, no verified network returned'}</strong><p>Only the discovered candidates were checked. Narrow the profile scope or increase the relevant Advanced bounds to examine more. Candidate variants and solver columns both limit the network size, so review the column limit when increasing variants. This does not establish a global best result or prove production is impossible.</p></div>}<p>Candidate discovery: {report.discovery.coverage_complete?'complete within this captured neighborhood':'partial or bounded'}. Solver enumeration: {report.search.complete?'finished within its bound':'partial or bounded'}.</p>
    {(report.discovery.limit_reasons.length>0 || report.search.limit_reasons.length>0) && <p className="notice warning">Limits: {[...report.discovery.limit_reasons,...report.search.limit_reasons].join(', ')}</p>}
    {report.benchmark && <section className="benchmark-result"><h4>Native benchmark at equal target quantity</h4><p>Runs {quantity(report.benchmark.runs)} · {quantity(report.benchmark.energy.total_eu,'decimal')} nominal EU · {quantity(report.benchmark.energy.eu_per_target,'decimal')} EU per target unit</p><QuantityList label="Benchmark co-feeds" values={report.benchmark.cofeeds} resources={resources} onSelect={inspectResource}/><QuantityList label="Benchmark co-products" values={report.benchmark.coproducts} resources={resources} onSelect={inspectResource}/><details><summary>Complete benchmark recipe</summary><ProcessDetail process={report.benchmark.process} resources={resources} onSelect={inspectResource}/><LedgerDetails ledger={report.benchmark.ledger} resources={resources} onSelect={inspectResource}/></details></section>}
    {report.solutions.length===0?<div><p>No verified solution was established within these captured candidates and bounds.</p><p className="help">Check allowed feeds or profile basics, exclusions and unresolved recipe inputs. If search reached a limit, raise that bound in Advanced settings. An empty result is not proof that the pack has no production route.</p></div>:<><label>Network solution<select value={index} onChange={event=>{setIndex(Number(event.target.value));setInspected(null);setResourceId(null)}}>{report.solutions.map((item,i)=><option key={i} value={i}>Solution {i+1} · {item.executions.length} recipe variants · {item.nominal_energy.status} energy</option>)}</select></label>
      <dl className="metrics"><div><dt>Exact ledger witness</dt><dd>{solution.witness_verified?'Verified':'Unverified'}</dd></div><div><dt>Nominal total energy</dt><dd>{quantity(solution.nominal_energy.total_eu,'decimal')} EU</dd></div><div><dt>Nominal energy per target</dt><dd>{quantity(solution.nominal_energy.eu_per_target,'decimal')} EU</dd></div><div><dt>Integer batch scale</dt><dd>{solution.integer_batch_scale.toLocaleString()}</dd></div>{solution.savings && <div><dt>Energy saving against benchmark</dt><dd>{solution.savings.status==='known'?`${quantity(solution.savings.percent,'decimal')}% · ${quantity(solution.savings.eu,'decimal')} EU`:'Unknown'}</dd></div>}</dl>
      <UnsupportedFacts label="Unknown nominal energy" items={solution.nominal_energy.unknown_processes}/><p className="help">Nominal EU excludes overclocking, machine efficiency, container handling and co-product credits. Expected yields don't establish available stock.</p>
      <div className={`trace-layout ${execution||resourceId?'has-inspector':''}`}><div className="free-recipe-graph" role="region" aria-label="Network recipe graph"><RecipeGraph graph={graph} highlight={null} inspect={inspect} inspectResource={inspectResource}/></div>{(execution||resourceId) && <RecordInspector onClose={()=>{setInspected(null);setResourceId(null)}}>{execution ? <><ProcessDetail process={report.discovery.processes[execution.process_id]} resources={resources} onSelect={inspectResource}/><h4>Resolved input choices</h4><ul>{Object.entries(execution.selections).map(([slot,choice])=><li key={slot}>Slot {Number(slot)+1} · Alternative {choice.choice_index+1} · <ResourceRef id={choice.resource_id} resources={resources} onSelect={inspectResource}/></li>)}</ul><LedgerDetails ledger={execution.ledger} resources={resources} onSelect={inspectResource}/></> : resourceId && <ResourceInspector key={resourceId} id={resourceId} resources={resources} onInspect={inspectResource} onOpenLibrary={onSelect}/>}</RecordInspector>}</div>
      <div className="balance-grid"><QuantityList label="Net external imports" values={solution.net_imports} resources={resources} onSelect={inspectResource}/><QuantityList label="Net co-products" values={solution.net_coproducts} resources={resources} onSelect={inspectResource}/></div>
      <LedgerDetails ledger={solution.ledger} startup={solution.startup} resources={resources} onSelect={inspectResource}/>{solution.base_boundary && <><strong>Basic-resource boundary: {solution.base_boundary.status.replaceAll('_',' ')}</strong><QuantityList label="Unresolved non-basic startup" values={solution.base_boundary.unresolved_startup} resources={resources} onSelect={inspectResource}/><p className="help">{solution.base_boundary.semantics}</p></>}
    </>}
    {!solution && resourceId && <RecordInspector onClose={()=>setResourceId(null)}><ResourceInspector key={resourceId} id={resourceId} resources={resources} onInspect={inspectResource} onOpenLibrary={onSelect}/></RecordInspector>}
    <JsonData label="Candidate coverage, exclusions and search" value={report.discovery}/><JsonData label="Full network result" value={report}/>
  </section>
}
