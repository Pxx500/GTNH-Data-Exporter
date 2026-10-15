import {useCallback,useEffect,useRef,useState} from 'react'
import {query} from './api'
import type {Trace,TraceJob} from './api'

async function request(path:string,method='GET',body?:unknown,signal?:AbortSignal):Promise<TraceJob> {
  const response=await fetch(query(path),{method,signal,...(body===undefined?{}:{headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})})
  const value=await response.json()
  if(!response.ok)throw new Error(typeof value.error==='string'?value.error:typeof value.detail==='string'?value.detail:JSON.stringify(value))
  return value
}
const jobPath=(id:string)=>`trace-jobs/${encodeURIComponent(id)}`

export function useTraceJob(snapshotId:string) {
  const [state,setState]=useState<{job?:TraceJob;result?:Trace;busy:boolean;closing?:boolean;error?:string}>({busy:false})
  const latest=useRef<TraceJob|undefined>(undefined)
  const generation=useRef(0)
  const mounted=useRef(true)
  const closingRequest=useRef<AbortController|undefined>(undefined)
  const accept=useCallback((value:TraceJob,token:number)=>{
    if(!mounted.current || token!==generation.current)return
    const previous=latest.current
    if(value.snapshot_id!==snapshotId)throw new Error('Search belongs to a different snapshot. Start a new search.')
    if(previous && (value.job_id!==previous.job_id || value.revision<=previous.revision))return
    latest.current=value
    setState(current=>({...current,job:value,result:value.result && (!previous || value.result_revision>previous.result_revision)?value.result:current.result,error:undefined}))
  },[snapshotId])
  useEffect(()=>{
    mounted.current=true
    return ()=>{
      mounted.current=false
      generation.current++
      closingRequest.current?.abort()
      const current=latest.current
      latest.current=undefined
      if(current)void request(jobPath(current.job_id),'DELETE').catch(()=>{})
    }
  },[])
  useEffect(()=>{
    if(state.job?.status!=='running' || state.busy || state.error)return
    const controller=new AbortController()
    const token=generation.current
    let timer:ReturnType<typeof setTimeout>
    async function poll(){
      const current=latest.current
      if(!current)return
      try{
        const value=await request(`${jobPath(current.job_id)}?after_revision=${current.revision}`,'GET',undefined,controller.signal)
        if(!controller.signal.aborted){accept(value,token);timer=setTimeout(poll,500)}
      }catch(error){if(!controller.signal.aborted && token===generation.current)setState(current=>({...current,error:error instanceof Error?error.message:String(error)}))}
    }
    timer=setTimeout(poll,500)
    return ()=>{clearTimeout(timer);controller.abort()}
  },[state.job,state.busy,state.error,accept])
  const dispose=useCallback(async(current:TraceJob,token:number)=>{
    const controller=new AbortController()
    closingRequest.current?.abort()
    closingRequest.current=controller
    const timeout=setTimeout(()=>controller.abort(),10000)
    try{
      let value=await request(jobPath(current.job_id),'DELETE',undefined,controller.signal)
      accept(value,token)
      while(value.status==='running'){
        await new Promise<void>((resolve,reject)=>{
          const cancelled=()=>{clearTimeout(timer);reject(new Error('Closing wait cancelled'))}
          const timer=setTimeout(()=>{controller.signal.removeEventListener('abort',cancelled);resolve()},250)
          if(controller.signal.aborted)cancelled()
          else controller.signal.addEventListener('abort',cancelled,{once:true})
        })
        value=await request(`${jobPath(current.job_id)}?after_revision=${value.revision}`,'GET',undefined,controller.signal)
        accept(value,token)
      }
    }catch(error){
      if(controller.signal.aborted)throw new Error('The previous search has not confirmed closure. Retry updates before starting a new search.')
      throw error
    }finally{
      clearTimeout(timeout)
      if(closingRequest.current===controller)closingRequest.current=undefined
    }
  },[accept])
  const close=useCallback(async()=>{
    const token=++generation.current
    const current=latest.current
    setState(state=>({...state,busy:true,closing:!!current,error:undefined}))
    try{
      if(current)await dispose(current,token)
      if(!mounted.current || token!==generation.current)return false
      latest.current=undefined
      setState({busy:false})
      return true
    }catch(error){
      if(mounted.current && token===generation.current)setState(state=>({...state,busy:false,closing:false,error:error instanceof Error?error.message:String(error)}))
      return false
    }
  },[dispose])
  const start=useCallback(async(arguments_:Record<string,unknown>)=>{
    const token=++generation.current
    const previous=latest.current
    setState(current=>({...current,busy:true,closing:!!previous,error:undefined}))
    try{
      if(previous)await dispose(previous,token)
      if(!mounted.current || token!==generation.current)return false
      const value=await request('trace-jobs','POST',arguments_)
      if(!mounted.current || token!==generation.current){void request(jobPath(value.job_id),'DELETE').catch(()=>{});return false}
      if(value.snapshot_id!==snapshotId){void request(jobPath(value.job_id),'DELETE').catch(()=>{})}
      latest.current=undefined
      setState({busy:true})
      accept(value,token)
      return true
    }catch(error){if(mounted.current && token===generation.current)setState(current=>({...current,error:error instanceof Error?error.message:String(error)}));return false}
    finally{if(mounted.current && token===generation.current)setState(current=>({...current,busy:false,closing:false}))}
  },[snapshotId,accept,dispose])
  const command=useCallback(async(action:'pause'|'continue',timeBudget?:number)=>{
    const current=latest.current
    if(!current || (action==='continue' && current.status!=='paused'))return
    const token=generation.current
    setState(state=>({...state,busy:true,error:undefined}))
    try{accept(await request(`${jobPath(current.job_id)}/${action}`,'POST',action==='continue'?{time_budget_seconds:timeBudget}:{}),token)}
    catch(error){if(mounted.current && token===generation.current)setState(state=>({...state,error:error instanceof Error?error.message:String(error)}))}
    finally{if(mounted.current && token===generation.current)setState(state=>({...state,busy:false}))}
  },[accept])
  return {...state,start,close,pause:()=>command('pause'),continueSearch:(seconds:number)=>command('continue',seconds),retry:()=>setState(current=>({...current,error:undefined,job:latest.current?{...latest.current}:undefined}))}
}
