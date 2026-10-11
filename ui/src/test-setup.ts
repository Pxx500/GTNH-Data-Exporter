import '@testing-library/jest-dom/vitest'
// jsdom has no layout engine. Supply the browser measurement primitives used
// by ReactFlow while keeping its real node rendering and interactions in tests.
class LayoutObserver {
  constructor(private callback: ResizeObserverCallback) {}
  observe(target: Element) {queueMicrotask(()=>this.callback([{target,contentRect:target.getBoundingClientRect()} as ResizeObserverEntry],this as unknown as ResizeObserver))}
  unobserve() {}
  disconnect() {}
}
Object.defineProperty(window,'ResizeObserver',{value:LayoutObserver,writable:true})
Object.defineProperty(globalThis,'ResizeObserver',{value:LayoutObserver,writable:true})
Object.defineProperty(HTMLElement.prototype,'offsetWidth',{get(){return parseFloat(this.style.width)||1000},configurable:true})
Object.defineProperty(HTMLElement.prototype,'offsetHeight',{get(){return parseFloat(this.style.height)||350},configurable:true})
Object.defineProperty(window,'DOMMatrixReadOnly',{value:class {m22=1},writable:true})
Object.defineProperty(SVGElement.prototype,'getBBox',{value(){return {x:0,y:0,width:100,height:20}},configurable:true})
