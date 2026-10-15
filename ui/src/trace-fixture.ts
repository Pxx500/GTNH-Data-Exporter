import type {Trace} from './api'

// Existing fixtures describe native recipes with no equivalent variants.
export function traceFixture(trace:Omit<Trace,'recipe_groups'|'path_groups'>):Trace {
  return {...trace,
    recipe_groups:trace.processes.map(process=>({id:`native:${process.id}`,basis:'native_process',process_ids:[process.id],auxiliary_input_indices:{[process.id]:[]}})),
    path_groups:trace.paths.map((_,index)=>({id:`path:${index}`,representative_path_index:index,path_indices:[index]})),
  }
}
