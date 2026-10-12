import type { Resource } from './api'
import { Badge, JsonData, ResourceRef } from './Details'

export interface Rational {numerator:number;denominator:number}
export type Quantities = Record<string,Rational>
export interface Ledger {
  status:string;yield_mode:'guaranteed'|'expected';consumed:Quantities;produced:Quantities;net:Quantities;presence:Quantities
  unsupported:{process_id?:string;reason:string}[];assumptions:unknown[]
}
export interface Startup {required_start_stock:Quantities;final_stock:Quantities;feasible:boolean|null;steps?:{process_id:string;ledger:Ledger}[];integer_batch_scale?:number|null;requires_integer_batch_scaling?:boolean|null;startup_scope?:string;feasibility_scope?:string}
export function quantity(value:Rational|null|undefined) {
  return value == null ? 'Unknown' : value.denominator===1 ? value.numerator.toLocaleString() : `${value.numerator.toLocaleString()}/${value.denominator.toLocaleString()}`
}
export function UnsupportedFacts({items,label}: {items:unknown[];label:string}) {
  return items.length>0 ? <div className="notice warning"><strong>{label}</strong><ul>{items.map((item,index)=><li key={index}>{typeof item==='string'?item:JSON.stringify(item)}</li>)}</ul></div> : null
}
export function QuantityList({values,label,resources,onSelect}: {values:Quantities|undefined;label:string;resources?:ReadonlyMap<string,Resource>;onSelect?:(id:string)=>void}) {
  return <section className="balance-list"><h4>{label}</h4>{values===undefined ? <p>Unknown</p> : Object.keys(values).length===0 ? <p>None recorded</p> : <ul>{Object.entries(values).map(([id,value])=><li key={id}><ResourceRef id={id} resources={resources} onSelect={onSelect}/><strong>{quantity(value)}</strong></li>)}</ul>}</section>
}
export function LedgerDetails({ledger,startup,resources,onSelect}: {ledger:Ledger|null|undefined;startup?:Startup|null;resources?:ReadonlyMap<string,Resource>;onSelect?:(id:string)=>void}) {
  if(!ledger)return <p className="warning-text">Quantitative accounting is unresolved.</p>
  return <section className="ledger-detail"><div className="detail-title"><h4>Resource ledger</h4><Badge tone={ledger.status==='complete'?'good':'warning'}>{ledger.status}</Badge><Badge>{ledger.yield_mode} yields</Badge></div>
    <p className="help">Amounts use captured native resource units. Expected output is an average, not guaranteed stock. Presence requirements are not consumed.</p>
    <div className="balance-grid"><QuantityList values={ledger.consumed} label="Consumed" resources={resources} onSelect={onSelect}/><QuantityList values={ledger.produced} label="Produced" resources={resources} onSelect={onSelect}/><QuantityList values={ledger.net} label="Net balance" resources={resources} onSelect={onSelect}/><QuantityList values={ledger.presence} label="Nonconsumed presence" resources={resources} onSelect={onSelect}/></div>
    {startup && <><p>Stock feasibility: {startup.feasible===true?'feasible with listed starting stock':startup.feasible===false?'not feasible':'unknown for fractional, expected or unsupported execution'}</p><p className="help">Starting stock is sufficient for the declared batch order. It is not a minimum interleaved-machine stock requirement. Energy and machine conditions remain unverified.</p>{startup.requires_integer_batch_scaling===true && <p className="notice warning">Fractional accounting requires integer batch scaling by {startup.integer_batch_scale?.toLocaleString() ?? 'an unresolved factor'}. This result does not prove native batch execution.</p>}<div className="balance-grid"><QuantityList values={startup.required_start_stock} label="Required starting stock" resources={resources} onSelect={onSelect}/><QuantityList values={startup.final_stock} label="Final stock" resources={resources} onSelect={onSelect}/></div></>}
    {ledger.unsupported.length>0 && <div className="notice warning"><strong>Unsupported accounting</strong><ul>{ledger.unsupported.map((item,index)=><li key={index}>{item.process_id && <code>{item.process_id} </code>}{item.reason}</li>)}</ul></div>}
    {ledger.assumptions.length>0 && <JsonData label="Accounting assumptions" value={ledger.assumptions}/>}
  </section>
}
