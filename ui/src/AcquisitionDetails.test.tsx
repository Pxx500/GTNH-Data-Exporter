import {cleanup,fireEvent,render,screen} from '@testing-library/react'
import {afterEach,expect,test,vi} from 'vitest'
import {AcquisitionDetails} from './AcquisitionDetails'

afterEach(()=>{cleanup();vi.unstubAllGlobals()})

test('Natural Gas acquisition renders native underground sources with nullable resource semantics',async()=>{
  const item={unification:{status:'unassociated',preferred_resource_ids:[],group_ids:[],evidence:null},acquisition:{status:'known_source',source_count:2,eligible_producer_count:1,unresolved_producer_count:0,coverage_complete:false,reason:'Captured definitions do not prove inventory'},provenance:{world_source:{status:'captured_inventory_source',inventory_obtainable_proven:false,evidence_counts:{direct_world_source:2},evidence:[{source_id:'underground:0:gas_natural_gas',kind:'gregtech:underground_fluid',status:'active',resource_semantics:null,classification:'direct_world_source',confidence:'captured_definition',environment_ids:['dimension:0'],environments:[{id:'dimension:0',name:'Overworld',dimension_id:0,provider:null,properties:{},provenance:{}}],conditions:{dimension_id:0}}]},initial_processing:{status:'no_bounded_evidence',confidence:'unknown',max_steps:3,evidence:[]},renewable:{status:'unknown',reason:'Renewability is not established'},basic_suggestion:{suggested:true,requires_user_selection:true,reason:'World source definition'}}}
  vi.stubGlobal('fetch',vi.fn(async()=>new Response(JSON.stringify({snapshot_id:'native',item,grounding:{status:'structural_reachable'},discovery:{}}))))
  render(<AcquisitionDetails resourceId="r46628"/>)
  fireEvent.click(screen.getByText('Acquisition evidence'))
  expect(await screen.findByText('direct world source')).toBeVisible()
  expect(screen.getByText('gregtech:underground_fluid')).toBeVisible()
  expect(screen.getByText('Environments: Overworld (dimension 0)')).toBeVisible()
  const technical=screen.getByText('Technical data: native unification and acquisition evidence').closest('details')!.querySelector('pre')!
  expect(JSON.parse(technical.textContent!).provenance.world_source.evidence[0].resource_semantics).toBeNull()
})
