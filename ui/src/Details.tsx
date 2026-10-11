import { useState } from 'react'
import type { Coverage, Environment, Group, Output, Process, Resource, Single, Source } from './api'
import { query, useRequest } from './api'

export function Badge({children, tone = ''}: {children: React.ReactNode; tone?: string}) {
  return <span className={`badge ${tone}`}>{children}</span>
}
export function JsonData({label, value}: {label: string; value: unknown}) {
  return <details className="json-data"><summary>{label}</summary><pre>{JSON.stringify(value, null, 2) ?? 'Unknown'}</pre></details>
}
export function RequestState({loading, error, retry}: {loading: boolean; error?: string; retry?: () => void}) {
  if (loading) return <p className="loading" role="status">Loading dataset records…</p>
  if (error) return <div className="notice error" role="alert"><strong>Could not load data</strong><p>{error}</p>{retry && <button onClick={retry}>Try again</button>}</div>
  return null
}
export function ResourceRef({id, onSelect, resources}: {id: string; onSelect?: (id: string) => void; resources?: ReadonlyMap<string, Resource>}) {
  const known = resources?.get(id)
  const request = useRequest<Single<Resource>>(known ? null : query(`resources/${encodeURIComponent(id)}`))
  const resource = known ?? request.data?.item
  return <span className="resource-ref" title={resource ? `${resource.registry_name}${resource.metadata == null ? '' : ` · metadata ${resource.metadata}`}${resource.nbt == null ? '' : ' · NBT'}` : id}>{onSelect ? <button className="text-button" onClick={() => onSelect(id)}>{resource?.display_name || resource?.registry_name || id}</button> : <strong>{resource?.display_name || resource?.registry_name || id}</strong>}<code>{resource?.registry_name || id}</code>{request.error && <small className="warning-text">Identity lookup failed: {request.error}</small>}</span>
}
function GroupRef({id, onSelect, resources}: {id: string; onSelect?: (id: string) => void; resources?: ReadonlyMap<string, Resource>}) {
  const [open, setOpen] = useState(false)
  const request = useRequest<Single<Group>>(open ? query(`groups/${encodeURIComponent(id)}`) : null)
  return <details className="group" onToggle={event => setOpen(event.currentTarget.open)}><summary>Alternatives</summary><RequestState {...request} retry={request.reload}/>{open && request.data && <><p>{request.data.item.name} · {request.data.item.members.length} members</p><ul>{request.data.item.members.map(member => <li key={member}><ResourceRef id={member} onSelect={onSelect} resources={resources}/></li>)}</ul><JsonData label="Group record" value={request.data.item}/></>}</details>
}
function Amount({value}: {value: number | null | undefined}) {
  return <span className="quantity">{value == null ? 'Amount unknown' : `Amount ${value.toLocaleString()}`}</span>
}
function Chance({value, label = 'Chance'}: {value: Output['chance']; label?: string}) {
  if (value && value.numerator === value.denominator) return null
  if (value == null) return <Badge tone="warning">{label} unknown</Badge>
  const percent = 100 * value.numerator / value.denominator
  const text = percent > 0 && percent < .01 ? '<0.01%' : percent < 100 && percent > 99.99 ? '>99.99%' : `${percent.toLocaleString('en', {maximumFractionDigits: 2})}%`
  return <Badge>{label} {text}</Badge>
}
export function OutputRows({outputs, onSelect, resources}: {outputs: Output[]; onSelect?: (id: string) => void; resources?: ReadonlyMap<string, Resource>}) {
  return <div className="output-list">{outputs.map((output, index) => <div className="choice" key={index}><ResourceRef id={output.resource_id} onSelect={onSelect} resources={resources}/><div className="choice-meta"><Amount value={output.amount}/><Chance value={output.chance}/></div><JsonData label="Output fields" value={output}/></div>)}</div>
}
export function ProcessDetail({process, onSelect, resources}: {process: Process; onSelect?: (id: string) => void; resources?: ReadonlyMap<string, Resource>}) {
  const roles: Record<string, string> = {presence: 'Required presence', tool: 'Tool'}
  return <section className="process-detail">
    <div className="detail-title"><div><p className="eyebrow">{process.family}</p><h3>{process.display_name || process.id}</h3><code>{process.id}</code></div>{process.executable !== true && <Badge tone={process.executable === false ? 'warning' : 'muted'}>{process.executable === false ? 'Informational / fake' : 'Execution unknown'}</Badge>}</div>
    {(process.duration_ticks != null || process.eu_per_tick != null || (process.amperage != null && process.amperage !== 1)) && <dl className="metrics">{process.duration_ticks != null && <div><dt>Duration</dt><dd>{process.duration_ticks.toLocaleString()} ticks</dd></div>}{process.eu_per_tick != null && <div><dt>Energy</dt><dd>{process.eu_per_tick.toLocaleString()} EU/t</dd></div>}{process.amperage != null && process.amperage !== 1 && <div><dt>Amperage</dt><dd>{process.amperage}</dd></div>}</dl>}
    <div className="recipe-io"><div className="recipe-inputs"><h4 title="All slots are required. Choose one alternative within each slot.">Inputs</h4>
    {process.inputs.length === 0 && <p className="empty-inline">No input slots captured.</p>}
    <div className="slot-list">{process.inputs.map((slot, index) => <section className="slot" key={index}><div className="slot-heading"><strong>Slot {index + 1}</strong>{slot.role !== 'consume' && <Badge tone="presence">{roles[slot.role] || slot.role}</Badge>}{slot.consumption_chance !== undefined && <Chance value={slot.consumption_chance} label="Consumption chance"/>} {slot.choices.length > 1 && <small>{slot.choices.length} alternatives</small>}</div>{slot.choices.map((choice, choiceIndex) => <div className="choice" key={choiceIndex}>{choiceIndex > 0 && <span className="choice-or">OR</span>}{choice.resource_id !== null && <ResourceRef id={choice.resource_id} onSelect={onSelect} resources={resources}/>}<div className="choice-meta"><Amount value={choice.amount}/>{!['exact','unified','ore_dict'].includes(choice.match.mode) && <Badge>{choice.match.mode}</Badge>}{choice.match.nbt_sensitive === true && <Badge>NBT-sensitive</Badge>}{choice.consumption_chance !== undefined && <Chance value={choice.consumption_chance} label="Consumption chance"/>}</div>{choice.match.group_id && <GroupRef id={choice.match.group_id} onSelect={onSelect} resources={resources}/>}<JsonData label="Choice fields" value={choice}/></div>)}<JsonData label="Slot fields" value={slot}/></section>)}</div>
    </div><div className="recipe-outputs"><h4>Outputs</h4><OutputRows outputs={process.outputs} onSelect={onSelect} resources={resources}/></div></div>
    <JsonData label="Conditions and research" value={process.conditions}/><JsonData label="Provenance" value={process.provenance}/><JsonData label="Full process record, including extension fields" value={process}/>
  </section>
}
export function SourceDetail({source, environments, onSelect}: {source: Source; environments: Environment[]; onSelect?: (id: string) => void}) {
  return <article className="source-card"><div className="detail-title"><div><p className="eyebrow">{source.kind}</p><h3>{source.display_name || source.id}</h3><code>{source.id}</code></div><Badge tone={source.status === 'active' ? 'good' : 'warning'}>{source.status}</Badge></div><h4>Possible outputs</h4><OutputRows outputs={source.outputs} onSelect={onSelect}/><h4>Environments</h4>{source.environment_ids.length ? <ul className="environment-refs">{source.environment_ids.map(id => {const environment = environments.find(item => item.id === id); return <li key={id}>{environment?.name || id}<small>{environment ? `Dimension ${environment.dimension_id ?? 'unknown'} · Provider ${environment.provider ?? 'unknown'}` : 'Environment record not in the loaded catalog'}</small><code>{id}</code></li>})}</ul> : <p className="empty-inline">No environments captured.</p>}<JsonData label="Source conditions" value={source.conditions}/><JsonData label="Generator parameters and weights" value={source.parameters}/><JsonData label="Full source record" value={source}/></article>
}
export function CoverageList({records}: {records: Coverage[]}) {
  return <div className="coverage-list">{records.map(record => <article key={record.id}><div><strong>{record.domain}</strong><Badge tone={record.status === 'complete' ? 'good' : record.status === 'error' ? 'danger' : 'warning'}>{record.status}</Badge><span>{record.records.toLocaleString()} records</span></div>{record.reason && <p>{record.reason}</p>}<JsonData label="Coverage evidence" value={record}/></article>)}</div>
}
