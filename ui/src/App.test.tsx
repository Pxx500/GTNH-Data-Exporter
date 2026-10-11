import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import App from './App'
import type { Process, Resource } from './api'

afterEach(() => {cleanup(); vi.unstubAllGlobals()})
const resource: Resource = {id:'resource/opaque:1',kind:'item',registry_name:'test:mold',display_name:'Test mold',metadata:0,nbt:null,provenance:{}}
const process: Process = {id:'process/opaque:1',family:'test',display_name:'Mold cast',inputs:[{role:'presence',choices:[{resource_id:resource.id,amount:1,match:{mode:'exact'}}]}],outputs:[{resource_id:resource.id,amount:1,chance:{numerator:1,denominator:1}}],duration_ticks:20,eu_per_tick:4,amperage:1,executable:true,conditions:{},provenance:{}}
const status = {snapshot_id:'test-snapshot',manifest:{created_at:'2026-10-11',capture:{kind:'synthetic'},pack:{name:'Synthetic contract fixture'}},counts:{resources:1,groups:0,processes:1,sources:0,environments:0,coverage:1},coverage:[{id:'coverage',domain:'test',status:'partial',records:1,reason:'Fixture only',provenance:{}}]}
function response(value: unknown, code=200) { return new Response(JSON.stringify(value), {status:code,headers:{'Content-Type':'application/json'}}) }
function page(items: unknown[]) {return {snapshot_id:'test-snapshot',items,total:items.length,limit:30,offset:0}}

test('labels synthetic data and forwards trace controls to Dataset, retaining cycles and truncation', async () => {
  const traceCalls: URL[] = []
  vi.stubGlobal('fetch', vi.fn(async (input: string) => {
    const url = new URL(input,'http://localhost')
    if (url.pathname === '/api/status') return response(status)
    if (url.pathname === '/api/resources') return response(page([resource]))
    if (url.pathname === '/api/environments') return response(page([]))
    if (url.pathname.startsWith('/api/resources/')) return response({snapshot_id:'test-snapshot',item:resource})
    if (url.pathname === '/api/trace') {
      traceCalls.push(url)
      return response({snapshot_id:'test-snapshot',start_id:resource.id,target_id:resource.id,resources:[resource],processes:[process],edges:[{source:`resource:${resource.id}`,target:`process:${process.id}`,role:'presence'},{source:`process:${process.id}`,target:`resource:${resource.id}`,role:'output'}],leaves:[{resource_id:resource.id,status:'assumed',sources:[]}],cycles:[[`resource:${resource.id}`,`process:${process.id}`]],truncated:true,coverage:status.coverage})
    }
    throw new Error(`Unexpected route ${url.pathname}`)
  }))
  render(<App/>)
  expect(await screen.findByText('Synthetic verification data')).toBeInTheDocument()
  expect(screen.getByText('Pack: Synthetic contract fixture')).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button',{name:/^Trace$/}))
  const start = screen.getByLabelText('Supplied start resource')
  fireEvent.focus(start)
  fireEvent.change(start,{target:{value:'Test mold'}})
  fireEvent.click(await screen.findByRole('option',{name:/Test mold/}))
  const target = screen.getByLabelText('Target resource')
  fireEvent.focus(target)
  fireEvent.change(target,{target:{value:'Test mold'}})
  fireEvent.click(await screen.findByRole('option',{name:/Test mold/}))
  fireEvent.change(screen.getByLabelText('Maximum depth'),{target:{value:'7'}})
  fireEvent.change(screen.getByLabelText('Maximum processes'),{target:{value:'25'}})
  fireEvent.click(screen.getByRole('button',{name:'Trace dependencies'}))
  expect(await screen.findByText('Dependency expansion was truncated')).toBeInTheDocument()
  expect(screen.getByText('1 cycle groups')).toBeInTheDocument()
  await waitFor(() => expect(traceCalls).toHaveLength(1))
  expect(traceCalls[0].searchParams.get('start_id')).toBe(resource.id)
  expect(traceCalls[0].searchParams.get('target_id')).toBe(resource.id)
  expect(traceCalls[0].searchParams.get('max_depth')).toBe('7')
  expect(traceCalls[0].searchParams.get('max_processes')).toBe('25')
  fireEvent.click(screen.getByRole('button',{name:'Process Mold cast'}))
  expect(screen.getByText('Required presence')).toBeInTheDocument()
  expect(screen.getByText('Guaranteed (1/1)')).toBeInTheDocument()
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
    if (url.pathname === '/api/trace') {calls.push(url); return response({snapshot_id:'test-snapshot',start_id:dust.id,target_id:plate.id,resources:[],processes:[],edges:[],leaves:[],cycles:[],truncated:false,coverage:[]})}
    throw new Error(`Unexpected route ${url.pathname}`)
  }))
  render(<App/>)
  await screen.findByText('Synthetic verification data')
  fireEvent.click(screen.getByRole('button',{name:/^Trace$/}))
  const start = screen.getByRole('combobox',{name:'Supplied start resource'})
  const target = screen.getByRole('combobox',{name:'Target resource'})
  const submit = screen.getByRole('button',{name:'Trace dependencies'})
  expect(submit).toBeDisabled()
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
  fireEvent.click(submit)
  await waitFor(() => expect(calls).toHaveLength(1))
  expect(calls[0].searchParams.get('start_id')).toBe(dust.id)
  expect(calls[0].searchParams.get('target_id')).toBe(plate.id)
  fireEvent.change(target,{target:{value:'iron'}})
  expect(submit).toBeDisabled()
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
