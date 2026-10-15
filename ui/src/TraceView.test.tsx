import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import type { Process, Resource, Trace } from './api'
import { TraceView } from './TraceView'

afterEach(() => {cleanup(); vi.unstubAllGlobals()})
test('complete alternative paths share recipe tiles and never add unrelated support or cross-links', async () => {
  const dust: Resource = {id:'dust',display_name:'Iron Dust',registry_name:'fixture:dust',kind:'item',metadata:0,nbt:null,provenance:{}}
  const crusher = {...processes[0],id:'crusher',display_name:'Crusher',outputs:[{resource_id:'dust',amount:1,chance:{numerator:1,denominator:1}}]}
  const smelter = {...processes[1],id:'direct',display_name:'Direct smelter',inputs:[{role:'consume',choices:[{resource_id:'dust',amount:1,match:{mode:'exact'}}]}]}
  const unrelated = {...processes[0],id:'unrelated',display_name:'Random support recipe'}
  const {rerender}=render(<TraceView trace={{...trace,resources:[...trace.resources,dust],processes:[...trace.processes,crusher,smelter,unrelated],paths:[{resource_ids:['r0','r1','r2','r3'],process_ids:['p0','p1','p2']},{resource_ids:['r0','dust','r2','r3'],process_ids:['crusher','direct','p2']}]}} onSelect={vi.fn()}/>)
  const graph = screen.getByRole('region',{name:'Recipe path graph'})
  await within(graph).findByRole('article',{name:'Recipe Bender'})
  expect(within(graph).getAllByRole('article',{name:'Recipe Bender'})).toHaveLength(1)
  expect(within(graph).getAllByRole('article')).toHaveLength(5)
  expect(within(graph).queryByText('Random support recipe')).not.toBeInTheDocument()
  const links = screen.getByRole('list',{name:'Direct recipe connections'})
  expect(within(links).getByText('Crusher → Direct smelter')).toBeInTheDocument()
  expect(within(links).getByText('Direct smelter → Bender')).toBeInTheDocument()
  expect(within(links).queryByText('Furnace → Direct smelter')).not.toBeInTheDocument()
  fireEvent.change(screen.getByLabelText('Highlight path'),{target:{value:'1'}})
  fireEvent.click(within(graph).getByRole('button',{name:'Process Bender'}))
  expect(within(screen.getByRole('complementary')).getByRole('heading',{name:'Bender'})).toBeInTheDocument()
  rerender(<TraceView trace={trace} onSelect={vi.fn()}/>)
  await waitFor(()=>expect(within(graph).getAllByRole('article')).toHaveLength(3))
  expect(within(graph).queryByRole('article',{name:'Recipe Crusher'})).not.toBeInTheDocument()
})
const resources: Resource[] = ['Crushed Iron Ore','Iron Nugget','Iron Ingot','Double Iron Plate','Side input mold'].map((display_name,index) => ({id:`r${index}`,display_name,registry_name:`fixture:r${index}`,kind:'item',metadata:index,nbt:null,provenance:{fixture:true}}))
test('missing graph resource opens local details and production recipes, and Escape returns focus to the board',async()=>{
  const navigate=vi.fn()
  vi.stubGlobal('fetch',vi.fn(async(input:string)=>{
    const url=new URL(input,'http://localhost')
    if(url.pathname.startsWith('/api/resources/'))return new Response(JSON.stringify({snapshot_id:'fixture',item:resources[4]}))
    if(url.pathname==='/api/processes')return new Response(JSON.stringify({snapshot_id:'fixture',items:[],total:0,offset:0,limit:5}))
    throw new Error(`Unexpected ${url.pathname}`)
  }))
  render(<TraceView trace={{...trace,resources:resources.slice(0,4)}} onSelect={navigate}/>)
  const tile=await screen.findByRole('article',{name:'Recipe Alloy Smelter'})
  const opener=await within(tile).findByRole('button',{name:'Side input mold'})
  opener.focus()
  fireEvent.click(opener)
  const inspector=await screen.findByRole('complementary',{name:'Record inspector'})
  expect(await within(inspector).findByRole('heading',{name:'Side input mold'})).toBeInTheDocument()
  expect(navigate).not.toHaveBeenCalled()
  fireEvent.click(within(inspector).getByText('Production recipes in dump'))
  expect(await within(inspector).findByText('0 matching production recipes')).toBeInTheDocument()
  const close=within(inspector).getByRole('button',{name:'Close record inspector'})
  close.focus()
  fireEvent.keyDown(close,{key:'Escape'})
  expect(screen.queryByRole('complementary')).not.toBeInTheDocument()
  expect(opener).toHaveFocus()
  expect(screen.getByRole('article',{name:'Recipe Alloy Smelter'})).toBe(tile)
})
const processes: Process[] = ['Furnace','Alloy Smelter','Bender'].map((display_name,index) => ({id:`p${index}`,display_name,family:display_name,inputs:[{role:'consume',choices:[{resource_id:`r${index}`,amount:1,match:{mode:'exact'}}]}],outputs:[{resource_id:`r${index+1}`,amount:1,chance:{numerator:1,denominator:1}}],duration_ticks:20,eu_per_tick:4,amperage:1,executable:true,conditions:{fixture:true},provenance:{fixture:true}}))
processes[1].inputs.push({role:'presence',choices:[{resource_id:'r4',amount:1,match:{mode:'exact'}}]})
const trace: Trace = {branch_coverage:[],path_selection:'diverse',snapshot_id:'fixture',start_id:'r0',target_id:'r3',resources:[resources[4],resources[2],resources[0],resources[3],resources[1]],processes:[processes[2],processes[0],processes[1]],edges:[{source:'resource:r0',target:'process:p0',role:'consume'},{source:'process:p0',target:'resource:r1',role:'output'},{source:'resource:r1',target:'process:p1',role:'consume'},{source:'resource:r4',target:'process:p1',role:'presence'},{source:'process:p1',target:'resource:r2',role:'output'},{source:'resource:r2',target:'process:p2',role:'consume'},{source:'process:p2',target:'resource:r3',role:'output'}],leaves:[],cycles:[],truncated:false,coverage:[],route:{status:'found',strategy:'shortest_known_dependency_path',resource_ids:['r0','r1','r2','r3'],process_ids:['p0','p1','p2']},search:{examined_processes:37,limit:1000,truncated:false},limit_reasons:[],paths:[{resource_ids:['r0','r1','r2','r3'],process_ids:['p0','p1','p2']}]}

test('material path explanations identify their target ingredient branch and honest secondary-output hints',()=>{
  render(<TraceView trace={{...trace,path_selection:'material',path_details:[{path_index:0,selection_reason:'Prioritized native material continuity and target ingredient coverage',material_continuity:'supported',byproduct_steps:[{process_id:'p0',resource_id:'r1',basis:'secondary_output_position_hint'}],target_process_id:'p2',target_slot_index:1,scope:'dependency_spine_with_external_inputs'}]}} onSelect={vi.fn()}/>)
  expect(screen.getByText(/Results prioritize native material continuity/)).toBeInTheDocument()
  const paths=screen.getByText('Ordered paths and explanations (1)').closest('details')!
  paths.setAttribute('open','')
  expect(within(paths).getByText('Prioritized native material continuity and target ingredient coverage')).toBeVisible()
  expect(within(paths).getByText(/Material continuity hint: supported/)).toHaveTextContent('input 2')
  expect(within(paths).getByText(/Other recipe inputs still need external supplies/)).toBeVisible()
  expect(within(paths).getByText(/Native output order is a hint/)).toBeVisible()
  expect(within(paths).queryByText('Crafting tool category:')).not.toBeInTheDocument()
  expect(screen.queryByText(/Excluded groups on paths:/)).not.toBeInTheDocument()
})

test('applied group exclusions retain their native kinds and counts without resetting graph inspection',async()=>{
  const ore={group_id:'ore:nuggetIron',name:'nuggetIron',kind:'ore_dict',member_count:5}
  const unified={group_id:'unified:nuggetIron',name:'nuggetIron',kind:'unified',member_count:3}
  const {rerender}=render(<TraceView trace={{...trace,group_exclusions:[ore,unified]}} onSelect={vi.fn()}/>)
  const note=screen.getByText(/Excluded groups on paths:/)
  expect(note).toHaveTextContent('nuggetIron (ore_dict, 5 members), nuggetIron (unified, 3 members)')
  expect(note).toHaveAttribute('title','Exclusions use literal captured members on paths. Other recipe inputs remain visible.')
  fireEvent.change(screen.getByLabelText('Highlight path'),{target:{value:'0'}})
  const tile=await screen.findByRole('article',{name:'Recipe Alloy Smelter'})
  fireEvent.click(within(tile).getByRole('button',{name:'Process Alloy Smelter'}))
  expect(within(screen.getByRole('complementary')).getByText('Required presence')).toBeInTheDocument()
  rerender(<TraceView trace={{...trace,group_exclusions:[ore]}} onSelect={vi.fn()}/>)
  expect(screen.getByText(/Excluded groups on paths:/)).toHaveTextContent('nuggetIron (ore_dict, 5 members)')
  expect(screen.getByText(/Excluded groups on paths:/)).not.toHaveTextContent('unified')
  expect(screen.getByLabelText('Highlight path')).toHaveValue('0')
  expect(screen.getByRole('article',{name:'Recipe Alloy Smelter'})).toBe(tile)
  expect(within(screen.getByRole('complementary')).getByText('Required presence')).toBeInTheDocument()
})

test.each([
  {basis:'exact_captured_ore_dictionary_membership' as const,description:'Captured OreDictionary membership for this literal registered variant.'},
  {basis:'native_ore_dictionary_matching_membership' as const,description:'Native OreDictionary matching uses the item and metadata, including registered wildcards, and ignores NBT.'},
])('category hints explain $basis and preserve local inspection and graph state',async({basis,description})=>{
  const navigate=vi.fn()
  const wrench={...resources[1],display_name:'Steel Wrench'}
  vi.stubGlobal('fetch',vi.fn(async(input:string)=>new Response(JSON.stringify({snapshot_id:'fixture',item:input.endsWith('r1')?wrench:resources.find(resource=>input.endsWith(resource.id))}))))
  const {rerender}=render(<TraceView trace={{...trace,resources:trace.resources.map(resource=>resource.id==='r1'?wrench:resource),paths:[trace.paths[0],trace.paths[0]],path_details:[{path_index:0,selection_reason:'Selected dependency branch',material_continuity:'partial',byproduct_steps:[],target_process_id:'p2',target_slot_index:0,scope:'dependency_spine_with_external_inputs',input_category_hints:[{step_index:1,process_id:'p1',resource_id:'r1',category:'crafting_tool',basis,group_ids:['ore:craftingToolWrench'],input_role:'consume',native_accounting:{tool_accounting:'container_damage_and_breakage_unresolved',container_returns:'native_unknown',input_accounting:'declared_consumption_without_container_return_credit'},scope:'selected_resource_category_only'}]}]}} onSelect={navigate}/>)
  const graph=screen.getByRole('region',{name:'Recipe path graph'})
  const tile=await within(graph).findByRole('article',{name:'Recipe Alloy Smelter'})
  fireEvent.change(screen.getByLabelText('Highlight path'),{target:{value:'1'}})
  const paths=screen.getByText('Ordered paths and explanations (2)').closest('details')!
  paths.setAttribute('open','')
  const hintedPath=within(paths).getByRole('heading',{name:'Path 1 · 3 steps'}).closest('section')!
  const otherPath=within(paths).getByRole('heading',{name:'Path 2 · 3 steps'}).closest('section')!
  const label=within(hintedPath).getByText('Crafting tool category:')
  const note=label.closest('p')!
  expect(note).toHaveTextContent('Steel Wrench at step 2 (Alloy Smelter)')
  expect(label).toHaveAttribute('title','Category membership does not determine actual tool use, wear or material contribution.')
  expect(within(note).getByTitle(description)).toHaveTextContent('Steel Wrench at step 2 (Alloy Smelter)')
  expect(note).toHaveTextContent('See the recipe for other inputs and consumption')
  expect(within(otherPath).queryByText('Crafting tool category:')).not.toBeInTheDocument()
  fireEvent.click(within(note).getByRole('button',{name:'Steel Wrench'}))
  expect(await within(screen.getByRole('complementary')).findByRole('heading',{name:'Steel Wrench'})).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button',{name:'Close record inspector'}))
  fireEvent.click(within(note).getByRole('button',{name:'Alloy Smelter'}))
  expect(within(screen.getByRole('complementary')).getByText('Required presence')).toBeInTheDocument()
  expect(screen.getByLabelText('Highlight path')).toHaveValue('1')
  expect(within(graph).getByRole('article',{name:'Recipe Alloy Smelter'})).toBe(tile)
  expect(navigate).not.toHaveBeenCalled()
  rerender(<TraceView trace={{...trace,path_details:[{path_index:0,selection_reason:'Selected dependency branch',material_continuity:'partial',byproduct_steps:[],target_process_id:'p2',target_slot_index:0,scope:'dependency_spine_with_external_inputs',input_category_hints:[]}]}} onSelect={navigate}/>)
  expect(within(paths).queryByText('Crafting tool category:')).not.toBeInTheDocument()
})

test('narrow inspector keeps its close control outside the scrolling content and Escape restores graph focus',async()=>{
  vi.stubGlobal('innerWidth',754)
  render(<TraceView trace={trace} onSelect={vi.fn()}/>)
  const graph=screen.getByRole('region',{name:'Recipe path graph'})
  const opener=await within(graph).findByRole('button',{name:'Process Alloy Smelter'})
  opener.focus()
  fireEvent.click(opener)
  const inspector=screen.getByRole('complementary',{name:'Record inspector'})
  const close=within(inspector).getByRole('button',{name:'Close record inspector'})
  const record=within(inspector).getByRole('heading',{name:'Alloy Smelter'})
  expect(close.closest('header')).toBeInTheDocument()
  expect(close.closest('header')).not.toContainElement(record)
  expect(close).toHaveFocus()
  fireEvent.keyDown(close,{key:'Escape'})
  expect(screen.queryByRole('complementary')).not.toBeInTheDocument()
  expect(opener).toHaveFocus()
  expect(screen.getByRole('region',{name:'Recipe path graph'})).toBe(graph)
})
test('recycled returns connect every accounted consumer and skip the unselected OR alternative',async()=>{
  const r=(numerator:number)=>({numerator,denominator:1})
  const choice=(resource_id:string)=>({resource_id,amount:1,match:{mode:'exact'}})
  const extra:Resource[]=['Byproduct','Other OR input'].map((display_name,index)=>({...resources[0],id:`extra${index}`,registry_name:`fixture:extra${index}`,display_name}))
  const mainProcesses=processes.map(process=>({...process,inputs:[...process.inputs],outputs:[...process.outputs]}))
  mainProcesses[0].inputs.push({role:'consume',choices:[choice('r4'),choice('extra1')]})
  mainProcesses[0].outputs.push({resource_id:'extra0',amount:1,chance:r(1)})
  mainProcesses[1].inputs.push({role:'consume',choices:[choice('r4')]})
  mainProcesses[2].inputs.push({role:'consume',choices:[choice('r4')]})
  const side={...processes[0],id:'side',display_name:'Side recycler',inputs:[{role:'consume',choices:[choice('extra0')]}],outputs:[{resource_id:'r4',amount:2,chance:r(1)}]}
  const allResources=[...resources,...extra]
  const fullTrace={...trace,resources:allResources,processes:mainProcesses,edges:[...trace.edges,{source:'resource:r4',target:'process:p0',role:'consume'},{source:'resource:r4',target:'process:p1',role:'consume'},{source:'resource:r4',target:'process:p2',role:'consume'}]}
  const ledger=(consumed:Record<string,ReturnType<typeof r>>)=>({status:'complete',yield_mode:'guaranteed',consumed,produced:{},net:{},presence:{},unsupported:[],assumptions:[]})
  vi.stubGlobal('fetch',vi.fn(async(input:string)=>{
    const url=new URL(input,'http://localhost')
    if(url.pathname.startsWith('/api/resources/'))return new Response(JSON.stringify({snapshot_id:'fixture',item:allResources.find(item=>url.pathname.endsWith(item.id))}))
    if(url.pathname==='/api/resources')return new Response(JSON.stringify({snapshot_id:'fixture',items:[resources[4]],total:1,offset:0,limit:8}))
    if(url.pathname==='/api/recycling-plan')return new Response(JSON.stringify({snapshot_id:'fixture',status:'complete',main_path:trace.paths[0],byproduct_id:'extra0',return_id:'r4',yield_mode:'guaranteed',limitations:[],
      main_plan:{status:'complete',ledger:ledger({r4:r(2)}),selected_inputs:{p0:{'1':{choice_index:1,resource_id:'extra1'}},p1:{'2':{choice_index:0,resource_id:'r4'}},p2:{'1':{choice_index:0,resource_id:'r4'}}},
        startup:{required_start_stock:{},final_stock:{},feasible:true,steps:[{process_id:'p0',ledger:ledger({r0:r(1),extra1:r(1)})},{process_id:'p1',ledger:ledger({r1:r(1),r4:r(1)})},{process_id:'p2',ledger:ledger({r2:r(1),r4:r(1)})}]},byproduct_available:r(1),return_consumed:r(2),unsupported:[]},
      secondary_trace:{...trace,resources:allResources,processes:[side]},alternatives:[{path:{resource_ids:['extra0','r4'],process_ids:['side']},status:'complete',ledger:null,startup:null,combined_ledger:null,combined_startup:null,recovery:null,external_inputs:[],unsupported:[]}]}))
    throw new Error(`Unexpected ${url.pathname}`)
  }))
  render(<TraceView trace={fullTrace} onSelect={vi.fn()}/>)
  fireEvent.click(await within(screen.getByRole('region',{name:'Recipe path graph'})).findByRole('button',{name:'Recycle output extra0'}))
  fireEvent.change(screen.getByRole('combobox',{name:'Returned resource'}),{target:{value:'mold'}})
  fireEvent.click(await screen.findByRole('option',{name:/Side input mold/}))
  fireEvent.click(screen.getByRole('button',{name:'Inspect return paths and recovery'}))
  fireEvent.click(await screen.findByRole('button',{name:'Show connected return path in map'}))
  expect(screen.getByText('Returned input: Side recycler → Alloy Smelter · Side input mold')).toBeInTheDocument()
  expect(screen.getByText('Returned input: Side recycler → Bender · Side input mold')).toBeInTheDocument()
  expect(screen.queryByText('Returned input: Side recycler → Furnace · Side input mold')).not.toBeInTheDocument()
})

test('the selected route is ordered independently of context records and process clicks retain all input slots', async () => {
  vi.stubGlobal('fetch', vi.fn(async (input:string) => new Response(JSON.stringify({snapshot_id:'fixture',item:resources.find(resource => input.endsWith(resource.id))}))))
  render(<TraceView trace={trace} onSelect={vi.fn()}/>)
  const route = screen.getByRole('region',{name:'Recipe path graph'})
  await within(route).findByRole('article',{name:'Recipe Furnace'})
  expect(within(route).getAllByRole('article').map(tile => tile.getAttribute('aria-label'))).toEqual(['Recipe Furnace','Recipe Alloy Smelter','Recipe Bender'])
  expect(screen.getByText('Known paths found')).toBeInTheDocument()
  fireEvent.click(within(route).getByRole('button',{name:'Process Alloy Smelter'}))
  expect(within(screen.getByRole('complementary')).getByText('Required presence')).toBeInTheDocument()
  expect(await within(screen.getByRole('complementary')).findByText('Side input mold')).toBeInTheDocument()
  expect(within(screen.getByRole('complementary')).getByText('Conditions and research')).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button',{name:'Close record inspector'}))
  expect(screen.queryByRole('complementary')).not.toBeInTheDocument()
  expect(within(route).getAllByRole('article')).toHaveLength(3)
})

test('recipe graph arranges intrinsic card measurements without imposing a shared fixed width',async()=>{
  const widths:Record<string,number>={p0:280,p1:420,p2:360}
  const heights:Record<string,number>={p0:220,p1:400,p2:160}
  const width=vi.spyOn(HTMLElement.prototype,'offsetWidth','get').mockImplementation(function(this:HTMLElement){return parseFloat(this.style.width)||widths[this.dataset.id??'']||1000})
  const height=vi.spyOn(HTMLElement.prototype,'offsetHeight','get').mockImplementation(function(this:HTMLElement){return parseFloat(this.style.height)||heights[this.dataset.id??'']||350})
  try{
    render(<TraceView trace={trace} onSelect={vi.fn()}/>)
    const furnace=(await screen.findByRole('article',{name:'Recipe Furnace'})).closest('.react-flow__node') as HTMLElement
    const alloy=screen.getByRole('article',{name:'Recipe Alloy Smelter'}).closest('.react-flow__node') as HTMLElement
    const position=(node:HTMLElement)=>node.style.transform.match(/translate\(([\d.-]+)px,\s*([\d.-]+)px\)/)!.slice(1).map(Number)
    await waitFor(()=>expect(position(alloy)[1]).toBeGreaterThan(0))
    expect(furnace.style.width).toBe('')
    expect(alloy.style.width).toBe('')
    expect(position(furnace)[0]+widths.p0/2).toBe(position(alloy)[0]+widths.p1/2)
    expect(position(alloy)[1]-position(furnace)[1]).toBeGreaterThanOrEqual(heights.p0)
    expect(screen.getByRole('button',{name:'Arrange recipes'})).toBeInTheDocument()
    expect(screen.getByRole('button',{name:'Recycle output r1'})).toBeInTheDocument()
  }finally{width.mockRestore();height.mockRestore()}
})

test('whole recipe tiles retain OR slots and co-products along complete emitted paths', async () => {
  const furnace = {...processes[0],outputs:[{resource_id:'r1',amount:2,chance:{numerator:1,denominator:1}},{resource_id:'r4',amount:3,chance:{numerator:1,denominator:4}}]}
  const alloy: Process = {...processes[1],inputs:[{role:'consume',choices:[{resource_id:null,amount:9,match:{mode:'ore_dict',group_id:'g-iron'}},{resource_id:'r1',amount:4,match:{mode:'exact'}}]},{role:'presence',choices:[{resource_id:'r4',amount:1,match:{mode:'exact'}}]},{role:'tool',choices:[{resource_id:'r4',amount:1,match:{mode:'exact'}}]}]}
  const zero = {...processes[0],id:'zero',display_name:'Zero producer',outputs:[{resource_id:'r1',amount:0,chance:{numerator:0,denominator:1}}]}
  const edges = trace.edges.map(edge => edge.target === 'process:p1' ? {...edge,slot_index:edge.source === 'resource:r4' ? 1 : 0,choice_index:0} : edge.target.startsWith('process:') ? {...edge,slot_index:0,choice_index:0} : edge)
  const fetch = vi.fn()
  vi.stubGlobal('fetch',fetch)
  render(<TraceView trace={{...trace,processes:[zero,processes[2],furnace,alloy],edges:[...edges,{source:'process:zero',target:'resource:r1',role:'output'}]}} onSelect={vi.fn()}/>)
  const furnaceTile = await screen.findByRole('article',{name:'Recipe Furnace'})
  expect(within(furnaceTile).getByText('Amount 2')).toBeInTheDocument()
  expect(within(furnaceTile).getByText('Amount 3')).toBeInTheDocument()
  expect(within(furnaceTile).getByText('Chance 25%')).toBeInTheDocument()
  const alloyTile = screen.getByRole('article',{name:'Recipe Alloy Smelter'})
  expect(within(alloyTile).getByText('Amount 9')).toBeInTheDocument()
  expect(within(alloyTile).getByText('Amount 4')).toBeInTheDocument()
  expect(within(alloyTile).getByText('OR')).toBeInTheDocument()
  expect(within(alloyTile).getByText('Required presence')).toBeInTheDocument()
  expect(within(alloyTile).getByText('Tool')).toBeInTheDocument()
  const links = screen.getByRole('list',{name:'Direct recipe connections'})
  expect(within(links).getByText('Furnace → Alloy Smelter')).toBeInTheDocument()
  expect(within(links).getByText('Alloy Smelter → Bender')).toBeInTheDocument()
  expect(within(links).queryByText('Zero producer → Alloy Smelter')).not.toBeInTheDocument()
  expect(screen.queryByRole('article',{name:'Recipe Zero producer'})).not.toBeInTheDocument()
  expect(fetch).not.toHaveBeenCalled()
})

test('not found is displayed as a scoped negative instead of a selected successful route', () => {
  render(<TraceView trace={{...trace,route:{...trace.route,status:'not_found',resource_ids:[],process_ids:[]},resources:[resources[0],resources[3]],processes:[],edges:[],paths:[]}} onSelect={vi.fn()}/>)
  expect(screen.getByRole('heading',{name:'No known route found'})).toBeInTheDocument()
  expect(screen.queryByRole('list',{name:'Selected main route'})).not.toBeInTheDocument()
  expect(screen.queryByText('Shortest known route found')).not.toBeInTheDocument()
  expect(screen.getByText(/Coverage and unresolved mechanics still limit/)).toBeInTheDocument()
})

test('incomplete search reports the fixed server bound separately from context limits', () => {
  render(<TraceView trace={{...trace,truncated:true,route:{...trace.route,status:'incomplete',resource_ids:[],process_ids:[]},paths:[],search:{examined_processes:1000,limit:1000,truncated:true},limit_reasons:['search_process_limit','path_process_limit']}} onSelect={vi.fn()}/>)
  expect(screen.getByRole('heading',{name:'Route discovery is incomplete'})).toBeInTheDocument()
  expect(screen.queryByRole('list',{name:'Selected main route'})).not.toBeInTheDocument()
  expect(screen.getByText(/Graph controls do not change that server bound/)).toBeInTheDocument()
  expect(screen.getByText(/An additional complete path exceeded the included recipe limit/)).toBeInTheDocument()
  expect(screen.getByText(/Search examined .* processes/)).toHaveTextContent('Search truncated')
})

test('same resource shows zero production steps without implying acquisition', () => {
  render(<TraceView trace={{...trace,target_id:'r0',route:{...trace.route,status:'same_resource',resource_ids:['r0'],process_ids:[]},resources:[resources[0]],processes:[],edges:[],paths:[{resource_ids:['r0'],process_ids:[]}],search:{examined_processes:0,limit:1000,truncated:false}}} onSelect={vi.fn()}/>)
  expect(screen.getByRole('heading',{name:'Start and target are the same resource'})).toBeInTheDocument()
  expect(screen.getByText(/Zero production steps/)).toHaveTextContent('does not establish its availability or quantity')
  expect(screen.getByText('0 primary path steps')).toBeInTheDocument()
  expect(screen.queryByRole('button',{name:'Inspect process Furnace'})).not.toBeInTheDocument()
})

test('a zero-step material path does not invent a target recipe or input branch',()=>{
  render(<TraceView trace={{...trace,path_selection:'material',target_id:'r0',route:{...trace.route,status:'same_resource',resource_ids:['r0'],process_ids:[]},resources:[resources[0]],processes:[],edges:[],paths:[{resource_ids:['r0'],process_ids:[]}],path_details:[{path_index:0,selection_reason:'No recipe step',material_continuity:'partial',byproduct_steps:[],target_process_id:null,target_slot_index:null,scope:'dependency_spine_with_external_inputs'}]}} onSelect={vi.fn()}/>)
  expect(screen.queryByText(/Target ingredient branch/)).not.toBeInTheDocument()
  expect(screen.queryByText(/input 1/)).not.toBeInTheDocument()
})

test('verified crafting-grid voltage is shown as not applicable instead of unknown',async()=>{
  render(<TraceView trace={{...trace,recipe_tiers:[{process_id:'p0',status:'not_applicable',tier:null,name:null,scope:'crafting_grid_not_recipe_voltage',reason:'Verified static GT shaped crafting-grid recipe has no machine voltage requirement'}]}} onSelect={vi.fn()}/>)
  fireEvent.click(await screen.findByRole('button',{name:'Process Furnace'}))
  expect(screen.getByText(/Selected recipe voltage: No machine voltage requirement/)).toBeInTheDocument()
  expect(screen.queryByText(/Selected recipe voltage: Unknown/)).not.toBeInTheDocument()
})
