# Potential future extensions

These ideas are deferred while the core capture, faithful recipe lookup,
bounded path search, GUI and MCP are completed. They are candidates for
later work, not commitments or requirements of the current milestone.

## Production planning

- Quantitative plans for a requested amount of output, including all input
  slots, alternative ingredients, co-products, losses and external supplies
- Multiple starting resources and multiple target products
- Net resource, reagent and energy balances
- Recycling loops with separate startup stocks and ongoing consumption
- Separate guaranteed production from expected probabilistic yields
- Throughput and overclocking models where native machine behavior is known
- Explicit comparisons of yield, energy, steps and machine requirements

## Richer discovery and constraints

- Function-based recipe search, such as acid recovery, returning verifiable
  native recipes with an explanation of why they match
- Material composition, formula and form catalogs captured from native data
- Constraints on side-input consumption, distinct from path intermediates
- Supplied-resource boundaries and permitted external imports
- Machine, tier, temperature, cleanroom and environment constraints, with
  unknown requirements reported explicitly
- More diverse alternatives, grouping similar paths without losing costs
- Collapsible form conversions and packaging, retaining empty containers,
  returns and the complete underlying operations
- Material/form filters spanning variants only where captured relations
  justify that grouping

## Design boundaries

Exact resource identity and native ingredient matching remain authoritative.
Semantic search proposes candidates and does not prove chemical behavior.
A material dependency path is not a balanced or executable production plan.
Steady-state balance does not establish that a loop can start.
Search and capture limits remain visible. Global factory optimization is
not an initial target.
