import { render, screen } from '@testing-library/react'
import { expect, test, vi } from 'vitest'
import { ProcessDetail } from './Details'

test('preserves presence, per-alternative amounts and unknown output chance', async () => {
  vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({snapshot_id:'test', item:{id:'mold',kind:'item',registry_name:'test:mold',display_name:'Mold'}}))))
  render(<ProcessDetail process={{id:'process',family:'solidifier',display_name:'Contract specimen',inputs:[{role:'presence',choices:[{resource_id:'mold',amount:1,match:{mode:'exact',nbt_sensitive:true},consumption_chance:{numerator:1,denominator:2}},{resource_id:'mold',amount:null,match:{mode:'native_unknown'}}]}],outputs:[{resource_id:'mold',amount:null,chance:null}],duration_ticks:null,eu_per_tick:null,amperage:null,executable:null,conditions:{research:'unresolved'},provenance:{}}} />)
  expect(screen.getByText('Required presence')).toBeInTheDocument()
  expect(screen.getAllByText('Amount unknown')).toHaveLength(2)
  expect(screen.getByText('Chance unknown')).toBeInTheDocument()
  expect(screen.getByText('Execution unknown')).toBeInTheDocument()
  expect(screen.getByText('native_unknown')).toBeInTheDocument()
  expect(screen.getByText('Consumption chance 1/2')).toBeInTheDocument()
  expect(screen.getByText('NBT-sensitive: yes')).toBeInTheDocument()
})
