import {useState} from 'react'
import {cleanup,fireEvent,render,screen,waitFor,within} from '@testing-library/react'
import {afterEach,expect,test,vi} from 'vitest'
import type {BoundaryProfile,NetworkWitnessReport,Process,Resource} from './api'
import {NetworkAnalysis} from './NetworkAnalysis'
import {NetworkResult} from './NetworkResult'
import {AcquisitionBadges} from './AcquisitionDetails'
import {BoundaryProfileEditor} from './BoundaryProfileEditor'

afterEach(()=>{cleanup();vi.unstubAllGlobals()})
const r=(numerator:number)=>({numerator,denominator:1})
const resources:Resource[]=['Water','Hydrogen','Other basic'].map((display_name,index)=>({id:['water','hydrogen','other'][index],display_name,registry_name:`test:${index}`,kind:'fluid',metadata:null,nbt:null,provenance:{}}))
const profile:BoundaryProfile={id:'basics',name:'User basics',revision:2,base_resource_ids:['other'],scope:{},semantics:'assumed_external_feed_not_inventory_or_generation'}
const process:Process={id:'benchmark',display_name:'Electrolyser',family:'test',inputs:[{role:'consume',choices:[{resource_id:'water',amount:1000,match:{mode:'exact'}}]}],outputs:[{resource_id:'hydrogen',amount:2000,chance:r(1)}],duration_ticks:20,eu_per_tick:8,amperage:1,executable:true,conditions:{},provenance:{}}
const empty:NetworkWitnessReport={snapshot_id:'fixture',status:'infeasible',discovery:{resources,processes:{},variants:[],groups:[],search:{},exclusions:{},limit_reasons:[],coverage_complete:true},solutions:[],search:{complete:true,limit_reasons:[]}}

test('human energy summaries round decimals and percentages while the full record retains exact fractions',()=>{
  const ledger={status:'complete',yield_mode:'guaranteed' as const,consumed:{},produced:{},net:{},presence:{},unsupported:[],assumptions:[]}
  const report:NetworkWitnessReport={...empty,status:'complete',solutions:[{executions:[],ledger,net_imports:{},net_coproducts:{},nominal_energy:{status:'known',total_eu:{numerator:147440,denominator:3},eu_per_target:{numerator:7372,denominator:300},unknown_processes:[]},integer_batch_scale:3,startup:{required_start_stock:{},final_stock:{},feasible:null},witness_verified:true,savings:{status:'known',percent:{numerator:814,denominator:45},eu:{numerator:32560,denominator:3}}}]}
  render(<NetworkResult report={report} onSelect={vi.fn()}/>)
  expect(screen.getByText('49,146.67 EU')).toBeInTheDocument()
  expect(screen.getByText('24.57 EU')).toBeInTheDocument()
  expect(screen.getByText('18.09% · 10,853.33 EU')).toBeInTheDocument()
  const detail=screen.getByText('Full network result').closest('details')!.querySelector('pre')!
  expect(JSON.parse(detail.textContent!).solutions[0].savings.percent).toEqual({numerator:814,denominator:45})
})

test('energy sends only explicitly allowed feeds and profile scope, never profile basics implicitly',async()=>{
  let body:Record<string,unknown>|undefined
  vi.stubGlobal('fetch',vi.fn(async(input:string,options?:RequestInit)=>{
    const url=new URL(input,'http://localhost')
    if(url.pathname==='/api/boundary-profiles')return new Response(JSON.stringify({snapshot_id:'fixture',items:[profile]}))
    if(url.pathname==='/api/resources')return new Response(JSON.stringify({snapshot_id:'fixture',items:resources.filter(item=>item.display_name.toLowerCase().includes(url.searchParams.get('q')!.toLowerCase())),total:1,offset:0,limit:8}))
    if(url.pathname.startsWith('/api/resources/'))return new Response(JSON.stringify({snapshot_id:'fixture',item:resources.find(item=>url.pathname.endsWith(item.id))}))
    if(url.pathname==='/api/processes')return new Response(JSON.stringify({snapshot_id:'fixture',items:[process],total:1,offset:0,limit:50}))
    if(url.pathname==='/api/energy-audit'){body=JSON.parse(options!.body as string);return new Response(JSON.stringify(empty))}
    throw new Error(`Unexpected ${input}`)
  }))
  render(<NetworkAnalysis snapshotId="fixture" profile={profile} onProfileChange={vi.fn()} onSelect={vi.fn()}/>)
  expect(screen.getByText('Select a primary feed and target product from the search results.')).toBeInTheDocument()
  expect(screen.getByRole('button',{name:'Run energy audit'})).toBeDisabled()
  fireEvent.change(screen.getByRole('combobox',{name:'Primary feed (e.g. Water)'}),{target:{value:'Water'}})
  fireEvent.click(await screen.findByRole('option',{name:/Water.*test:0/}))
  fireEvent.change(screen.getByRole('combobox',{name:'Target product (e.g. Hydrogen)'}),{target:{value:'Hydrogen'}})
  fireEvent.click(await screen.findByRole('option',{name:/Hydrogen.*test:1/}))
  await screen.findByRole('option',{name:/Electrolyser.*benchmark/})
  expect(screen.getByText('Choose a native benchmark recipe to compare against.')).toBeInTheDocument()
  expect(screen.getByRole('button',{name:'Run energy audit'})).toBeDisabled()
  fireEvent.change(screen.getByLabelText('Native benchmark recipe'),{target:{value:'benchmark'}})
  await waitFor(()=>expect(screen.getByRole('button',{name:'Run energy audit'})).toBeEnabled())
  expect(screen.getByText('Ready to compare networks with the selected benchmark at equal target quantity.')).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button',{name:'Run energy audit'}))
  await screen.findByText('No verified solution was established within these captured candidates and bounds.')
  expect(body).toMatchObject({primary_feed_id:'water',target_id:'hydrogen',benchmark_process_id:'benchmark',profile_id:'basics',allowed_feed_ids:['water'],max_depth:8,max_processes:200,max_variants:128,max_resources:512})
  expect((body!.allowed_feed_ids as string[])).not.toContain('other')
  expect(body!.start_stock).toBeNull()
  fireEvent.click(screen.getByText('Advanced settings: Network bounds and initial stock'))
  const stockEditor=screen.getByRole('group',{name:'Declared initial stocks'})
  fireEvent.change(within(stockEditor).getByRole('combobox',{name:'Add declared initial stocks'}),{target:{value:'Water'}})
  fireEvent.click(await within(stockEditor).findByRole('option',{name:/Water.*test:0/}))
  fireEvent.click(within(stockEditor).getByRole('button',{name:'Add resource'}))
  fireEvent.change(screen.getByLabelText('Initial stock quantity for water'),{target:{value:'0'}})
  fireEvent.click(screen.getByRole('button',{name:'Run energy audit'}))
  await waitFor(()=>expect(body!.start_stock).toEqual({water:0}))
  fireEvent.change(screen.getByLabelText('Target quantity'),{target:{value:'2'}})
  expect(screen.queryByRole('region',{name:'Stoichiometric network result'})).not.toBeInTheDocument()
  expect(screen.getByText(/Settings changed/)).toBeInTheDocument()
})

test('network cards show complete canonical predicates while connections use resolved positive ledgers',async()=>{
  const ledger={status:'complete',yield_mode:'guaranteed' as const,consumed:{water:r(1)},produced:{hydrogen:r(1)},net:{water:r(-1),hydrogen:r(1)},presence:{},unsupported:[],assumptions:[]}
  const canonical={...process,inputs:[{role:'consume',choices:[{resource_id:'water',amount:1000,match:{mode:'exact'}},{resource_id:'other',amount:7,match:{mode:'exact'}}]}]}
  const report:NetworkWitnessReport={...empty,status:'complete',discovery:{...empty.discovery,processes:{benchmark:canonical},variants:[{variant_id:'variant',process_id:'benchmark',process,selections:{'0':{choice_index:0,resource_id:'water'}}}]},solutions:[{executions:[{variant_id:'variant',process_id:'benchmark',runs:r(1),selections:{'0':{choice_index:0,resource_id:'water'}},ledger}],ledger,net_imports:{water:r(1)},net_coproducts:{},nominal_energy:{status:'unknown',total_eu:null,eu_per_target:null,unknown_processes:['Duration is unknown']},integer_batch_scale:1,startup:{required_start_stock:{water:r(1)},final_stock:{hydrogen:r(1)},feasible:true},witness_verified:true}]}
  render(<NetworkResult report={report} onSelect={vi.fn()}/>)
  const tile=await screen.findByRole('article',{name:'Recipe Electrolyser'})
  expect(within(tile).getByText('OR')).toBeInTheDocument()
  expect(within(tile).getByText('Amount 7')).toBeInTheDocument()
  expect(screen.getAllByText('Unknown EU')).toHaveLength(2)
  expect(screen.getByText('Duration is unknown')).toBeInTheDocument()
  expect(screen.getByText(/does not establish a global optimum/)).toBeInTheDocument()
})

test('already-basic targets show assumed supplies without a fake recipe or no-solution message',async()=>{
  vi.stubGlobal('fetch',vi.fn(async()=>new Response(JSON.stringify({snapshot_id:'fixture',item:resources[0]}))))
  render(<NetworkResult report={{snapshot_id:'fixture',status:'complete',boundary:{resource_id:'water',amount:r(3)},base_requirements:{water:r(3)},solutions:[],profile,execution_scope:'assumed_external_feed_boundary',coverage_complete:true}} onSelect={vi.fn()}/>)
  expect(screen.getByText('Target is already a declared basic resource')).toBeInTheDocument()
  expect(await screen.findByText('Water',{selector:'button'})).toBeInTheDocument()
  expect(screen.queryByText(/No verified solution/)).not.toBeInTheDocument()
  expect(screen.queryByRole('region',{name:'Network recipe graph'})).not.toBeInTheDocument()
})

test('acquisition badges distinguish native replacement evidence from partial no-known-source suspicion',async()=>{
  vi.stubGlobal('fetch',vi.fn(async()=>new Response(JSON.stringify({snapshot_id:'fixture',item:resources[0]}))))
  render(<AcquisitionBadges resource={{...resources[2],acquisition_analysis:{unification:{status:'noncanonical_unification_variant',preferred_resource_ids:['water'],group_ids:['native-group'],evidence:'captured_native_unification_anchor'},acquisition:{status:'no_known_acquisition',source_count:0,eligible_producer_count:0,unresolved_producer_count:0,coverage_complete:false,reason:'Captured data has no known source'}}}} basic/>)
  expect(screen.getByText('Basic resource')).toBeInTheDocument()
  expect(screen.getByText('Noncanonical variant')).toBeInTheDocument()
  expect(screen.getByText('No known acquisition')).toBeInTheDocument()
  expect(screen.queryByText('Unobtainable')).not.toBeInTheDocument()
  await waitFor(()=>expect(screen.getByText('Noncanonical variant').closest('[title]')).toHaveAttribute('title',expect.stringContaining('Water')))
})

test('profile editing submits captured groups, namespaces and recipe families with the original revision',async()=>{
  const saved=vi.fn()
  let payload:Record<string,unknown>|undefined
  vi.stubGlobal('fetch',vi.fn(async(input:string,options?:RequestInit)=>{
    const url=new URL(input,'http://localhost')
    if(url.pathname==='/api/scope-catalog')return new Response(JSON.stringify({snapshot_id:'fixture',namespaces:[{id:'test',resources:3}],families:[{id:'test.recipe',processes:1}],unknown_namespace_count:2}))
    if(url.pathname.startsWith('/api/resources/'))return new Response(JSON.stringify({snapshot_id:'fixture',item:resources[2]}))
    if(url.pathname==='/api/resource-groups')return new Response(JSON.stringify({snapshot_id:'fixture',items:[{id:'g',name:'Metal choices',kind:'unified',members:['water','other'],member_count:2}],total:1,limit:20,offset:0}))
    if(url.pathname==='/api/groups/g')return new Response(JSON.stringify({snapshot_id:'fixture',item:{id:'g',name:'Metal choices',members:['water','other']}}))
    if(url.pathname==='/api/boundary-profiles/basics'){payload=JSON.parse(options!.body as string);return new Response(JSON.stringify({snapshot_id:'fixture',item:{...profile,...payload,revision:3}}))}
    throw new Error(`Unexpected ${input}`)
  }))
  render(<BoundaryProfileEditor snapshotId="fixture" profile={profile} onSaved={saved}/>)
  fireEvent.click(screen.getByText('Advanced: Profile identity and scope exclusions'))
  fireEvent.click(await screen.findByRole('checkbox',{name:'test 3 resources'}))
  fireEvent.click(screen.getByRole('checkbox',{name:'test.recipe 1 recipes'}))
  fireEvent.change(screen.getByLabelText('Search captured groups'),{target:{value:'metal'}})
  fireEvent.click(screen.getByRole('button',{name:'Find groups'}))
  fireEvent.click(await screen.findByRole('checkbox',{name:/Metal choices.*2 members/}))
  fireEvent.click(screen.getByRole('button',{name:'Save basic input set (profile)'}))
  await waitFor(()=>expect(saved).toHaveBeenCalledWith(expect.objectContaining({revision:3})))
  expect(payload).toMatchObject({expected_revision:2,base_resource_ids:['other'],scope:{excluded_group_ids:['g'],excluded_namespaces:['test'],excluded_family_ids:['test.recipe']}})
  expect(screen.getByText('Basic resource')).toBeInTheDocument()
})

test('basic planning requires a populated input set and explains an existing empty Energy profile',async()=>{
  const emptyProfile={...profile,id:'energy-only',name:'Exclusions only',base_resource_ids:[]}
  vi.stubGlobal('fetch',vi.fn(async(input:string)=>{
    const url=new URL(input,'http://localhost')
    if(url.pathname==='/api/boundary-profiles')return new Response(JSON.stringify({snapshot_id:'fixture',items:[emptyProfile,profile]}))
    if(url.pathname==='/api/resources')return new Response(JSON.stringify({snapshot_id:'fixture',items:[resources[1]],total:1,offset:0,limit:8}))
    if(url.pathname.startsWith('/api/resources/'))return new Response(JSON.stringify({snapshot_id:'fixture',item:resources[1]}))
    throw new Error(`Unexpected ${input}`)
  }))
  function Workspace(){
    const [active,setActive]=useState<BoundaryProfile>()
    return <NetworkAnalysis snapshotId="fixture" profile={active} onProfileChange={setActive} onSelect={vi.fn()}/>
  }
  render(<Workspace/>)
  fireEvent.click(screen.getByRole('button',{name:'Target from basics'}))
  expect(screen.getByText('Create or choose a basic input set, then select the supplies you want the plan to start from.')).toBeInTheDocument()
  expect(screen.getByRole('button',{name:'Run basic-resource plan'})).toBeDisabled()
  fireEvent.change(screen.getByRole('combobox',{name:'Target product'}),{target:{value:'Hydrogen'}})
  fireEvent.click(await screen.findByRole('option',{name:/Hydrogen.*test:1/}))
  expect(screen.getByRole('button',{name:'Run basic-resource plan'})).toBeDisabled()
  await screen.findByRole('option',{name:/Exclusions only/})
  fireEvent.change(screen.getByRole('combobox',{name:'Basic input set'}),{target:{value:emptyProfile.id}})
  expect(screen.getByRole('button',{name:'Run basic-resource plan'})).toBeDisabled()
  expect(screen.getByText('Edit this basic input set and add at least one basic resource before running the plan.')).toBeInTheDocument()
  fireEvent.change(screen.getByRole('combobox',{name:'Basic input set'}),{target:{value:profile.id}})
  await waitFor(()=>expect(screen.getByRole('button',{name:'Run basic-resource plan'})).toBeEnabled())
  expect(screen.getByText('Ready to plan from your selected basic inputs.')).toBeInTheDocument()
})

test('benchmark lookup failure explains the next step and retry does not submit a disabled energy audit',async()=>{
  let benchmarkFailed=true
  let analysisSubmitted=false
  vi.stubGlobal('fetch',vi.fn(async(input:string)=>{
    const url=new URL(input,'http://localhost')
    if(url.pathname==='/api/boundary-profiles')return new Response(JSON.stringify({snapshot_id:'fixture',items:[]}))
    if(url.pathname==='/api/resources')return new Response(JSON.stringify({snapshot_id:'fixture',items:resources.filter(item=>item.display_name===url.searchParams.get('q')),total:1,offset:0,limit:8}))
    if(url.pathname.startsWith('/api/resources/'))return new Response(JSON.stringify({snapshot_id:'fixture',item:resources.find(item=>url.pathname.endsWith(item.id))}))
    if(url.pathname==='/api/processes'){
      if(benchmarkFailed)return new Response(JSON.stringify({error:'Captured recipe lookup failed'}),{status:500})
      return new Response(JSON.stringify({snapshot_id:'fixture',items:[process],total:1,offset:0,limit:50}))
    }
    if(url.pathname==='/api/energy-audit'){analysisSubmitted=true;return new Response(JSON.stringify(empty))}
    throw new Error(`Unexpected ${input}`)
  }))
  render(<NetworkAnalysis snapshotId="fixture" onProfileChange={vi.fn()} onSelect={vi.fn()}/>)
  fireEvent.change(screen.getByRole('combobox',{name:'Primary feed (e.g. Water)'}),{target:{value:'Water'}})
  fireEvent.click(await screen.findByRole('option',{name:/Water.*test:0/}))
  fireEvent.change(screen.getByRole('combobox',{name:'Target product (e.g. Hydrogen)'}),{target:{value:'Hydrogen'}})
  fireEvent.click(await screen.findByRole('option',{name:/Hydrogen.*test:1/}))
  await screen.findByText('Benchmark recipes could not be loaded. Use Try again beside the benchmark selector.')
  expect(screen.getByRole('button',{name:'Run energy audit'})).toBeDisabled()
  benchmarkFailed=false
  fireEvent.click(screen.getByRole('button',{name:'Try again'}))
  await screen.findByRole('option',{name:/Electrolyser.*benchmark/})
  expect(analysisSubmitted).toBe(false)
})

test('basic planning starts with essential controls and saves an explicit input set using an automatic stable ID',async()=>{
  let savedProfile:BoundaryProfile|undefined
  let savedPayload:Record<string,unknown>|undefined
  let planningPayload:Record<string,unknown>|undefined
  vi.stubGlobal('fetch',vi.fn(async(input:string,options?:RequestInit)=>{
    const url=new URL(input,'http://localhost')
    if(url.pathname==='/api/boundary-profiles')return new Response(JSON.stringify({snapshot_id:'fixture',items:savedProfile?[savedProfile]:[]}))
    if(url.pathname==='/api/scope-catalog')return new Response(JSON.stringify({snapshot_id:'fixture',namespaces:[],families:[],unknown_namespace_count:0}))
    if(url.pathname==='/api/resources')return new Response(JSON.stringify({snapshot_id:'fixture',items:resources.filter(item=>item.display_name===url.searchParams.get('q')),total:1,offset:0,limit:8}))
    if(url.pathname.startsWith('/api/resources/'))return new Response(JSON.stringify({snapshot_id:'fixture',item:resources.find(item=>url.pathname.endsWith(item.id))}))
    if(url.pathname.startsWith('/api/boundary-profiles/')){
      savedPayload=JSON.parse(options!.body as string)
      savedProfile={id:decodeURIComponent(url.pathname.split('/').pop()!),name:savedPayload!.name as string,revision:1,base_resource_ids:savedPayload!.base_resource_ids as string[],scope:{},semantics:profile.semantics}
      return new Response(JSON.stringify({snapshot_id:'fixture',item:savedProfile}))
    }
    if(url.pathname==='/api/plan-to-bases'){planningPayload=JSON.parse(options!.body as string);return new Response(JSON.stringify(empty))}
    throw new Error(`Unexpected ${input}`)
  }))
  function Workspace(){
    const [active,setActive]=useState<BoundaryProfile>()
    return <NetworkAnalysis snapshotId="fixture" profile={active} onProfileChange={setActive} onSelect={vi.fn()}/>
  }
  render(<Workspace/>)
  fireEvent.change(screen.getByLabelText('Target quantity'),{target:{value:'2000'}})
  fireEvent.click(screen.getByRole('button',{name:'Target from basics'}))
  expect(screen.getByLabelText('Target quantity')).toHaveValue(1)
  expect(screen.getByLabelText('Target quantity')).not.toBeVisible()
  expect(screen.getByLabelText('Network yield mode')).not.toBeVisible()
  expect(screen.getByLabelText('Network objective')).not.toBeVisible()
  expect(screen.getByText(/LV machine casing/)).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button',{name:'Energy benchmark'}))
  expect(screen.getByLabelText('Target quantity')).toHaveValue(2000)
  fireEvent.click(screen.getByRole('button',{name:'Target from basics'}))
  expect(screen.getByLabelText('Target quantity')).toHaveValue(1)
  fireEvent.change(screen.getByRole('combobox',{name:'Target product'}),{target:{value:'Hydrogen'}})
  fireEvent.click(await screen.findByRole('option',{name:/Hydrogen.*test:1/}))
  fireEvent.click(screen.getByRole('button',{name:'Create basic input set'}))
  expect(screen.getByLabelText('Profile ID')).not.toBeVisible()
  expect(screen.getByRole('combobox',{name:'Add excluded resources'})).not.toBeVisible()
  const automaticId=(screen.getByLabelText('Profile ID') as HTMLInputElement).value
  const editor=screen.getByRole('region',{name:'Boundary profile editor'})
  fireEvent.change(within(editor).getByRole('textbox',{name:'Basic input set name'}),{target:{value:'Steel inputs'}})
  const save=within(editor).getByRole('button',{name:'Save basic input set (profile)'})
  expect(save).toBeDisabled()
  expect(within(editor).getByText('Add at least one basic resource before saving.')).toBeInTheDocument()
  fireEvent.change(within(editor).getByRole('combobox',{name:'Add basic resources'}),{target:{value:'Water'}})
  fireEvent.click(await within(editor).findByRole('option',{name:/Water.*test:0/}))
  expect(save).toBeDisabled()
  expect(within(editor).getByText('Add at least one basic resource before saving.')).toBeInTheDocument()
  fireEvent.click(within(within(editor).getByRole('group',{name:'Basic resources'})).getByRole('button',{name:'Add resource'}))
  expect(save).toBeEnabled()
  expect(screen.getByLabelText('Profile ID')).toHaveValue(automaticId)
  fireEvent.click(within(editor).getByRole('button',{name:'Save basic input set (profile)'}))
  await waitFor(()=>expect(screen.getByRole('combobox',{name:'Basic input set'})).toHaveValue(savedProfile!.id))
  expect(savedProfile!.id).toBe(automaticId)
  expect(savedProfile!.id).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i)
  expect(savedPayload).toMatchObject({name:'Steel inputs',base_resource_ids:['water'],scope:{},expected_revision:0})
  expect(screen.getByRole('button',{name:'Run basic-resource plan'})).toBeEnabled()
  fireEvent.click(screen.getByRole('button',{name:'Run basic-resource plan'}))
  await waitFor(()=>expect(planningPayload).toMatchObject({profile_id:savedProfile!.id,target_id:'hydrogen',target_amount:1,yield_mode:'guaranteed',objective:'recipe_runs',start_stock:null}))
})

test('energy boundary profiles may save an empty basic list for exclusion-only scope',async()=>{
  let payload:Record<string,unknown>|undefined
  vi.stubGlobal('fetch',vi.fn(async(input:string,options?:RequestInit)=>{
    const url=new URL(input,'http://localhost')
    if(url.pathname==='/api/boundary-profiles')return new Response(JSON.stringify({snapshot_id:'fixture',items:[]}))
    if(url.pathname==='/api/scope-catalog')return new Response(JSON.stringify({snapshot_id:'fixture',namespaces:[],families:[],unknown_namespace_count:0}))
    if(url.pathname.startsWith('/api/boundary-profiles/')){
      payload=JSON.parse(options!.body as string)
      return new Response(JSON.stringify({snapshot_id:'fixture',item:{id:url.pathname.split('/').pop(),...payload,revision:1,semantics:profile.semantics}}))
    }
    throw new Error(`Unexpected ${input}`)
  }))
  render(<NetworkAnalysis snapshotId="fixture" onProfileChange={vi.fn()} onSelect={vi.fn()}/>)
  fireEvent.click(screen.getByRole('button',{name:'Create boundary profile'}))
  const editor=screen.getByRole('region',{name:'Boundary profile editor'})
  fireEvent.change(within(editor).getByRole('textbox',{name:'Basic input set name'}),{target:{value:'Energy scope'}})
  const save=within(editor).getByRole('button',{name:'Save basic input set (profile)'})
  expect(save).toBeEnabled()
  expect(within(editor).queryByText('Add at least one basic resource before saving.')).not.toBeInTheDocument()
  fireEvent.click(save)
  await waitFor(()=>expect(payload).toMatchObject({name:'Energy scope',base_resource_ids:[],expected_revision:0}))
})
