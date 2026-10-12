import { useState } from 'react'
import type { Group,Process,Resource,Single } from './api'
import { query,useRequest } from './api'
import { Badge,RequestState,ResourceRef } from './Details'
import { ResourcePicker } from './ResourcePicker'

export interface InputSelection {choice_index:number;resource_id:string}
export type InputSelectionMap = Record<string,Record<string,InputSelection>>
export function InputSelections({processes,selections,resources,onChange}: {processes:Process[];selections:InputSelectionMap;resources:ReadonlyMap<string,Resource>;onChange:(processId:string,slot:string,value:InputSelection)=>void}) {
  return <section className="input-selections"><h4>Captured input choices</h4><p className="help">Use automatic choices first. If a result reports an unresolved input, open its slot and choose an alternative and a concrete resource from search or captured group members. Slot indices start at 0. The Dataset validates quantity, NBT, group membership and matching.</p>
    {processes.map(process=><section key={process.id}><h5>{process.display_name || process.id} <code>{process.id}</code></h5>{process.inputs.map((slot,index)=><SlotSelection key={index} process={process} slotIndex={index} selected={selections[process.id]?.[String(index)]} resources={resources} onChange={value=>onChange(process.id,String(index),value)}/>)}</section>)}
  </section>
}
function SlotSelection({process,slotIndex,selected,resources,onChange}: {process:Process;slotIndex:number;selected?:unknown;resources:ReadonlyMap<string,Resource>;onChange:(value:InputSelection)=>void}) {
  const [open,setOpen]=useState(false)
  const slot=process.inputs[slotIndex]
  const selection=selected!==null && typeof selected==='object' && !Array.isArray(selected) ? selected as Partial<InputSelection> : undefined
  const validSelection=selection!==undefined && Number.isInteger(selection.choice_index) && selection.choice_index!>=0 && selection.choice_index!<slot.choices.length && typeof selection.resource_id==='string'
  const choiceIndex=selected===undefined ? 0 : validSelection ? selection!.choice_index! : -1
  const choice=slot.choices[choiceIndex]
  return <details className="slot-selection" onToggle={event=>setOpen(event.currentTarget.open)}><summary>Slot {slotIndex} · {slot.role} · {selected?'selected':'automatic / unresolved'}</summary>
    {open && <>{selected!==undefined && !validSelection && <p role="alert">Invalid input selection. Choose an alternative to edit it. Dataset validates submitted selections.</p>}<label>Alternative for {process.id} slot {slotIndex}<select value={choice ? choiceIndex : ''} onChange={event=>{const index=Number(event.target.value);onChange({choice_index:index,resource_id:slot.choices[index].resource_id??''})}}>{!choice && <option value="" disabled>Invalid selection</option>}{slot.choices.map((candidate,index)=><option key={index} value={index}>Choice {index} · {candidate.match.mode} · {candidate.resource_id??candidate.match.group_id??'unknown'}</option>)}</select></label>
      {choice && <><Badge>{choice.match.mode}</Badge>{choice.resource_id && <ResourceRef id={choice.resource_id} resources={resources}/>}
      <ConcreteChoice key={choiceIndex} processId={process.id} slotIndex={slotIndex} choiceIndex={choiceIndex} groupId={choice.match.group_id} resourceId={validSelection ? selection!.resource_id! : choice.resource_id ?? ''} resources={resources} onChange={onChange}/></>}
    </>}
  </details>
}
function ConcreteChoice({processId,slotIndex,choiceIndex,groupId,resourceId,resources,onChange}: {processId:string;slotIndex:number;choiceIndex:number;groupId?:string;resourceId:string;resources:ReadonlyMap<string,Resource>;onChange:(value:InputSelection)=>void}) {
  const group=useRequest<Single<Group>>(groupId?query(`groups/${encodeURIComponent(groupId)}`):null)
  const [resolved,setResolved]=useState('')
  function choose(id:string){
    onChange({choice_index:choiceIndex,resource_id:id})
  }
  return <><RequestState {...group} retry={group.reload}/><ResourcePicker label={`Concrete input for ${processId} slot ${slotIndex}`} selectedId={resourceId} onSelect={choose} onResolve={setResolved}/>{resourceId && resolved!==resourceId && <p className="help">Concrete identity lookup is pending or unresolved.</p>}
    {group.data && <details><summary>Browse captured group members ({group.data.item.members.length})</summary><p className="help">First 40 declared IDs shown. Autocomplete can select other concrete variants. Dataset validates native matching.</p><ul>{group.data.item.members.slice(0,40).map(id=><li key={id}><ResourceRef id={id} resources={resources}/><button onClick={()=>choose(id)}>Choose member {id}</button></li>)}</ul></details>}
  </>
}
