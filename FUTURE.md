# Potential future extensions

These ideas extend the implemented capture, lookup, bounded path search,
selected-path recycling, chemical loop witnesses, GUI and MCP. They are
candidates for later work, not requirements of the current milestone.

## Production planning

- Joint quantitative plans with several secondary material roles at once,
  protecting requested target output and accounting shared side inputs
- Joint objectives for multiple target products
- Shared objectives and resource budgets across independently requested plans
- Minimal startup stocks under interleaved native batch scheduling
- Native correlated stochastic behavior beyond labelled expected quantities
- Throughput and overclocking models where native machine behavior is known
- Explicit comparisons of yield, energy, steps and machine requirements

## Richer discovery and constraints

- Additional side-material roles and explicit reagent-budget constraints
- Native composition integration for unresolved GT++, BartWorks and other
  materials, without treating display formulas as authoritative chemistry
- Constraints on side-input consumption, distinct from path intermediates
- Weighted resource budgets and priorities beyond explicit basic-resource boundaries
- Full machine, amperage, temperature, cleanroom and environment constraints
  beyond nominal recipe voltage tiers, with unknown requirements explicit
- More diverse alternatives, grouping similar paths without losing costs
- Collapsible form conversions and packaging, retaining empty containers,
  returns and the complete underlying operations
- Material/form filters spanning variants only where captured relations
  justify that grouping
- More direct library entry points for existing network and loop audits
- More selective bounded trace discovery for broad full-pack queries that
  currently reach the server's process-search bound
- A portable filtered-snapshot export that preserves all referenced records
  and explains omissions, beyond non-destructive offline query scopes
- Broader acquisition adapters and machine execution checks to strengthen
  structural dead-end warnings
- Additional statistically justified anomaly cohorts, without treating
  unrelated products as comparable energy costs

## Design boundaries

Exact resource identity and native ingredient matching remain authoritative.
Semantic search proposes candidates and does not prove chemical behavior.
A material dependency path is not a balanced or executable production plan.
Steady-state balance does not establish that a loop can start.
Search and capture limits remain visible. Global factory optimization is
not an initial target.
