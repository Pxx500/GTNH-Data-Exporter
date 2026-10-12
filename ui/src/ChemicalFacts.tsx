import { query, useRequest } from './api'
import { Badge, JsonData, RequestState } from './Details'
import { quantity,UnsupportedFacts } from './AccountingDetails'
import type { Quantities } from './AccountingDetails'

interface ChemistryReply {snapshot_id:string;resource_id:string;status:string;basis:unknown;vector:Quantities;unsupported:unknown[];material_facts:unknown}
export function ChemicalFacts({resourceId}: {resourceId:string}) {
  const [open,setOpen]=useState(false)
  const request=useRequest<ChemistryReply>(open?query(`chemistry/${encodeURIComponent(resourceId)}`):null)
  return <details className="chemical-facts" onToggle={event=>setOpen(event.currentTarget.open)}><summary>Source-backed material accounting</summary><RequestState {...request} retry={request.reload}/>
    {request.data && <><Badge tone={request.data.status==='complete'?'good':'warning'}>{request.data.status}</Badge><p className="help">These facts describe captured material accounting. Formula text is not proof of chemical purity or recipe balance.</p>
      {Object.keys(request.data.vector).length>0 && <dl className="element-vector">{Object.entries(request.data.vector).map(([element,amount])=><div key={element}><dt><code>{element}</code></dt><dd>{quantity(amount)}</dd></div>)}</dl>}
      <JsonData label="Material accounting basis" value={request.data.basis}/><JsonData label="Captured material facts" value={request.data.material_facts}/><UnsupportedFacts label="Unresolved material accounting" items={request.data.unsupported}/></>}
  </details>
}
import { useState } from 'react'
