import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import { ProcessDetail } from './Details'

afterEach(() => {cleanup(); vi.unstubAllGlobals()})

test('labels native output templates separately from resolved recipe outputs', () => {
  render(<ProcessDetail process={{id:'template',family:'minecraft:crafting',display_name:'Crafting',inputs:[],outputs:[{resource_id:'item',amount:1,chance:null}],duration_ticks:null,eu_per_tick:null,amperage:null,executable:null,conditions:{dynamic_output:'unresolved'},provenance:{}}} resources={new Map([['item',{id:'item',kind:'item',registry_name:'test:item',display_name:'Item',metadata:0,nbt:null,provenance:{}}]])}/>)
  expect(screen.getByRole('heading', {name:'Output templates'})).toBeInTheDocument()
  expect(screen.getByText('Runtime result is unresolved. Shown outputs are native display templates.')).toBeInTheDocument()
})

test('omits routine defaults and displays exceptional chances as percentages', () => {
  const process = {id:'process',family:'test',display_name:'Recipe',inputs:[{role:'consume',consumption_chance:{numerator:10000,denominator:10000},choices:[{resource_id:null,amount:9,match:{mode:'exact',nbt_sensitive:false},consumption_chance:{numerator:1,denominator:2}}]}],outputs:[{resource_id:'item',amount:1,chance:{numerator:1,denominator:1}},{resource_id:'item',amount:2,chance:{numerator:2500,denominator:10000}},{resource_id:'item',amount:0,chance:{numerator:0,denominator:10000}}],duration_ticks:20,eu_per_tick:4,amperage:1,executable:true,conditions:{},provenance:{}}
  render(<ProcessDetail process={process} resources={new Map([['item',{id:'item',kind:'item',registry_name:'test:item',display_name:'Item',metadata:0,nbt:null,provenance:{}}]])}/>)
  expect(screen.queryAllByText(/Guaranteed|10000\/10000/)).toHaveLength(0)
  expect(screen.queryByText('Executable')).not.toBeInTheDocument()
  expect(screen.queryByText('Consumed')).not.toBeInTheDocument()
  expect(screen.queryByText('NBT-sensitive: no')).not.toBeInTheDocument()
  expect(screen.queryByText('Amperage')).not.toBeInTheDocument()
  expect(screen.getByText('Consumption chance 50%')).toBeInTheDocument()
  expect(screen.getByText('Chance 25%')).toBeInTheDocument()
  expect(screen.getByText('Chance 0%')).toBeInTheDocument()
  expect(screen.getByText('Amount 9')).toBeInTheDocument()
  expect(screen.getByText('20 ticks')).toBeInTheDocument()
})

test('preserves presence, per-alternative amounts and unknown output chance', async () => {
  vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({snapshot_id:'test', item:{id:'mold',kind:'item',registry_name:'test:mold',display_name:'Mold'}}))))
  render(<ProcessDetail process={{id:'process',family:'solidifier',display_name:'Contract specimen',inputs:[{role:'presence',choices:[{resource_id:'mold',amount:1,match:{mode:'exact',nbt_sensitive:true},consumption_chance:{numerator:1,denominator:2}},{resource_id:'mold',amount:null,match:{mode:'native_unknown'}}]}],outputs:[{resource_id:'mold',amount:null,chance:null}],duration_ticks:null,eu_per_tick:null,amperage:null,executable:null,conditions:{research:'unresolved'},provenance:{}}} />)
  expect(screen.getByText('Required presence')).toBeInTheDocument()
  expect(screen.getAllByText('Amount unknown')).toHaveLength(2)
  expect(screen.getByText('Chance unknown')).toBeInTheDocument()
  expect(screen.getByText('Execution unknown')).toBeInTheDocument()
  expect(screen.getByText('native_unknown')).toBeInTheDocument()
  expect(screen.getByText('Consumption chance 50%')).toBeInTheDocument()
  expect(screen.getByText('NBT-sensitive')).toBeInTheDocument()
})
