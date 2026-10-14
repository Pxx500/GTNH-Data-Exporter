import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import App from './App'
import type { Process, Resource } from './api'

afterEach(() => {cleanup(); vi.unstubAllGlobals()})
const resource: Resource = {id:'resource/opaque:1',kind:'item',registry_name:'test:mold',display_name:'Test mold',metadata:0,nbt:null,provenance:{}}
const process: Process = {id:'process/opaque:1',family:'test',display_name:'Mold cast',inputs:[{role:'presence',choices:[{resource_id:resource.id,amount:1,match:{mode:'exact'}}]}],outputs:[{resource_id:resource.id,amount:1,chance:{numerator:1,denominator:1}}],duration_ticks:20,eu_per_tick:4,amperage:1,executable:true,conditions:{},provenance:{}}
const status = {snapshot_id:'test-snapshot',manifest:{created_at:'2026-10-11',capture:{kind:'synthetic'},pack:{name:'Synthetic contract fixture'}},counts:{resources:1,groups:0,processes:1,sources:0,environments:0,coverage:1},coverage:[{id:'coverage',domain:'test',status:'partial',records:1,reason:'Fixture only',provenance:{}}]}
function response(value: unknown, code=200) { return new Response(JSON.stringify(value), {status:code,headers:{'Content-Type':'application/json'}}) }
function page(items: unknown[]) {return {snapshot_id:'test-snapshot',items,total:items.length,limit:30,offset:0}}

test('analysis exposes distinct energy benchmark and target-from-basics modes with explicit profile semantics',async()=>{
  vi.stubGlobal('fetch',vi.fn(async(input:string)=>{
    const url=new URL(input,'http://localhost')
    if(url.pathname==='/api/status')return response(status)
    if(url.pathname==='/api/resources' || url.pathname==='/api/environments')return response(page([]))
    if(url.pathname==='/api/boundary-profiles')return response({snapshot_id:'test-snapshot',items:[]})
    throw new Error(`Unexpected ${url.pathname}`)
  }))
  render(<App/>)
  await screen.findByText('Pack: Synthetic contract fixture')
  fireEvent.click(screen.getByRole('button',{name:'Analysis'}))
  expect(screen.getByRole('heading',{name:'Production energy benchmark'})).toBeInTheDocument()
  expect(screen.getByText(/Profile basics are not implicit energy feeds/)).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button',{name:'Target from basics'}))
  expect(screen.getByRole('heading',{name:'Target from basic resources'})).toBeInTheDocument()
})

test('shows captured mod inventory and native lifecycle when the manifest has no pack name or capture kind', async () => {
  const nativeStatus = {...status, manifest:{created_at:'2026-10-12',
    pack:{mods:[{id:'gregtech',version:'5.09.54.221'},{id:'Forestry',version:'4.11.39'}],config_script_digests:[],context:'configured native registries, no observed deposit scan'},
    capture:{lifecycle:'integrated-world-server-tick-end',client_world_attached:true,server_started:true}}}
  vi.stubGlobal('fetch',vi.fn(async(input:string)=>{
    const url=new URL(input,'http://localhost')
    if(url.pathname==='/api/status')return response(nativeStatus)
    if(url.pathname==='/api/resources' || url.pathname==='/api/environments')return response(page([]))
    throw new Error(`Unexpected route ${url.pathname}`)
  }))
  render(<App/>)
  expect(await screen.findByText('Pack identity: 2 captured mods')).toBeInTheDocument()
  expect(screen.getByText('Capture lifecycle: integrated-world-server-tick-end')).toBeInTheDocument()
  expect(screen.queryByText(/Name not captured|Kind not captured/)).not.toBeInTheDocument()
  expect(screen.queryByText('Synthetic verification data')).not.toBeInTheDocument()
})

test('labels synthetic data and forwards trace controls to Dataset while retaining complete-path bounds', async () => {
  const targetResource={...resource,id:'result-id',display_name:'Test output'}
  const recipe={...process,inputs:[{role:'consume',choices:[{resource_id:resource.id,amount:1,match:{mode:'exact'}}]},...process.inputs],outputs:[{resource_id:targetResource.id,amount:1,chance:{numerator:1,denominator:1}}]}
  const traceCalls: URL[]=[]
  let currentStatus=status
  vi.stubGlobal('fetch',vi.fn(async(input:string)=>{
    const url=new URL(input,'http://localhost')
    if(url.pathname==='/api/status')return response(currentStatus)
    if(url.pathname==='/api/resources')return response(page(url.searchParams.get('q')==='Test output' ? [targetResource] : [resource]))
    if(url.pathname==='/api/environments')return response(page([]))
    if(url.pathname.startsWith('/api/resources/'))return response({snapshot_id:'test-snapshot',item:url.pathname.endsWith('result-id') ? targetResource : resource})
    if(url.pathname==='/api/trace'){
      traceCalls.push(url)
      return response({branch_coverage:[],path_selection:'shortest',snapshot_id:'test-snapshot',start_id:resource.id,target_id:targetResource.id,resources:[resource,targetResource],processes:[recipe],edges:[],leaves:[],cycles:[],truncated:true,coverage:status.coverage,route:{status:'found',strategy:'shortest_known_dependency_path',resource_ids:[resource.id,targetResource.id],process_ids:[recipe.id]},paths:[{resource_ids:[resource.id,targetResource.id],process_ids:[recipe.id]}],search:{examined_processes:37,limit:1000,truncated:false},limit_reasons:['path_process_limit']})
    }
    throw new Error(`Unexpected route ${url.pathname}`)
  }))
  render(<App/>)
  expect(await screen.findByText('Synthetic verification data')).toBeInTheDocument()
  expect(screen.getByText('Pack: Synthetic contract fixture')).toBeInTheDocument()
  expect(screen.getByText('Capture: synthetic')).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button',{name:/^Trace$/}))
  expect(screen.getByLabelText('Route selection')).toHaveValue('material')
  expect(screen.getByLabelText('Additional steps')).toHaveValue(6)
  expect(screen.getByLabelText('Maximum processes')).toHaveValue(150)
  const start=screen.getByLabelText('Supplied start resource')
  fireEvent.focus(start);fireEvent.change(start,{target:{value:'Test mold'}})
  fireEvent.click(await screen.findByRole('option',{name:/Test mold/}))
  const target=screen.getByLabelText('Target resource')
  fireEvent.focus(target);fireEvent.change(target,{target:{value:'Test output'}})
  fireEvent.click(await screen.findByRole('option',{name:/Test output/}))
  fireEvent.change(screen.getByLabelText('Maximum depth'),{target:{value:'7'}})
  fireEvent.change(screen.getByLabelText('Maximum processes'),{target:{value:'25'}})
  fireEvent.change(screen.getByLabelText('Paths'),{target:{value:'4'}})
  fireEvent.change(screen.getByLabelText('Additional steps'),{target:{value:'3'}})
  fireEvent.change(screen.getByLabelText('Route selection'),{target:{value:'shortest'}})
  fireEvent.change(screen.getByLabelText('Minimum recipe voltage tier'),{target:{value:'1'}})
  fireEvent.change(screen.getByLabelText('Maximum recipe voltage tier'),{target:{value:'3'}})
  fireEvent.change(screen.getByLabelText('Unknown recipe voltage'),{target:{value:'include'}})
  fireEvent.click(screen.getByRole('button',{name:'Trace dependencies'}))
  expect(await screen.findByText('Bounded trace has omitted work')).toBeInTheDocument()
  expect(traceCalls[0].searchParams.get('start_id')).toBe(resource.id)
  expect(traceCalls[0].searchParams.get('target_id')).toBe(targetResource.id)
  expect(traceCalls[0].searchParams.get('max_depth')).toBe('7')
  expect(traceCalls[0].searchParams.get('max_processes')).toBe('25')
  expect(traceCalls[0].searchParams.get('max_paths')).toBe('4')
  expect(traceCalls[0].searchParams.get('max_extra_steps')).toBe('3')
  expect(traceCalls[0].searchParams.get('path_selection')).toBe('shortest')
  expect(traceCalls[0].searchParams.get('min_tier')).toBe('1')
  expect(traceCalls[0].searchParams.get('max_tier')).toBe('3')
  expect(traceCalls[0].searchParams.get('unknown_tier_policy')).toBe('include')
  fireEvent.click(screen.getByRole('button',{name:'Process Mold cast'}))
  expect(within(screen.getByRole('complementary')).getByText('Required presence')).toBeInTheDocument()
  expect(within(screen.getByRole('complementary')).queryByText(/Chance 100%/)).not.toBeInTheDocument()
  fireEvent.change(screen.getByLabelText('Highlight path'),{target:{value:'0'}})
  const tile=screen.getByRole('article',{name:'Recipe Mold cast'}).closest('.react-flow__node')!
  const viewport=tile.closest('.react-flow__viewport') as HTMLElement
  const originalPosition=(tile as HTMLElement).style.transform
  const movableTile=tile as HTMLElement
  movableTile.focus()
  fireEvent.keyDown(tile,{key:'ArrowRight'})
  await waitFor(()=>expect((tile as HTMLElement).style.transform).not.toBe(originalPosition))
  const position=(tile as HTMLElement).style.transform
  const originalCamera=viewport.style.transform
  fireEvent.wheel(tile,{deltaY:-80,ctrlKey:true,clientX:100,clientY:100})
  await waitFor(()=>expect(viewport.style.transform).not.toBe(originalCamera))
  const camera=viewport.style.transform
  fireEvent.click(within(screen.getByRole('region',{name:'Target-directed route'})).getByRole('button',{name:'Test output'}))
  fireEvent.click(screen.getByRole('button',{name:'Open in Library'}))
  fireEvent.click(screen.getByRole('button',{name:'Trace'}))
  expect(screen.getByLabelText('Maximum depth')).toHaveValue(7)
  expect(screen.getByLabelText('Highlight path')).toHaveValue('0')
  expect(screen.getByRole('article',{name:'Recipe Mold cast'}).closest('.react-flow__node')).toBe(tile)
  expect(tile.closest('.react-flow__viewport')).toBe(viewport)
  expect((tile as HTMLElement).style.transform).toBe(position)
  expect(viewport.style.transform).toBe(camera)
  expect(traceCalls).toHaveLength(1)
  currentStatus={...status,snapshot_id:'next-snapshot'}
  fireEvent.click(screen.getByRole('button',{name:'Refresh'}))
  await screen.findByText('next-snapshot')
  expect(screen.getByLabelText('Maximum depth')).toHaveValue(12)
  expect(screen.queryByLabelText('Highlight path')).not.toBeInTheDocument()
})

test('concrete intermediate tags forward repeated IDs and changing filters invalidates the displayed result', async () => {
  const catalog = ['Start ore','Target plate','Iron Dust','Purified Dust','Iron Nugget'].map((display_name,index)=>({...resource,id:`opaque:${index}`,display_name,metadata:index}))
  const calls: URL[]=[]
  vi.stubGlobal('fetch',vi.fn(async(input:string)=>{
    const url=new URL(input,'http://localhost')
    if(url.pathname==='/api/status')return response(status)
    if(url.pathname==='/api/environments')return response(page([]))
    if(url.pathname==='/api/resources')return response(page(catalog.filter(item=>item.display_name===url.searchParams.get('q'))))
    if(url.pathname.startsWith('/api/resources/'))return response({snapshot_id:'test-snapshot',item:catalog.find(item=>item.id===decodeURIComponent(url.pathname.split('/').pop()!))})
    if(url.pathname==='/api/trace'){
      calls.push(url)
      return response({branch_coverage:[],path_selection:'shortest',snapshot_id:'test-snapshot',start_id:catalog[0].id,target_id:catalog[1].id,resources:catalog,processes:[],edges:[],leaves:[],cycles:[],truncated:false,coverage:[],route:{status:'not_found',strategy:'shortest_known_dependency_path',resource_ids:[],process_ids:[]},paths:[],search:{examined_processes:5,limit:10000,truncated:false},limit_reasons:[]})
    }
    throw new Error(`Unexpected route ${url.pathname}`)
  }))
  render(<App/>)
  await screen.findByText('Synthetic verification data')
  fireEvent.click(screen.getByRole('button',{name:/^Trace$/}))
  async function choose(label:string,name:string){
    const input=screen.getByRole('combobox',{name:label})
    fireEvent.focus(input)
    fireEvent.change(input,{target:{value:name}})
    fireEvent.click(await screen.findByRole('option',{name:new RegExp(name)}))
  }
  await choose('Supplied start resource','Start ore')
  await choose('Target resource','Target plate')
  await choose('Required intermediate','Iron Dust')
  fireEvent.click(screen.getByRole('button',{name:'Add required material'}))
  await choose('Required intermediate','Purified Dust')
  fireEvent.click(screen.getByRole('button',{name:'Add required material'}))
  await choose('Excluded intermediate','Iron Nugget')
  fireEvent.click(screen.getByRole('button',{name:'Add excluded material'}))
  fireEvent.click(screen.getByRole('button',{name:'Trace dependencies'}))
  expect(await screen.findByRole('heading',{name:'No known route found'})).toBeInTheDocument()
  expect(calls[0].searchParams.getAll('required_resource_id')).toEqual(['opaque:2','opaque:3'])
  expect(calls[0].searchParams.getAll('excluded_resource_id')).toEqual(['opaque:4'])
  fireEvent.click(screen.getByRole('button',{name:'Remove required material opaque:2'}))
  expect(screen.queryByRole('heading',{name:'No known route found'})).not.toBeInTheDocument()
  expect(screen.getByText(/Search selections or filters changed/)).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button',{name:'Trace dependencies'}))
  await screen.findByRole('heading',{name:'No known route found'})
  expect(calls[1].searchParams.getAll('required_resource_id')).toEqual(['opaque:3'])
})

test('typing iron dust and iron plate selects concrete IDs, and later editing invalidates the selection', async () => {
  const dust = {...resource,id:'opaque/dust:17',registry_name:'gregtech:meta',display_name:'Iron Dust',metadata:241}
  const plate = {...resource,id:'opaque/plate:29',registry_name:'gregtech:meta',display_name:'Iron Plate',metadata:1241}
  const calls: URL[] = []
  vi.stubGlobal('fetch', vi.fn(async (input: string) => {
    const url = new URL(input,'http://localhost')
    if (url.pathname === '/api/status') return response(status)
    if (url.pathname === '/api/resources') return response(page(url.searchParams.get('q') === 'iron dust' ? [dust] : url.searchParams.get('q') === 'iron plate' ? [plate] : []))
    if (url.pathname === '/api/environments') return response(page([]))
    if (url.pathname.startsWith('/api/resources/')) return response({snapshot_id:'test-snapshot',item:decodeURIComponent(url.pathname.split('/').pop()!) === dust.id ? dust : plate})
    if (url.pathname === '/api/trace') {calls.push(url); return response({branch_coverage:[],path_selection:'shortest',snapshot_id:'test-snapshot',start_id:dust.id,target_id:plate.id,resources:[],processes:[],edges:[],leaves:[],cycles:[],truncated:false,coverage:[],route:{status:'not_found',strategy:'shortest_known_dependency_path',resource_ids:[],process_ids:[]},search:{examined_processes:0,limit:1000,truncated:false},limit_reasons:[],paths:[]})}
    throw new Error(`Unexpected route ${url.pathname}`)
  }))
  render(<App/>)
  await screen.findByText('Synthetic verification data')
  fireEvent.click(screen.getByRole('button',{name:/^Trace$/}))
  const start = screen.getByRole('combobox',{name:'Supplied start resource'})
  const target = screen.getByRole('combobox',{name:'Target resource'})
  const submit = screen.getByRole('button',{name:'Trace dependencies'})
  expect(submit).toBeDisabled()
  expect(screen.getByText('Select a supplied start and a target from the search results.')).toBeInTheDocument()
  fireEvent.focus(start)
  fireEvent.change(start,{target:{value:'iron dust'}})
  expect(await screen.findByRole('option',{name:/Iron Dust.*metadata 241/})).toBeInTheDocument()
  fireEvent.keyDown(start,{key:'ArrowDown'})
  fireEvent.keyDown(start,{key:'Enter'})
  expect(start).toHaveValue('Iron Dust')
  expect(submit).toBeDisabled()
  fireEvent.focus(target)
  fireEvent.change(target,{target:{value:'iron plate'}})
  await screen.findByRole('option',{name:/Iron Plate.*metadata 1241/})
  fireEvent.keyDown(target,{key:'ArrowDown'})
  fireEvent.keyDown(target,{key:'Enter'})
  expect(submit).toBeEnabled()
  expect(screen.getByText('Ready to find paths between the selected resources.')).toBeInTheDocument()
  fireEvent.click(submit)
  await waitFor(() => expect(calls).toHaveLength(1))
  expect(calls[0].searchParams.get('start_id')).toBe(dust.id)
  expect(calls[0].searchParams.get('target_id')).toBe(plate.id)
  fireEvent.change(target,{target:{value:'iron'}})
  expect(submit).toBeDisabled()
  expect(screen.getByText('Select a target from the search results.')).toBeInTheDocument()
  fireEvent.keyDown(target,{key:'Escape'})
  expect(screen.queryByRole('listbox')).not.toBeInTheDocument()
})

test('a late result for an earlier query cannot replace current candidates or select the wrong identity', async () => {
  const dust = {...resource,id:'dust-id',display_name:'Iron Dust'}
  const plate = {...resource,id:'plate-id',display_name:'Iron Plate'}
  let finishOld: ((value: Response) => void) | undefined
  vi.stubGlobal('fetch', vi.fn(async (input: string) => {
    const url = new URL(input,'http://localhost')
    if (url.pathname === '/api/status') return response(status)
    if (url.pathname === '/api/environments') return response(page([]))
    if (url.pathname.startsWith('/api/resources/')) return response({snapshot_id:'test-snapshot',item:plate})
    if (url.pathname === '/api/resources') {
      if (url.searchParams.get('q') === 'iron') return new Promise<Response>(resolve => {finishOld = resolve})
      return response(page(url.searchParams.get('q') === 'iron plate' ? [plate] : []))
    }
    throw new Error(`Unexpected route ${url.pathname}`)
  }))
  render(<App/>)
  await screen.findByText('Synthetic verification data')
  fireEvent.click(screen.getByRole('button',{name:/^Trace$/}))
  const target = screen.getByRole('combobox',{name:'Target resource'})
  fireEvent.focus(target)
  fireEvent.change(target,{target:{value:'iron'}})
  await waitFor(() => expect(finishOld).toBeDefined())
  fireEvent.change(target,{target:{value:'iron plate'}})
  expect(await screen.findByRole('option',{name:/Iron Plate/})).toBeInTheDocument()
  await act(async () => finishOld!(response(page([dust]))))
  expect(screen.queryByRole('option',{name:/Iron Dust/})).not.toBeInTheDocument()
  fireEvent.keyDown(target,{key:'ArrowDown'})
  fireEvent.keyDown(target,{key:'Enter'})
  expect(target).toHaveValue('Iron Plate')
  expect(await screen.findByText('Resource ID: plate-id')).toBeInTheDocument()
})

test('library actions hydrate both resource names while retaining their selected IDs', async () => {
  const dust = {...resource,id:'dust-id',display_name:'Iron Dust'}
  const plate = {...resource,id:'plate-id',display_name:'Iron Plate'}
  vi.stubGlobal('fetch', vi.fn(async (input: string) => {
    const url = new URL(input,'http://localhost')
    if (url.pathname === '/api/status') return response(status)
    if (url.pathname === '/api/resources') return response(page([dust,plate]))
    if (url.pathname === '/api/environments' || url.pathname === '/api/processes') return response(page([]))
    if (url.pathname.startsWith('/api/resources/')) return response({snapshot_id:'test-snapshot',item:url.pathname.endsWith('dust-id') ? dust : plate})
    throw new Error(`Unexpected route ${url.pathname}`)
  }))
  render(<App/>)
  fireEvent.click(await screen.findByRole('button',{name:/Iron Dust.*test:mold/}))
  fireEvent.click(await screen.findByRole('button',{name:'Use as supplied start'}))
  await waitFor(() => expect(screen.getByRole('combobox',{name:'Supplied start resource'})).toHaveValue('Iron Dust'))
  fireEvent.click(screen.getByRole('button',{name:'Library'}))
  fireEvent.click(await screen.findByRole('button',{name:/Iron Plate.*test:mold/}))
  fireEvent.click(await screen.findByRole('button',{name:'Trace this target'}))
  await waitFor(() => {
    expect(screen.getByRole('combobox',{name:'Supplied start resource'})).toHaveValue('Iron Dust')
    expect(screen.getByRole('combobox',{name:'Target resource'})).toHaveValue('Iron Plate')
    expect(screen.getByRole('button',{name:'Trace dependencies'})).toBeEnabled()
  })
  expect(screen.getByText('Resource ID: dust-id')).toBeInTheDocument()
  expect(screen.getByText('Resource ID: plate-id')).toBeInTheDocument()
})
