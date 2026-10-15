import {getNodesBounds,getViewportForBounds} from '@xyflow/react'
import type {Node} from '@xyflow/react'
import {toPng,toSvg} from 'html-to-image'
import {shareSvgStyles} from './SvgStyles'

export type BoardImageFormat='png'|'svg'
export async function renderRecipeBoard(root:HTMLElement,nodes:Node[],edgeIds:string[],format:BoardImageFormat) {
  const viewport=root.querySelector<HTMLElement>('.react-flow__viewport')
  if(!viewport || !nodes.length || nodes.some(node=>!node.measured?.width || !node.measured?.height))throw new Error('Wait for recipe tiles to finish loading, then export again.')
  const renderedNodes=new Set([...viewport.querySelectorAll('.react-flow__node')].map(node=>node.getAttribute('data-id')))
  if(renderedNodes.size!==nodes.length || nodes.some(node=>!renderedNodes.has(node.id)))throw new Error('Some recipe tiles are still loading. Wait, then export again.')
  const renderedEdges=new Map([...viewport.querySelectorAll<SVGGElement>('.react-flow__edge')].map(edge=>[edge.getAttribute('data-id'),edge]))
  const rectangles=[getNodesBounds(nodes)]
  for(const id of edgeIds){
    const edge=renderedEdges.get(id)
    if(!edge || edge.querySelector('[visibility="hidden"]'))throw new Error('Some recipe links or labels are still loading. Wait, then export again.')
    // This SVG group contains the curve and its translated label. getBBox uses
    // graph coordinates, independent of the live viewport's CSS zoom.
    const box=edge.getBBox()
    if(![box.x,box.y,box.width,box.height].every(Number.isFinite) || box.width+box.height<=0)throw new Error('Could not measure every recipe link. Arrange the board, then try again.')
    rectangles.push(box)
  }
  const x=Math.min(...rectangles.map(rect=>rect.x)),y=Math.min(...rectangles.map(rect=>rect.y))
  const bounds={x,y,width:Math.max(...rectangles.map(rect=>rect.x+rect.width))-x,height:Math.max(...rectangles.map(rect=>rect.y+rect.height))-y}
  // 64px per side covers the fixed 20px arrow markers and tile shadows.
  const width=Math.ceil(bounds.width+128),height=Math.ceil(bounds.height+128)
  if(![bounds.x,bounds.y,width,height].every(Number.isFinite) || width<=0 || height<=0)throw new Error('Could not measure the board. Arrange recipes, then export again.')
  // Keep 2x text readable. Reject before allocating a large raster, and disable
  // html-to-image's automatic 16,384px downscaling below.
  if(format==='png' && (width*2>16384 || height*2>16384 || width*height*4>64000000))throw new Error('This board exceeds PNG limits (16,384px per side or 64 million pixels at 2x). Use SVG for the whole board.')
  const camera=getViewportForBounds(bounds,width,height,1,1,0)
  const options={width,height,backgroundColor:'#ffffff',pixelRatio:format==='png'?2:1,skipAutoScale:true,
    style:{transform:`translate(${camera.x}px, ${camera.y}px) scale(1)`,transformOrigin:'0 0'},
    filter:(node:HTMLElement)=>!node.matches?.('.react-flow__handle, .recipe-tile-toolbar button, .choice-meta button, .react-flow__edge-interaction')}
  let dataUrl=await (format==='png'?toPng(viewport,options):toSvg(viewport,options))
  if(format==='png' && !dataUrl.startsWith('data:image/png;'))throw new Error('The browser could not allocate this PNG. Use SVG for the whole board.')
  if(format==='svg'){
    // The exported viewport is translated. Put the background on the outer
    // SVG so it also covers margins beyond that translated HTML rectangle.
    const document=new DOMParser().parseFromString(decodeURIComponent(dataUrl.slice(dataUrl.indexOf(',')+1)),'image/svg+xml')
    const svg=document.documentElement
    if(svg.localName!=='svg')throw new Error('SVG rendering failed. Wait for the board to finish loading, then try again.')
    const background=document.createElementNS('http://www.w3.org/2000/svg','rect')
    background.setAttribute('width','100%')
    background.setAttribute('height','100%')
    background.setAttribute('fill','#ffffff')
    svg.insertBefore(background,svg.firstChild)
    shareSvgStyles(svg as unknown as SVGElement)
    dataUrl=`data:image/svg+xml;charset=utf-8,${encodeURIComponent(new XMLSerializer().serializeToString(svg))}`
  }
  return {dataUrl,width:width*options.pixelRatio,height:height*options.pixelRatio}
}
