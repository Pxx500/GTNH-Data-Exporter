# GT++ material owner facts without chemical certification

Research and implementation evidence, 2026-10-14. The canonical snapshot `779ea030-ae9c-40ea-8854-99a176f7cc42` remains immutable. The initial read-only investigation below deepens [SEMANTIC_METADATA_RESEARCH.md](SEMANTIC_METADATA_RESEARCH.md). Subsequent implementation and capture attempts are recorded at the end of this report.

## Decision

The exporter can capture a faithful GT++ material and form declaration for the two missing Hastelloy items through direct native owner fields. Keep that evidence inside the existing `MaterialFacts` owner, separate from its GT ItemData association and accounting tree. Preserve `accounting.status: unresolved` and `chemistry_purity: not_certified`.

A bounded implementation is source-supported and needs no new dependency. A general passive bridge from any GT++ child material to its originating GT5 `Materials` object is **not** available in the inspected runtime interface. The factory copies data and discards the reference. Its public `getGTMaterial()` performs name lookup. That method cannot establish authoritative object identity.

These are native semantic declarations. They do not establish physical purity, molar amounts, or atom provenance. Capturing them also does not prove a search improvement. The existing flow guidance flattens constituent names, so feeding this tree into its current association path would reproduce the mechanism already shown to damage branch coverage.

## Exact runtime and dependency evidence

The initial source investigation uses GT5 `5.09.54.221`, commit `0c2037baa0a0c145f4f2e021729cf5621a1850f5`. Local GT5 HEAD is newer, so it was used only for discovery. The additional seven exact-commit extracts match the cached source JAR byte for byte. The earlier report retains the other 27 inspected files. Later runtime checks on `.223` are recorded separately below.

[exporter/build.gradle](exporter/build.gradle:9) declares `com.github.GTNewHorizons:GT5-Unofficial:5.09.54.221:dev`. `javap -public` against that exact cached dev JAR confirms `BaseItemComponent.componentMaterial`, `componentType`, `ComponentTypes.getGtOrePrefix()`, `Material.getUnlocalizedName()`, `getInternalName()`, `getDefaultLocalName()`, `getComposites()`, `MaterialStack.getStackMaterial()`, `getPartsPerOneHundred()`, and `BlockBaseModular.getMaterialEx()` / `blockType`. All five inspected class checks returned exit 0 with empty stderr. The dev JAR SHA256 is `8919e3e1de0ed99fd9a9bf2977f97d501357def69014c358201b7a5ebf127441`.

The library-search skill was read and existing inventories checked. Previous saved library-search attempts failed with `Gradle produced no usable IntelliJ project`. They do not prove a working inventory. This research obeyed the no-Gradle constraint by using the consuming module's declared dependency, its already cached exact-version dev/source JARs, the indexed attached source project `gt221-attached`, and exact-commit Git extraction. No class was loaded or invoked. Public symbol presence is not a successful exporter compile or runtime linkage test.

Raw evidence is in [exports/search-research-20261014/material-owner/](exports/search-research-20261014/material-owner/). It includes `source-manifest.json`, `dev-jar-public-api.json`, and `declaration-projection.json`. The projection is explicitly source-derived, not a new runtime capture. This directory is Git-excluded and should stay local.

## The two concrete declarations

The saved canonical observations establish registry/meta/NBT identity and the actual OreDictionary labels. Their GT ItemData facts remain `unassociated`.

| Captured resource | Direct native source chain | GT++ internal identity | Native form |
| --- | --- | --- | --- |
| `r10135`, `miscutils:itemGearHastelloyW`, meta 0, null NBT | `ModItems.runMaterialGenerator` generates `MaterialsAlloy.HASTELLOY_W`, which creates `BaseItemGear`, whose parent stores material/type | `gtpp` / `HastelloyW`, default label `Hastelloy-W` | `ComponentTypes.GEAR`, exact `OrePrefixes.gearGt`, captured `ore:gearGtHastelloyW` |
| `r24290`, `miscutils:itemPlateDoubleHastelloyN`, meta 0, null NBT | The same generator generates `MaterialsAlloy.HASTELLOY_N` and `BaseItemPlateDouble` | `gtpp` / `HastelloyN`, default label `Hastelloy-N` | `ComponentTypes.PLATEDOUBLE`, exact `OrePrefixes.plateDouble`, captured `ore:plateDoubleHastelloyN` |

References: [generation calls](https://github.com/GTNewHorizons/GT5-Unofficial/blob/0c2037baa0a0c145f4f2e021729cf5621a1850f5/src/main/java/gtPlusPlus/core/item/ModItems.java#L539), [generator](https://github.com/GTNewHorizons/GT5-Unofficial/blob/0c2037baa0a0c145f4f2e021729cf5621a1850f5/src/main/java/gtPlusPlus/core/material/MaterialGenerator.java#L69), [owner fields and registration](https://github.com/GTNewHorizons/GT5-Unofficial/blob/0c2037baa0a0c145f4f2e021729cf5621a1850f5/src/main/java/gtPlusPlus/core/item/base/BaseItemComponent.java#L42), [form enum](https://github.com/GTNewHorizons/GT5-Unofficial/blob/0c2037baa0a0c145f4f2e021729cf5621a1850f5/src/main/java/gtPlusPlus/core/item/base/BaseItemComponent.java#L277).

The internal name comes from the native constructor's `StringUtils.sanitizeString(materialName)`. It removes the hyphen from these definitions. `getInternalName()` returns `getUnlocalizedName()`. Export that literal native value and the separate default local label. Do not use a translated display label or recreate normalization in Python. Native registry/meta/typed-NBT remains the resource identity.

The namespace plus internal name is a useful semantic key for these declarations, but the native API does not promise global uniqueness across all objects. `mMaterialMap` is an object set, while `mMaterialsByName` overwrites a duplicate string key. A future capture should check distinct object identities sharing a key and report ambiguity. Do not merge them silently. `Material.getId()` is unsuitable as a stable material identifier because it calls component getters and returns a runtime Minecraft item numeric ID.

References: [constructor and name map](https://github.com/GTNewHorizons/GT5-Unofficial/blob/0c2037baa0a0c145f4f2e021729cf5621a1850f5/src/main/java/gtPlusPlus/core/material/Material.java#L334), [identity getters](https://github.com/GTNewHorizons/GT5-Unofficial/blob/0c2037baa0a0c145f4f2e021729cf5621a1850f5/src/main/java/gtPlusPlus/core/material/Material.java#L701), [native sanitizer](https://github.com/GTNewHorizons/GT5-Unofficial/blob/0c2037baa0a0c145f4f2e021729cf5621a1850f5/src/main/java/gregtech/api/util/StringUtils.java#L173).

| Native alloy | Ordered child declarations | Parts exposed by native getter |
| --- | --- | --- |
| `HASTELLOY_W` | `IRON`, `COBALT`, `MOLYBDENUM`, `CHROMIUM`, `NICKEL` | 6, 2, 24, 6, 62 |
| `HASTELLOY_N` | `YTTRIUM`, `MOLYBDENUM`, `CHROMIUM`, `TITANIUM`, `NICKEL` | 8, 16, 8, 8, 60 |

Each entry is a native `gtPlusPlus.core.material.MaterialStack` pointing to another GT++ `Material`. Recursion can follow those actual references through `getComposites()` / `getStackMaterial()` and preserve the tree's order and quantities. The inspected children are factory-created GT++ wrappers with empty component lists. An empty list establishes a terminal GT++ declaration, **not** an authoritative elemental leaf. An exporter must not invent `Element` identity from protons, neutrons, formula text, or the field name `CHROMIUM`.

The child wrapper internal names at this source version are `Iron`, `Cobalt`, `Molybdenum`, `Chrome`, `Nickel`, `Yttrium`, and `Titanium`. In particular, `MaterialsElements.CHROMIUM` is created from GT5 `Materials.Chrome`. Preserve the actual wrapper name `Chrome`, with the native field symbol separately if a bounded symbol mapping is intentionally captured. Do not normalize it from the English word Chromium.

References: [Hastelloy declarations](https://github.com/GTNewHorizons/GT5-Unofficial/blob/0c2037baa0a0c145f4f2e021729cf5621a1850f5/src/main/java/gtPlusPlus/core/material/MaterialsAlloy.java#L296), [element wrapper definitions](https://github.com/GTNewHorizons/GT5-Unofficial/blob/0c2037baa0a0c145f4f2e021729cf5621a1850f5/src/main/java/gtPlusPlus/core/material/MaterialsElements.java#L45), [Yttrium/Molybdenum wrappers](https://github.com/GTNewHorizons/GT5-Unofficial/blob/0c2037baa0a0c145f4f2e021729cf5621a1850f5/src/main/java/gtPlusPlus/core/material/MaterialsElements.java#L103), [GT5 Chrome declaration](https://github.com/GTNewHorizons/GT5-Unofficial/blob/0c2037baa0a0c145f4f2e021729cf5621a1850f5/src/main/java/gregtech/loaders/materials/MaterialsInit.java#L447).

## No generic authoritative GT5 back-reference

`MaterialUtils.generateMaterialFromGtENUM` receives an actual GT5 object, copies its `mName`, default label, color, temperatures, protons/neutrons, blast-furnace flag, and formula display into a new GT++ `Material`, then caches it under a lowercased default label. Neither the GT5 `Materials` object nor its `Element` is stored. The cache is private and maps strings to GT++ objects. The generated wrapper also does not copy GT5 `mMaterialList` into its component list.

The public factory is not a passive reverse query. A missing cache entry constructs a material and causes native registration work. `Material.getGTMaterial()` calls `tryFindGregtechMaterialEquivalent`, which searches the default label and transformed label strings. This is a native convenience heuristic, not a retained identity reference. `werkstoffID` refers to a different material system and does not provide a GT5 identity.

The exact source pairs are stronger evidence than name guessing. A version-pinned exporter could compare a child object with `MaterialsElements.getInstance().IRON` and associate it with `Materials.Iron`, and similarly bind `CHROMIUM` to `Materials.Chrome`. That would be an explicit source-backed bridge authored by the exporter, not a generic runtime back-reference. It must record its source/version and reject unknown or conflicting objects. Such a bridge is optional for semantic capture and should not become a general elemental-accounting claim. The narrow recommendation is to preserve GT++ children in their own namespace first.

References: [factory and private cache](https://github.com/GTNewHorizons/GT5-Unofficial/blob/0c2037baa0a0c145f4f2e021729cf5621a1850f5/src/main/java/gtPlusPlus/core/util/minecraft/MaterialUtils.java#L34), [copied fields and construction](https://github.com/GTNewHorizons/GT5-Unofficial/blob/0c2037baa0a0c145f4f2e021729cf5621a1850f5/src/main/java/gtPlusPlus/core/util/minecraft/MaterialUtils.java#L48), [name-based equivalent lookup](https://github.com/GTNewHorizons/GT5-Unofficial/blob/0c2037baa0a0c145f4f2e021729cf5621a1850f5/src/main/java/gtPlusPlus/core/material/Material.java#L1570).

## Passive access and lifecycle

The item fields, identity getters, enum prefix getter, component-list getter, and child-reference getter can be read without creating components or modifying native caches. `getComposites()` returns the mutable native list directly, so only iterate or copy it. `getStackMaterial()` logs when a reference is null. Preserve null lists/entries and cycles as unresolved declaration evidence. Track active nodes by object identity and use an explicit node/depth budget for a bounded capture. Do not report a truncated or cyclic tree as complete.

Avoid `getComponentByPrefix`, `generatesPrefix`, material `getId`, dust/item/fluid convenience getters, and the factory while exporting passive associations. The existing native `getCompoundMaterialsRecursively` helper is also a poor fit. It flattens leaves, loses edge quantities and ancestry, silently stops after 1,000 processed nodes, and does not report truncation or cycles. Direct bounded tree traversal inside `MaterialFacts` retains the needed declaration semantics.

For generated blocks, resolve the actual block owner from the item and accept only `BlockBaseModular`. `getMaterialEx()` is a direct read and `blockType` retains `STANDARD`, `FRAME`, or `ORE`. These types are distinct native evidence. At this version the block constructor registers both `FRAME` and `ORE` under `frameGt`, so blindly using that ore label as the block's form would lose information. Keep the original block type. A `STANDARD` to `block` or `FRAME` to `frameGt` relationship can be a versioned declaration, while `ORE` remains distinct. This owner does not apply to every GT++ metadata casing block.

GT++ calls `Material.registerAllPending()` during `ModItems.runMaterialGenerator`, which finishes fluid/cell registration and opens the registration gate. The exporter already captures after load completion, server start, and the first GT world tick. A future addition should run in that same ready capture, without initializing native catalogs earlier. The two item owner fields are assigned at construction. The material and block registries remain mutable, so the capture describes that ready runtime state rather than all possible later mutations.

References: [component list getter](https://github.com/GTNewHorizons/GT5-Unofficial/blob/0c2037baa0a0c145f4f2e021729cf5621a1850f5/src/main/java/gtPlusPlus/core/material/Material.java#L1122), [child getter](https://github.com/GTNewHorizons/GT5-Unofficial/blob/0c2037baa0a0c145f4f2e021729cf5621a1850f5/src/main/java/gtPlusPlus/core/material/MaterialStack.java#L62), [flattening helper](https://github.com/GTNewHorizons/GT5-Unofficial/blob/0c2037baa0a0c145f4f2e021729cf5621a1850f5/src/main/java/gtPlusPlus/core/util/minecraft/MaterialUtils.java#L234), [block declarations](https://github.com/GTNewHorizons/GT5-Unofficial/blob/0c2037baa0a0c145f4f2e021729cf5621a1850f5/src/main/java/gtPlusPlus/core/block/base/BlockBaseModular.java#L68), [capture lifecycle](exporter/src/main/java/dev/gtnh/data/NativeCapture.java:109).

## Quantity evidence stays unresolved for accounting

The constructor accepts `double partOutOf100`, rounds it to two decimal places, and stores the integer and fraction privately. `getPartsPerOneHundred()` returns only the integer field if it is 1 through 100, otherwise it returns 100. Therefore it is an exposed native relative-parts value with truncation/default semantics, not a lossless percentage declaration for arbitrary materials. The two source definitions above contain positive integers at most 100 and total 100, so their getters retain those particular declarations. This does not justify labelling all exported values as exact percentages.

Retain each edge value with basis `gtpp_parts_per_one_hundred_api`, source method, and getter limitations. Keep nested edges local to their parent. Do not multiply them into a universal elemental vector. Prefix amounts such as gearGt `4 * GTValues.M` and plateDouble `2 * GTValues.M` are nominal form amounts. They do not provide the missing GT++ quantity profile. `smallestRatio` is native recipe-generation evidence, not an independent molar conversion.

Reference: [full native amount semantics](https://github.com/GTNewHorizons/GT5-Unofficial/blob/0c2037baa0a0c145f4f2e021729cf5621a1850f5/src/main/java/gtPlusPlus/core/material/MaterialStack.java#L17). The earlier report documents the native recipe-generator quantity conventions and prefix amounts.

## Representation choices and current consumers

The existing seam is `MaterialFacts.item(ItemStack)`. `NativeCapture.resource` adds its returned JSON directly to the resource. No caller needs a GT++ material store, factory, registry scan, or new public method.

| Choice | Caller example and consequence | Assessment |
| --- | --- | --- |
| Replace or extend `association.primary.material` with the GT++ tree | Existing `material_tokens(resource)` immediately consumes all nested names. ItemData status/source would need reinterpretation. A consumer could mistake relative parts for GT component coefficients | Reject for this narrow capture. It mixes two owner declarations and silently changes guidance |
| Add native-owner evidence under the same `material_facts` object | `get_resource` retains the evidence in the canonical payload. The existing accounting path still uses its original GT association. A future typed projection can read material identity, form, and declared constituents separately | Recommend. Native knowledge stays with `MaterialFacts` and current accounting semantics stay explicit |
| Add a separate material catalog/store and resource references | Callers must join a new collection, resolve references and understand another lifecycle. Could reduce repeated trees at catalog scale | Defer until measured size/coverage warrants it. It adds a public persistence contract without a present requirement |

The recommended object should carry an independent evidence status, source owner class, semantic identity namespace/internal name, default label, direct form enum/prefix, nominal prefix amount, and a recursive native declaration tree with per-edge relative-parts basis. A terminal declaration should use an explicit declaration status, not the existing accounting-tree `status: complete`. Keep null/missing/cyclic/truncated cases visible. Item owner facts describe the item class, not arbitrary effects of NBT. Do not unify resource identities or OR predicates from matching material/form labels. If direct GT and GT++ owners disagree, retain both declarations and expose the conflict rather than silently preferring either.

A coherent proposal for the existing facts object is below. This is a shape illustration for `r10135`, not captured runtime JSON. The original root `status` and `source_api` still describe GT ItemData. The added `native_owner` describes the independent direct owner. Existing version/profile/unit fields and unresolved quantity fields are omitted here for readability.

```json
{
  "schema_version": 1,
  "source_api": "GTOreDictUnificator.getItemData",
  "status": "unassociated",
  "chemistry_purity": "not_certified",
  "accounting": {
    "status": "unresolved",
    "reason": "No proved GT++ quantity accounting profile"
  },
  "native_owner": {
    "status": "associated",
    "source_api": "BaseItemComponent.componentMaterial + componentType",
    "scope": "native_item_owner",
    "owner_class": "gtPlusPlus.core.item.base.gears.BaseItemGear",
    "form": {
      "native_type": "GEAR",
      "prefix": "gearGt",
      "nominal_material_amount": "14515200",
      "amount_basis": "OrePrefixes.getMaterialAmount"
    },
    "material": {
      "native_class": "gtPlusPlus.core.material.Material",
      "native_system": "gtpp",
      "internal_name": "HastelloyW",
      "default_local_name": "Hastelloy-W",
      "identity_basis": "literal_native_internal_name_not_global_unique_id",
      "traversal_status": "complete",
      "declaration_kind": "composite",
      "components": [
        {"declared_parts": "6", "quantity_basis": "gtpp_parts_per_one_hundred_api", "source_api": "MaterialStack.getPartsPerOneHundred", "material": {"native_class": "gtPlusPlus.core.material.Material", "native_system": "gtpp", "internal_name": "Iron", "default_local_name": "Iron", "traversal_status": "complete", "declaration_kind": "terminal", "components": []}},
        {"declared_parts": "2", "quantity_basis": "gtpp_parts_per_one_hundred_api", "source_api": "MaterialStack.getPartsPerOneHundred", "material": {"native_class": "gtPlusPlus.core.material.Material", "native_system": "gtpp", "internal_name": "Cobalt", "default_local_name": "Cobalt", "traversal_status": "complete", "declaration_kind": "terminal", "components": []}},
        {"declared_parts": "24", "quantity_basis": "gtpp_parts_per_one_hundred_api", "source_api": "MaterialStack.getPartsPerOneHundred", "material": {"native_class": "gtPlusPlus.core.material.Material", "native_system": "gtpp", "internal_name": "Molybdenum", "default_local_name": "Molybdenum", "traversal_status": "complete", "declaration_kind": "terminal", "components": []}},
        {"declared_parts": "6", "quantity_basis": "gtpp_parts_per_one_hundred_api", "source_api": "MaterialStack.getPartsPerOneHundred", "material": {"native_class": "gtPlusPlus.core.material.Material", "native_system": "gtpp", "internal_name": "Chrome", "default_local_name": "Chrome", "traversal_status": "complete", "declaration_kind": "terminal", "components": []}},
        {"declared_parts": "62", "quantity_basis": "gtpp_parts_per_one_hundred_api", "source_api": "MaterialStack.getPartsPerOneHundred", "material": {"native_class": "gtPlusPlus.core.material.Material", "native_system": "gtpp", "internal_name": "Nickel", "default_local_name": "Nickel", "traversal_status": "complete", "declaration_kind": "terminal", "components": []}}
      ]
    }
  }
}
```

Each actual component entry should be `{declared_parts, quantity_basis, source_api, material}`, with `declared_parts` a decimal integer string, `quantity_basis: gtpp_parts_per_one_hundred_api`, and `source_api: MaterialStack.getPartsPerOneHundred`. Its `material` has the same identity/class fields and either recursively populated components or `declaration_kind: terminal`. A GT++ terminal has no invented `element`, density conversion, or GT5 reference. `traversal_status: complete` means only that all exposed declaration edges were visited without missing data, cycle, or budget truncation. It does not mean that the native getter retained the original fractional quantity or that chemical accounting is complete. Null/missing/cyclic/truncated cases set `traversal_status: unresolved` and carry a reason.

This keeps native-specific traversal, form extraction and quantity limitations behind `MaterialFacts.item(ItemStack)`. Any private object-identity memoization belongs to that existing owner. It does not require a separate public catalog or equality table. A future shared `Dataset` projection can read this evidence using class plus native-system/internal-name identity, separately retaining primary material, form and declared constituents. It should not require HTTP, CLI, UI, MCP, or flow callers to interpret GT++ classes or quantity conventions.

Public-contract inspection found these practical impacts:

- [Dataset._validate_record](python/src/gtnh_data/dataset.py:237) validates base resource identity, but does not validate the internal material-facts extension. [Dataset._insert_record](python/src/gtnh_data/dataset.py:459) retains the full JSON payload. [FORMAT.md](FORMAT.md:28) requires preservation of unknown extension fields. A new evidence section can be retained without a new SQL collection, but its contract still needs documentation and meaningful validation if it is implemented
- [flow_index.material_tokens](python/src/gtnh_data/flow_index.py:35) recursively unions all names under `association.primary.material` without reading quantity, source, form, or declaration status. [rebuild](python/src/gtnh_data/flow_index.py:74) stores that set in the existing prepared flow index. Appending the new tree there would immediately change routing guidance. The recommended evidence section leaves this unsupported flat-union behavior untouched until a measured typed projection replaces it
- [acquisition._native_materials](python/src/gtnh_data/acquisition.py:149) accepts only associated, untagged, nonwildcard items whose source is exactly `GTOreDictUnificator.getItemData` and class is exactly `gregtech.api.enums.Materials`. GT++ owner facts should not broaden its same-material ore-processing claim by accident
- [balance.inspect_chemistry](python/src/gtnh_data/balance.py:324) requires a supported version/unit and an eligible accounting profile. [_accounting_vector](python/src/gtnh_data/balance.py:308) rejects unresolved accounting before using the tree. GT++ declarations should remain unsupported there. The existing tree's `coefficient`, density and component-unit fields encode a different GT accounting contract
- [ChemicalFacts](ui/src/ChemicalFacts.tsx:7) renders the chemistry result and full facts JSON. It can expose retained evidence as JSON, but its current display is an accounting display. A dedicated semantic material/form view would be separate product work, not a reason to claim an elemental vector
- HTTP, CLI and MCP use the Python `Dataset` owner as documented in [FORMAT.md](FORMAT.md:5). A semantic interpretation belongs in that shared owner, with the flow preparation derived from it. Do not create a parallel GUI or MCP chemistry/material implementation

`material_tokens` is a **guidance** consumer, not an accounting authority. [find_paths](python/src/gtnh_data/flow_index.py:376) assigns discontinuity penalties from name-set overlap, adds a source-overlap tie preference, orders target ingredient branches, and prunes score/depth-dominated states. It does not use overlap to fabricate a recipe edge or elemental vector. Names can still change which witnesses are found before the global limits. [path_details](python/src/gtnh_data/flow_index.py:571) reports the same overlap as `material_continuity: supported`, with a dependency-spine scope. That label supports the guidance interpretation, not chemical continuity or atom provenance. The present implementation has no class/namespace guard, so a GT++ label matching a GT5 label would become equal as a hint if inserted into its input tree. It is not authoritative cross-owner identity.

The existing `MaterialFacts.material` tree's `status: complete` is stronger than traversal completion. It requires a positive native GT density, an element or declared nonempty component list, resolved nested quantity bases, positive coefficients and complete descendants. Accounting eligibility then adds resource/prefix/NBT/version checks. This establishes the exporter’s bounded **native GT accounting** model, while purity still remains `not_certified`. It does not certify physical chemistry. Reusing this same status for a fully visited GT++ declaration would blur those distinct contracts, hence the separate `traversal_status` and unresolved root accounting.

## Implementation readiness and remaining evidence

**Safe to implement a bounded passive capture:** direct GT++ item/block owner evidence, literal native names/form, recursive declared constituents, exposed relative parts, independent unresolved accounting, and explicit null/cycle/truncation/conflict handling inside `MaterialFacts`. Keep the existing `item`/`fluid` seam and full resource identity. The cited exact-version dependency interface supports this work.

**Not established:** successful compilation/linkage of that future implementation, actual runtime owner coverage, a whole-pack key-collision census, absence of later native mutations, full NBT semantics, a general GT++ to GT5 reference bridge, a certified GT++ quantity profile, or a search benefit. An implementation must be checked by compile/linkage and a bounded fresh capture before claiming runtime success. The new snapshot must be separate from the immutable canonical snapshot.

For the next capture, verify these two items' actual runtime class/material/type, native child keys/parts and unchanged accounting rejection. Count direct owners, null owners, duplicate internal names, terminal declarations, missing/cyclic/truncated trees and disagreements with existing GT/OreDictionary evidence. Leave unknown identities searchable. Search experiments should use typed primary-material/form facts and concrete recipe witnesses under the shared budget, not the flat constituent union.

## Initial research verification and scope

Source discovery used the graph. Exact-commit Git bytes and cached source-JAR comparison verified new native files. `javap` verified the public dependency symbols without loading the classes. One Context Mode extraction failed because `StringUtils` was initially addressed under the wrong package. That failure was reported immediately, and graph discovery resolved `gregtech.api.util.StringUtils` before retry. The resulting seven source extracts all match the exact cached source JAR.

Only this report and `material-owner/` evidence were authored during the initial investigation. Reindexing refreshed the Git-excluded local `.codebase-memory/graph.db.zst`. No tests, Gradle tasks, game APIs, imports, sidecar rebuilds, canonical writes or production patches were performed in that stage. Those source findings establish feasible declarations and contract risks, not runtime execution.

## Implementation and runtime verification

The existing `MaterialFacts.item` owner now attaches independent direct GT++
item/block declarations. Its original GT ItemData path, fluid facts, accounting
eligibility and purity remain intact. The implementation adds 113 lines, uses
the actual component/block owner, and traverses literal child references with
a 32-level and 1,024-entry bound. It reports missing, cyclic and omitted
declarations. Internal names are literal evidence, not globally unique IDs.
No cross-owner equality table or material-token routing change is introduced.
The format contract is documented in [FORMAT.md](FORMAT.md).

Compilation passed, and the existing 30 Java tests pass. IntelliJ completed
the capture-package scan. New redundant assignment and generic-type findings
were fixed. Remaining style, complexity, coupling and existing findings are
retained with reasons. The combined runner skips PMD because its wrapper
discovery normalizes this nested project to the outer Git root. An explicit
PMD 7.26.0 scan of `MaterialFacts` completed with 20 advisory findings and no
processing/configuration errors. This supplemental scan is distinct from the
skipped combined-runner phase.

A native-constructor fixture did not reach the owner assertion. Default test
runtime lacked fastutil. Reusing its cached JAR in a temporary invocation then
reached a missing JOML texture dependency. The setup-failing fixture and logs
remain Git-excluded, with no persistent dependency or default-suite change.
They do not provide positive owner-output verification.

The first real pack attempt rebuilt successfully but failed after 97.065
seconds before capture or manifest publication. `runFullPack` refreshed GT5
to `5.09.54.223` and CoreMod to `2.9.89`. The existing native login readiness
gate required `2.9.88`. Game exit was 2 and automation exit was 1. Canonical
index SHA256 stayed identical. No new snapshot was published or imported,
and no GUI/MCP dataset was switched.

Exact old/new CoreMod message, handler, registration and synchronous update
contracts were checked. The readiness profile now supports exactly `2.9.89`,
preserving observation after the original handler returns. Compilation and all
30 Java tests pass. The readiness file's IntelliJ and supplemental PMD scans
found no new blocking issue. The combined runner's PMD skip remains distinct
from that explicit scan.

The subsequent real capture and isolated import succeeded in 170.655 seconds.
Snapshot `fa5e7522-6726-45c5-8749-121f9cfe4bb4` uses GT/miscutils
`5.09.54.223` and CoreMod `2.9.89`. Native dump publication took about 13 seconds
by second-resolution log timestamps. The six compressed streams occupy
14,413,613 bytes. The imported SQLite index occupies 1,109,975,040 bytes.

Both required Hastelloy records capture the actual material, form and child
parts listed above. Their direct GT ItemData association remains unassociated,
accounting remains unresolved, and actual `inspect_chemistry` calls reject
them. Root independently read both records from the compressed native stream,
checked the literal identity basis and quantities, and confirmed the owner
status counts. No collision-checked or globally unique material key is claimed
by the implemented literal identity fields in the initial example above.

The capture contains 1,709 owner records across 20 owner classes. Of these,
1,646 have associated owners and complete declaration traversal. The other 63
are CELL declarations with missing direct native material fields. No failed
owner capture, cycle or traversal truncation was observed. The 1,574 generated
components cover 24 native forms. The 135 blocks comprise 77 STANDARD and 58
FRAME forms. Their actual block owner supplies no invented OrePrefix. The
trees contain 8,141 component-edge occurrences, not unique materials.

This refreshed pack changes 51 mod records and 623 configuration/script
digests. Resource count increases by two and process count by four. The GT
accounting profile then supported only `5.09.54.221`, so all 118,719 resources
in the new snapshot have unresolved accounting. Whole-pack equality and
chemical support for the refreshed version are not established. The isolated
capture is not promoted to the active GUI or MCP dataset.

The canonical index retains SHA256
`9aaaf36d8ac77ad960383cf528a349897d000a0f73f310f0b980076ead511a87`.
Root independently verified this hash after capture. Runtime evidence,
native records, public inspection replies, audit and failed-run evidence are
under the Git-excluded `exports/search-research-20261014/material-owner/`
directory. Captured owner evidence is verified. Chemical accounting, a
cross-owner reference bridge and improved search remain separate work.

## Subsequent verified GT version support

An explicit version extension now admits GT `.223` under the unchanged `.221`
quantity profile. Fifteen relevant native source files and 22 actual runtime
class files are byte-identical between these inspected releases. Root checked
four critical class files directly from both JARs. The other accounting gates
and purity limits remain unchanged.

A fresh isolated capture `0d74a12d-9969-4055-b479-8e5573946098` retains the GT++
owner evidence and supplies the new runtime eligibility observations. All
4,695 complete canonical accounting identities match by kind, registry,
metadata and typed NBT, with identical vectors and quantity bases. No previous
persisted facts are mutated or retroactively promoted. Both Hastelloy items
still reject chemistry inspection. Root directly verified these rejections
and the Iron Dust, Water and Hydrogen vectors in the new snapshot.

All 170 integrated Python tests and 30 Java tests pass. The fresh pipeline
takes 168.587 seconds, with about 15 seconds of native dump publication.
Protected indexes retain their hashes. The active GUI and MCP dataset stay
on the canonical `.221` snapshot. Detailed source comparisons, actual native
samples, all vector comparisons and audit evidence are in
`exports/search-research-20261014/accounting-223/`.

## Passive GT++ fluid ownership

The existing `MaterialFacts.fluid` owner now also captures native GT++ fluid
bindings. The public `Material.mMaterialMap` catalog and direct `getFluid` and
`getPlasma` field returns permit passive object-reference comparison. Native
name equality is not used for candidate deduplication. The implementation
adds 45 lines and keeps the original GT fluid association/accounting body.
It records every distinct matching object, actual field bindings and the
existing bounded declaration tree. Failed scans retain partial candidates
without claiming uniqueness. This does not establish global material equality
or quantities for the GT++ namespace.

The isolated runtime refreshes to GT `.225`, CoreMod `2.9.89` and GTNHLib
`0.11.54`. Snapshot `4966d66c-68f3-4689-adf5-ab55c1a8e4b2` contains 268
associated fluid owners and 1,152 unassociated fluids. No ambiguous or failed
scan is observed. All 268 owners use the native Material class, with 231
`mFluid` and 37 `mPlasma` bindings. All 865 emitted declaration nodes have
complete traversal. Ambiguity and failure handling are reviewed code paths,
not positive runtime cases from this pack.

Molten Hastelloy-W `r33027` and gear `r10135` have equal declaration trees.
Molten Hastelloy-N `r33043` and double plate `r24290` likewise agree. Both
fluids are actual FluidGT6 objects with one `mFluid` owner. Native alloy and
casting witnesses preserve all cofeeds and the required mold. Tree agreement
does not prove shared persisted object identity or chemical accounting.

The four relevant owner class files remain byte-identical across `.221`,
`.223` and the actual `.225` JAR. Compilation and all 30 Java tests pass.
IntelliJ completes and supplemental PMD reports 22 metric advisories with no
analyzer error, independently of the combined runner's wrapper-discovery skip.
The default tests cover the existing GT phase/accounting seam. Runtime
capture supplies the positive GT++ object-link evidence.

GT `.225` remains outside the explicit chemical accounting versions. Both
Hastelloy pairs remain unsupported, and complete-vector equivalence is not
claimed. Native declarations and GT associations match 118,718 prior resource
identities after excluding runtime versions and every accounting object.
One Printer Manual NBT text correction changes its identity. This is scoped
declaration comparison, not whole-pack equality.

The fresh pipeline takes 174.823 seconds, including about 14 seconds of native
dump publication. Compressed streams total 14,455,749 bytes. The canonical
`.221` and preceding `.223` indexes retain their hashes. No active dataset is
switched. Exact source/API evidence, class bytes, native records, recipe
witnesses and limitations are in
`exports/search-research-20261014/gtpp-fluid-owner/`.
