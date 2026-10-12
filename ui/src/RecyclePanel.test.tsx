import { cleanup,fireEvent,render,screen,waitFor } from '@testing-library/react'
import { afterEach,expect,test,vi } from 'vitest'
import type { Process,Resource,Trace } from './api'
import { RecyclePanel } from './RecyclePanel'
import { InputSelections } from './InputSelections'

afterEach(()=>{cleanup();vi.unstubAllGlobals()})
const resources:Resource[]=['Start','Product','Byproduct','Circuit'].map((display_name,index)=>({id:`r${index}`,kind:'item',registry_name:`test:r${index}`,metadata:index,nbt:null,display_name,provenance:{}}))
const main:Process={id:'main',family:'test',display_name:'Main converter',inputs:[{role:'consume',choices:[{resource_id:'r0',amount:1,match:{mode:'exact'}}]}],outputs:[{resource_id:'r1',amount:1,chance:{numerator:1,denominator:1}},{resource_id:'r2',amount:2,chance:{numerator:1,denominator:1}}],duration_ticks:20,eu_per_tick:4,amperage:1,executable:true,conditions:{},provenance:{}}
const path={resource_ids:['r0','r1'],process_ids:['main']}
const trace:Trace={branch_coverage:[],path_selection:'diverse',snapshot_id:'fixture',start_id:'r0',target_id:'r1',resources,processes:[main],edges:[],leaves:[],cycles:[],truncated:false,coverage:[],route:{status:'found',strategy:'shortest_known_dependency_path',...path},paths:[path],search:{examined_processes:1,limit:10000,truncated:false},limit_reasons:[]}
const r=(numerator:number)=>({numerator,denominator:1})
const ledger={status:'complete',yield_mode:'guaranteed',consumed:{r0:r(1)},produced:{r0:r(2)},net:{r0:r(1)},presence:{r3:r(1)},unsupported:[],assumptions:[]}
const startup={required_start_stock:{r0:r(1)},final_stock:{r0:r(2)},feasible:true}

test('recycling forwards the chosen path, defaults return to its consumed input and renders owner recovery including surplus', async()=>{
  const calls:Record<string,unknown>[]=[]
  const overlay=vi.fn()
  vi.stubGlobal('fetch',vi.fn(async(input:string,options?:RequestInit)=>{
    const url=new URL(input,'http://localhost')
    if(url.pathname.startsWith('/api/resources/'))return new Response(JSON.stringify({snapshot_id:'fixture',item:resources.find(item=>url.pathname.endsWith(item.id))}))
    if(url.pathname==='/api/recycling-plan'){
      calls.push(JSON.parse(options!.body as string))
      return new Response(JSON.stringify({snapshot_id:'fixture',status:'complete',main_path:path,byproduct_id:'r2',return_id:'r0',yield_mode:'guaranteed',
        main_plan:{status:'complete',ledger,startup,byproduct_available:r(2),return_consumed:r(1),unsupported:[]},secondary_trace:{...trace,start_id:'r2',target_id:'r0'},limitations:['Native conditions remain requirements'],
        alternatives:[{path:{resource_ids:['r2','r0'],process_ids:['secondary']},status:'complete',ledger,startup,combined_ledger:ledger,combined_startup:startup,unsupported:[],external_inputs:[],
          recovery:{resource_id:'r0',main_consumed:r(1),side_produced:r(2),side_consumed:r(0),net_returned:r(2),main_input_returned_percent:r(200),usable_returned:r(1),surplus_returned:r(1)}}]}))
    }
    throw new Error(`Unexpected ${url.pathname}`)
  }))
  render(<RecyclePanel trace={trace} ownerId="main" byproductId="r2" tierOptions={{min_tier:1,max_tier:3,unknown_tier_policy:'exclude'}} onSelect={vi.fn()} onOverlay={overlay}/>)
  await waitFor(()=>expect(screen.getByRole('button',{name:'Inspect return paths and recovery'})).toBeEnabled())
  expect(screen.getByRole('combobox',{name:'Returned resource'})).toHaveValue('Start')
  fireEvent.click(screen.getByRole('button',{name:'Inspect return paths and recovery'}))
  expect(await screen.findByText('200%')).toBeInTheDocument()
  expect(screen.getByText('Usable returned')).toBeInTheDocument()
  expect(screen.getByText('Surplus returned')).toBeInTheDocument()
  expect(screen.getAllByText('Required starting stock')).toHaveLength(2)
  expect(screen.getAllByText('Nonconsumed presence')).toHaveLength(2)
  expect(calls[0]).toMatchObject({main_path:path,byproduct_id:'r2',return_id:'r0',main_runs:1,yield_mode:'guaranteed',min_tier:1,max_tier:3,unknown_tier_policy:'exclude'})
  fireEvent.click(screen.getByRole('button',{name:'Show connected return path in map'}))
  expect(overlay).toHaveBeenCalledWith(expect.objectContaining({main_path:path}),0)
  fireEvent.change(screen.getByLabelText('Main path runs'),{target:{value:'2'}})
  expect(screen.queryByText('200%')).not.toBeInTheDocument()
})

test('captured group inputs can be selected by a human without constructing JSON or using a UI matcher', async()=>{
  const changes=vi.fn()
  const grouped={...main,inputs:[{role:'presence',choices:[{resource_id:null,amount:1,match:{mode:'ore_dict',group_id:'g-circuit'}}]}]}
  vi.stubGlobal('fetch',vi.fn(async(input:string)=>{
    if(input.startsWith('/api/groups/'))return new Response(JSON.stringify({snapshot_id:'fixture',item:{id:'g-circuit',name:'Circuit choices',kind:'ore_dict',members:['r3']}}))
    if(input.startsWith('/api/resources/'))return new Response(JSON.stringify({snapshot_id:'fixture',item:resources[3]}))
    if(input.startsWith('/api/resources?'))return new Response(JSON.stringify({snapshot_id:'fixture',items:[resources[3]],total:1,offset:0,limit:8}))
    throw new Error(`Unexpected ${input}`)
  }))
  render(<InputSelections processes={[grouped]} selections={{}} resources={new Map(resources.map(item=>[item.id,item]))} onChange={changes}/>)
  fireEvent.click(screen.getByText('Slot 0 · presence · automatic / unresolved'))
  fireEvent.click(await screen.findByText('Browse captured group members (1)'))
  fireEvent.click(screen.getByRole('button',{name:'Choose member r3'}))
  expect(changes).toHaveBeenCalledWith('main','0',{choice_index:0,resource_id:'r3'})
})

test('group browsing does not reject a concrete NBT or wildcard variant before Dataset validation',async()=>{
  const changes=vi.fn()
  const variant={...resources[3],id:'variant',display_name:'Circuit variant',nbt:{type:'compound',value:{}}}
  const grouped={...main,inputs:[{role:'presence',choices:[{resource_id:null,amount:1,match:{mode:'ore_dict',group_id:'g-circuit'}}]}]}
  vi.stubGlobal('fetch',vi.fn(async(input:string)=>new Response(JSON.stringify(input.startsWith('/api/groups/')
    ? {snapshot_id:'fixture',item:{id:'g-circuit',members:['r3']}}
    : {snapshot_id:'fixture',items:[variant],total:1,offset:0,limit:8}))))
  render(<InputSelections processes={[grouped]} selections={{}} resources={new Map(resources.map(item=>[item.id,item]))} onChange={changes}/>)
  fireEvent.click(screen.getByText('Slot 0 · presence · automatic / unresolved'))
  await screen.findByText('Browse captured group members (1)')
  fireEvent.change(screen.getByRole('combobox',{name:'Concrete input for main slot 0'}),{target:{value:'Circuit'}})
  fireEvent.click(await screen.findByRole('option',{name:/Circuit variant/}))
  expect(changes).toHaveBeenCalledWith('main','0',{choice_index:0,resource_id:'variant'})
  expect(screen.queryByText('Choose a resource ID in this captured group')).not.toBeInTheDocument()
})

test('malformed advanced selection indices remain editable without crashing slot inspection',async()=>{
  const changes=vi.fn()
  render(<InputSelections processes={[main]} selections={{main:{'0':{choice_index:999,resource_id:'r0'}}}} resources={new Map(resources.map(item=>[item.id,item]))} onChange={changes}/>)
  fireEvent.click(screen.getByText('Slot 0 · consume · selected'))
  expect(await screen.findByRole('alert')).toHaveTextContent('Invalid input selection')
  fireEvent.change(screen.getByLabelText('Alternative for main slot 0'),{target:{value:'0'}})
  expect(changes).toHaveBeenCalledWith('main','0',{choice_index:0,resource_id:'r0'})
})
