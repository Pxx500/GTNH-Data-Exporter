import {cleanup,fireEvent,render,screen,waitFor,createEvent} from '@testing-library/react'
import {afterEach,expect,test,vi} from 'vitest'
import type {Process,Resource} from './api'
import {RecipeGraph} from './RecipeGraph'
import {toPng,toSvg} from 'html-to-image'
vi.mock('html-to-image',()=>({toPng:vi.fn(),toSvg:vi.fn()}))

afterEach(()=>{cleanup();vi.clearAllMocks()})
test('whole networks retain distinct recipe variants and real cycle connections without pretending they are paths',async()=>{
  const resources:Resource[]=['a','b'].map(id=>({id,kind:'item',registry_name:`test:${id}`,display_name:id,metadata:0,nbt:null,provenance:{}}))
  const process:Process={id:'native',family:'test',display_name:'Native recipe',inputs:[{role:'consume',choices:[{resource_id:'a',amount:2,match:{mode:'exact'}}]}],outputs:[{resource_id:'b',amount:1,chance:{numerator:1,denominator:1}}],duration_ticks:20,eu_per_tick:8,amperage:1,executable:true,conditions:{},provenance:{}}
  const inspect=vi.fn()
  render(<RecipeGraph graph={{resources,recipes:[{id:'variant-a',process,runs:{numerator:1,denominator:2}},{id:'variant-b',process,runs:{numerator:2,denominator:1}}],connections:[
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

test('ordinary wheel leaves page scrolling available and Ctrl wheel zooms on both canvas and recipe content',async()=>{
  const process:Process={id:'one',family:'test',display_name:'Wheel recipe',inputs:[],outputs:[],duration_ticks:20,eu_per_tick:8,amperage:1,executable:true,conditions:{},provenance:{}}
  const view=render(<RecipeGraph graph={{resources:[],recipes:[{id:'one',process}],connections:[]}} highlight={null} inspect={vi.fn()} inspectResource={vi.fn()}/>)
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
  render(<RecipeGraph graph={{resources:[],recipes:[{id:'one',process}],connections:[]}} highlight={null} inspect={vi.fn()} inspectResource={vi.fn()}/>)
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
  render(<RecipeGraph graph={{resources:[],recipes:[{id:'one',process}],connections:[]}} highlight={null} inspect={vi.fn()} inspectResource={vi.fn()}/>)
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
