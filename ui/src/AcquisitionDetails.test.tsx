import {cleanup,fireEvent,render,screen} from '@testing-library/react'
import {afterEach,expect,test,vi} from 'vitest'
import {AcquisitionDetails} from './AcquisitionDetails'
import {SourceDetail} from './Details'

afterEach(()=>{cleanup();vi.unstubAllGlobals()})

const capturedFilter={status:'captured',source_api:'gregtech.GTMod.proxy.mUndergroundOil.blackList',scope:'native_numeric_filter_not_resolved_availability'}
test.each([
  {label:'nonempty',properties:{dimension_blacklist:{...capturedFilter,dimension_ids:[7,-1,0,7]}},expected:'ids'},
  {label:'distinct ordered lists',properties:{dimension_blacklist:{...capturedFilter,dimension_ids:[7,-1,0,7]}},expected:'distinct'},
  {label:'empty',properties:{dimension_blacklist:{...capturedFilter,dimension_ids:[]}},expected:null},
  {label:'unresolved',properties:{dimension_blacklist:{status:'unresolved',dimension_ids:null,reason:'native_array_is_null'}},expected:'unresolved'},
  {label:'ordinary',properties:{ordinary_property:'retained'},expected:null},
])('Natural Gas source and acquisition preserve raw $label exclusion context without inferring availability',async({properties,expected})=>{
  const environment={id:'dimension:0',name:'Overworld',dimension_id:0,provider:null,properties,provenance:{}}
  const otherEnvironment={...environment,id:'dimension:1',name:'Second captured environment',dimension_id:1,properties:expected==='distinct'?{dimension_blacklist:{...capturedFilter,dimension_ids:[7,-1,7,0]}}:properties}
  const environments=[environment,otherEnvironment]
  const source={id:'underground:0:gas_natural_gas',kind:'gregtech:underground_fluid',display_name:'Native gas source',outputs:[],environment_ids:environments.map(value=>value.id),status:'active',conditions:{},parameters:{},provenance:{}}
  const item={unification:{status:'unassociated',preferred_resource_ids:[],group_ids:[],evidence:null},acquisition:{status:'known_source',source_count:2,eligible_producer_count:1,unresolved_producer_count:0,coverage_complete:false,reason:'Captured definitions do not prove inventory'},provenance:{world_source:{status:'captured_inventory_source',inventory_obtainable_proven:false,evidence_counts:{direct_world_source:2},evidence:environments.map(value=>({source_id:`underground:${value.dimension_id}:gas_natural_gas`,kind:source.kind,status:'active',resource_semantics:null,classification:'direct_world_source',confidence:'captured_definition',environment_ids:[value.id],environments:[value],conditions:{dimension_id:value.dimension_id}}))},initial_processing:{status:'no_bounded_evidence',confidence:'unknown',max_steps:3,evidence:[]},renewable:{status:'unknown',reason:'Renewability is not established'},basic_suggestion:{suggested:true,requires_user_selection:true,reason:'World source definition'}}}
  const fetch=vi.fn(async()=>new Response(JSON.stringify({snapshot_id:'native',item,grounding:{status:'structural_reachable'},discovery:{}})))
  vi.stubGlobal('fetch',fetch)
  render(<><SourceDetail source={source} environments={environments}/><AcquisitionDetails resourceId="r46628"/></>)
  fireEvent.click(screen.getByText('Acquisition evidence'))
  for(const label of await screen.findAllByText('direct world source'))expect(label).toBeVisible()
  for(const label of screen.getAllByText('gregtech:underground_fluid'))expect(label).toBeVisible()
  expect(screen.getByText('Environments: Overworld (dimension 0)')).toBeVisible()
  if(expected==='ids' || expected==='distinct'){
    const labels=screen.getAllByText('Underground fluid exclusions:')
    expect(labels).toHaveLength(expected==='distinct'?4:2)
    expect(labels.filter(label=>label.closest('p')!.textContent!.includes('7, -1, 0, 7'))).toHaveLength(2)
    if(expected==='distinct')expect(labels.filter(label=>label.closest('p')!.textContent!.includes('7, -1, 7, 0'))).toHaveLength(2)
    for(const label of labels){
      expect(label).toBeVisible()
      expect(label.closest('p')).toHaveTextContent("These global native filter IDs don't establish environment or inventory availability")
    }
  }else if(expected==='unresolved'){
    const notes=screen.getAllByText('Underground fluid exclusions are unresolved in this capture.')
    expect(notes).toHaveLength(2)
    for(const note of notes)expect(note).toBeVisible()
  }else expect(screen.queryByText(/Underground fluid exclusions/)).not.toBeInTheDocument()
  expect(screen.queryByText(capturedFilter.source_api)).not.toBeInTheDocument()
  expect(fetch).toHaveBeenCalledTimes(1)
  const technical=screen.getByText('Technical data: native unification and acquisition evidence').closest('details')!.querySelector('pre')!
  expect(JSON.parse(technical.textContent!)).toEqual(item)
  expect(technical).not.toBeVisible()
})
