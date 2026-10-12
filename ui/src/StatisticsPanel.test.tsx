import {cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react'
import {afterEach,expect,test,vi} from 'vitest'
import {StatisticsPanel} from './StatisticsPanel'
import type {StatisticsReport,Process} from './api'

afterEach(()=>{cleanup();vi.unstubAllGlobals()})
test('statistics forwards profile scope, displays exact quartiles and exposes candidate native records without calling them bugs',async()=>{
  const r=(numerator:number)=>({numerator,denominator:1})
  const process:Process={id:'cheap',display_name:'Captured converter',family:'test.family',inputs:[],outputs:[],duration_ticks:20,eu_per_tick:8,amperage:1,executable:true,conditions:{},provenance:{}}
  const summary={count:2,min:r(160),q1:r(200),median:r(240),q3:r(280),max:r(320),iqr:r(80)}
  const report:StatisticsReport={snapshot_id:'fixture',overview:{resources:{count:4,by_kind:{item:4},by_namespace:{test:4}},groups:{count:0,by_kind:{},member_counts:{...summary,count:0,min:null,q1:null,median:null,q3:null,max:null,iqr:null}},processes:{count:2,by_family:{'test.family':2},by_tier:[{recipe_tier:{status:'known',tier:2,name:'MV'},count:2}],by_executability:{true:2},gates:{},energy_status:{known:2}}},distributions:[{family:'test.family',recipe_tier:{status:'known',tier:2,name:'MV'},metric:'nominal_eu_per_captured_execution',comparison:'exploratory_across_products',...summary}],findings:[{kind:'normalized_capture_cost_spread',comparison_scope:'identical_captured_predicates_and_conditions_normalized_batch',process_ids:['cheap','expensive'],normalized_signature:{inputs:[],outputs:[]},batch_scales:{cheap:r(1),expensive:r(1)},normalized_costs:{minimum:r(160),maximum:r(320)},cost_ratio:{numerator:25,denominator:2},count:2}],exclusions:{},search:{complete:false,truncated:true,limit_reasons:['finding_limit']},processes:{cheap:process,expensive:{...process,id:'expensive',eu_per_tick:16}}}
  let body:Record<string,unknown>|undefined
  vi.stubGlobal('fetch',vi.fn(async(input:string,options?:RequestInit)=>{
    if(input.startsWith('/api/boundary-profiles'))return new Response(JSON.stringify({snapshot_id:'fixture',items:[{id:'profile',name:'User scope',revision:1,base_resource_ids:[],scope:{},semantics:'assumed'}]}))
    if(input==='/api/statistics'){body=JSON.parse(options!.body as string);return new Response(JSON.stringify(report))}
    throw new Error(`Unexpected ${input}`)
  }))
  render(<StatisticsPanel profile={{id:'profile',name:'User scope',revision:1,base_resource_ids:[],scope:{},semantics:'assumed'}} onProfileChange={vi.fn()} onSelect={vi.fn()}/>)
  fireEvent.click(screen.getByRole('button',{name:'Analyze scoped statistics'}))
  await screen.findByText('Partial statistics')
  expect(body).toMatchObject({profile_id:'profile',max_records:600000,max_findings:50,max_signature_buckets:50000,timeout_seconds:15})
  expect(screen.getByText(/inspection candidates/)).toBeInTheDocument()
  expect(screen.getByText('Limits: finding_limit')).toBeInTheDocument()
  expect(screen.getByText('12.5×')).toBeInTheDocument()
  fireEvent.click(screen.getByText('Exploratory family and tier distributions'))
  expect(screen.getByText('Median EU')).toBeInTheDocument()
  expect(screen.getByText('240')).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button',{name:'Captured converter · cheap'}))
  expect(screen.getByRole('heading',{name:'Captured converter'})).toBeInTheDocument()
  expect(screen.getByText('8 EU/t')).toBeInTheDocument()
  fireEvent.change(screen.getByLabelText('Maximum candidate findings'),{target:{value:'3'}})
  await waitFor(()=>expect(screen.queryByText('Partial statistics')).not.toBeInTheDocument())
  expect(screen.getByText(/Statistics settings changed/)).toBeInTheDocument()
})
