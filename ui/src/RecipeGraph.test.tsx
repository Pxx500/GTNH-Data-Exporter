import {cleanup,fireEvent,render,screen,waitFor,createEvent,within} from '@testing-library/react'
import {afterEach,expect,test,vi} from 'vitest'
import type {Process,Resource,Trace} from './api'
import {RecipeGraph,recipeGraphForTrace} from './RecipeGraph'
import {toPng,toSvg} from 'html-to-image'
vi.mock('html-to-image',()=>({toPng:vi.fn(),toSvg:vi.fn()}))

afterEach(()=>{cleanup();vi.clearAllMocks()})
test('material groups show shared inputs once and keep auxiliary inputs, costs and exact inspection with each machine',async()=>{
  const resources:Resource[]=['Metal','Casing','Wrench','Programmed circuit'].map((display_name,index)=>({id:`r${index}`,display_name,registry_name:`test:r${index}`,kind:'item',metadata:0,nbt:null,provenance:{}}))
  const crafting:Process={id:'craft',family:'minecraft:crafting',display_name:'Crafted casing',inputs:[{role:'consume',choices:[{resource_id:'r0',amount:2,match:{mode:'exact'}}]},{role:'consume',choices:[{resource_id:'r2',amount:1,match:{mode:'exact'}}]}],outputs:[{resource_id:'r1',amount:1,chance:{numerator:1,denominator:1}}],duration_ticks:null,eu_per_tick:null,amperage:null,executable:true,conditions:{tool_accounting:'container_damage_and_breakage_unresolved'},provenance:{}}
  const assembler:Process={...crafting,id:'assemble',family:'assembler',display_name:'Assembled casing',inputs:[crafting.inputs[0],{role:'presence',choices:[{resource_id:'r3',amount:1,match:{mode:'exact'}}]}],duration_ticks:200,eu_per_tick:7680,amperage:1,conditions:{cleanroom:true}}
  const trace:Trace={path_selection:'material',branch_coverage:[],snapshot_id:'fixture',start_id:'r0',target_id:'r1',edges:[],leaves:[],cycles:[],truncated:false,coverage:[],route:{status:'found',strategy:'shortest_known_dependency_path',resource_ids:['r0','r1'],process_ids:['craft']},search:{examined_processes:2,limit:100,truncated:false},limit_reasons:[],path_groups:[{id:'path:casing',representative_path_index:0,path_indices:[0,1]}],resources,processes:[crafting,assembler],paths:[{resource_ids:['r0','r1'],process_ids:['craft']},{resource_ids:['r0','r1'],process_ids:['assemble']}],recipe_groups:[{id:'material:casing',basis:'declared_material_transformation',process_ids:['craft','assemble'],auxiliary_input_indices:{craft:[1],assemble:[1]}}]}
  const inspect=vi.fn()
  render(<RecipeGraph graph={recipeGraphForTrace(trace)} highlight={null} inspect={inspect} inspectResource={vi.fn()}/>)
  const tile=await screen.findByRole('article',{name:'Recipe Casing'})
  expect(screen.getAllByRole('article')).toHaveLength(1)
  expect(within(tile).getAllByRole('button',{name:'Metal'})).toHaveLength(1)
  expect(within(tile).getAllByRole('button',{name:'Casing'})).toHaveLength(1)
  const variants=within(tile).getByText('Machine variants (2)').closest('details')!
  expect(variants).not.toHaveAttribute('open')
  expect(within(tile).getByText('7680 EU/t')).not.toBeVisible()
  expect(within(tile).getByRole('button',{name:'Wrench'})).not.toBeVisible()
  fireEvent.click(within(tile).getByText('Machine variants (2)'))
  const craft=within(tile).getByRole('region',{name:'Variant Crafted casing'})
  const assemble=within(tile).getByRole('region',{name:'Variant Assembled casing'})
  expect(within(craft).getByRole('button',{name:'Wrench'})).toBeVisible()
  expect(within(craft).getByText('Unknown EU/t')).toBeVisible()
  expect(within(craft).queryByText('0 EU/t')).not.toBeInTheDocument()
  expect(within(assemble).getByRole('button',{name:'Programmed circuit'})).toBeVisible()
  expect(within(assemble).getByText('200 ticks')).toBeVisible()
  expect(within(assemble).getByText('7680 EU/t')).toBeVisible()
  fireEvent.click(within(assemble).getByRole('button',{name:'Inspect details'}))
  expect(inspect).toHaveBeenLastCalledWith('assemble')
  fireEvent.click(within(craft).getByText('Conditions and research'))
  expect(within(craft).getByText('container damage and breakage unresolved')).toBeVisible()
})

test('whole networks retain distinct recipe variants and real cycle connections without pretending they are paths',async()=>{
  const resources:Resource[]=['a','b'].map(id=>({id,kind:'item',registry_name:`test:${id}`,display_name:id,metadata:0,nbt:null,provenance:{}}))
  const process:Process={id:'native',family:'test',display_name:'Native recipe',inputs:[{role:'consume',choices:[{resource_id:'a',amount:2,match:{mode:'exact'}}]}],outputs:[{resource_id:'b',amount:1,chance:{numerator:1,denominator:1}}],duration_ticks:20,eu_per_tick:8,amperage:1,executable:true,conditions:{},provenance:{}}
  const inspect=vi.fn()
  render(<RecipeGraph graph={{resources,recipes:[{id:'variant-a',inspectId:'variant-a',process,runs:{numerator:1,denominator:2}},{id:'variant-b',inspectId:'variant-b',process,runs:{numerator:2,denominator:1}}],connections:[
    {id:'forward',source:'variant-a',target:'variant-b',resourceId:'b'},{id:'return',source:'variant-b',target:'variant-a',resourceId:'a'}]}} highlight={null} inspect={inspect} inspectResource={vi.fn()}/>)
  await waitFor(()=>expect(screen.getAllByRole('article',{name:'Recipe Native recipe'})).toHaveLength(2))
  expect(screen.getAllByText('Network recipe')).toHaveLength(2)
  expect(screen.getByText('Runs 1/2')).toBeInTheDocument()
  expect(screen.getByText('Runs 2')).toBeInTheDocument()
  expect(screen.queryByText('Path 1')).not.toBeInTheDocument()
  fireEvent.click(screen.getAllByRole('button',{name:'Process Native recipe'})[1])
  expect(inspect).toHaveBeenCalledWith('variant-b')
  expect(document.querySelectorAll('.react-flow__edge')).toHaveLength(2)
})

test('recycling uses the current selected-path action when highlight changes on an existing board',async()=>{
  const resources:Resource[]=['a','b'].map(id=>({id,kind:'item',registry_name:`test:${id}`,display_name:id,metadata:0,nbt:null,provenance:{}}))
  const process:Process={id:'native',family:'test',display_name:'Shared finish',inputs:[],outputs:[{resource_id:'b',amount:1,chance:{numerator:1,denominator:1}}],duration_ticks:20,eu_per_tick:8,amperage:1,executable:true,conditions:{},provenance:{}}
  const graph={resources,recipes:[{id:'material-group',inspectId:process.id,process,paths:[0,1]}],connections:[]}
  const firstPath=vi.fn(),secondPath=vi.fn(),inspect=vi.fn(),inspectResource=vi.fn()
  const view=render(<RecipeGraph graph={graph} highlight={0} inspect={inspect} inspectResource={inspectResource} recycle={firstPath}/>)
  const output=await screen.findByRole('button',{name:'Recycle output b'})
  view.rerender(<RecipeGraph graph={graph} highlight={1} inspect={inspect} inspectResource={inspectResource} recycle={secondPath}/>)
  fireEvent.click(output)
  expect(secondPath).toHaveBeenCalledWith('native','b')
  expect(firstPath).not.toHaveBeenCalled()
})

test('ordinary wheel leaves page scrolling available and Ctrl wheel zooms on both canvas and recipe content',async()=>{
  const process:Process={id:'one',family:'test',display_name:'Wheel recipe',inputs:[],outputs:[],duration_ticks:20,eu_per_tick:8,amperage:1,executable:true,conditions:{},provenance:{}}
  const view=render(<RecipeGraph graph={{resources:[],recipes:[{id:'one',inspectId:'one',process}],connections:[]}} highlight={null} inspect={vi.fn()} inspectResource={vi.fn()}/>)
  const tile=await screen.findByRole('article',{name:'Recipe Wheel recipe'})
  const pane=view.container.querySelector('.react-flow__pane')!
  const viewport=view.container.querySelector('.react-flow__viewport') as HTMLElement
  await waitFor(()=>expect(viewport.style.transform).toContain('scale('))
  for(const target of [pane,tile.querySelector('.process-detail')!]){
    const before=viewport.style.transform
    const ordinary=createEvent.wheel(target,{deltaY:80,bubbles:true,cancelable:true})
    fireEvent(target,ordinary)
    expect(ordinary.defaultPrevented).toBe(false)
    expect(viewport.style.transform).toBe(before)
    const modified=createEvent.wheel(target,{deltaY:-80,ctrlKey:true,bubbles:true,cancelable:true,clientX:100,clientY:100})
    fireEvent(target,modified)
    expect(modified.defaultPrevented).toBe(true)
    await waitFor(()=>expect(viewport.style.transform).not.toBe(before))
  }
})

test('export has visible pending and retryable failure states, prevents duplicate exports',async()=>{
  const process:Process={id:'one',family:'test',display_name:'Export recipe',inputs:[],outputs:[],duration_ticks:null,eu_per_tick:null,amperage:null,executable:true,conditions:{},provenance:{}}
  let fail:(error:Error)=>void=()=>{}
  vi.mocked(toPng).mockImplementation(()=>new Promise((_,reject)=>{fail=reject}))
  render(<RecipeGraph graph={{resources:[],recipes:[{id:'one',inspectId:'one',process}],connections:[]}} highlight={null} inspect={vi.fn()} inspectResource={vi.fn()}/>)
  const png=await screen.findByRole('button',{name:'Export whole board PNG'})
  const svg=screen.getByRole('button',{name:'Export whole board SVG'})
  await waitFor(()=>expect(png).toBeEnabled())
  fireEvent.click(png)
  await waitFor(()=>expect(toPng).toHaveBeenCalledTimes(1))
  expect(png).toBeDisabled()
  expect(svg).toBeDisabled()
  expect(screen.getByText('Exporting the whole board as PNG…')).toBeInTheDocument()
  fireEvent.click(png)
  expect(toPng).toHaveBeenCalledTimes(1)
  fail(new Error('Browser rendering failed'))
  await screen.findByRole('alert')
  expect(screen.getByRole('alert')).toHaveTextContent('Try SVG')
  expect(png).toBeEnabled()
  expect(svg).toBeEnabled()
})

test.each(['png','svg'] as const)('successful %s export keeps a real download link above the canvas without another render',async format=>{
  const process:Process={id:'one',family:'test',display_name:'Download recipe',inputs:[],outputs:[],duration_ticks:null,eu_per_tick:null,amperage:null,executable:true,conditions:{},provenance:{}}
  const dataUrl=format==='png'?'data:image/png;base64,captured':`data:image/svg+xml;charset=utf-8,${encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg"><foreignObject/></svg>')}`
  const renderer=format==='png'?vi.mocked(toPng):vi.mocked(toSvg)
  renderer.mockResolvedValue(dataUrl)
  render(<RecipeGraph graph={{resources:[],recipes:[{id:'one',inspectId:'one',process}],connections:[]}} highlight={null} inspect={vi.fn()} inspectResource={vi.fn()}/>)
  const button=screen.getByRole('button',{name:`Export whole board ${format.toUpperCase()}`})
  await waitFor(()=>expect(button).toBeEnabled())
  fireEvent.click(button)
  const link=await screen.findByRole('link',{name:`Download ${format.toUpperCase()}`})
  expect(link).toHaveAttribute('download',`recipe-board.${format}`)
  expect(link.getAttribute('href')).toMatch(new RegExp(`^data:image/${format==='png'?'png':'svg\\+xml'};`))
  const actions=screen.getByRole('region',{name:'Recipe board actions'})
  expect(actions).toContainElement(link)
  expect(screen.getByRole('application')).not.toContainElement(actions)
  const href=link.getAttribute('href')
  renderer.mockRejectedValue(new Error('A later render failed'))
  fireEvent.click(button)
  await screen.findByRole('alert')
  expect(screen.getByRole('link',{name:`Download ${format.toUpperCase()}`})).toHaveAttribute('href',href)
})
