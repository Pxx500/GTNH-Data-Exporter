import {afterEach,expect,test,vi} from 'vitest'
import type {Node} from '@xyflow/react'
import {toPng,toSvg} from 'html-to-image'
import {renderRecipeBoard} from './RecipeBoardImage'

vi.mock('html-to-image',()=>({toPng:vi.fn(),toSvg:vi.fn()}))
afterEach(()=>{document.body.replaceChildren();vi.clearAllMocks()})
const nodes:Node[]=[{id:'first',position:{x:100,y:200},measured:{width:300,height:400},data:{}},{id:'last',position:{x:800,y:1000},measured:{width:300,height:400},data:{}}]
function board(transform:string) {
  const root=document.createElement('div')
  root.innerHTML='<div class="react-flow__viewport"><div class="react-flow__node" data-id="first"></div><div class="react-flow__node" data-id="last"></div><svg><g class="react-flow__edge" data-id="cycle"><path/><text>Returning chemical</text></g></svg><div class="recipe-tile-toolbar"><button>Inspect details</button></div><span class="resource-ref"><button>Oxygen</button></span><div class="react-flow__handle"></div></div>'
  const viewport=root.querySelector<HTMLElement>('.react-flow__viewport')!
  viewport.style.transform=transform
  const edge=root.querySelector<SVGGElement>('.react-flow__edge')!
  Object.defineProperty(edge,'getBBox',{value:()=>({x:-200,y:-100,width:1700,height:2100} as DOMRect)})
  document.body.append(root)
  return {root,viewport}
}
test('whole-board bounds include offscreen cycle paths and labels, ignore camera zoom, and stay scoped to their own graph',async()=>{
  const first=board('translate(900px, 400px) scale(0.2)')
  const other=board('translate(0px, 0px) scale(2)')
  vi.mocked(toPng).mockResolvedValue('data:image/png;base64,captured')
  const image=await renderRecipeBoard(first.root,nodes,['cycle'],'png')
  expect(image).toMatchObject({width:3656,height:4456})
  const [element,options]=vi.mocked(toPng).mock.calls[0]
  expect(element).toBe(first.viewport)
  expect(element).not.toBe(other.viewport)
  expect(options!.filter!(first.root.querySelector('.resource-ref button') as HTMLElement)).toBe(true)
  expect(options!.filter!(first.root.querySelector('.recipe-tile-toolbar button') as HTMLElement)).toBe(false)
  expect(options!.filter!(first.root.querySelector('.react-flow__handle') as HTMLElement)).toBe(false)
  const before=first.viewport.style.transform
  first.viewport.style.transform='translate(-300px, -200px) scale(1.8)'
  const second=await renderRecipeBoard(first.root,nodes,['cycle'],'png')
  expect(second).toEqual(image)
  expect(first.viewport.style.transform).toBe('translate(-300px, -200px) scale(1.8)')
  expect(before).not.toBe(first.viewport.style.transform)
})
test.each([{width:9000,height:10},{width:6000,height:6000}])('PNG rejects dimension or area overflow without shrinking, while SVG keeps natural dimensions: %j',async size=>{
  const {root}=board('scale(0.1)')
  const large=nodes.map(node=>({...node,position:{x:0,y:0},measured:size}))
  await expect(renderRecipeBoard(root,large,[],'png')).rejects.toThrow('Use SVG')
  expect(toPng).not.toHaveBeenCalled()
  vi.mocked(toSvg).mockResolvedValue(`data:image/svg+xml;charset=utf-8,${encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg"><foreignObject/></svg>')}`)
  const image=await renderRecipeBoard(root,large,[],'svg')
  expect(image).toMatchObject({width:size.width+128,height:size.height+128})
  const svg=new DOMParser().parseFromString(decodeURIComponent(image.dataUrl.split(',')[1]),'image/svg+xml')
  expect(svg.documentElement.querySelector('rect')?.getAttribute('fill')).toBe('#ffffff')
})
test('unavailable browser canvas or unmeasured links fail explicitly instead of returning an empty export',async()=>{
  const {root}=board('scale(0.2)')
  vi.mocked(toPng).mockResolvedValue('data:,')
  await expect(renderRecipeBoard(root,nodes,['cycle'],'png')).rejects.toThrow('Use SVG')
  await expect(renderRecipeBoard(root,nodes,['not-rendered'],'svg')).rejects.toThrow('still loading')
})
