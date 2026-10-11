import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import type { Process, Resource, Trace } from './api'
import { TraceView } from './TraceView'

afterEach(() => {cleanup(); vi.unstubAllGlobals()})
const resources: Resource[] = ['Crushed Iron Ore','Iron Nugget','Iron Ingot','Double Iron Plate','Side input mold'].map((display_name,index) => ({id:`r${index}`,display_name,registry_name:`fixture:r${index}`,kind:'item',metadata:index,nbt:null,provenance:{fixture:true}}))
const processes: Process[] = ['Furnace','Alloy Smelter','Bender'].map((display_name,index) => ({id:`p${index}`,display_name,family:display_name,inputs:[{role:'consume',choices:[{resource_id:`r${index}`,amount:1,match:{mode:'exact'}}]}],outputs:[{resource_id:`r${index+1}`,amount:1,chance:{numerator:1,denominator:1}}],duration_ticks:20,eu_per_tick:4,amperage:1,executable:true,conditions:{fixture:true},provenance:{fixture:true}}))
processes[1].inputs.push({role:'presence',choices:[{resource_id:'r4',amount:1,match:{mode:'exact'}}]})
const trace: Trace = {snapshot_id:'fixture',start_id:'r0',target_id:'r3',resources:[resources[4],resources[2],resources[0],resources[3],resources[1]],processes:[processes[2],processes[0],processes[1]],edges:[{source:'resource:r0',target:'process:p0',role:'consume'},{source:'process:p0',target:'resource:r1',role:'output'},{source:'resource:r1',target:'process:p1',role:'consume'},{source:'resource:r4',target:'process:p1',role:'presence'},{source:'process:p1',target:'resource:r2',role:'output'},{source:'resource:r2',target:'process:p2',role:'consume'},{source:'process:p2',target:'resource:r3',role:'output'}],leaves:[],cycles:[],truncated:false,coverage:[],route:{status:'found',strategy:'shortest_known_dependency_path',resource_ids:['r0','r1','r2','r3'],process_ids:['p0','p1','p2']},search:{examined_processes:37,limit:1000,truncated:false},limit_reasons:[]}

test('the selected route is ordered independently of context records and process clicks retain all input slots', async () => {
  vi.stubGlobal('fetch', vi.fn(async (input:string) => new Response(JSON.stringify({snapshot_id:'fixture',item:resources.find(resource => input.endsWith(resource.id))}))))
  render(<TraceView trace={trace} onSelect={vi.fn()}/>)
  const route = screen.getByRole('list',{name:'Selected main route'})
  expect(within(route).getAllByRole('button').map(button => button.textContent)).toEqual(['Crushed Iron Ore','Furnace','Iron Nugget','Alloy Smelter','Iron Ingot','Bender','Double Iron Plate'])
  expect(within(route).queryByText('Side input mold')).not.toBeInTheDocument()
  expect(screen.getByText('Shortest known route found')).toBeInTheDocument()
  fireEvent.click(within(route).getByRole('button',{name:'Inspect process Alloy Smelter'}))
  expect(screen.getByText('Required presence')).toBeInTheDocument()
  expect(await within(screen.getByRole('complementary')).findByText('Side input mold')).toBeInTheDocument()
  expect(screen.getByText('Conditions and research')).toBeInTheDocument()
})

test('not found is displayed as a scoped negative instead of a selected successful route', () => {
  render(<TraceView trace={{...trace,route:{...trace.route,status:'not_found',resource_ids:[],process_ids:[]},resources:[resources[0],resources[3]],processes:[],edges:[]}} onSelect={vi.fn()}/>)
  expect(screen.getByRole('heading',{name:'No known route found'})).toBeInTheDocument()
  expect(screen.queryByRole('list',{name:'Selected main route'})).not.toBeInTheDocument()
  expect(screen.queryByText('Shortest known route found')).not.toBeInTheDocument()
  expect(screen.getByText(/Coverage and unresolved mechanics still limit/)).toBeInTheDocument()
})

test('incomplete search reports the fixed server bound separately from context limits', () => {
  render(<TraceView trace={{...trace,truncated:true,route:{...trace.route,status:'incomplete',resource_ids:[],process_ids:[]},search:{examined_processes:1000,limit:1000,truncated:true},limit_reasons:['search_process_limit','context_process_limit']}} onSelect={vi.fn()}/>)
  expect(screen.getByRole('heading',{name:'Route discovery is incomplete'})).toBeInTheDocument()
  expect(screen.queryByRole('list',{name:'Selected main route'})).not.toBeInTheDocument()
  expect(screen.getByText(/Raising graph limits does not change this fixed search bound/)).toBeInTheDocument()
  expect(screen.getByText(/Supporting dependencies reached Maximum processes/)).toBeInTheDocument()
  expect(screen.getByText(/Search examined .* processes/)).toHaveTextContent('Search truncated')
})

test('same resource shows zero production steps without implying acquisition', () => {
  render(<TraceView trace={{...trace,target_id:'r0',route:{...trace.route,status:'same_resource',resource_ids:['r0'],process_ids:[]},resources:[resources[0]],processes:[],edges:[],search:{examined_processes:0,limit:1000,truncated:false}}} onSelect={vi.fn()}/>)
  expect(screen.getByRole('heading',{name:'Start and target are the same resource'})).toBeInTheDocument()
  expect(screen.getByText(/Zero production steps/)).toHaveTextContent('does not establish its availability or quantity')
  expect(screen.getByText('0 selected route steps')).toBeInTheDocument()
  expect(screen.queryByRole('button',{name:'Inspect process Furnace'})).not.toBeInTheDocument()
})
