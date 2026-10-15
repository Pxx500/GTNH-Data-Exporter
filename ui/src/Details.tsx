import { useState } from 'react'
import type { Coverage, Environment, Group, Output, Process, ProcessInspection, Resource, Single, Source } from './api'
import { query, useRequest } from './api'

export function Badge({children, tone = ''}: {children: React.ReactNode; tone?: string}) {
  return <span className={`badge ${tone}`}>{children}</span>
}
export function JsonData({label, value}: {label: string; value: unknown}) {
  const [copyState,setCopyState]=useState('')
  const json=JSON.stringify(value,null,2)??'Unknown'
  async function copy(){
    try{await navigator.clipboard.writeText(json);setCopyState('JSON copied')}
    catch{setCopyState('Could not copy. Select the record text below and copy it.')}
  }
  return <details className="json-data"><summary>{label}</summary><button type="button" onClick={()=>void copy()}>Copy JSON</button>{copyState && <p role="status">{copyState}</p>}<pre tabIndex={0}>{json}</pre></details>
}
export function ConditionFacts({value,label='Conditions and research'}:{value:unknown;label?:string}) {
  function compact(data:unknown,parent=''):unknown {
    if(Array.isArray(data))return data.map(item=>compact(item,parent))
    if(data===null || typeof data!=='object')return data
    return Object.fromEntries(Object.entries(data as Record<string,unknown>).flatMap(([key,item])=>{
      const routine=(key==='enabled' && item===true)
        || (['fake','hidden','nbt_sensitive','requires_empty_outputs'].includes(key) && item===false)
        || (key==='native_special_value' && item===0)
        || (['native_description','special_items'].includes(key) && item===null)
      const implementation=['recipe_voltage_tier_source','recipe_voltage_tier_semantics'].includes(key)
        || (parent==='recipe_voltage' && ['source','semantics'].includes(key))
      if(routine || implementation)return []
      if(parent==='native_metadata' && key==='space_pumping' && item!==null && typeof item==='object' && !Array.isArray(item)){
        const pumping=item as Record<string,unknown>
        if(pumping.status==='captured_native_declaration' && pumping.quantity_scope==='selected_line_one_parallel_batch_one'){
          return [[key,{planet_selector:pumping.planet_type,gas_selector:pumping.gas_type,quantity_scope:'Nominal one line, one parallel, batch one',runtime_requirements:pumping.runtime_execution,environment_mapping:pumping.environment_mapping}]]
        }
      }
      const result=compact(item,key)
      if(result!==null && typeof result==='object' && Object.keys(result).length===0)return []
      return [[key,result]]
    }))
  }
  function facts(data:unknown):React.ReactNode {
    if(data===null)return 'Unknown'
    if(typeof data==='number')return data.toLocaleString()
    if(typeof data==='boolean')return data?'Yes':'No'
    if(Array.isArray(data))return <ul>{data.map((item,index)=><li key={index}>{facts(item)}</li>)}</ul>
    if(typeof data==='object')return <dl className="condition-facts">{Object.entries(data as Record<string,unknown>).map(([key,item])=><div key={key}><dt>{key.replaceAll('_',' ').replace(/^./,letter=>letter.toUpperCase())}</dt><dd>{facts(item)}</dd></div>)}</dl>
    return String(data).replaceAll('_',' ')
  }
  const readable=compact(value)
  if(readable && typeof readable==='object' && Object.keys(readable).length===0)return null
  return <details className="recipe-conditions"><summary>{label}</summary>{facts(readable)}</details>
}
export function RequestState({loading, error, retry}: {loading: boolean; error?: string; retry?: () => void}) {
  if (loading) return <p className="loading" role="status">Loading dataset records…</p>
  if (error) return <div className="notice error" role="alert"><strong>Could not load data</strong><p>{error}</p><p className="help">The request did not return a usable result. Check the message and relevant selections, then try again.</p>{retry && <button type="button" onClick={retry}>Try again</button>}</div>
  return null
}
export function ActionHint({reason,ready,id}: {reason?:string;ready:string;id?:string}) {
  return <p id={id} className={`action-hint ${reason?'needs-input':'ready'}`} role="status">{reason??ready}</p>
}
export function ResourceRef({id, onSelect, resources,amount}: {id: string; onSelect?: (id: string) => void; resources?: ReadonlyMap<string, Resource>;amount?:number|null}) {
  const known = resources?.get(id)
  const request = useRequest<Single<Resource>>(known ? null : query(`resources/${encodeURIComponent(id)}`))
  const resource = known ?? request.data?.item
  return <span className="resource-ref" title={resource ? `${resource.registry_name}${resource.metadata == null ? '' : ` · metadata ${resource.metadata}`}${resource.nbt == null ? '' : ' · NBT'}` : id}>{onSelect ? <button className="text-button" onClick={() => onSelect(id)}>{resource?.display_name || resource?.registry_name || id}</button> : <strong>{resource?.display_name || resource?.registry_name || id}</strong>}<code>{resource?.registry_name || id}</code>{amount!==undefined && <span className="choice-meta"><Amount value={amount} resource={resource}/></span>}{request.error && <small className="warning-text">Identity lookup failed: {request.error}</small>}</span>
}
function GroupRef({id, onSelect, resources}: {id: string; onSelect?: (id: string) => void; resources?: ReadonlyMap<string, Resource>}) {
  const [open, setOpen] = useState(false)
  const request = useRequest<Single<Group>>(open ? query(`groups/${encodeURIComponent(id)}`) : null)
  return <details className="group" onToggle={event => setOpen(event.currentTarget.open)}><summary>Alternatives</summary><RequestState {...request} retry={request.reload}/>{open && request.data && <><p>{request.data.item.name} · {request.data.item.members.length} members</p><ul>{request.data.item.members.map(member => <li key={member}><ResourceRef id={member} onSelect={onSelect} resources={resources}/></li>)}</ul><JsonData label="Group record" value={request.data.item}/></>}</details>
}
function Amount({value,resource}: {value: number | null | undefined;resource?:Resource}) {
  return <><span className="quantity">{value == null ? 'Amount unknown' : `Amount ${value.toLocaleString()}`}</span>{resource && <span className="quantity-unit">{resource.kind==='fluid'?'mB':resource.kind==='item'?'items':resource.kind}</span>}</>
}
function Chance({value, label = 'Chance'}: {value: Output['chance']; label?: string}) {
  if (value && value.numerator === value.denominator) return null
  if (value == null) return <Badge tone="warning">{label} unknown</Badge>
  const percent = 100 * value.numerator / value.denominator
  const text = percent > 0 && percent < .01 ? '<0.01%' : percent < 100 && percent > 99.99 ? '>99.99%' : `${percent.toLocaleString('en', {maximumFractionDigits: 2})}%`
  return <Badge>{label} {text}</Badge>
}
export function OutputRows({outputs, onSelect, resources, onRecycle}: {outputs: Output[]; onSelect?: (id: string) => void; resources?: ReadonlyMap<string, Resource>;onRecycle?:(id:string)=>void}) {
  return <div className="output-list">{outputs.map((output, index) => <div className="choice" key={index}><ResourceRef id={output.resource_id} onSelect={onSelect} resources={resources} amount={output.amount??null}/><div className="choice-meta"><Chance value={output.chance}/>{onRecycle && <button onClick={()=>onRecycle(output.resource_id)} aria-label={`Recycle output ${output.resource_id}`}>Recycle output</button>}</div></div>)}</div>
}
function fields(value:unknown):Record<string,unknown>|undefined {
  return value!==null && typeof value==='object' && !Array.isArray(value) ? value as Record<string,unknown> : undefined
}
function reference(value:unknown) {
  return typeof value==='string' && value.trim()!=='' ? value : undefined
}
function declaredSlot(value:unknown) {
  const slot=fields(value)
  if(!slot || !Array.isArray(slot.choices))return undefined
  return {
    position:typeof slot.native_slot==='number' && Number.isSafeInteger(slot.native_slot) && slot.native_slot>=0 ? slot.native_slot+1 : undefined,
    role:slot.role==='consume'?'Captured consumption':slot.role==='presence'?'Required presence':slot.role==='tool'?'Tool':'Consumption unresolved',
    choices:slot.choices.map(value=>{
      const choice=fields(value)
      if(!choice || (choice.resource_id!==null && !reference(choice.resource_id)))return undefined
      const match=fields(choice.match)
      const modes:Record<string,string>={exact:'Exact reference',wildcard:'Metadata wildcard',ore_dict:'OreDictionary reference',unified:'Unified reference'}
      const mode=typeof match?.mode==='string' && Object.hasOwn(modes,match.mode) ? modes[match.mode] : undefined
      return {id:reference(choice.resource_id),amount:typeof choice.amount==='number' && Number.isFinite(choice.amount) && choice.amount>=0 ? choice.amount : null,
        matching:mode??'Native matching unresolved',nbtSensitive:match?.nbt_sensitive===true,group:reference(match?.group_id),
        returned:choice.native_return_semantics==='same_selected_stack_copied'?'Selected stack returned':choice.native_return_semantics==='consumed_without_container_return'?'Consumed without container return':undefined}
    })
  }
}
function declaredInputs(conditions:unknown) {
  const native=fields(conditions)
  if(!native || (!('native_inputs' in native) && !('native_controller_input' in native)))return undefined
  return {slots:Array.isArray(native.native_inputs)?native.native_inputs.map(declaredSlot):[],malformed:!Array.isArray(native.native_inputs),
    hasController:'native_controller_input' in native,controller:declaredSlot(native.native_controller_input),
    excludesSeedAndRefill:native.native_inputs_scope==='catalog_ingredient_occurrences_excludes_seed_and_refill'}
}
export function ProcessInputSummary({process}:{process:Process}) {
  const declared=process.inputs.length===0 ? declaredInputs(process.conditions) : undefined
  if(!declared)return <>{process.inputs.length} input slots</>
  if(declared.malformed)return <>Captured ingredients unresolved</>
  return <>{declared.slots.length} captured ingredient {declared.slots.length===1?'slot':'slots'}</>
}
function DeclaredSlot({slot,index,onSelect,resources}:{slot:ReturnType<typeof declaredSlot>;index:number;onSelect?:(id:string)=>void;resources?:ReadonlyMap<string,Resource>}) {
  return <section className="slot"><div className="slot-heading"><strong>Captured slot {slot?.position??index+1}</strong><Badge>{slot?.role??'Consumption unresolved'}</Badge></div>
    {!slot ? <p>Captured entry unresolved</p> : slot.choices.length===0 ? <p>No alternatives captured.</p> : slot.choices.map((choice,choiceIndex)=><div className="choice" key={choiceIndex}>
      {choiceIndex>0 && <span className="choice-or">OR</span>}
      {!choice ? <p>Captured alternative unresolved</p> : <>{choice.id ? <ResourceRef id={choice.id} amount={choice.amount} resources={resources} onSelect={onSelect}/> : <><span>Identity unresolved</span><Amount value={choice.amount}/></>}
        <div className="choice-meta"><Badge>{choice.matching}</Badge>{choice.nbtSensitive && <Badge>NBT-sensitive</Badge>}{choice.returned && <Badge>{choice.returned}</Badge>}</div>
        {choice.group && <GroupRef id={choice.group} onSelect={onSelect} resources={resources}/>}</>}
    </div>)}
  </section>
}
function CapturedInputs({declared,onSelect,resources}:{declared:NonNullable<ReturnType<typeof declaredInputs>>;onSelect?:(id:string)=>void;resources?:ReadonlyMap<string,Resource>}) {
  return <><h4>Captured ingredients</h4><p className="help">Input accounting is incomplete. Captured alternatives don’t confirm native acceptance.</p>
    {declared.excludesSeedAndRefill && <p className="help">Seed trigger and water refill are separate from these ingredients.</p>}
    {declared.malformed && <p>Captured ingredient list unresolved. See technical data.</p>}
    {!declared.malformed && declared.slots.length===0 && <p>No ingredient declarations captured.</p>}
    <div className="slot-list">{declared.slots.map((slot,index)=><DeclaredSlot key={index} slot={slot} index={index} onSelect={onSelect} resources={resources}/>)}</div>
    {declared.hasController && <section><h4>Separate controller input</h4><DeclaredSlot slot={declared.controller} index={0} onSelect={onSelect} resources={resources}/></section>}
  </>
}
export function ProcessDetail({process, projectionIssue, onSelect, resources, onRecycle}: {process: Process; projectionIssue?:ProcessInspection['projection_issue']; onSelect?: (id: string) => void; resources?: ReadonlyMap<string, Resource>;onRecycle?:(id:string)=>void}) {
  const roles: Record<string, string> = {presence: 'Required presence', tool: 'Tool'}
  const declared=process.inputs.length===0 ? declaredInputs(process.conditions) : undefined
  const conditions = process.conditions
  const native = conditions !== null && typeof conditions === 'object' ? conditions as Record<string, unknown> : undefined
  const noMachineVoltage=native?.recipe_voltage_applicability==='not_applicable_crafting_grid'
    && process.family==='minecraft:crafting' && process.executable===true && process.eu_per_tick===null
    && native.native_class==='gregtech.api.util.GTShapedRecipe' && native.dynamic_output==='resolved_static'
    && process.provenance!==null && typeof process.provenance==='object'
    && 'owner' in process.provenance && process.provenance.owner==='CraftingManager'
  const mana = native?.energy_unit === 'mana' && typeof native.total_mana === 'number' && Number.isFinite(native.total_mana)
    ? native.total_mana : undefined
  const catalystBelow = native?.catalyst_below !== null && typeof native?.catalyst_below === 'object'
    ? native.catalyst_below as Record<string, unknown> : undefined
  const requiredCatalysts = ['alchemy','conjuration'].filter(kind => catalystBelow?.[`${kind}_required`] === true)
    .map(kind => {
      const candidate = catalystBelow?.[`${kind}_block`]
      const block = candidate !== null && typeof candidate === 'object' ? candidate as Record<string, unknown> : undefined
      return {kind, block}
    })
  const outputTemplates = conditions !== null && typeof conditions === 'object' && 'dynamic_output' in conditions
    && conditions.dynamic_output === 'unresolved' && process.outputs.length > 0
  return <section className="process-detail">
    <div className="detail-title"><div><p className="eyebrow">{process.family}</p><h3>{process.display_name || process.id}</h3><code>{process.id}</code></div>{process.executable !== true && <Badge tone={process.executable === false ? 'warning' : 'muted'}>{process.executable === false ? 'Informational / fake' : 'Execution unknown'}</Badge>}</div>
    {noMachineVoltage && <Badge>No machine voltage requirement</Badge>}
    {(mana !== undefined || process.duration_ticks != null || process.eu_per_tick != null || (process.amperage != null && process.amperage !== 1)) && <dl className="metrics">{mana !== undefined && <div><dt>Mana cost</dt><dd>{mana.toLocaleString(undefined, {maximumFractionDigits: 20})} mana</dd></div>}{process.duration_ticks != null && <div><dt>Duration</dt><dd>{process.duration_ticks.toLocaleString()} ticks</dd></div>}{process.eu_per_tick != null && <div><dt>Energy</dt><dd>{process.eu_per_tick.toLocaleString()} EU/t</dd></div>}{process.amperage != null && process.amperage !== 1 && <div><dt>Amperage</dt><dd>{process.amperage}</dd></div>}</dl>}
    {requiredCatalysts.length > 0 && <section className="slot"><h4>Required catalysts</h4>
      {catalystBelow?.position === 'one_block_below_pool' && <p>Catalyst position: one block below the mana pool.</p>}
      {requiredCatalysts.map(({kind, block}) => <div className="choice" key={kind}>
        <strong>{kind === 'alchemy' ? 'Alchemy catalyst' : 'Conjuration catalyst'}</strong>
        {typeof block?.resource_id === 'string' && <ResourceRef id={block.resource_id} onSelect={onSelect} resources={resources}/>}
        {block?.consumed === false && <Badge tone="presence">Not consumed</Badge>}
      </div>)}
    </section>}
    {outputTemplates && <p className="notice warning">Runtime result is unresolved. Shown outputs are native display templates.</p>}
    <div className="recipe-io"><div className="recipe-inputs">{declared ? <CapturedInputs declared={declared} onSelect={onSelect} resources={resources}/> : <><h4 title="All slots are required. Choose one alternative within each slot.">Inputs</h4>
    {process.inputs.length === 0 && <p className="empty-inline">No input slots captured.</p>}
    <div className="slot-list">{process.inputs.map((slot, index) => <section className="slot" key={index}><div className="slot-heading"><strong>Slot {index + 1}</strong>{slot.role !== 'consume' && <Badge tone="presence">{roles[slot.role] || slot.role}</Badge>}{slot.consumption_chance !== undefined && <Chance value={slot.consumption_chance} label="Consumption chance"/>} {slot.choices.length > 1 && <small>{slot.choices.length} alternatives</small>}</div>{slot.choices.map((choice, choiceIndex) => <div className="choice" key={choiceIndex}>{choiceIndex > 0 && <span className="choice-or">OR</span>}{choice.resource_id !== null && <ResourceRef id={choice.resource_id} onSelect={onSelect} resources={resources} amount={choice.amount}/>}<div className="choice-meta">{choice.resource_id===null && <Amount value={choice.amount}/>}{!['exact','unified','ore_dict'].includes(choice.match.mode) && <Badge>{choice.match.mode}</Badge>}{choice.match.nbt_sensitive === true && <Badge>NBT-sensitive</Badge>}{choice.consumption_chance !== undefined && <Chance value={choice.consumption_chance} label="Consumption chance"/>}</div>{choice.match.group_id && <GroupRef id={choice.match.group_id} onSelect={onSelect} resources={resources}/>}</div>)}</section>)}</div>
    </>}</div><div className="recipe-outputs"><h4>{outputTemplates ? 'Output templates' : 'Outputs'}</h4>{projectionIssue?.status==='unsupported_accounting' && <section className="notice warning"><h4>Operation accounting unavailable</h4><p>{projectionIssue.reason}</p></section>}<OutputRows outputs={process.outputs} onSelect={onSelect} resources={resources} onRecycle={onRecycle}/></div></div>
    <ConditionFacts value={process.conditions}/><JsonData label="Technical data: full process record" value={process}/>
  </section>
}
export function EnvironmentFacts({environments}:{environments:readonly Environment[]}) {
  const seen=new Set<string>()
  return <>{environments.map(environment=>{
    const properties=environment.properties!==null && typeof environment.properties==='object' ? environment.properties as Record<string,unknown>:undefined
    const value=properties?.dimension_blacklist
    if(value===null || typeof value!=='object' || Array.isArray(value))return null
    const blacklist=value as Record<string,unknown>
    const unresolved=blacklist.status==='unresolved' && blacklist.dimension_ids===null && blacklist.reason==='native_array_is_null'
    const ids=blacklist.dimension_ids
    if(!unresolved && (blacklist.status!=='captured' || blacklist.scope!=='native_numeric_filter_not_resolved_availability' || !Array.isArray(ids) || ids.length===0 || !ids.every(Number.isInteger)))return null
    const key=JSON.stringify({status:blacklist.status,scope:blacklist.scope,dimension_ids:ids,reason:blacklist.reason})
    if(seen.has(key))return null
    seen.add(key)
    return unresolved ? <p className="help" key={key}>Underground fluid exclusions are unresolved in this capture.</p> : <p className="help" key={key}><strong>Underground fluid exclusions:</strong> {(ids as number[]).join(', ')}. These global native filter IDs don't establish environment or inventory availability.</p>
  })}</>
}

export function SourceDetail({source, environments, onSelect}: {source: Source; environments: Environment[]; onSelect?: (id: string) => void}) {
  return <article className="source-card"><div className="detail-title"><div><p className="eyebrow">{source.kind}</p><h3>{source.display_name || source.id}</h3><code>{source.id}</code></div><Badge tone={source.status === 'active' ? 'good' : 'warning'}>{source.status}</Badge></div><h4>Possible outputs</h4><OutputRows outputs={source.outputs} onSelect={onSelect}/><h4>Environments</h4>{source.environment_ids.length ? <ul className="environment-refs">{source.environment_ids.map(id => {const environment = environments.find(item => item.id === id); return <li key={id}>{environment?.name || id}<small>{environment ? `Dimension ${environment.dimension_id ?? 'unknown'} · Provider ${environment.provider ?? 'unknown'}` : 'Environment record not in the loaded catalog'}</small><code>{id}</code></li>})}</ul> : <p className="empty-inline">No environments captured.</p>}<EnvironmentFacts environments={environments.filter(environment=>source.environment_ids.includes(environment.id))}/><JsonData label="Source conditions" value={source.conditions}/><JsonData label="Generator parameters and weights" value={source.parameters}/><JsonData label="Full source record" value={source}/></article>
}
export function CoverageList({records}: {records: Coverage[]}) {
  return <div className="coverage-list">{records.map(record => <article key={record.id}><div><strong>{record.domain}</strong><Badge tone={record.status === 'complete' ? 'good' : record.status === 'error' ? 'danger' : 'warning'}>{record.status}</Badge><span>{record.records.toLocaleString()} records</span></div>{record.reason && <p>{record.reason}</p>}<JsonData label="Coverage evidence" value={record}/></article>)}</div>
}
