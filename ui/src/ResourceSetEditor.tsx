import {useState} from 'react'
import {ResourcePicker} from './ResourcePicker'
import {ActionHint,ResourceRef} from './Details'

export function ResourceSetEditor({label,ids,onChange,profileId}:{label:string;ids:string[];onChange:(ids:string[])=>void;profileId?:string}) {
  const [candidate,setCandidate]=useState('')
  const [resolved,setResolved]=useState('')
  const disabledReason=!candidate?'Select a search result before adding this resource.':candidate!==resolved?'Wait for the selected resource to load.':ids.includes(candidate)?'This resource is already in the list.':undefined
  return <fieldset className="resource-set-editor"><legend>{label}</legend>
    <ResourcePicker label={`Add ${label.toLowerCase()}`} selectedId={candidate} onSelect={setCandidate} onResolve={setResolved} profileId={profileId}/>
    <ActionHint reason={disabledReason} ready="Ready to add the selected resource."/><button type="button" disabled={!!disabledReason} onClick={()=>{onChange([...ids,candidate]);setCandidate('');setResolved('')}}>Add resource</button>
    {ids.length===0?<p className="help">None selected</p>:<ul className="filter-tags">{ids.map(id=><li key={id}><ResourceRef id={id}/>{label==='Basic resources' && <span className="badge presence">Basic resource</span>}<button type="button" aria-label={`Remove ${id} from ${label.toLowerCase()}`} onClick={()=>onChange(ids.filter(value=>value!==id))}>Remove</button></li>)}</ul>}
  </fieldset>
}
