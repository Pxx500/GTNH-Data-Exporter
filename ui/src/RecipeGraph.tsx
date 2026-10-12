import { useCallback, useEffect, useMemo, useRef } from 'react'
import { Background, Controls, Handle, MiniMap, Panel, Position, ReactFlow, ReactFlowProvider, MarkerType, useNodesInitialized, useNodesState, useReactFlow } from '@xyflow/react'
import type { Edge, Node, NodeProps } from '@xyflow/react'
import dagre from '@dagrejs/dagre'
import type { Process, Resource, Trace } from './api'
import { Badge, ProcessDetail } from './Details'
import '@xyflow/react/dist/style.css'

type RecipeNodeData = {process: Process; resources: ReadonlyMap<string, Resource>; paths: number[]; muted: boolean; inspect: (id: string) => void; inspectResource: (id: string) => void;recycle?:(processId:string,resourceId:string)=>void}
type RecipeNode = Node<RecipeNodeData, 'recipe'>
export interface AttachedConnection {source:string;target:string;resourceId:string;label:string}
function RecipeTile({data}: NodeProps<RecipeNode>) {
  return <article aria-label={`Recipe ${data.process.display_name || data.process.id}`} className={`recipe-tile ${data.muted ? 'path-muted' : ''}`}>
    <Handle type="target" position={Position.Top}/>
    <div className="recipe-tile-toolbar"><Badge tone="good">{data.paths.length > 1 ? `Shared by ${data.paths.length} paths` : `Path ${data.paths[0] + 1}`}</Badge><button className="nodrag" aria-label={`Process ${data.process.display_name || data.process.id}`} onClick={() => data.inspect(data.process.id)}>Inspect details</button></div>
    <div className="nodrag nowheel" onClick={event=>event.stopPropagation()}><ProcessDetail process={data.process} resources={data.resources} onSelect={data.inspectResource} onRecycle={data.recycle ? id=>data.recycle!(data.process.id,id) : undefined}/></div>
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

export function RecipeGraph(props: {trace: Trace; highlight: number | null; inspect: (id: string) => void; inspectResource: (id: string) => void;recycle?:(processId:string,resourceId:string)=>void;recycleProcesses?:string[];attachments?:AttachedConnection[]}) {
  return <ReactFlowProvider><Flow {...props}/></ReactFlowProvider>
}
function Flow({trace, highlight, inspect, inspectResource,recycle,recycleProcesses,attachments}: {trace: Trace; highlight: number | null; inspect: (id: string) => void; inspectResource: (id: string) => void;recycle?:(processId:string,resourceId:string)=>void;recycleProcesses?:string[];attachments?:AttachedConnection[]}) {
  const resources = useMemo(() => new Map(trace.resources.map(resource => [resource.id,resource])),[trace.resources])
  const initialNodes = useMemo(() => {
    const membership = new Map<string,number[]>()
    trace.paths.forEach((path,index) => path.process_ids.forEach(id => membership.set(id,[...(membership.get(id) ?? []),index])))
    return [...membership].map(([id,paths]) => ({id,type:'recipe' as const,position:{x:0,y:0},style:{width:480},dragHandle:'.recipe-tile-toolbar',data:{process:trace.processes.find(process=>process.id===id)!,resources,paths,muted:false,inspect,inspectResource,recycle:recycleProcesses && !recycleProcesses.includes(id) ? undefined : recycle}}))
  },[trace,resources,inspect,inspectResource,recycle,recycleProcesses])
  const [nodes,setNodes,onNodesChange] = useNodesState<RecipeNode>(initialNodes)
  const loadedTrace = useRef(trace)
  const arrangedTrace = useRef<Trace | null>(null)
  useEffect(()=>{if(loadedTrace.current!==trace){loadedTrace.current=trace;setNodes(initialNodes)}},[trace,initialNodes,setNodes])
  const initialized = useNodesInitialized()
  const {getNodes,fitView} = useReactFlow<RecipeNode>()
  const dimensions = nodes.map(node => `${node.id}:${node.measured?.width}:${node.measured?.height}`).join('|')
  const connections = useMemo(()=>[...pathConnections(trace),...(attachments??[]).map(link=>({...link,id:JSON.stringify(['attached',link.source,link.target,link.resourceId]),paths:[0,1]}))],[trace,attachments])
  const edges: Edge[] = useMemo(()=>connections.map(link=>({id:link.id,source:link.source,target:link.target,label:('label' in link ? `${link.label}: ` : '')+(resources.get(link.resourceId)?.display_name || resources.get(link.resourceId)?.registry_name || link.resourceId),markerEnd:{type:MarkerType.ArrowClosed},style:{stroke:highlight===null || link.paths.includes(highlight) ? '#087c70' : '#bac5ce',strokeWidth:highlight===null || link.paths.includes(highlight) ? 2.5 : 1},labelStyle:{fontSize:11,fill:'#38596c'},labelBgPadding:[7,4] as [number,number],labelBgBorderRadius:4})),[connections,resources,highlight])
  const arrange = useCallback(() => {
    const graph = new dagre.graphlib.Graph().setGraph({rankdir:'TB',nodesep:85,ranksep:100,marginx:40,marginy:40}).setDefaultEdgeLabel(()=>({}))
    const current = getNodes()
    if(current.length!==initialNodes.length || current.some(node=>!initialNodes.some(expected=>expected.id===node.id))) return false
    current.forEach(node=>graph.setNode(node.id,{width:node.measured?.width ?? 480,height:node.measured?.height ?? 320}))
    connections.forEach(edge=>graph.setEdge(edge.source,edge.target))
    dagre.layout(graph)
    setNodes(current.map(node=>{const point=graph.node(node.id);return {...node,position:{x:point.x-(node.measured?.width ?? 480)/2,y:point.y-(node.measured?.height ?? 320)/2}}}))
    requestAnimationFrame(()=>{void fitView({padding:.16,maxZoom:.9})})
    return true
  },[getNodes,setNodes,connections,fitView,initialNodes])
  useEffect(()=>{if(initialized && arrangedTrace.current!==trace && arrange()) arrangedTrace.current=trace},[initialized,dimensions,arrange,trace])
  useEffect(()=>{setNodes(current=>current.map(node=>({...node,data:{...node.data,muted:highlight!==null && !node.data.paths.includes(highlight)}})))},[highlight,setNodes])
  return <ReactFlow nodes={nodes} edges={edges} onNodesChange={onNodesChange} nodeTypes={nodeTypes} minZoom={.1} maxZoom={2} nodesConnectable={false} onNodeClick={(_,node)=>inspect(node.id)} fitView ariaLabelConfig={{'controls.fitView.ariaLabel':'Fit all recipes','controls.zoomIn.ariaLabel':'Zoom in','controls.zoomOut.ariaLabel':'Zoom out'}}>
    <Background gap={20}/><Controls/><MiniMap pannable zoomable nodeColor="#c0dfd3"/>
    <Panel position="top-right"><button onClick={arrange}>Arrange recipes</button></Panel>
  </ReactFlow>
}
