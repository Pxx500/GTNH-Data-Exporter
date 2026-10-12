import { cleanup,fireEvent,render,screen,waitFor } from '@testing-library/react'
import { afterEach,expect,test,vi } from 'vitest'
import type { Resource } from './api'
import { LedgerDetails } from './AccountingDetails'
import { LoopAuditPanel } from './LoopAuditPanel'
import { ChemicalFacts } from './ChemicalFacts'

afterEach(()=>{cleanup();vi.unstubAllGlobals()})
const resource:Resource={id:'a',display_name:'Selected chemical',registry_name:'fixture:a',kind:'item',metadata:0,nbt:null,provenance:{}}
const resources=new Map([['a',resource]])
const r=(numerator:number,denominator=1)=>({numerator,denominator})
const ledger={status:'complete',yield_mode:'expected' as const,consumed:{a:r(1)},produced:{a:r(3,2)},net:{a:r(1,2)},presence:{},unsupported:[],assumptions:['Expected yields are not inventory']}

test('undeclared stock shows batch net change while declared stock retains the final-stock label',()=>{
  const capturedLedger={...ledger,yield_mode:'guaranteed' as const,consumed:{a:r(9000)},produced:{},net:{a:r(-9000)},assumptions:[]}
  const startup={required_start_stock:{a:r(9000)},final_stock:{a:r(-9000)},feasible:null,start_stock_declared:false,final_stock_semantics:'batch_net_change_without_declared_stock' as const}
  const view=render(<LedgerDetails ledger={capturedLedger} startup={startup} resources={resources}/>)
  expect(screen.getByText('Batch net change (initial stock not declared)')).toBeInTheDocument()
  expect(screen.queryByText('Final stock')).not.toBeInTheDocument()
  expect(screen.getByText(/Stock feasibility:/)).toHaveTextContent('initial stock not declared')
  view.rerender(<LedgerDetails ledger={capturedLedger} startup={{...startup,final_stock:{a:r(0)},feasible:true,start_stock_declared:true,final_stock_semantics:'declared_stock_plus_batch_net'}} resources={resources}/>)
  expect(screen.getByText('Final stock')).toBeInTheDocument()
  expect(screen.queryByText('Batch net change (initial stock not declared)')).not.toBeInTheDocument()
})

test('expected fractional accounting keeps feasibility unknown and labels conservative batch starting stock',()=>{
  render(<LedgerDetails ledger={ledger} startup={{required_start_stock:{a:r(1)},final_stock:{a:r(1,2)},feasible:null,integer_batch_scale:2,requires_integer_batch_scaling:true}} resources={resources}/>)
  expect(screen.getByText('expected yields')).toBeInTheDocument()
  expect(screen.getByText('3/2')).toBeInTheDocument()
  expect(screen.getByText(/unknown with initial stock not declared, or for fractional, expected or unsupported execution/)).toBeInTheDocument()
  expect(screen.getByText(/not a minimum interleaved-machine stock requirement/)).toBeInTheDocument()
  expect(screen.getByText(/requires integer batch scaling by 2/)).toBeInTheDocument()
})

test('loop controls distinguish material return from chemical balance and preserve expected-yield scope',async()=>{
  const calls:URL[]=[]
  vi.stubGlobal('fetch',vi.fn(async(input:string)=>{
    const url=new URL(input,'http://localhost')
    if(url.pathname==='/api/resources/a')return new Response(JSON.stringify({snapshot_id:'fixture',item:resource}))
    if(url.pathname==='/api/loops'){
      calls.push(url)
      return new Response(JSON.stringify({snapshot_id:'fixture',status:'limited',yield_mode:'expected',search:{examined_states:100},limit_reasons:['state_limit'],unsupported:[],
        witnesses:[{steps:[{process_id:'loop-step',runs:r(1)}],resource_ids:['a','a'],classification:'gaining',return_ratio:r(3,2),ledger,required_start_stock:{a:r(1)},external_consumption:{a:r(1)},autonomous:false,
          chemical_balance:{status:'complete',classification:'balanced',element_inputs:{H:r(2)},element_outputs:{H:r(2)},element_delta:{},unsupported:[]}}]}))
    }
    throw new Error(`Unexpected ${url.pathname}`)
  }))
  render(<LoopAuditPanel startId="a" resources={resources} tierOptions={{max_tier:3,unknown_tier_policy:'exclude'}} onSelect={vi.fn()}/>)
  expect(screen.getByLabelText('Loop maximum depth')).toHaveAttribute('max','20')
  await waitFor(()=>expect(screen.getByRole('button',{name:'Run bounded loop audit'})).toBeEnabled())
  fireEvent.change(screen.getByLabelText('Material return'),{target:{value:'gaining'}})
  fireEvent.change(screen.getByLabelText('Chemical balance'),{target:{value:'balanced'}})
  fireEvent.change(screen.getByLabelText('Loop yield mode'),{target:{value:'expected'}})
  fireEvent.click(screen.getByRole('button',{name:'Run bounded loop audit'}))
  expect(await screen.findByText('external consumption required')).toBeInTheDocument()
  expect(screen.getByText('balanced · complete')).toBeInTheDocument()
  expect(screen.getByText('Bounded audit: state_limit')).toBeInTheDocument()
  expect(calls[0].searchParams.get('kind')).toBe('gaining')
  expect(calls[0].searchParams.get('chemical_kind')).toBe('balanced')
  expect(calls[0].searchParams.get('yield_mode')).toBe('expected')
  expect(calls[0].searchParams.get('max_tier')).toBe('3')
  expect(screen.getByText(/does not mean self-powered/)).toBeInTheDocument()
})

test('expected gain with no external debit leaves material autonomy unverified',async()=>{
  vi.stubGlobal('fetch',vi.fn(async(input:string)=>new Response(JSON.stringify(input.startsWith('/api/resources/')
    ? {snapshot_id:'fixture',item:resource}
    : {snapshot_id:'fixture',status:'complete',yield_mode:'expected',search:{},limit_reasons:[],unsupported:[],witnesses:[{
      steps:[],resource_ids:['a','a'],classification:'gaining',return_ratio:r(3,2),ledger,required_start_stock:{a:r(1)},external_consumption:{},autonomous:false,
      chemical_balance:{status:'unsupported',classification:'unsupported',element_inputs:{},element_outputs:{},element_delta:{},unsupported:[]}}]}))))
  render(<LoopAuditPanel startId="a" resources={resources} onSelect={vi.fn()}/>)
  await waitFor(()=>expect(screen.getByRole('button',{name:'Run bounded loop audit'})).toBeEnabled())
  fireEvent.change(screen.getByLabelText('Loop yield mode'),{target:{value:'expected'}})
  fireEvent.click(screen.getByRole('button',{name:'Run bounded loop audit'}))
  expect(await screen.findByText('autonomy unverified')).toBeInTheDocument()
  expect(screen.queryByText('external consumption required')).not.toBeInTheDocument()
})

test('material facts are inspected on demand and unsupported source facts never become a purity claim',async()=>{
  const fetch=vi.fn(async()=>new Response(JSON.stringify({snapshot_id:'fixture',resource_id:'a',status:'unsupported',basis:null,vector:{},material_facts:null,unsupported:['Native material association is missing']})))
  vi.stubGlobal('fetch',fetch)
  render(<ChemicalFacts resourceId="a"/>)
  expect(fetch).not.toHaveBeenCalled()
  fireEvent.click(screen.getByText('Source-backed material accounting'))
  expect(await screen.findByText('Native material association is missing')).toBeInTheDocument()
  expect(screen.getByText(/Formula text is not proof of chemical purity/)).toBeInTheDocument()
  expect(fetch.mock.calls).toHaveLength(1)
})
