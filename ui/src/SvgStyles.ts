/** Share captured declarations without changing the SVG's materialized layout. */
export function shareSvgStyles(svg:SVGElement) {
  // Inline declarations outrank existing selectors. Keep that cascade intact
  // when a capture includes its own stylesheet (including embedded fonts).
  if(svg.querySelector('style, link[rel="stylesheet"]'))return
  const attributeBase='data-recipe-board-style'
  let attribute=attributeBase
  for(let suffix=1;svg.hasAttribute(attribute) || svg.querySelector(`[${attribute}]`);suffix++)attribute=`${attributeBase}-${suffix}`
  const styles=new Map<string,{style:CSSStyleDeclaration,elements:Element[]}>()
  for(const element of [svg,...svg.querySelectorAll('[style]')]){
    const text=element.getAttribute('style')
    if(!text)continue
    const existing=styles.get(text)
    if(existing){existing.elements.push(element);continue}
    const style=document.createElement('div').style
    style.cssText=text
    // CSSOM can discard unknown syntax. Such declarations stay inline verbatim.
    if(style.cssText===text)styles.set(text,{style,elements:[element]})
  }
  if(!styles.size)return
  const entries=[...styles.values()]
  const common=document.createElement('div').style
  // Custom properties have no shorthand interactions. Other properties keep
  // their original order together in each complete style-specific rule.
  for(const property of Array.from(entries[0].style).filter(name=>name.startsWith('--'))){
    const priority=entries[0].style.getPropertyPriority(property)
    if(entries.some(entry=>!Array.from(entry.style).includes(property) || entry.style.getPropertyPriority(property)!==priority))continue
    const values=new Map<string,number>()
    for(const entry of entries){
      const value=entry.style.getPropertyValue(property)
      values.set(value,(values.get(value) || 0)+1)
    }
    const value=[...values].sort((left,right)=>right[1]-left[1])[0][0]
    common.setProperty(property,value,priority)
  }
  const rules=common.cssText?[`[${attribute}]{${common.cssText}}`]:[]
  for(const [index,entry] of entries.entries()){
    for(const property of Array.from(common)){
      if(entry.style.getPropertyValue(property)===common.getPropertyValue(property))entry.style.removeProperty(property)
    }
    if(entry.style.cssText)rules.push(`[${attribute}="${index}"]{${entry.style.cssText}}`)
    for(const element of entry.elements){
      element.removeAttribute('style')
      element.setAttribute(attribute,String(index))
    }
  }
  const stylesheet=svg.ownerDocument.createElementNS('http://www.w3.org/2000/svg','style')
  stylesheet.textContent=rules.join('\n')
  svg.insertBefore(stylesheet,svg.firstChild)
}
