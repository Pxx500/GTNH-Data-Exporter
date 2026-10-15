import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Background, Controls, Handle, MiniMap, Position, ReactFlow, ReactFlowProvider, MarkerType, useNodesInitialized, useNodesState, useReactFlow } from '@xyflow/react'
import type { Edge, Node, NodeProps } from '@xyflow/react'
import dagre from '@dagrejs/dagre'
import type { Process, Resource, Trace } from './api'
import { Badge, ProcessDetail } from './Details'
import { quantity } from './AccountingDetails'
import type { Rational } from './AccountingDetails'
import {renderRecipeBoard} from './RecipeBoardImage'
import type {BoardImageFormat} from './RecipeBoardImage'
import '@xyflow/react/dist/style.css'

export interface RecipeGraphData {recipes:{id:string;process:Process;paths?:number[];runs?:Rational}[];resources:Resource[];connections:{id:string;source:string;target:string;resourceId:string;paths?:number[];label?:string}[]}
type RecipeNodeData = RecipeGraphData['recipes'][number] & {resources: ReadonlyMap<string, Resource>; paths:number[];muted: boolean; inspect: (id: string) => void; inspectResource: (id: string) => void;recycle?:(processId:string,resourceId:string)=>void}
type RecipeNode = Node<RecipeNodeData, 'recipe'>
export interface AttachedConnection {source:string;target:string;resourceId:string;label:string}
function RecipeTile({id,data}: NodeProps<RecipeNode>) {
  return <article aria-label={`Recipe ${data.process.display_name || data.process.id}`} className={`recipe-tile ${data.muted ? 'path-muted' : ''}`}>
    <Handle type="target" position={Position.Top}/>
    <div className="recipe-tile-toolbar"><Badge tone="good">{data.paths.length > 1 ? `Shared by ${data.paths.length} paths` : data.paths.length ? `Path ${data.paths[0] + 1}` : 'Network recipe'}</Badge>{data.runs && <Badge>Runs {quantity(data.runs)}</Badge>}<button className="nodrag" aria-label={`Process ${data.process.display_name || data.process.id}`} onClick={() => data.inspect(id)}>Inspect details</button></div>
    <div className="nodrag" onClick={event=>event.stopPropagation()}><ProcessDetail process={data.process} resources={data.resources} onSelect={data.inspectResource} onRecycle={data.recycle ? id=>data.recycle!(data.process.id,id) : undefined}/></div>
    <Handle type="source" position={Position.Bottom}/>
  </article>
}
const nodeTypes = {recipe: RecipeTile}

export function pathConnections(trace: Trace) {
  const connections = new Map<string, {id: string; source: string; target: string; resourceId: string; paths: number[]}>()
  trace.paths.forEach((path, pathIndex) => path.process_ids.slice(0,-1).forEach((source,index) => {
    const target = path.process_ids[index+1], resourceId = path.resource_ids[index+1]
    const id = JSON.stringify([source,target,resourceId])
    const entry = connections.get(id)
    if (entry) entry.paths.push(pathIndex)
    else connections.set(id,{id,source,target,resourceId,paths:[pathIndex]})
  }))
  return [...connections.values()]
}

export function recipeGraphForTrace(trace:Trace,attachments:AttachedConnection[]=[]):RecipeGraphData {
  const membership=new Map<string,number[]>()
  trace.paths.forEach((path,index)=>path.process_ids.forEach(id=>membership.set(id,[...(membership.get(id)??[]),index])))
  return {resources:trace.resources,recipes:[...membership].map(([id,paths])=>({id,paths,process:trace.processes.find(process=>process.id===id)!})),
    connections:[...pathConnections(trace),...attachments.map(link=>({...link,id:JSON.stringify(['attached',link.source,link.target,link.resourceId]),paths:[0,1]}))]}
}
interface RecipeGraphProps {graph:RecipeGraphData;highlight:number|null;inspect:(id:string)=>void;inspectResource:(id:string)=>void;recycle?:(processId:string,resourceId:string)=>void;recycleProcesses?:string[]}
export function RecipeGraph(props:RecipeGraphProps) {
  return <ReactFlowProvider><Flow {...props}/></ReactFlowProvider>
}
function Flow({graph:recipeGraph,highlight,inspect,inspectResource,recycle,recycleProcesses}:RecipeGraphProps) {
  const graphRoot=useRef<HTMLDivElement>(null)
  const exportLock=useRef(false)
  const [exporting,setExporting]=useState<BoardImageFormat|null>(null)
  const [exportNotice,setExportNotice]=useState('')
  const [exportError,setExportError]=useState('')
  const [exportImage,setExportImage]=useState<{format:BoardImageFormat;image:Awaited<ReturnType<typeof renderRecipeBoard>>}|null>(null)
  const resources=useMemo(()=>new Map(recipeGraph.resources.map(resource=>[resource.id,resource])),[recipeGraph.resources])
  const initialNodes=useMemo(()=>recipeGraph.recipes.map(recipe=>({id:recipe.id,type:'recipe' as const,position:{x:0,y:0},dragHandle:'.recipe-tile-toolbar',
    data:{...recipe,paths:recipe.paths??[],resources,muted:false,inspect,inspectResource,recycle:recycleProcesses && !recycleProcesses.includes(recipe.process.id)?undefined:recycle}})),[recipeGraph,resources,inspect,inspectResource,recycle,recycleProcesses])
  const [nodes,setNodes,onNodesChange] = useNodesState<RecipeNode>(initialNodes)
  const loadedTrace = useRef(recipeGraph)
  const arrangedTrace = useRef<RecipeGraphData | null>(null)
  const placed=useRef(new Set<string>())
  useEffect(()=>{if(loadedTrace.current!==recipeGraph){
    loadedTrace.current=recipeGraph
    const ids=new Set(initialNodes.map(node=>node.id))
    placed.current=new Set([...placed.current].filter(id=>ids.has(id)))
    setNodes(current=>{
      const existing=new Map(current.map(node=>[node.id,node]))
      return initialNodes.map(node=>{
        const data={...node.data,muted:highlight!==null && !node.data.paths.includes(highlight)}
        return existing.has(node.id)?{...existing.get(node.id)!,data}:{...node,data}
      })
    })
    setExportImage(null);setExportNotice('');setExportError('')
  }},[recipeGraph,initialNodes,setNodes,highlight])
  const initialized = useNodesInitialized()
  const {getNodes,fitView} = useReactFlow<RecipeNode>()
  const dimensions = nodes.map(node => `${node.id}:${node.measured?.width}:${node.measured?.height}`).join('|')
  const connections=recipeGraph.connections
  const edges: Edge[] = useMemo(()=>connections.map(link=>({id:link.id,source:link.source,target:link.target,label:(link.label ? `${link.label}: ` : '')+(resources.get(link.resourceId)?.display_name || resources.get(link.resourceId)?.registry_name || link.resourceId),markerEnd:{type:MarkerType.ArrowClosed},style:{stroke:highlight===null || (link.paths??[]).includes(highlight) ? '#087c70' : '#bac5ce',strokeWidth:highlight===null || (link.paths??[]).includes(highlight) ? 2.5 : 1},labelStyle:{fontSize:11,fill:'#38596c'},labelBgPadding:[7,4] as [number,number],labelBgBorderRadius:4})),[connections,resources,highlight])
  const arrange = useCallback((onlyNew=false) => {
    const graph = new dagre.graphlib.Graph().setGraph({rankdir:'TB',nodesep:40,ranksep:60,marginx:24,marginy:24}).setDefaultEdgeLabel(()=>({}))
    const current = getNodes()
    if(current.length!==initialNodes.length || current.some(node=>!initialNodes.some(expected=>expected.id===node.id) || !node.measured?.width || !node.measured?.height)) return false
    const moving=onlyNew?current.filter(node=>!placed.current.has(node.id)):current
    if(moving.length===0)return true
    const movingIds=new Set(moving.map(node=>node.id))
    const fixed=current.filter(node=>!movingIds.has(node.id))
    moving.forEach(node=>graph.setNode(node.id,{width:node.measured!.width!,height:node.measured!.height!}))
    connections.filter(edge=>movingIds.has(edge.source) && movingIds.has(edge.target)).forEach(edge=>graph.setEdge(edge.source,edge.target))
    dagre.layout(graph)
    const offsetX=fixed.length?Math.max(...fixed.map(node=>node.position.x+node.measured!.width!))+40:0
    const offsetY=fixed.length?Math.min(...fixed.map(node=>node.position.y)):0
    setNodes(current.map(node=>{
      if(!movingIds.has(node.id))return node
      const point=graph.node(node.id)
      return {...node,position:{x:point.x-node.measured!.width!/2+offsetX,y:point.y-node.measured!.height!/2+offsetY}}
    }))
    moving.forEach(node=>placed.current.add(node.id))
    if(!onlyNew || fixed.length===0)requestAnimationFrame(()=>{void fitView({padding:.16,maxZoom:.9})})
    return true
  },[getNodes,setNodes,connections,fitView,initialNodes])
  useEffect(()=>{if(initialized && arrangedTrace.current!==recipeGraph && arrange(true)) arrangedTrace.current=recipeGraph},[initialized,dimensions,arrange,recipeGraph])
  useEffect(()=>{setNodes(current=>current.map(node=>({...node,data:{...node.data,muted:highlight!==null && !node.data.paths.includes(highlight)}})))},[highlight,setNodes])
  const exportReady=initialized && nodes.length>0 && nodes.length===initialNodes.length
  async function exportBoard(format:BoardImageFormat){
    if(exportLock.current || !graphRoot.current || !exportReady)return
    exportLock.current=true
    setExporting(format)
    setExportError('')
    setExportNotice(`Exporting the whole board as ${format.toUpperCase()}…`)
    try{
      const image=await renderRecipeBoard(graphRoot.current,getNodes(),edges.map(edge=>edge.id),format)
      setExportImage({format,image})
      setExportNotice(`${format.toUpperCase()} ready: ${image.width.toLocaleString()} × ${image.height.toLocaleString()} px. Use the Download link to save it.`)
    }catch(error){
      const message=error instanceof Error?error.message:String(error)
      setExportNotice('')
      setExportError(`${message}${message.includes('Use SVG')?'':format==='png'?' Try SVG or retry after the board finishes loading.':' Retry after the board finishes loading.'}`)
    }finally{
      exportLock.current=false
      setExporting(null)
    }
  }
  return <div className="recipe-board">    <section aria-label="Recipe board actions" className="recipe-board-actions"><div className="recipe-board-buttons"><button onClick={()=>arrange()}>Arrange recipes</button><button disabled={!exportReady || !!exporting} onClick={()=>void exportBoard('png')}>Export whole board PNG</button><button disabled={!exportReady || !!exporting} onClick={()=>void exportBoard('svg')}>Export whole board SVG</button></div><p>Scroll the page normally. Ctrl+scroll or pinch zooms the graph. Drag the canvas to pan and a tile header to move it.</p><p>Export, then use the Download link to save. PNG uses 2× tile size. SVG suits larger boards and browser viewing.</p>{!exportReady && <p role="status">Wait for recipe tiles to finish loading before exporting.</p>}{exportNotice && <p role="status">{exportNotice}</p>}{exportImage && <div className="recipe-board-download"><a href={exportImage.image.dataUrl} download={`recipe-board.${exportImage.format}`}>Download {exportImage.format.toUpperCase()}</a><span>recipe-board.{exportImage.format}</span></div>}{exportError && <p className="warning-text" role="alert">{exportError}</p>}</section><div className="recipe-board-canvas"><ReactFlow ref={graphRoot} nodes={nodes} edges={edges} onNodesChange={onNodesChange} nodeTypes={nodeTypes} minZoom={.1} maxZoom={2} nodesConnectable={false} zoomOnScroll={false} panOnScroll={false} preventScrolling={false} zoomOnPinch zoomActivationKeyCode="Control" onNodeClick={(_,node)=>inspect(node.id)} fitView ariaLabelConfig={{'controls.fitView.ariaLabel':'Fit all recipes','controls.zoomIn.ariaLabel':'Zoom in','controls.zoomOut.ariaLabel':'Zoom out'}}>
    <Background gap={20}/><Controls/><MiniMap pannable={false} zoomable={false} style={{pointerEvents:'none'}} nodeColor="#c0dfd3"/>

  </ReactFlow></div></div>
}
