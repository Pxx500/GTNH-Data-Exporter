import {act,cleanup,renderHook,waitFor} from '@testing-library/react'
import {afterEach,expect,test,vi} from 'vitest'
import {useTraceJob} from './useTraceJob'

afterEach(()=>{cleanup();vi.unstubAllGlobals();vi.useRealTimers()})
const job={job_id:'client-job',snapshot_id:'snapshot',revision:1,result_revision:0,status:'running',phase:'preparing',elapsed_seconds:0,progress:{},request:{path_selection:'material'}}
const response=(value:unknown,status=200)=>new Response(JSON.stringify(value),{status})

test('a creation finishing after unmount is disposed without reviving client state',async()=>{
  let finish:((value:Response)=>void)|undefined
  const calls:{url:string;method:string}[]=[]
  vi.stubGlobal('fetch',vi.fn(async(url:string,init?:RequestInit)=>{
    calls.push({url,method:init?.method??'GET'})
    if(init?.method==='POST')return new Promise<Response>(resolve=>{finish=resolve})
    return response({...job,status:'closed'})
  }))
  const view=renderHook(()=>useTraceJob('snapshot'))
  act(()=>{void view.result.current.start({path_selection:'material'})})
  await waitFor(()=>expect(finish).toBeDefined())
  view.unmount()
  await act(async()=>{finish!(response(job))})
  expect(calls).toEqual([{url:'/api/trace-jobs',method:'POST'},{url:'/api/trace-jobs/client-job',method:'DELETE'}])
})

test('unchanged job revisions keep polling with one request in flight until a terminal response',async()=>{
  vi.useFakeTimers()
  let finish:((value:Response)=>void)|undefined
  const reads:string[]=[]
  vi.stubGlobal('fetch',vi.fn(async(url:string,init?:RequestInit)=>{
    if(init?.method==='POST')return response(job)
    if(init?.method==='DELETE')return response({...job,status:'closed'})
    reads.push(url)
    if(reads.length===1)return response(job)
    return new Promise<Response>(resolve=>{finish=resolve})
  }))
  const view=renderHook(()=>useTraceJob('snapshot'))
  await act(async()=>{await view.result.current.start({path_selection:'material'})})
  await act(async()=>{await vi.advanceTimersByTimeAsync(500)})
  expect(reads).toHaveLength(1)
  await act(async()=>{await vi.advanceTimersByTimeAsync(500)})
  expect(reads).toHaveLength(2)
  await act(async()=>{await vi.advanceTimersByTimeAsync(3000)})
  expect(reads).toHaveLength(2)
  await act(async()=>{finish!(response({...job,revision:2,status:'finished'}))})
  await act(async()=>{await vi.advanceTimersByTimeAsync(1500)})
  expect(reads).toEqual(['/api/trace-jobs/client-job?after_revision=1','/api/trace-jobs/client-job?after_revision=1'])
  expect(view.result.current.job?.status).toBe('finished')
})

test('a failed job start exposes the server error without falling back to synchronous trace',async()=>{
  const fetch=vi.fn(async()=>response({error:'Material jobs unavailable'},503))
  vi.stubGlobal('fetch',fetch)
  const view=renderHook(()=>useTraceJob('snapshot'))
  await act(async()=>{await view.result.current.start({path_selection:'material'})})
  expect(view.result.current.error).toBe('Material jobs unavailable')
  expect(view.result.current.result).toBeUndefined()
  expect(fetch).toHaveBeenCalledTimes(1)
  expect(fetch.mock.calls[0]).toEqual(['/api/trace-jobs',expect.objectContaining({method:'POST'})])
})
