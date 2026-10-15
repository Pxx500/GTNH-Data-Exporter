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

test('SVG export shares computed styles without changing declarations, content, geometry, or the live board',async()=>{
  const {root,viewport}=board('translate(300px, 200px) scale(0.3)')
  const source=document.createElementNS('http://www.w3.org/2000/svg','svg')
  source.setAttribute('viewBox','0 0 1200 1400')
  const foreign=document.createElementNS(source.namespaceURI,'foreignObject')
  foreign.setAttribute('width','100%')
  foreign.setAttribute('height','100%')
  source.append(foreign)
  for(let index=0;index<12;index++){
    const tile=document.createElement('div')
    tile.className='recipe-node'
    tile.textContent=`Recipe ${index}`
    tile.style.cssText=`--board-token: "semi;colon}"; --flow-theme: rgb(10, 20, 30); margin: 1px 2px; margin-left: 7px; border: 2px solid red; border-left-width: 5px; font: italic 12px serif; color: ${index%2?'red':'blue'} !important; background-image: url("data:image/svg+xml,%3Csvg%3E;%3C/svg%3E");`
    foreign.append(tile)
  }
  const sourceText=new XMLSerializer().serializeToString(source)
  vi.mocked(toSvg).mockResolvedValue(`data:image/svg+xml;charset=utf-8,${encodeURIComponent(sourceText)}`)
  const before=viewport.outerHTML
  const image=await renderRecipeBoard(root,nodes,['cycle'],'svg')
  const output=new DOMParser().parseFromString(decodeURIComponent(image.dataUrl.slice(image.dataUrl.indexOf(',')+1)),'image/svg+xml')
  expect(output.querySelector('style')).not.toBeNull()
  const expanded=(element:Element)=>{
    const style=document.createElement('div').style
    const sheet=document.createElement('style')
    sheet.textContent=output.querySelector('style')!.textContent
    document.head.append(sheet)
    for(const rule of Array.from(sheet.sheet!.cssRules)){
      if(rule instanceof CSSStyleRule && element.matches(rule.selectorText)){
        for(const property of Array.from(rule.style))style.setProperty(property,rule.style.getPropertyValue(property),rule.style.getPropertyPriority(property))
      }
    }
    sheet.remove()
    return style.cssText
  }
  const original=Array.from(foreign.children)
  const exported=Array.from(output.querySelector('foreignObject')!.children)
  expect(exported).toHaveLength(original.length)
  for(let index=0;index<original.length;index++){
    expect(exported[index].textContent).toBe(original[index].textContent)
    expect(exported[index].getAttribute('class')).toBe(original[index].getAttribute('class'))
    const normalized=document.createElement('div').style
    normalized.cssText=expanded(exported[index])
    const expected=(original[index] as HTMLElement).style
    expect(Array.from(normalized).sort()).toEqual(Array.from(expected).sort())
    for(const property of Array.from(expected)){
      expect(normalized.getPropertyValue(property),property).toBe(expected.getPropertyValue(property))
      expect(normalized.getPropertyPriority(property),property).toBe(expected.getPropertyPriority(property))
    }
  }
  expect(output.documentElement.getAttribute('viewBox')).toBe('0 0 1200 1400')
  expect(output.querySelector('foreignObject')!.getAttribute('height')).toBe('100%')
  expect(decodeURIComponent(image.dataUrl.slice(image.dataUrl.indexOf(',')+1)).length).toBeLessThan(sourceText.length/2)
  expect(viewport.outerHTML).toBe(before)
})

test('SVG export retains unknown CSS and declarations that CSSOM cannot replay exactly',async()=>{
  const {root}=board('scale(0.3)')
  const source=document.createElementNS('http://www.w3.org/2000/svg','svg')
  const foreign=document.createElementNS(source.namespaceURI,'foreignObject')
  source.append(foreign)
  const styles=['future-board-layout: exact-unknown; color: red;',
    'font: italic 12px serif; font-size: 14px;', '--priority: one !important; color: blue;']
  for(const text of styles){
    const tile=document.createElement('div')
    tile.setAttribute('style',text)
    foreign.append(tile)
  }
  vi.mocked(toSvg).mockResolvedValue(`data:image/svg+xml;charset=utf-8,${encodeURIComponent(new XMLSerializer().serializeToString(source))}`)
  const image=await renderRecipeBoard(root,nodes,['cycle'],'svg')
  const output=new DOMParser().parseFromString(decodeURIComponent(image.dataUrl.slice(image.dataUrl.indexOf(',')+1)),'image/svg+xml')
  const elements=Array.from(output.querySelector('foreignObject')!.children)
  for(let index=0;index<styles.length;index++)expect(elements[index].getAttribute('style')).toBe(styles[index])
})

test('SVG export keeps inline cascade priority when the capture contains its own stylesheet',async()=>{
  const {root}=board('scale(0.3)')
  const source='<svg xmlns="http://www.w3.org/2000/svg"><style>.existing {color: blue !important}</style><foreignObject><div xmlns="http://www.w3.org/1999/xhtml" class="existing" style="color: red !important;">Recipe</div></foreignObject></svg>'
  vi.mocked(toSvg).mockResolvedValue(`data:image/svg+xml;charset=utf-8,${encodeURIComponent(source)}`)
  const image=await renderRecipeBoard(root,nodes,['cycle'],'svg')
  const output=new DOMParser().parseFromString(decodeURIComponent(image.dataUrl.slice(image.dataUrl.indexOf(',')+1)),'image/svg+xml')
  expect(output.querySelectorAll('style')).toHaveLength(1)
  expect(output.querySelector('div')!.getAttribute('style')).toBe('color: red !important;')
  expect(output.querySelector('style')!.textContent).toBe('.existing {color: blue !important}')
})
