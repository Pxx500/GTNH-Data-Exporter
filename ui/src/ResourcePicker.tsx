import { useEffect, useId, useRef, useState } from 'react'
import type { Page, Resource, Single } from './api'
import { query, useRequest } from './api'

export function ResourcePicker({label, selectedId, onSelect, onResolve}: {
  label: string
  selectedId: string
  onSelect: (id: string) => void
  onResolve: (id: string) => void
}) {
  const id = useId()
  const input = useRef<HTMLInputElement>(null)
  const [text, setText] = useState('')
  const [search, setSearch] = useState<string | null>(null)
  const [open, setOpen] = useState(false)
  const [activeIndex, setActiveIndex] = useState(-1)
  const hydration = useRequest<Single<Resource>>(selectedId ? query(`resources/${encodeURIComponent(selectedId)}`) : null)
  const results = useRequest<Page<Resource>>(search && !selectedId ? query('resources', {q: search, limit: 8}) : null)
  const resource = hydration.data?.item.id === selectedId ? hydration.data.item : undefined
  const showMenu = open && !selectedId
  const currentSearch = search !== null && search === text.trim()
  const candidates = currentSearch ? results.data?.items ?? [] : []

  useEffect(() => {
    if (resource && selectedId) {
      setText(resource.display_name || resource.registry_name)
      onResolve(selectedId)
    }
  }, [resource, selectedId, onResolve])

  useEffect(() => {
    setSearch(null)
    if (selectedId || !text.trim()) return
    const timer = setTimeout(() => setSearch(text.trim()), 250)
    return () => clearTimeout(timer)
  }, [text, selectedId])

  function choose(candidate: Resource) {
    setText(candidate.display_name || candidate.registry_name)
    setOpen(false)
    setActiveIndex(-1)
    onSelect(candidate.id)
    onResolve(candidate.id)
  }

  return <div className="resource-picker">
    <label htmlFor={`${id}-input`}>{label}</label>
    <div className="picker-input">
      <input ref={input} id={`${id}-input`} role="combobox" aria-autocomplete="list" aria-expanded={showMenu}
        aria-controls={`${id}-options`} aria-describedby={`${id}-identity`}
        aria-activedescendant={showMenu && candidates[activeIndex] ? `${id}-option-${activeIndex}` : undefined}
        autoComplete="off" placeholder="Type a resource name" value={text}
        onFocus={() => setOpen(true)} onBlur={() => setOpen(false)}
        onChange={event => {setText(event.target.value); onSelect(''); setOpen(true); setActiveIndex(-1)}}
        onKeyDown={event => {
          if (event.key === 'Escape') {event.preventDefault(); setOpen(false); setActiveIndex(-1)}
          else if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
            event.preventDefault(); setOpen(true)
            if (candidates.length) setActiveIndex(index => event.key === 'ArrowDown' ? (index + 1) % candidates.length : (index <= 0 ? candidates.length - 1 : index - 1))
          } else if (event.key === 'Enter' && !selectedId) {
            event.preventDefault()
            if (showMenu && candidates[activeIndex]) choose(candidates[activeIndex])
          }
        }}/>
      {(text || selectedId) && <button type="button" className="picker-clear" aria-label={`Clear ${label}`} onClick={() => {setText(''); onSelect(''); setActiveIndex(-1); setOpen(true); input.current?.focus()}}>×</button>}
    </div>
    <div className="picker-identity" id={`${id}-identity`}>
      {resource ? <><span>{resource.kind} · {resource.registry_name}{resource.metadata == null ? '' : ` · metadata ${resource.metadata}`} · {resource.nbt == null ? 'No NBT' : 'NBT identity present'}</span><code>Resource ID: {resource.id}</code></> : selectedId ? <span>{hydration.loading ? 'Loading selected resource…' : `Resource ID: ${selectedId}`}</span> : <span>Select a result to use its exact resource identity.</span>}
      {hydration.error && selectedId && <span role="alert">Selected resource lookup failed: {hydration.error} <button type="button" onClick={hydration.reload}>Retry</button></span>}
    </div>
    {showMenu && <div className="picker-menu">
      <ul role="listbox" id={`${id}-options`} aria-label={`${label} suggestions`}>
        {candidates.map((candidate, index) => <li role="option" id={`${id}-option-${index}`} aria-selected={activeIndex === index} key={candidate.id}
          onMouseDown={event => event.preventDefault()} onMouseMove={() => setActiveIndex(index)} onClick={() => choose(candidate)}>
          <strong>{candidate.display_name || candidate.registry_name}</strong>
          <span>{candidate.kind} · {candidate.registry_name}{candidate.metadata == null ? '' : ` · metadata ${candidate.metadata}`} · {candidate.nbt == null ? 'No NBT' : 'NBT identity present'}</span>
          <code>{candidate.id}</code>
        </li>)}
      </ul>
      {!text.trim() && <p>Type a display name or registry ID.</p>}
      {text.trim() && (!currentSearch || results.loading) && <p role="status">Searching resources…</p>}
      {currentSearch && results.error && <p role="alert">Search failed: {results.error} <button type="button" onMouseDown={event => event.preventDefault()} onClick={results.reload}>Retry</button></p>}
      {currentSearch && results.data && !candidates.length && <p>No matching resources. Try another name or registry ID.</p>}
    </div>}
  </div>
}
