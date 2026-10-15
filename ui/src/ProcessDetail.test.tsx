import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import { ProcessDetail } from './Details'
import type { Process } from './api'

afterEach(() => {cleanup(); vi.unstubAllGlobals()})

const manaProcess: Process = {id:'mana-recipe',family:'botania:mana_infusion',display_name:'Mana infusion',
  inputs:[],outputs:[],duration_ticks:null,eu_per_tick:null,amperage:null,executable:true,
  conditions:{total_mana:1000000,energy_unit:'mana',effective_duration:'collision_runtime_gate_unknown'},provenance:{}}

test('captured Space Pumping selectors and nominal scope are readable without guessing environment mappings',()=>{
  const metadata={status:'captured_native_declaration',planet_type:3,gas_type:5,quantity_scope:'selected_line_one_parallel_batch_one',runtime_execution:'unresolved',environment_mapping:'unresolved',controller_class:'fixture.Controller',source_api:'fixture.entries',duration_source_api:'fixture.duration',energy_source_api:'fixture.energy'}
  const gas={id:'gas',kind:'fluid',registry_name:'fixture:gas',display_name:'Captured gas',metadata:null,nbt:null,provenance:{}}
  const resources=new Map([[gas.id,gas]])
  const recipe:Process={...manaProcess,id:'pumping',family:'test',display_name:'Captured gas declaration',outputs:[{resource_id:gas.id,amount:1000,chance:{numerator:1,denominator:1}}],duration_ticks:20,eu_per_tick:8192,executable:null,conditions:{native_metadata:{space_pumping:metadata}}}
  const view=render(<ProcessDetail process={recipe} resources={resources}/>)
  const panel=screen.getByText('Conditions and research').closest('details')!
  expect(panel).not.toHaveAttribute('open')
  fireEvent.click(within(panel).getByText('Conditions and research'))
  expect(within(panel).getByText('Planet selector')).toBeVisible()
  expect(within(panel).getByText('3')).toBeVisible()
  expect(within(panel).getByText('Gas selector')).toBeVisible()
  expect(within(panel).getByText('5')).toBeVisible()
  expect(within(panel).getByText('Nominal one line, one parallel, batch one')).toBeVisible()
  expect(panel).toHaveTextContent(/Runtime requirements\s*unresolved/)
  expect(panel).toHaveTextContent(/Environment mapping\s*unresolved/)
  expect(within(panel).queryByText('fixture.Controller')).not.toBeInTheDocument()
  expect(within(panel).queryByText('fixture.entries')).not.toBeInTheDocument()
  expect(screen.getByText('20 ticks')).toBeVisible()
  expect(screen.getByText(/^Amount 1[\s,.]?000$/)).toBeVisible()
  expect(screen.getByText('mB')).toBeVisible()
  expect(screen.getByText('Execution unknown')).toBeVisible()
  expect(screen.queryByText('Informational / fake')).not.toBeInTheDocument()
  const technical=screen.getByText('Technical data: full process record').closest('details')!.querySelector('pre')!
  expect(JSON.parse(technical.textContent!)).toEqual(recipe)
  view.rerender(<ProcessDetail process={{...recipe,conditions:{planet_type:7,gas_type:9}}} resources={resources}/>)
  expect(within(panel).queryByText('Planet selector')).not.toBeInTheDocument()
  expect(within(panel).getByText('Planet type')).toBeVisible()
  expect(within(panel).getByText('Gas type')).toBeVisible()
})

test('a fetched EBF fluid identity supplies its name and millibucket quantity through one lookup',async()=>{
  const fetch=vi.fn(async()=>new Response(JSON.stringify({snapshot_id:'native',item:{id:'r32743',kind:'fluid',display_name:'Oxygen',registry_name:'oxygen',metadata:null,nbt:null,provenance:{owner:'native_registry'}}})))
  vi.stubGlobal('fetch',fetch)
  const process:Process={id:'p34292',family:'gregtech:gt.recipe.blastfurnace',display_name:'Blast Furnace',inputs:[{role:'consume',choices:[{resource_id:'r32743',amount:1000,native_amount:1000,match:{mode:'exact',nbt_sensitive:true}}]}],outputs:[],duration_ticks:500,eu_per_tick:120,amperage:1,executable:true,conditions:{native_special_value:1000},provenance:{owner:'GTRecipe'}}
  render(<ProcessDetail process={process} resources={new Map()}/>)
  expect(await screen.findByText('Oxygen')).toBeVisible()
  expect(screen.getByText(/^Amount 1[\s,.]?000$/)).toBeVisible()
  expect(screen.getByText('mB')).toBeVisible()
  expect(fetch).toHaveBeenCalledTimes(1)
  const technical=screen.getByText('Technical data: full process record').closest('details')!.querySelector('pre')!
  expect(JSON.parse(technical.textContent!).inputs[0].choices[0].amount).toBe(1000)
})

test('verified static GT crafting marks voltage as not applicable without treating null EU as zero energy',()=>{
  const recipe:Process={...manaProcess,id:'p1030',family:'minecraft:crafting',display_name:'Static GT crafting',conditions:{recipe_voltage_applicability:'not_applicable_crafting_grid',native_class:'gregtech.api.util.GTShapedRecipe',dynamic_output:'resolved_static'},provenance:{owner:'CraftingManager'}}
  const view=render(<ProcessDetail process={recipe}/>)
  expect(screen.getByText('No machine voltage requirement')).toBeInTheDocument()
  expect(screen.queryByText('Energy')).not.toBeInTheDocument()
  view.rerender(<ProcessDetail process={{...recipe,conditions:{dynamic_output:'unresolved'}}}/>)
  expect(screen.queryByText('No machine voltage requirement')).not.toBeInTheDocument()
  expect(screen.queryByText('Energy')).not.toBeInTheDocument()
  view.rerender(<ProcessDetail process={{...recipe,eu_per_tick:0}}/>)
  expect(screen.queryByText('No machine voltage requirement')).not.toBeInTheDocument()
  expect(screen.getByText('0 EU/t')).toBeInTheDocument()
})

test('technical data is collapsed and copyable while recipe conditions remain readable',async()=>{
  const record={...manaProcess,conditions:{heat:1000,research:'Required research'},extension:{secret:'exact original field'},inputs:[{role:'tool',slot_id:'native-slot',choices:[{resource_id:null,amount:1,match:{mode:'exact'}}]}]}
  const writeText=vi.fn().mockResolvedValue(undefined)
  vi.stubGlobal('navigator',{clipboard:{writeText}})
  render(<ProcessDetail process={record}/>)
  expect(screen.queryByText('Choice fields')).not.toBeInTheDocument()
  expect(screen.queryByText('Slot fields')).not.toBeInTheDocument()
  const technical=screen.getByText('Technical data: full process record').closest('details')!
  expect(technical).not.toHaveAttribute('open')
  const conditions=screen.getByText('Conditions and research').closest('details')!
  expect(conditions).not.toHaveAttribute('open')
  expect(screen.getByText('Heat')).not.toBeVisible()
  fireEvent.click(within(conditions).getByText('Conditions and research'))
  expect(screen.getByText('Heat')).toBeVisible()
  expect(screen.getByText(/^1[\s,.]?000$/)).toBeVisible()
  fireEvent.click(within(technical).getByRole('button',{name:'Copy JSON',hidden:true}))
  await screen.findByText('JSON copied')
  expect(JSON.parse(writeText.mock.calls[0][0])).toEqual(record)
})

test('readable conditions omit routine native defaults but retain exceptional requirements and the complete record',()=>{
  const conditions={enabled:true,fake:false,hidden:false,nbt_sensitive:false,requires_empty_outputs:false,native_special_value:0,native_description:null,special_items:null,recipe_voltage_tier_source:'GTUtility.getTier(mEUt)',recipe_voltage_tier_semantics:'nominal recipe voltage class, not machine capability',recipe_voltage:{tier:2,name:'MV',source:'GTUtility.getTier',semantics:'internal_voltage_classification'},coil_heat:1000,research:'unresolved',environment:'vacuum',unfamiliar_requirement:'native_unknown'}
  render(<ProcessDetail process={{...manaProcess,conditions}}/>)
  const panel=screen.getByText('Conditions and research').closest('details')!
  expect(panel).not.toHaveAttribute('open')
  fireEvent.click(within(panel).getByText('Conditions and research'))
  for(const label of ['Enabled','Fake','Hidden','Nbt sensitive','Requires empty outputs','Native special value','Native description','Special items','Recipe voltage tier source','Recipe voltage tier semantics','Source','Semantics'])expect(within(panel).queryByText(label)).not.toBeInTheDocument()
  for(const label of ['Coil heat','Research','Environment','Unfamiliar requirement'])expect(within(panel).getByText(label)).toBeVisible()
  expect(within(panel).getByText('MV')).toBeVisible()
  const full=screen.getByText('Technical data: full process record').closest('details')!.querySelector('pre')!
  expect(JSON.parse(full.textContent!).conditions).toEqual(conditions)
})

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
