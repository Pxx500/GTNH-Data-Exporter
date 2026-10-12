import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import { ProcessDetail } from './Details'
import type { Process } from './api'

afterEach(() => {cleanup(); vi.unstubAllGlobals()})

const manaProcess: Process = {id:'mana-recipe',family:'botania:mana_infusion',display_name:'Mana infusion',
  inputs:[],outputs:[],duration_ticks:null,eu_per_tick:null,amperage:null,executable:true,
  conditions:{total_mana:1000000,energy_unit:'mana',effective_duration:'collision_runtime_gate_unknown'},provenance:{}}

test('shows the exact total mana cost with units without inventing EU or a processing rate', () => {
  const view=render(<ProcessDetail process={manaProcess}/>)
  expect(screen.getByText('Mana cost')).toBeInTheDocument()
  expect(screen.getByText(/^1[\s,.]000[\s,.]000 mana$/)).toBeInTheDocument()
  expect(screen.queryByText('Energy')).not.toBeInTheDocument()
  expect(screen.queryByText('Duration')).not.toBeInTheDocument()
  expect(screen.queryByText(/EU\/t|mana\/t/)).not.toBeInTheDocument()
  view.rerender(<ProcessDetail process={{...manaProcess,conditions:{total_mana:0,energy_unit:'mana'}}}/>)
  expect(screen.getByText('0 mana')).toBeInTheDocument()
})

test('hides missing, non-numeric and non-finite mana costs and costs with another energy unit', () => {
  const view=render(<ProcessDetail process={{...manaProcess,conditions:{}}}/>)
  for(const conditions of [{},null,{energy_unit:'mana'},{energy_unit:'mana',total_mana:'2500'},
    {energy_unit:'mana',total_mana:null},{energy_unit:'mana',total_mana:NaN},
    {energy_unit:'mana',total_mana:Infinity},{energy_unit:'mana',total_mana:-Infinity},
    {energy_unit:'eu',total_mana:2500},{total_mana:2500}]){
    view.rerender(<ProcessDetail process={{...manaProcess,conditions}}/>)
    expect(screen.queryByText('Mana cost')).not.toBeInTheDocument()
  }
})

const catalystBelow={alchemy_required:true,conjuration_required:true,position:'one_block_below_pool',
  alchemy_block:{resource_id:'catalyst/alchemy',registry_name:'Botania:alchemyCatalyst',match:'block_identity',metadata:'ignored',consumed:false},
  conjuration_block:{resource_id:'catalyst/conjuration',registry_name:'Botania:conjurationCatalyst',match:'block_identity',metadata:'ignored',consumed:false}}

test('shows both required catalysts below the pool and resolves anchors absent from graph resources', async () => {
  vi.stubGlobal('fetch',vi.fn(async(input:string)=>{
    const url=new URL(input,'http://localhost')
    const id=decodeURIComponent(url.pathname.slice('/api/resources/'.length))
    const alchemy=id==='catalyst/alchemy'
    if(!alchemy && id!=='catalyst/conjuration')throw new Error(`Unexpected resource ${id}`)
    return new Response(JSON.stringify({snapshot_id:'test',item:{id,kind:'item',registry_name:alchemy?'Botania:alchemyCatalyst':'Botania:conjurationCatalyst',
      display_name:alchemy?'Alchemy Catalyst':'Conjuration Catalyst',metadata:0,nbt:null,provenance:{}}}))
  }))
  render(<ProcessDetail process={{...manaProcess,conditions:{total_mana:2500,energy_unit:'mana',catalyst_below:catalystBelow}}} resources={new Map()}/>)
  expect(screen.getByRole('heading',{name:'Required catalysts'})).toBeInTheDocument()
  expect(screen.getByText('Catalyst position: one block below the mana pool.')).toBeInTheDocument()
  expect(await screen.findByText('Alchemy Catalyst',{selector:'strong'})).toBeInTheDocument()
  expect(await screen.findByText('Conjuration Catalyst',{selector:'strong'})).toBeInTheDocument()
  expect(screen.getAllByText('Not consumed')).toHaveLength(2)
  expect(screen.queryByText(/^Slot \d/)).not.toBeInTheDocument()
})

test('does not display catalysts whose native required flag is false', async () => {
  const view=render(<ProcessDetail process={{...manaProcess,conditions:{catalyst_below:{...catalystBelow,alchemy_required:false,conjuration_required:false}}}}/>)
  expect(screen.queryByRole('heading',{name:'Required catalysts'})).not.toBeInTheDocument()
  expect(screen.queryByText('Alchemy catalyst')).not.toBeInTheDocument()
  expect(screen.queryByText('Conjuration catalyst')).not.toBeInTheDocument()
  vi.stubGlobal('fetch',vi.fn(async()=>new Response(JSON.stringify({snapshot_id:'test',item:{id:'catalyst/conjuration',kind:'item',registry_name:'Botania:conjurationCatalyst',display_name:'Conjuration Catalyst'}}))))
  view.rerender(<ProcessDetail process={{...manaProcess,conditions:{catalyst_below:{...catalystBelow,alchemy_required:false}}}}/>)
  expect(await screen.findByText('Conjuration Catalyst',{selector:'strong'})).toBeInTheDocument()
  expect(screen.queryByText('Alchemy catalyst')).not.toBeInTheDocument()
})

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
