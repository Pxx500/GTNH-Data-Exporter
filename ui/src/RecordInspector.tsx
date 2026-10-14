import {useEffect,useRef,useState} from 'react'
import type {ReactNode} from 'react'
import type {Page,Process,Resource,Single} from './api'
import {query,useRequest} from './api'
import {JsonData,ProcessDetail,RequestState} from './Details'
import {ChemicalFacts} from './ChemicalFacts'
import {AcquisitionDetails} from './AcquisitionDetails'

export function RecordInspector({children,onClose}:{children:ReactNode;onClose:()=>void}) {
  const close=useRef<HTMLButtonElement>(null)
  useEffect(()=>{
    const opener=document.activeElement instanceof HTMLElement?document.activeElement:null
    close.current?.focus({preventScroll:true})
    return ()=>{if(opener?.isConnected && !opener.closest('[hidden]'))opener.focus({preventScroll:true})}
  },[])
  return <aside className="graph-inspector" aria-label="Record inspector" onKeyDown={event=>{if(event.key==='Escape'){event.stopPropagation();onClose()}}}>
    <header className="inspector-header"><h3>Selected record</h3><button ref={close} onClick={onClose} aria-label="Close record inspector">Close</button></header>
    <div className="inspector-content">{children}</div>
  </aside>
}

export function ResourceInspector({id,resources,onInspect,onOpenLibrary,onUseStart,onUseTarget}:{id:string;resources:ReadonlyMap<string,Resource>;onInspect:(id:string)=>void;onOpenLibrary:(id:string)=>void;onUseStart?:(id:string)=>void;onUseTarget?:(id:string)=>void}) {
  const known=resources.get(id)
  const request=useRequest<Single<Resource>>(known?null:query(`resources/${encodeURIComponent(id)}`))
  const resource=known??request.data?.item
  const [relationships,setRelationships]=useState(false)
  const [offset,setOffset]=useState(0)
  const processes=useRequest<Page<Process>>(relationships?query('processes',{output_id:id,offset,limit:5}):null)
  return <><RequestState {...request} retry={request.reload}/>{resource && <>
    <h3>{resource.display_name||resource.registry_name}</h3><code>{resource.registry_name}</code>
    <p className="help">{resource.kind}{resource.metadata==null?'':` · metadata ${resource.metadata}`}{resource.nbt==null?'':' · NBT identity preserved'}</p>
    <div className="inspector-actions"><button onClick={()=>onOpenLibrary(id)}>Open in Library</button>{onUseStart && <button onClick={()=>onUseStart(id)}>Use as start in new query</button>}{onUseTarget && <button onClick={()=>onUseTarget(id)}>Use as target in new query</button>}</div>
    {(onUseStart || onUseTarget) && <p className="help">New query actions change the search selections. Submit the query to search again.</p>}
    <AcquisitionDetails resourceId={id}/><ChemicalFacts resourceId={id}/>
    <details onToggle={event=>setRelationships(event.currentTarget.open)}><summary>Production recipes in dump</summary>{relationships && <>
      <p className="help">These records produce this resource. Their ingredients and conditions still need to be supplied.</p>
      <RequestState {...processes} retry={processes.reload}/>{processes.data && <>
        <p>{processes.data.total.toLocaleString()} matching production recipes</p>{processes.data.matching_complete===false && <p className="warning-text">Matching is incomplete. Missing results are not an exact negative.</p>}
        {processes.data.items.map(process=><details key={process.id}><summary>{process.display_name||process.id}</summary><ProcessDetail process={process} resources={resources} onSelect={onInspect}/></details>)}
        <div className="pagination"><button disabled={offset===0} onClick={()=>setOffset(Math.max(0,offset-5))}>Previous recipes</button><button disabled={offset+processes.data.items.length>=processes.data.total} onClick={()=>setOffset(offset+5)}>Next recipes</button></div>
      </>}
    </>}</details>
    <JsonData label="Technical data: full resource record" value={resource}/>
  </>}</>
}
