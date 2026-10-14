# Reaction routes with material continuity and bounded alternatives

Researched 2026-10-14. This is research only. No production code, canonical database, running GUI, or MCP configuration was changed. Sources were fetched and parsed. Their implementations were inspected but not executed against GTNH.

## Recommendation

Keep the prepared symbolic factor graph and its relaxed distance guidance. Test a typed material/form transformation map with concrete recipe witnesses, a very small set of competing labels, and branch-first structural diversity within the existing search limits. Carry source-contribution evidence and construction roles through that map. Reaction-network research supports these ingredients, but none of the papers establishes that this combination will improve GTNH at the current budget. Measure that claim explicitly.

Start with the concrete native-metadata gap found by the main agent: the current material token extraction ignores additional declared association constituents. Test those already-exported facts before investing in a larger semantic-map preparation. This is a bounded signal improvement within experiment A, not a claim of atom provenance or a new export requirement.

The useful question for Iron Dust to LV Machine Hull is whether a route preserves evidence that the starting material contributes to the construction branch. A short route through Hydrogen, plastic, and cable can be a legal dependency explanation while answering that question poorly. Low world-source depth cannot resolve this because Hydrogen itself has a shallow acquisition route. The current material policy and these limitations are recorded in [FLOW_SEARCH_RESEARCH.md](FLOW_SEARCH_RESEARCH.md).

The supplied latest Volcanus query returned six paths covering eight of fifteen target ingredient branches, with 512 examined and a 20,000 queued-state limit. This is a supplied baseline, not a measurement performed by this research. Reallocating work might improve coverage. Reranking an already discovered pool cannot recover a branch absent from that pool.

## Five relevant primary sources

### 1. Source atoms, rather than arbitrary reaction adjacency

**Allison P. Heath, George N. Bennett, and Lydia E. Kavraki. Finding metabolic pathways using atom tracking.** Published online 2010-04-25, Bioinformatics 26(12), issue 2010-06-15.

The algorithms search linear and branched pathways while retaining a specified number of atoms from a source compound. The search state includes an atom marking. Thus, two visits to the same compound can have different surviving source atoms. The authors also share identical atom-mapping patterns across multiple reactions, reducing repeated exploration while retaining the reaction correspondence for branched results. This is close to the purpose of prepared symbolic factors, though GTNH matching predicates are not atom mappings. [Full paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC2881407/)

On 48 known linear pathways, the reported top-path accuracy was 0.64 when conserving the maximum number of source carbons, 0.37 when conserving at least one carbon, and 0.15 without tracking. Best-of-five accuracy was 0.85, 0.65, and 0.39 respectively. These results support source contribution as a relevance objective. They do not predict GTNH accuracy or runtime. The branched experiments used up to one million candidate paths, so that enumeration budget is unsuitable here. The paper also reports a likely infeasible shortcut caused by missing reaction direction information. [Evaluation and limitations](https://pmc.ncbi.nlm.nih.gov/articles/PMC2881407/)

**Transfer:** retain history about source-material evidence instead of awarding fresh source credit whenever a later resource happens to overlap the source's native material labels. **Missing prerequisite:** GTNH has no verified per-recipe atom map in the current evidence. Native composition similarity cannot establish which input supplied an output's material.

### 2. Atom groups, branched merging, and ranking

**Yiran Huang, Yusi Xie, Cheng Zhong, and Fengfeng Zhou. Finding branched pathways in metabolic network via atom group tracking.** PLOS Computational Biology, 2021-02-02.

BPFinder enumerates linear pathways conserving atom groups, then merges them using overlapping or non-overlapping conserved-group rules. It ranks results using compound similarity, conserved groups, reaction thermodynamics, and branch information. The paper evaluates against 30 known branched pathways and several existing methods on a network of 5,848 compounds and 7,340 reactions with atom-mapping data. This is tested evidence for combining contribution and structural relevance. Its network is much smaller than the supplied GTNH workload. [Full paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC7880430/)

**Transfer:** contribution and structural relevance can be separate ranking dimensions. **Do not transfer:** Gibbs free energy is not a substitute for GTNH voltage, heat, machine access, duration, chance, or native conditions. Merging two GTNH spines would also need AND-slot, shared-resource, quantity, and tool semantics that this implementation does not provide.

### 3. Class continuity depends on path history

**Kevin Lim and Limsoon Wong. CMPF: Class-switching minimized pathfinding in metabolic networks.** BMC Bioinformatics 13(Suppl 17):S17, 2012-12-07.

CMPF retains the intersection of classes supporting successive reactions. If that intersection becomes empty, the route incurs a switch and starts a new class segment. A class can represent a pathway, species, or localization. The paper explains why a fixed edge weight cannot represent this accurately: the same shared edge can incur a switch on one route and none on another. Its implementation uses bounded-depth enumeration and path-specific scoring. Comparisons on known routes show fewer class switches and better alignment with native pathways, including the glucose-to-pyruvate example. [Full paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC3521384/)

**Transfer:** path-history labels and cumulative switching penalties are an established way to discourage wandering between unrelated contexts. **Limit:** GTNH recipe family is usually a machine or operation family, not a biological pathway class. A valid steel construction chain can change machine family several times. Native material classes are incomplete and can change legitimately through alloys and assemblies. Test a soft history penalty, not a family boundary or a hard continuity requirement. The authors' biological justification for class switching is a hypothesis, not proof that every switch is undesirable.

### 4. AND-aware topological scope and structural diversity

**Aarthi Ravikrishnan, Meghana Nasre, and Karthik Raman. Enumerating all possible biosynthetic pathways in metabolic networks.** Scientific Reports 8:9932, 2018-07-02.

MetQuest performs guided breadth-first expansion only when every reaction precursor belongs to the current scope. It then combines reaction sets with dynamic programming to enumerate branched and cyclic pathways under a size cutoff. It needs an explicit seed set, commonly including cofactors and energy currencies. Its definitions concern producibility from that seed set using network topology. They do not certify quantitative mass balance or a player's inventory. [Full article XML](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC6028704/fullTextXML), [author summary](https://ramanlab.github.io/publications/enumerating-all-possible-biosynthetic-pathways-from-metabolic-networks/)

The paper evaluates similarity using the Jaccard index of constituent reaction sets. In its glucose-to-pyruvate experiment, 4,787 enumerated pathways became 1,007 when requiring use of glucose. High-overlap alternatives included transporter variants, while low-overlap alternatives included different metabolic routes. This directly supports measuring structural route diversity separately from the number of returned paths. However, including a source-using reaction in a reaction set still does not prove source-atom contribution. [Full article](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC6028704/fullTextXML)

**Transfer:** compare the reaction sets of a bounded candidate pool. Keep AND-aware scope as a separate optional planning diagnostic. **Do not adopt full enumeration:** it needs seed assumptions and can multiply ingredient subpath combinations. The inspected assembler removes reactions with at least five nonseed reactants and defaults to a 1,000-combination threshold for some already-found outputs. Those implementation restrictions would silently discard important GTNH recipes. [Assembler source](https://github.com/RamanLab/metquest/blob/master/metquest/pathway_assembler.py)

### 5. Multiple labels without collapsing distinct tradeoffs

**Zhongqiang Ren, Carlos Hernández, Maxim Likhachev, Ariel Felner, Sven Koenig, Oren Salzman, Sivakumar Rathinam, and Howie Choset. EMOA*: A Framework for Search-Based Multi-Objective Path Planning.** Artificial Intelligence 339:104260, 2025. The fetched 44-page author preprint is dated 2024-12-03.

EMOA* retains nondominated cost labels at each vertex and accelerates frontier dominance checks. It uses nonnegative vector costs and consistent heuristics. The paper reports comparisons with three, four, and five objectives and speedups up to an order of magnitude over its baselines. It also states that the Pareto frontier can grow exponentially. Its exact guarantee applies to cost-unique Pareto paths when the full required search is performed, not to a small capped GTNH search. [Author PDF](https://rap-lab.github.io/documents/publications/2024_AIJ_EMOA.pdf), [author publication record](https://rap-lab.github.io/research/mopp)

**Transfer:** preserve a short material-continuous route and a shorter byproduct route when neither dominates the other. **Limit:** a label cap makes this a heuristic. Compare dominance only for states with equivalent future options. In GTNH, resource identity alone is insufficient when visited-resource restrictions, remaining depth, waypoints, branch obligations, NBT predicates, or material history differ. A global shortest-hop cost cannot safely erase these distinctions.

## GitHub implementations checked

| Project | Algorithm evidence read | License evidence | Fit and limits |
| --- | --- | --- | --- |
| [hyr0771/BPFinder](https://github.com/hyr0771/BPFinder) | `src/process/FileUtils.java`, `handleAtom` composes transfer matrices and tests conserved groups. `src/process/TreeTools.java` contains intersection-aware merge and conflict functions. `src/process/Process.java` contains path and branch ranking functions | [GPL version 3 LICENSE](https://github.com/hyr0771/BPFinder/blob/master/LICENSE) | Java implementation with native atom mappings and MySQL data. Reference for contribution and merging. No GTNH equivalence established |
| [RamanLab/metquest](https://github.com/RamanLab/metquest) | `guided_bfs.py`, `forward_pass` checks predecessor-set inclusion. `pathway_assembler.py`, `find_pathways` assembles reaction sets. `execute_metquest.py`, `find_jaccard_between_paths` computes reaction-set overlap | [GPL version 2 LICENSE](https://github.com/RamanLab/metquest/blob/master/LICENSE) | Useful algorithms and explicit APIs. Seed-set assumptions, combination growth, graph mutation, and the five-reactant removal prevent direct use |
| [rap-lab-org/public_emoa](https://github.com/rap-lab-org/public_emoa) | `source/search_emoa.cpp`, `EMOA::Search`, `_FrontierCheck`, `_SolutionCheck`, `_UpdateFrontier`, `RunEMOA`. Python `runEMOA` wraps the CLI | README says academic and noncommercial use. No `LICENSE` file in the fetched tree and GitHub API has no recognized SPDX license | Reference implementation rather than an adopted dependency. Ordinary directed cost graph. Python wrapper is documented for grid-like maps. No AND/NBT handling |
| [hyr0771/AFP](https://github.com/hyr0771/AFP) | README describes atom-group transfer plus stoichiometric MILP and four source/conservation modes | No LICENSE at repository root, and GitHub API has no recognized license | Boundary comparison only. Requires GUROBI. Full algorithm source was not inspected, and its scientific paper was not used as one of the five verified papers |

The [MetQuest traversal](https://github.com/RamanLab/metquest/blob/master/metquest/guided_bfs.py), [Jaccard implementation](https://github.com/RamanLab/metquest/blob/master/metquest/execute_metquest.py), [BPFinder atom tracking](https://github.com/hyr0771/BPFinder/blob/master/src/process/FileUtils.java), and [EMOA implementation](https://github.com/rap-lab-org/public_emoa/blob/main/source/search_emoa.cpp) were fetched successfully as source text. License descriptions above report the files and metadata checked. No third-party implementation was copied, installed, compiled, or run.

## What GTNH can support

The supplied workload has 118,717 item/fluid identities and 259,781 recipes. It preserves AND slots, OR choices, multiple outputs, cycles, NBT matching, amounts, chance, required-presence slots, and native conditions. Keep these contracts intact in every experiment.

The earlier prepared-graph study measured native primary-material labels on 28,631 resources, 24.12% of that snapshot. It found 122,883 eligible processes with known primary material on both input and output sides. These are earlier measurements, not a fresh coverage census for the latest snapshot. Component metadata can add evidence, but its completeness and semantics require separate checks. Primary material, recursive composition, item form, consumed contribution, and output position are different signals. [Existing measurements](FLOW_SEARCH_RESEARCH.md)

### Fresh native constituent evidence from the main agent

The main agent inspected `get_resource` records from canonical snapshot `779ea030-ae9c-40ea-8854-99a176f7cc42` and the current `material_tokens` implementation, lines 26–42 of [python/src/gtnh_data/flow_index.py](python/src/gtnh_data/flow_index.py). The native association source API is `GTOreDictUnificator.getItemData`. These observations are supplied evidence from the main agent, not a new database query performed by this research agent.

For `r32547`, Robot Arm IV, the native association's primary material is Graphene and its OrePrefix is null. The record also declares `has_explicit_composition: true`. Its association `byproducts` include TungstenSteel at 32,659,200 GT units, Tungsten at 30,844,800 GT units, and NeodymiumMagnetic at 5,443,200 GT units. TungstenSteel's native components include Steel, whose components include Iron and Carbon. The current token extraction collects the primary material and its recursive components, so it misses the declared Iron-bearing constituent path in this item. Source: main-agent `get_resource` observation for `r32547` in the snapshot above and `material_tokens` source inspection.

Here, **association `byproducts` means an additional material association field**. It is separate from outputs marked or hinted as byproducts of a recipe. Do not use an association constituent's position to penalize a recipe output. These GT-unit material amounts are not a verified recipe mass balance or an atom-origin map.

This supports a cheap first test: include all declared association constituents and their native recursive components in material evidence, retaining the field origin and declared amount. Report which tokens came from primary material and which came from additional constituents. Do not infer that Robot Arm IV's functional role is Graphene, or invent its missing form prefix. Additional material evidence can improve a source-contribution hint while leaving form and construction-role evidence unknown.

The main agent also observed no material association for `r10135` Hastelloy W Gear, `r24290` Double Hastelloy N Plate, `r41032` casing, and `r41033` Computer Cube in this snapshot. Their names are not composition evidence. The additional-constituent change needs no new export for the already-declared subset, but it does not repair these missing native associations. Source: main-agent `get_resource` observations for the four resource IDs above.

Do not infer chemical purity, atom counts, or source provenance from names such as Iron, Steel, Hydrogen, or Cable. A material overlap can come from another AND input. A declared secondary output can be the intended recovery product. Unknown composition is unknown, not zero contribution. Required-presence inputs can constrain execution without being consumed material.

| Result type | What it establishes | What remains unresolved |
| --- | --- | --- |
| Dependency spine | A sequence of legal ingredient/output relationships under the matching rules | Other AND inputs, material provenance, amounts, tools, machine access, and execution |
| MetQuest-style scope from declared seeds | Qualitative producibility when every input is in scope | Source contribution, quantities, stochastic outputs, inventory conservation, and machine conditions |
| Stoichiometric or inventory plan | Feasibility under its explicitly modeled balances and assumptions | Any omitted tools, machines, time, conditions, chance, or source-origin constraint |

AFP illustrates why balancing quantities and tracking source contribution are separate questions: its README explicitly adds atom-group transfer constraints to a stoichiometric MILP. It is not a drop-in bounded dependency-path engine. [AFP README](https://github.com/hyr0771/AFP/blob/master/README.md)

## A semantic transformation map is different from SCC islands

The failed SCC experiment groups resources by mutual reachability. A functional transformation map groups steps by what they do. A giant connected component can still contain useful material processing, forming, assembly, electronics, and chemical-recovery patterns. Failure of SCC partitions therefore does not reject this different abstraction. Native primary material alone is also insufficient because it discards the forms needed to connect actual recipes.

KEGG gives a concrete first-party example. **KEGG REACTION Database**, updated 2023-09-08, separates complete reaction records from RCLASS transformation classes. These classes describe the chemical changes in substrate-product pairs. It distinguishes a main pair from other reaction pairs and defines reaction modules as conserved sequences of transformation classes. **KEGG Reaction Module**, updated 2026-06-01, organizes these sequences into a hierarchy, variations, combinations, and overview maps. **KEGG PATHWAY Database**, updated 2026-07-23, describes manually drawn functional maps linked to reactions and modules. These are semantic maps grounded in chemical facts and curated roles, rather than connected-component partitions. [REACTION documentation](https://www.genome.jp/kegg/reaction/), [reaction-module documentation](https://www.genome.jp/kegg/reaction/rmodule.html), [PATHWAY documentation](https://www.genome.jp/kegg/pathway.html)

This establishes that transformation-based semantic maps exist and have a concrete representation. It does not establish that a KEGG ontology or hierarchy is a tested GTNH acceleration algorithm. CMPF supplies tested path-history class guidance, while the existing HPA* investigation supplies the need to refine abstract connections into concrete witnesses. Neither supplies GTNH material provenance. [CMPF](https://pmc.ncbi.nlm.nih.gov/articles/PMC3521384/), [existing hierarchical-pathfinding research](FLOW_SEARCH_RESEARCH.md)

A practical GTNH prototype can use the native facts already supplied: primary material and components, OrePrefix forms where present, recipe family/GT map, consumed-slot predicates, and output identities. Represent a typed transition as an input material/form, operation family, output material/form, and the exact selected consumed-slot/output pair. Retain every underlying recipe ID and matching predicate as a witness. Assembly endpoints without material metadata can still be reached through their concrete target ingredient branches. No name embedding is required.

The desired explanation can then distinguish these purposes:

| Purpose | Example meaning | Evidence available now |
| --- | --- | --- |
| Material transformation | Iron contributes to steel production | Native component overlap plus the concrete recipe. A contribution hint, not an atom map |
| Form change | Steel dust, ingot, molten material, or plate is converted into another steel form | Native material and OrePrefix plus exact recipe witnesses. Equal material labels do not establish lossless conversion |
| Construction role | Plate supplies a casing branch that supplies a hull or machine | Target ingredient branch and concrete assembly recipe. Broad construction-role names remain an interpretation unless exported natively |
| Supporting branch | Cable, electronics, tools, or chemical reagents support assembly | Independent target slots and native forms/families where available. They must remain separate AND obligations |

The iron-to-steel-to-plate-to-casing-to-machine sketch is a semantic explanation to test, not a promised executable recipe sequence. Actual tier filters and recipes must determine the refined sequence. A material region needs **form ports** that retain concrete identity and matching predicates. An ingot port cannot be substituted for a dust port solely because both carry the same material label. Required/excluded intermediates, NBT, OR choices, tiers, amounts, yields, chance, and conditions must remain visible in internal witnesses.

For an initial experiment, prepare typed memberships and transition classes, then lazily discover only the internal form-conversion witness needed to connect a candidate region entry to its requested exit. Cache a bounded number of concrete witnesses using the same snapshot and query constraints. Avoid all-pairs port preparation. Count internal witness work against the existing global budget. Do not compose two abstract edges unless their refined ports really match. A coarse transition with no qualifying witness is not a route.

This can reduce repeated explanation and exploration of ingot/plate/dust variants without treating every conversion as a new construction mechanism. The current engine already rejects exact resource revisits on a path. The remaining issue is aliases, different forms, and hub detours, not a missing exact-cycle check. Prefer a short qualifying internal witness while retaining conversions that the real recipes require. Do not blanket-remove recycling. A loop can be relevant to byproduct recovery, quantity/yield analysis, or an explicit chemical-loop audit.

**Practical now:** a partial typed map, concrete witness refinement, source-history hints, and branch-relative roles on metadata-covered routes. First measure how many resources, ports, and transitions are classifiable. Keep unclassified records explicit and searchable under the same budget. The earlier 24.12% primary-material coverage is too sparse to assume a complete map. Measure OrePrefix and component coverage separately, including the intersection of all three signals and coverage on the actual benchmark routes.

**Requires stronger export or curation:** comprehensive form/role metadata for unsupported items and assembled components, authoritative primary input/output contribution roles, or true per-recipe material provenance. Native composition alone cannot resolve which AND input supplied an element or whether a same-material conversion preserves quantity. Export these facts only if a useful native owner provides them. Do not manufacture purity, main-pair roles, lossless conversions, or atom mappings from resource names or output positions.

## Three narrow experiments at the current limits

These are proposed experiments, not verified GTNH improvements. Freeze the snapshot, source and target IDs, filters, path count, `max_extra_steps`, process-examination cap, state/expansion cap, and queue cap. Count every additional label and branch search against the same totals. Report preparation, queue work, payload assembly, cold and warm latency separately. Use the original benchmark endpoints plus a legal byproduct recovery route and a route whose useful intermediates lack native composition.

### A. Typed material/form map with lazy concrete witnesses

Run A in two stages. First compare existing primary-only material tokens with all declared native association constituents, including their component trees and evidence origins. The Robot Arm IV observation provides a concrete token-coverage check. Measure whether the extra native evidence improves the actual Volcanus route ordering or branch coverage at the same limits. If it helps, retain that result before measuring the larger abstraction. If it only produces generic overlap without useful route improvements, report that distinction.

Compare the current factor-graph search with the partial semantic map above. Group alternative native form transitions for guidance and display, while preserving concrete ports and witnesses for actual matching. Carry the target ingredient role so the construction branch can be compared with the separate electronics or cable branch. First restrict the experiment to metadata-covered benchmark routes and publish the classification coverage alongside the result.

Keep the existing primary/component/output-position hints. Add a small path history recording confirmed material continuity evidence, known disjoint transitions, and unknown transitions. A later resource overlapping the source must not erase earlier disjoint or unknown transitions. This is an evidence score, not an atom-provenance claim. Keep byproduct paths legal and report why they received a lower preference.

KEGG transformation modules motivate the map. Heath's source-atom markings and CMPF's path-specific class sets motivate its history. GTNH's weaker metadata means their exact conservation logic cannot be transplanted. Start with inexpensive counts or a tiny evidence state, leaving the hop lower bound unchanged. Test typed guidance and history as bounded preferences rather than hard prerequisites. [Reaction modules](https://www.genome.jp/kegg/reaction/rmodule.html), [atom tracking](https://pmc.ncbi.nlm.nih.gov/articles/PMC2881407/), [CMPF](https://pmc.ncbi.nlm.nih.gov/articles/PMC3521384/)

**Measure:** rank of the steel-to-casing construction spine for Iron Dust to Hull, native facts used in every typed edge, form-only variants expanded, successful/failed witness refinements, known-disjoint and unknown transitions per returned route, examined work, and target branch coverage. **Success:** improve construction-route rank and reduce redundant form exploration without losing necessary dust/ingot/molten steps, the tested byproduct route, or raising work caps. **Failure:** abstract ports do not compose, refinement consumes the savings, metadata gaps downgrade useful assembly, or a source component contributed by an unrelated coinput creates false confidence. Do not solve the latter by inventing atom provenance.

### B. Two competing labels per compatible state

Compare the current scalar ordering with at most two retained labels per compatible state, using nonnegative costs such as steps and cumulative material-evidence penalties. Keep the existing distance guidance, with zero as a safe lower bound for any new penalty whose future value is unknown. Do not add reverse Dijkstra passes for every objective in the first experiment.

EMOA* motivates nondominated labels. The two-label cap and GTNH evidence dimensions are our experimental adaptation. Explicitly record labels removed by dominance and labels dropped by the cap. Include branch identity and any other future-relevant search state in the compatibility key. A visited-set approximation cannot be advertised as exact dominance. [EMOA* paper](https://rap-lab.github.io/documents/publications/2024_AIJ_EMOA.pdf)

**Measure:** represented target branches per 512-state or current equivalent budget, returned useful alternatives, dominance-check time, queue occupancy, and cap-induced drops. **Success:** retain a construction route and a useful byproduct alternative while increasing or preserving Volcanus branch coverage at the same aggregate limits. **Failure:** incomparable histories occupy the queue and reduce coverage, or an incomplete state key prunes a route whose remaining legal continuations differ. Exact Pareto completeness is not a success claim for this capped version.

### C. Branch-first selection with quality-gated structural overlap

Use target-ingredient branches as the first selection dimension. Within a fixed discovered pool, compare reaction-set Jaccard overlap only after the existing material-quality preference. Give additional result slots to uncovered branches before returning another near-duplicate of a covered branch. The current engine already has representative branch spines, so test the change in allocation or within-branch selection against that baseline rather than adding a second branch subsystem.

First run this as pure reranking of saved candidates. Then test a branch scheduler that redistributes the existing total expansion allowance toward branches that still lack a witness. Keep the same global caps. Report separately which gain comes from selection and which comes from discovering a different pool. MetQuest's Jaccard experiment and implementation supply a tested overlap measure, but the quality gate and GTNH branch policy are experimental adaptations. [MetQuest article](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC6028704/fullTextXML), [overlap implementation](https://github.com/RamanLab/metquest/blob/master/metquest/execute_metquest.py)

For form-conversion variants, additionally compare a display-only signature based on available native material/form and operation metadata. Do not merge resource identities or recipe nodes. Preserve exact recipes, quantities, chance, NBT, and conditions. Report exact reaction overlap alongside any normalized overlap so the normalization cannot hide meaningful differences.

**Measure:** target branches covered, unique construction mechanisms, pairwise reaction overlap, redundant form-conversion steps, and search work. **Success:** more useful distinct mechanisms or more represented Volcanus branches without raising limits. **Failure:** low overlap rewards a long recycling detour, a normalization erases a meaningful machine/condition difference, or fair branch allocation wastes the whole budget on unreachable branches. Keep recycling legal and deprioritize redundant explanations through quality, not a cycle ban.

## Evidence and retrieval limits

Parsed papers, source excerpts, GitHub metadata, licenses, KEGG documentation, and `source-manifest.json` are under `exports/search-research-20261014/reaction/`. Git confirms this directory is excluded. The five papers have verified titles, dates, final URLs, and substantive parsed content. The three supplementary KEGG documentation pages have verified titles, update dates, final URLs, and relevant parsed text. EMOA* used `pypdf`, whose availability was checked first. MetQuest used Europe PMC full-text XML after other hosts failed.

Failures were reported when encountered. The Nature MetQuest page returned HTTP 200 with a client challenge. Its PMC page returned a browser check. The linked bioRxiv PDF returned HTTP 403. AFP's recursive tree exceeded a 2 MB read bound and produced truncated JSON, after which smaller root directory listings were used. PubMed returned HTTP 203 with a cookie check for the paper linked by KEGG's reaction-module page. That paper was not read or used as an additional verified paper. None of these responses is treated as successful article or source extraction. Web search used a private background Codex IAB tab with selective DuckDuckGo DOM extraction. `web.run` was not used.

The report supports choosing bounded experiments. It does not establish new chemical semantics, a complete factory planner, or a measured search improvement. The first decision should come from same-budget GTNH results for the construction, branch-coverage, unknown-composition, and legal-byproduct cases.

## Follow-up measurement: flat constituent union is rejected

The main agent ran the cheap association-constituent stage proposed above. It changed material hints for 5,397 resources in an experimental derived sidecar, leaving canonical recipe facts and matching unchanged. For fresh Volcanus, results fell from six paths covering eight of fifteen target branches to one path covering two of fifteen. Both reached 20,000 queued states. Peak pending queue rose from 6,334 to 18,438. The baseline examined 512 states and the treatment 316. Those are observed counts, not a configured 512-state cap. Casing, hull, and double-plate branch coverage did not change. [Measured artifact](exports/search-research-20261014/constituent-probe.json)

This supersedes the suggestion to promote additional constituents directly into a flat material token union. Richer native facts remain useful research evidence, but treating every shared constituent as a low-penalty continuation can enlarge the frontier and reduce useful coverage. Retain source evidence, native form, construction role, amount semantics, and path history as separate dimensions. Test a typed operation map against the existing dump before requiring another game export. [Native metadata research](SEMANTIC_METADATA_RESEARCH.md)
