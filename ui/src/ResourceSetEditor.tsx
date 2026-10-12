import {useState} from 'react'
import {ResourcePicker} from './ResourcePicker'
import {ResourceRef} from './Details'

export function ResourceSetEditor({label,ids,onChange,profileId}:{label:string;ids:string[];onChange:(ids:string[])=>void;profileId?:string}) {
  const [candidate,setCandidate]=useState('')
  const [resolved,setResolved]=useState('')
  return <fieldset className="resource-set-editor"><legend>{label}</legend>
    <ResourcePicker label={`Add ${label.toLowerCase()}`} selectedId={candidate} onSelect={setCandidate} onResolve={setResolved} profileId={profileId}/>
    <button type="button" disabled={!candidate || candidate!==resolved || ids.includes(candidate)} onClick={()=>{onChange([...ids,candidate]);setCandidate('');setResolved('')}}>Add resource</button>
    {ids.length===0?<p className="help">None selected</p>:<ul className="filter-tags">{ids.map(id=><li key={id}><ResourceRef id={id}/>{label==='Basic resources' && <span className="badge presence">Basic resource</span>}<button type="button" aria-label={`Remove ${id} from ${label.toLowerCase()}`} onClick={()=>onChange(ids.filter(value=>value!==id))}>Remove</button></li>)}</ul>}
  </fieldset>
}
