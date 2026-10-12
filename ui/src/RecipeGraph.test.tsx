import {cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react'
import {afterEach,expect,test,vi} from 'vitest'
import type {Process,Resource} from './api'
import {RecipeGraph} from './RecipeGraph'

afterEach(cleanup)
test('whole networks retain distinct recipe variants and real cycle connections without pretending they are paths',async()=>{
  const resources:Resource[]=['a','b'].map(id=>({id,kind:'item',registry_name:`test:${id}`,display_name:id,metadata:0,nbt:null,provenance:{}}))
  const process:Process={id:'native',family:'test',display_name:'Native recipe',inputs:[{role:'consume',choices:[{resource_id:'a',amount:2,match:{mode:'exact'}}]}],outputs:[{resource_id:'b',amount:1,chance:{numerator:1,denominator:1}}],duration_ticks:20,eu_per_tick:8,amperage:1,executable:true,conditions:{},provenance:{}}
  const inspect=vi.fn()
  render(<RecipeGraph graph={{resources,recipes:[{id:'variant-a',process,runs:{numerator:1,denominator:2}},{id:'variant-b',process,runs:{numerator:2,denominator:1}}],connections:[
    {id:'forward',source:'variant-a',target:'variant-b',resourceId:'b'},{id:'return',source:'variant-b',target:'variant-a',resourceId:'a'}]}} highlight={null} inspect={inspect} inspectResource={vi.fn()}/>)
  await waitFor(()=>expect(screen.getAllByRole('article',{name:'Recipe Native recipe'})).toHaveLength(2))
  expect(screen.getAllByText('Network recipe')).toHaveLength(2)
  expect(screen.getByText('Runs 1/2')).toBeInTheDocument()
  expect(screen.getByText('Runs 2')).toBeInTheDocument()
  expect(screen.queryByText('Path 1')).not.toBeInTheDocument()
  fireEvent.click(screen.getAllByRole('button',{name:'Process Native recipe'})[1])
  expect(inspect).toHaveBeenCalledWith('variant-b')
  expect(document.querySelectorAll('.react-flow__edge')).toHaveLength(2)
})
