import {useEffect,useState} from 'react'
import type {BoundaryProfile,Group,Page,ProfileList,QueryScope,ScopeCatalog,Single} from './api'
import {query,useRequest} from './api'
import {ActionHint,Badge,RequestState} from './Details'
import {ResourceSetEditor} from './ResourceSetEditor'

export function BoundaryProfileSelector({profile,label,onSelect,revision=0,emptyLabel='No profile'}:{profile?:BoundaryProfile;label:string;onSelect:(profile:BoundaryProfile|undefined)=>void;revision?:number;emptyLabel?:string}) {
  const request=useRequest<ProfileList>(query('boundary-profiles',{revision}))
  return <><label>{label}<select value={profile?.id??''} onChange={event=>onSelect(request.data?.items.find(item=>item.id===event.target.value))}><option value="">{emptyLabel}</option>{request.data?.items.map(item=><option key={item.id} value={item.id}>{item.name} · {item.base_resource_ids.length} basics · Revision {item.revision}</option>)}</select></label><RequestState {...request} retry={request.reload}/></>
}

export function BoundaryProfileEditor({profile,snapshotId,onSaved,requireBasicResources=false}:{profile?:BoundaryProfile;snapshotId:string;requireBasicResources?:boolean;onSaved:(profile:BoundaryProfile|null)=>void}) {
  const [id]=useState(()=>profile?.id??crypto.randomUUID())
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
  const missingBasics=requireBasicResources && bases.length===0
  const saveBlocked=saved.loading || missingBasics
  const disabledReason=saved.loading?'Saving profile changes. Wait for this request to finish.':!name?'Name your basic input set before saving.':missingBasics?'Add at least one basic resource before saving.':undefined
  const toggle=(key:keyof QueryScope,id:string)=>update(key,(scope[key]??[]).includes(id)?(scope[key]??[]).filter(value=>value!==id):[...(scope[key]??[]),id])
  return <section className="boundary-profile-editor" aria-label="Boundary profile editor"><h3>{profile?'Edit basic input set':'Create basic input set'}</h3><p className="help">Choose the supplies where the plan should stop. Save this named set to use it in the plan. Supplies are assumptions, not inventory or observed deposits.</p>
    <form onSubmit={event=>{event.preventDefault();if(saveBlocked)return;setMutation({id,method:'POST',body:{name,base_resource_ids:bases,scope,expected_revision:profile?.revision??0}})}}>
      <label>Basic input set name<input value={name} onChange={event=>setName(event.target.value)} placeholder="e.g. Steel inputs" required/></label>
      <p className="help">Search each basic resource, select a result, then click Add resource. No defaults are added for you.</p><ResourceSetEditor label="Basic resources" ids={bases} onChange={setBases}/>
      <details className="advanced-settings"><summary>Advanced: Profile identity and scope exclusions</summary><label>Profile ID<input value={id} readOnly/></label><p className="help">Created for snapshot {snapshotId}. This technical ID is assigned automatically and stays fixed. You can copy it when using the API.</p>{profile && <Badge>Revision {profile.revision}</Badge>}<p className="help">Optional. Exclude resources, captured groups, item namespaces or recipe families you want this profile to leave out. These choices affect Library search and network analyses, not historical Trace, recycling or loop searches.</p><ResourceSetEditor label="Excluded resources" ids={scope.excluded_resource_ids??[]} onChange={values=>update('excluded_resource_ids',values)}/>
        <fieldset><legend>Excluded captured groups</legend><div className="input-action"><label>Search captured groups<input value={groupText} onChange={event=>setGroupText(event.target.value)}/></label><button type="button" onClick={()=>setGroupQuery(groupText.trim())}>Find groups</button></div><RequestState {...groups} retry={groups.reload}/>
          {groups.data && <><p className="help">{groups.data.items.length} of {groups.data.total.toLocaleString()} matching groups shown. Narrow the search for others.</p><ul className="scope-options">{groups.data.items.map(group=><li key={group.id}><label><input type="checkbox" checked={(scope.excluded_group_ids??[]).includes(group.id)} onChange={()=>toggle('excluded_group_ids',group.id)}/>{group.name} <span>{group.member_count.toLocaleString()} members · {group.kind}</span><code>{group.id}</code></label></li>)}</ul></>}
          {(scope.excluded_group_ids??[]).length>0 && <ul className="filter-tags">{scope.excluded_group_ids!.map(group=><SelectedGroup key={group} id={group} remove={()=>toggle('excluded_group_ids',group)}/>)}</ul>}
        </fieldset>
        <RequestState {...catalog} retry={catalog.reload}/>{catalog.data && <><fieldset><legend>Excluded item namespaces</legend><p className="help">{catalog.data.unknown_namespace_count.toLocaleString()} resources have no captured namespace. Recipe families are a separate filter.</p><ul className="scope-options">{catalog.data.namespaces.map(item=><li key={item.id}><label><input type="checkbox" checked={(scope.excluded_namespaces??[]).includes(item.id)} onChange={()=>toggle('excluded_namespaces',item.id)}/>{item.id} <span>{item.resources.toLocaleString()} resources</span></label></li>)}</ul></fieldset>
          <fieldset><legend>Excluded recipe families</legend><ul className="scope-options">{catalog.data.families.map(item=><li key={item.id}><label><input type="checkbox" checked={(scope.excluded_family_ids??[]).includes(item.id)} onChange={()=>toggle('excluded_family_ids',item.id)}/>{item.id} <span>{item.processes.toLocaleString()} recipes</span></label></li>)}</ul></fieldset></>}
      </details>{profile && <p className="help">The profile ID stays fixed. Edit its name, supplies or exclusions, then save a new revision.</p>}<ActionHint id="profile-save-hint" reason={disabledReason} ready="Ready to save and use this basic input set."/><button aria-describedby="profile-save-hint" className="primary" disabled={saveBlocked}>Save basic input set (profile)</button>{profile && <button type="button" className="danger-button" disabled={saved.loading} onClick={()=>setMutation({id:profile.id,method:'DELETE',body:{expected_revision:profile.revision}})}>Delete profile</button>}
    </form><RequestState {...saved} retry={saved.reload}/>
  </section>
}
function SelectedGroup({id,remove}:{id:string;remove:()=>void}) {
  const group=useRequest<Single<Group>>(query(`groups/${encodeURIComponent(id)}`))
  return <li>{group.data?.item.name??id}<code>{id}</code><button type="button" onClick={remove} aria-label={`Remove group ${id}`}>Remove</button></li>
}
