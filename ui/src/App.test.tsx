import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
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
  fireEvent.change(screen.getByLabelText('Supplied start resource'),{target:{value:resource.id}})
  fireEvent.change(screen.getByLabelText('Target resource'),{target:{value:resource.id}})
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
