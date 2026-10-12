import {useEffect,useState} from 'react'
import type {BoundaryProfile,Group,Page,ProfileList,QueryScope,ScopeCatalog,Single} from './api'
import {query,useRequest} from './api'
import {Badge,RequestState} from './Details'
import {ResourceSetEditor} from './ResourceSetEditor'

export function BoundaryProfileSelector({profile,label,onSelect,revision=0}:{profile?:BoundaryProfile;label:string;onSelect:(profile:BoundaryProfile|undefined)=>void;revision?:number}) {
  const request=useRequest<ProfileList>(query('boundary-profiles',{revision}))
  return <><label>{label}<select value={profile?.id??''} onChange={event=>onSelect(request.data?.items.find(item=>item.id===event.target.value))}><option value="">No profile</option>{request.data?.items.map(item=><option key={item.id} value={item.id}>{item.name} · {item.base_resource_ids.length} basics · Revision {item.revision}</option>)}</select></label><RequestState {...request} retry={request.reload}/></>
}

export function BoundaryProfileEditor({profile,snapshotId,onSaved}:{profile?:BoundaryProfile;snapshotId:string;onSaved:(profile:BoundaryProfile|null)=>void}) {
  const [id,setId]=useState(profile?.id??'')
  const [name,setName]=useState(profile?.name??'')
  const [bases,setBases]=useState(profile?.base_resource_ids??[])
  const [scope,setScope]=useState<QueryScope>(profile?.scope??{})
  const [groupText,setGroupText]=useState('')
  const [groupQuery,setGroupQuery]=useState<string|null>(null)
  const [mutation,setMutation]=useState<{body:unknown;method:'POST'|'DELETE';id:string}|null>(null)
  const saved=useRequest<Single<BoundaryProfile|null>>(mutation?query(`boundary-profiles/${encodeURIComponent(mutation.id)}`):null,mutation?.body,mutation?.method)
  const catalog=useRequest<ScopeCatalog>(query('scope-catalog'))
  const groups=useRequest<Page<Group & {member_count:number}>>(groupQuery!==null?query('resource-groups',{q:groupQuery,limit:20}):null)
  useEffect(()=>{if(saved.data){onSaved(saved.data.item);setMutation(null)}},[saved.data,onSaved])
  const update=(key:keyof QueryScope,values:string[])=>setScope({...scope,[key]:values})
  const toggle=(key:keyof QueryScope,id:string)=>update(key,(scope[key]??[]).includes(id)?(scope[key]??[]).filter(value=>value!==id):[...(scope[key]??[]),id])
  return <section className="boundary-profile-editor" aria-label="Boundary profile editor"><h3>{profile?'Edit profile':'Create profile'}</h3><p className="help">Snapshot {snapshotId}. Basics are assumed external supplies. They don't prove deposits, inventory or progression. Exclusions filter searches and these network analyses, without deleting captured records.</p>
    <form onSubmit={event=>{event.preventDefault();setMutation({id,method:'POST',body:{name,base_resource_ids:bases,scope,expected_revision:profile?.revision??0}})}}>
      <div className="analysis-controls"><label>Profile ID<input value={id} onChange={event=>setId(event.target.value)} disabled={!!profile} required maxLength={100}/></label><label>Profile name<input value={name} onChange={event=>setName(event.target.value)} required/></label>{profile && <Badge>Revision {profile.revision}</Badge>}</div>
      <ResourceSetEditor label="Basic resources" ids={bases} onChange={setBases}/>
      <details open><summary>Offline scope exclusions</summary><ResourceSetEditor label="Excluded resources" ids={scope.excluded_resource_ids??[]} onChange={values=>update('excluded_resource_ids',values)}/>
        <fieldset><legend>Excluded captured groups</legend><div className="input-action"><label>Search captured groups<input value={groupText} onChange={event=>setGroupText(event.target.value)}/></label><button type="button" onClick={()=>setGroupQuery(groupText.trim())}>Find groups</button></div><RequestState {...groups} retry={groups.reload}/>
          {groups.data && <><p className="help">{groups.data.items.length} of {groups.data.total.toLocaleString()} matching groups shown. Narrow the search for others.</p><ul className="scope-options">{groups.data.items.map(group=><li key={group.id}><label><input type="checkbox" checked={(scope.excluded_group_ids??[]).includes(group.id)} onChange={()=>toggle('excluded_group_ids',group.id)}/>{group.name} <span>{group.member_count.toLocaleString()} members · {group.kind}</span><code>{group.id}</code></label></li>)}</ul></>}
          {(scope.excluded_group_ids??[]).length>0 && <ul className="filter-tags">{scope.excluded_group_ids!.map(group=><SelectedGroup key={group} id={group} remove={()=>toggle('excluded_group_ids',group)}/>)}</ul>}
        </fieldset>
        <RequestState {...catalog} retry={catalog.reload}/>{catalog.data && <><fieldset><legend>Excluded item namespaces</legend><p className="help">{catalog.data.unknown_namespace_count.toLocaleString()} resources have no captured namespace. Recipe families are a separate filter.</p><ul className="scope-options">{catalog.data.namespaces.map(item=><li key={item.id}><label><input type="checkbox" checked={(scope.excluded_namespaces??[]).includes(item.id)} onChange={()=>toggle('excluded_namespaces',item.id)}/>{item.id} <span>{item.resources.toLocaleString()} resources</span></label></li>)}</ul></fieldset>
          <fieldset><legend>Excluded recipe families</legend><ul className="scope-options">{catalog.data.families.map(item=><li key={item.id}><label><input type="checkbox" checked={(scope.excluded_family_ids??[]).includes(item.id)} onChange={()=>toggle('excluded_family_ids',item.id)}/>{item.id} <span>{item.processes.toLocaleString()} recipes</span></label></li>)}</ul></fieldset></>}
      </details><button className="primary" disabled={saved.loading}>Save profile</button>{profile && <button type="button" className="danger-button" disabled={saved.loading} onClick={()=>setMutation({id:profile.id,method:'DELETE',body:{expected_revision:profile.revision}})}>Delete profile</button>}
    </form><RequestState {...saved} retry={saved.reload}/>
  </section>
}
function SelectedGroup({id,remove}:{id:string;remove:()=>void}) {
  const group=useRequest<Single<Group>>(query(`groups/${encodeURIComponent(id)}`))
  return <li>{group.data?.item.name??id}<code>{id}</code><button type="button" onClick={remove} aria-label={`Remove group ${id}`}>Remove</button></li>
}
