package dev.gtnh.data;

import static dev.gtnh.data.Jsons.object;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.google.gson.JsonPrimitive;
import galacticgreg.api.ModDimensionDef;
import galacticgreg.registry.GalacticGregRegistry;
import gregtech.GTMod;
import gregtech.api.enums.Materials;
import gregtech.api.interfaces.IOreMaterial;
import gregtech.api.interfaces.IStoneType;
import gregtech.api.objects.GTUODimension;
import gregtech.api.objects.GTUOFluid;
import gregtech.common.WorldgenGTOreLayer;
import gregtech.common.WorldgenGTOreSmallPieces;
import gregtech.common.blocks.GTBlockOre;
import gregtech.common.ores.GTOreAdapter;
import gregtech.common.ores.OreInfo;
import gregtech.common.ores.OreManager;
import gregtech.common.ores.SmallOreDrops;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Collection;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Random;
import net.minecraft.block.Block;
import net.minecraft.item.ItemStack;
import net.minecraftforge.common.DimensionManager;
import net.minecraftforge.fluids.FluidStack;

/** Configured generation and conditional base acquisition. Never samples chunk deposits. */
final class WorldgenCapture {
    private static final Random NO_RANDOM_DRAWS = new Random(0L) {
        private static final long serialVersionUID = 1L;
        @Override
        protected int next(int bits) {
            throw new IllegalStateException("Normal ore Fortune 0 baseline requested a random draw");
        }
    };
    private final NativeCapture capture;
    private final SnapshotWriter writer;
    private final Map<String, ModDimensionDef> definitions = new HashMap<>();
    private final java.util.Set<String> environments = new java.util.HashSet<>();
    private long miningSourceCount;
    private long unsupportedMiningVariants;
    private long failedMiningBranches;
    private final JsonArray miningFailures = new JsonArray();
    private long smallMiningSourceCount;
    private long unsupportedSmallMiningVariants;
    private long failedSmallMiningVariants;
    private final JsonArray smallMiningFailures = new JsonArray();

    WorldgenCapture(NativeCapture capture, SnapshotWriter writer) { this.capture = capture; this.writer = writer; }

    static JsonObject smallOreYield(List<String> primaryResources, int nativeMultiplier,
        String pureDustResource, String impureDustResource) {
        if (primaryResources == null) throw new IllegalArgumentException("Native primary pool is null");
        Map<String, Integer> weights = new LinkedHashMap<>();
        for (String resource : primaryResources) {
            requireResource(resource);
            weights.merge(resource, 1, Integer::sum);
        }
        requireResource(pureDustResource);
        requireResource(impureDustResource);
        JsonArray candidates = new JsonArray();
        for (Map.Entry<String, Integer> entry : weights.entrySet())
            candidates.add(object("resource_id", entry.getKey(), "weight", entry.getValue()));
        JsonObject pureCase = object("case", "pure", "probability", object("numerator", 1, "denominator", 9));
        JsonObject impureCase = object("case", "impure", "probability", object("numerator", 2, "denominator", 9));
        JsonArray host = new JsonArray();
        host.add(object("native_cases", Jsons.array(object("case", "none", "probability", object("numerator", 2, "denominator", 3))),
            "probability", object("numerator", 2, "denominator", 3), "outputs", new JsonArray()));
        if (pureDustResource.equals(impureDustResource)) {
            host.add(object("native_cases", Jsons.array(pureCase, impureCase),
                "probability", object("numerator", 1, "denominator", 3),
                "outputs", Jsons.array(object("resource_id", pureDustResource, "amount", 1))));
        } else {
            host.add(object("native_cases", Jsons.array(pureCase), "probability", pureCase.get("probability"),
                "outputs", Jsons.array(object("resource_id", pureDustResource, "amount", 1))));
            host.add(object("native_cases", Jsons.array(impureCase), "probability", impureCase.get("probability"),
                "outputs", Jsons.array(object("resource_id", impureDustResource, "amount", 1))));
        }
        JsonObject rule = object("kind", "gt_small_ore_fortune0", "version", 1,
            "scope", "per_qualifying_native_base_harvest",
            "primary", object("kind", "weighted_draws_with_replacement", "draw_count", Math.max(1, nativeMultiplier),
                "total_weight", primaryResources.size(), "amount_per_draw", 1, "candidates", candidates,
                "empty_pool_behavior", "emit_nothing"),
            "host", object("kind", "exclusive_choice", "outcomes", host),
            "evaluation_order", new String[]{"primary", "host"});
        LinkedHashSet<String> support = new LinkedHashSet<>(weights.keySet());
        support.add(pureDustResource);
        support.add(impureDustResource);
        JsonArray outputs = new JsonArray();
        for (String resource : support)
            outputs.add(object("resource_id", resource, "resource_semantics", "mined_item_rule_candidate"));
        return object("output_rule", rule, "outputs", outputs);
    }

    private static void requireResource(String resource) {
        if (resource == null || resource.trim().isEmpty())
            throw new IllegalArgumentException("Native drop has no registered resource identity");
    }

    void capture() throws IOException {
        for (Integer dimension : DimensionManager.getStaticDimensionIDs()) {
            String id = "dimension:" + dimension;
            environments.add(id);
            writer.append("environments", object("id", id, "name", "Registered dimension " + dimension,
                "dimension_id", dimension, "provider", null,
                "properties", object("registered", true, "provider_type", DimensionManager.getProviderType(dimension),
                    "native_name_mapping", "unresolved"),
                "provenance", object("owner", "Forge DimensionManager.getStaticDimensionIDs")));
        }
        Collection<galacticgreg.api.ModContainer> containers = GalacticGregRegistry.getModContainers();
        if (containers == null) throw new IllegalStateException("GalacticGreg registry not initialized after first world tick");
        for (galacticgreg.api.ModContainer container : containers) {
            if (!container.isModLoaded()) continue;
            for (ModDimensionDef definition : container.getDimensionList()) {
                String name = definition.getDimensionName();
                if (definitions.put(name, definition) != null) continue;
                environments.add("gt:" + name);
                writer.append("environments", object("id", "gt:" + name, "name", name, "dimension_id", null,
                    "provider", definition.getChunkProviderName(), "properties",
                    object("native_identifier", definition.getDimIdentifier(), "dimension_type", definition.getDimensionType().toString(),
                        "generates_ore", definition.generatesOre(), "ore_vein_chance", definition.getOreVeinChance(),
                        "respects_ore_heights", definition.respectsOreVeinHeights(), "numeric_mapping", "unresolved"),
                    "provenance", object("owner", "GalacticGregRegistry loaded-mod dimension definitions")));
            }
        }
        long veins = 0;
        for (WorldgenGTOreLayer vein : WorldgenGTOreLayer.sList) {
            JsonArray outputs = new JsonArray();
            Map<String, ItemStack> generatedBlocks = new LinkedHashMap<>();
            addOre(outputs, generatedBlocks, vein.mPrimary, "primary", vein);
            addOre(outputs, generatedBlocks, vein.mSecondary, "secondary", vein);
            addOre(outputs, generatedBlocks, vein.mBetween, "between", vein);
            addOre(outputs, generatedBlocks, vein.mSporadic, "sporadic", vein);
            JsonArray contexts = new JsonArray();
            JsonObject heights = new JsonObject();
            JsonObject gates = new JsonObject();
            for (String name : vein.getAllowedDimensions()) {
                contexts.add(new JsonPrimitive(environment(name)));
                heights.add(name, object("min_y", vein.getMinY(name), "max_y", vein.getMaxY(name)));
                gates.add(name, dimensionGate(name));
            }
            String sourceId = "vein:" + vein.getName();
            JsonObject generationConditions = object("dimension_gates", gates, "biome", vein.mRestrictBiome,
                "stone_specific", vein.isStoneSpecific(), "region", "native_location_and_terrain_conditions");
            writer.append("sources", object("id", sourceId, "kind", "ore_vein", "display_name", vein.getName(),
                "outputs", outputs, "environment_ids", contexts, "status", "conditional",
                "conditions", generationConditions,
                "parameters", object("weight", vein.mWeight, "density", vein.mDensity, "size", vein.mSize, "heights", heights,
                    "weight_semantics", "relative_selection_weight_not_occurrence_probability"),
                "provenance", object("owner", "WorldgenGTOreLayer.sList", "generator", vein.getName())));
            emitMiningSources(sourceId, vein.getName(), generatedBlocks, contexts, generationConditions);
            veins++;
        }
        long small = 0;
        for (WorldgenGTOreSmallPieces ore : WorldgenGTOreSmallPieces.sList) {
            JsonArray outputs = new JsonArray();
              Map<String, ItemStack> generatedBlocks = new LinkedHashMap<>();
              addSmallOre(outputs, generatedBlocks, ore.getMaterial(), ore);
            JsonArray contexts = new JsonArray();
            JsonObject gates = new JsonObject();
            for (String name : ore.getAllowedDimensions()) {
                contexts.add(new JsonPrimitive(environment(name))); gates.add(name, dimensionGate(name));
            }
              String sourceId = "small:" + ore.getName();
              JsonObject generationConditions = object("dimension_gates", gates, "biome", ore.mBiome, "stone_specific", ore.isStoneSpecific());
              writer.append("sources", object("id", sourceId, "kind", "small_ore", "display_name", ore.getName(),
                "outputs", outputs, "environment_ids", contexts, "status", "conditional",
                  "conditions", generationConditions,
                "parameters", object("min_y", ore.mMinY, "max_y", ore.mMaxY, "amount_parameter", ore.mAmount,
                    "amount_semantics", "native_generation_parameter_not_guaranteed_yield"),
                "provenance", object("owner", "WorldgenGTOreSmallPieces.sList", "generator", ore.getName())));
              emitSmallMiningSources(sourceId, ore.getName(), generatedBlocks, contexts, generationConditions);
            small++;
        }
        int[] blacklist = GTMod.proxy.mUndergroundOil.blackList;
        JsonObject blacklistFacts = object("status", blacklist == null ? "unresolved" : "captured",
            "source_api", "gregtech.GTMod.proxy.mUndergroundOil.blackList", "dimension_ids", blacklist,
            "scope", "native_numeric_filter_not_resolved_availability");
        if (blacklist == null) blacklistFacts.addProperty("reason", "native_array_is_null");
        long fluids = 0;
        for (Map.Entry<String, GTUODimension> entry : GTMod.proxy.mUndergroundOil.getDimensionList().entrySet()) {
            GTUODimension dimension = entry.getValue();
            String context = "underground-rule:" + entry.getKey();
            environments.add(context);
            writer.append("environments", object("id", context, "name", dimension.Dimension,
                "dimension_id", null, "provider", null, "properties", object("rule", dimension.Dimension, "mapping", "unresolved",
                    "dimension_blacklist", blacklistFacts),
                "provenance", object("owner", "GTMod.proxy.mUndergroundOil", "config_key", entry.getKey())));
            for (Map.Entry<String, GTUOFluid> fluid : dimension.getFluids().entrySet()) {
                GTUOFluid rule = fluid.getValue();
                JsonArray outputs = new JsonArray();
                if (rule.getFluid() != null) outputs.add(object("resource_id", capture.fluid(new FluidStack(rule.getFluid(), 1)), "chance", null));
                writer.append("sources", object("id", "underground:" + entry.getKey() + ":" + fluid.getKey(),
                    "kind", "underground_fluid", "display_name", rule.Registry, "outputs", outputs,
                    "environment_ids", Jsons.array(new JsonPrimitive(context)), "status", rule.Chance > 0 ? "conditional" : "disabled",
                    "conditions", object("dimension_rule", dimension.Dimension, "blacklist_and_provider_resolution", "native_unresolved"),
                    "parameters", object("weight", rule.Chance, "min_amount", rule.MinAmount, "max_amount", rule.MaxAmount,
                        "decrease_per_operation_amount", rule.DecreasePerOperationAmount, "weight_semantics", "relative_configured_weight"),
                    "provenance", object("owner", "GTMod.proxy.mUndergroundOil", "config_key", entry.getKey(), "fluid_key", fluid.getKey())));
                fluids++;
            }
        }
        capture.coverage("forge.registered_dimensions", "complete", DimensionManager.getStaticDimensionIDs().length,
            "All registered numeric IDs, including unloaded worlds. Cross-mapping to GT names remains unresolved");
        capture.coverage("gt.worldgen.veins", "partial", veins,
            "Active runtime list captured. Generated blocks are world definitions. Location gates are not interpreted");
        capture.coverage("gt.worldgen.small_ores", "partial", small,
              "Active runtime list and stone resource variants captured. Native mining rules are separate conditional acquisition");
        capture.coverage("gt.worldgen.underground_fluids", "partial", fluids,
            "Native config rules and raw dimension blacklist context retained. Numeric/provider matching, blacklist applicability, seeded fields and depletion observations unresolved");
        capture.coverage("acquisition.gt_ore_mining_normal", "partial", miningSourceCount,
            "Conditional GT normal ore Fortune 0 plain/silk native base drops. Tool/event modifiers, positive Fortune and observed deposits are not modeled",
            object("native_drop_mode", GTMod.proxy.oreDropSystem.name(), "random_evaluation", "random_draws_rejected",
                "unsupported_generator_variants", unsupportedMiningVariants, "failed_branches", failedMiningBranches,
                "failure_examples", miningFailures, "records_semantics", "related_source_branches_not_deposit_count"));
          capture.coverage("acquisition.gt_ore_mining_small", "partial", smallMiningSourceCount,
              "Conditional GT small ore Fortune 0 joint weighted-draw and exclusive host-dust rules. No RNG sampled. Tool/event modifiers, positive Fortune and observed deposits are not modeled",
              object("rule_kind", "gt_small_ore_fortune0", "random_evaluation", "not_evaluated",
                  "unsupported_generator_variants", unsupportedSmallMiningVariants, "failed_variants", failedSmallMiningVariants,
                  "failure_examples", smallMiningFailures, "records_semantics", "related_source_rules_not_deposit_count"));
    }

    private String environment(String name) throws IOException {
        String id = "gt:" + name;
        if (environments.add(id)) writer.append("environments", object("id", id, "name", name,
            "dimension_id", null, "provider", null, "properties", object("mapping", "unresolved"),
            "provenance", object("owner", "native_worldgen_allow_set")));
        return id;
    }

    private JsonObject dimensionGate(String name) {
        ModDimensionDef definition = definitions.get(name);
        return definition == null ? object("status", "unresolved")
            : object("generates_ore", definition.generatesOre(), "ore_vein_chance", definition.getOreVeinChance(),
                "respects_ore_heights", definition.respectsOreVeinHeights());
    }

    private void addOre(JsonArray outputs, Map<String, ItemStack> generatedBlocks, IOreMaterial material,
        String role, WorldgenGTOreLayer layer) throws IOException {
        for (IStoneType stone : material.getValidStones()) {
            if (layer.isStoneSpecific() && !layer.canGenerateIn(stone.getCategory())) continue;
            ItemStack block = oreResource(outputs, material, stone, false, role);
            if (block != null) generatedBlocks.putIfAbsent(capture.item(block), block);
        }
    }

    private void addSmallOre(JsonArray outputs, Map<String, ItemStack> generatedBlocks, IOreMaterial material,
        WorldgenGTOreSmallPieces layer) throws IOException {
        for (IStoneType stone : material.getValidStones()) {
            if (layer.isStoneSpecific() && !layer.canGenerateIn(stone.getCategory())) continue;
            ItemStack block = oreResource(outputs, material, stone, true, "small");
            if (block != null) generatedBlocks.putIfAbsent(capture.item(block), block);
        }
    }

    private ItemStack oreResource(JsonArray outputs, IOreMaterial material, IStoneType stone, boolean small, String role) throws IOException {
        try (OreInfo<IOreMaterial> info = OreInfo.getNewInfo()) {
            info.material = material; info.stoneType = stone; info.isSmall = small; info.isNatural = true;
            ItemStack block = OreManager.getStack(info, 1);
            if (block != null) outputs.add(object("resource_id", capture.item(block), "chance", null,
                "material", material.getInternalName(), "material_role", role, "stone", stone.toString(),
                "resource_semantics", "generated_ore_block_not_mining_drop"));
            return block;
        }
    }

    private void emitSmallMiningSources(String generatedSourceId, String label, Map<String, ItemStack> generatedBlocks,
        JsonArray environments, JsonObject generationConditions) throws IOException {
        for (Map.Entry<String, ItemStack> entry : generatedBlocks.entrySet()) {
            String id = "mining:" + generatedSourceId + ":" + entry.getKey() + ":fortune0";
            JsonObject mining = object("scope", "native_base_drop", "effective_fortune", 0,
                "silk_touch_policy", "ignored_for_small_ore", "ore_drop_system_policy", "ignored_for_small_ore",
                "ore_drop_system", GTMod.proxy.oreDropSystem.name(),
                "actor_assumption", "successful_ordinary_harvest_with_suitable_tool", "tool_and_event_modifiers", "not_modeled");
            JsonObject parameters = object("generated_source_id", generatedSourceId, "generated_resource_id", entry.getKey(),
                "yield_semantics", "per_encountered_block_before_harvest_modifiers");
            JsonObject provenance = object("owner", "GTOreAdapter.getSmallOreDrops", "adapter_class", GTOreAdapter.class.getName(),
                "definition_api", "SmallOreDrops.getDropList, IStoneType.getDust", "generated_metadata", entry.getValue().getItemDamage());
            JsonArray nativeStacks = new JsonArray();
            provenance.add("native_stacks", nativeStacks);
            JsonArray outputs = new JsonArray();
            String status = "conditional";
            String phase = "decode_generated_block";
            try {
                Block block = Block.getBlockFromItem(entry.getValue().getItem());
                if (!(block instanceof GTBlockOre)) {
                    unsupportedSmallMiningVariants++;
                    continue;
                }
                try (OreInfo<Materials> info = GTOreAdapter.INSTANCE.getOreInfo(block, entry.getValue().getItemDamage())) {
                    phase = "native_support";
                    if (info == null || !info.isSmall || !GTOreAdapter.INSTANCE.supports(info)) {
                        unsupportedSmallMiningVariants++;
                        continue;
                    }
                    GTBlockOre ore = (GTBlockOre) block;
                    int metadata = entry.getValue().getItemDamage();
                    mining.addProperty("material", info.material.getInternalName());
                    mining.addProperty("stone", info.stoneType.toString());
                    mining.addProperty("natural", info.isNatural);
                    mining.addProperty("small", info.isSmall);
                    phase = "harvest_requirements";
                    mining.addProperty("harvest_tool", ore.getHarvestTool(metadata));
                    mining.addProperty("minimum_harvest_level", ore.getHarvestLevel(metadata));
                    mining.addProperty("harvest_requirements_scope", "native_block_declared_requirements");
                    provenance.addProperty("block_class", block.getClass().getName());
                    provenance.addProperty("native_ore_multiplier", info.material.mOreMultiplier);
                    phase = "native_primary_pool";
                    List<ItemStack> nativePool = SmallOreDrops.getDropList(info.material);
                    if (nativePool == null) throw new IllegalArgumentException("Native primary pool is null");
                    List<String> primary = new ArrayList<>();
                    for (ItemStack stack : nativePool) {
                        phase = "primary_identity_" + primary.size();
                        primary.add(smallOreResource(stack, "primary", nativeStacks));
                    }
                    provenance.add("resolved_primary_sequence", SnapshotWriter.JSON.toJsonTree(primary));
                    phase = "native_host_pure";
                    String pure = smallOreResource(info.stoneType.getDust(true, 1), "pure", nativeStacks);
                    phase = "native_host_impure";
                    String impure = smallOreResource(info.stoneType.getDust(false, 1), "impure", nativeStacks);
                    phase = "joint_rule";
                    JsonObject yield = smallOreYield(primary, info.material.mOreMultiplier, pure, impure);
                    outputs = yield.getAsJsonArray("outputs");
                    parameters.add("output_rule", yield.get("output_rule"));
                }
            } catch (RuntimeException | LinkageError failure) {
                outputs = new JsonArray();
                parameters.remove("output_rule");
                status = "unknown";
                JsonObject evidence = object("phase", phase, "class", failure.getClass().getName(), "message", failure.getMessage());
                parameters.add("failure", evidence);
                failedSmallMiningVariants++;
                if (smallMiningFailures.size() < 20) smallMiningFailures.add(object("source_id", id, "failure", evidence));
            }
            writer.append("sources", object("id", id, "kind", "ore_mining", "display_name", label + " baseline small-ore mining",
                "outputs", outputs, "environment_ids", environments, "status", status,
                "conditions", object("generation", generationConditions, "mining", mining),
                "parameters", parameters, "provenance", provenance));
            smallMiningSourceCount++;
        }
    }

    private String smallOreResource(ItemStack original, String nativeCase, JsonArray evidence) throws IOException {
        if (original == null || original.getItem() == null) {
            evidence.add(object("native_case", nativeCase, "stack", null));
            throw new IllegalArgumentException("Native " + nativeCase + " drop has no item");
        }
        ItemStack stack = original.copy();
        evidence.add(object("native_case", nativeCase, "item_class", stack.getItem().getClass().getName(),
            "metadata", stack.getItemDamage(), "amount", stack.stackSize, "nbt", TypedNbt.encode(stack.getTagCompound())));
        if (stack.stackSize != 1) throw new IllegalArgumentException("Native " + nativeCase + " drop is not quantity one");
        String resource = capture.item(stack);
        requireResource(resource);
        return resource;
    }

    private void emitMiningSources(String generatedSourceId, String label, Map<String, ItemStack> generatedBlocks,
        JsonArray environments, JsonObject generationConditions) throws IOException {
        for (Map.Entry<String, ItemStack> entry : generatedBlocks.entrySet()) {
            Block block = Block.getBlockFromItem(entry.getValue().getItem());
            try (OreInfo<IOreMaterial> info = OreManager.getOreInfo(entry.getValue())) {
                if (info == null || info.isSmall || !(info.material instanceof Materials)
                    || !(OreManager.getAdapter(info) instanceof GTOreAdapter) || !(block instanceof GTBlockOre)) {
                    unsupportedMiningVariants++;
                    continue;
                }
                GTBlockOre ore = (GTBlockOre) block;
                int metadata = entry.getValue().getItemDamage();
                for (boolean silk : new boolean[]{false, true}) {
                    String id = "mining:" + generatedSourceId + ":" + entry.getKey() + ":fortune0:" + (silk ? "silk" : "plain");
                    JsonObject mining = object("scope", "native_base_drop", "effective_fortune", 0, "silk_touch", silk,
                        "ore_drop_system", GTMod.proxy.oreDropSystem.name(),
                        "effective_drop_mode", silk ? "Block" : GTMod.proxy.oreDropSystem.name(),
                        "material", info.material.getInternalName(),
                        "stone", info.stoneType.toString(), "natural", info.isNatural,
                        "harvest_tool", ore.getHarvestTool(metadata), "minimum_harvest_level", ore.getHarvestLevel(metadata),
                        "harvest_requirements_scope", "native_block_declared_requirements",
                        "actor_assumption", "successful_ordinary_harvest_with_suitable_tool",
                        "tool_and_event_modifiers", "not_modeled");
                    JsonArray drops = new JsonArray();
                    String status = "conditional";
                    String failure = null;
                    try {
                        List<ItemStack> nativeDrops = GTOreAdapter.INSTANCE.getOreDrops(NO_RANDOM_DRAWS, info, silk, 0);
                        if (nativeDrops.isEmpty()) throw new IllegalStateException("Native baseline returned no drops");
                        for (ItemStack drop : nativeDrops) {
                            if (drop == null || drop.getItem() == null || drop.stackSize <= 0)
                                throw new IllegalStateException("Native baseline returned an invalid drop");
                            drops.add(object("resource_id", capture.item(drop), "amount", drop.stackSize,
                                "chance", object("numerator", 1, "denominator", 1),
                                "chance_semantics", "deterministic_given_baseline_harvest_not_deposit_occurrence",
                                "resource_semantics", "mined_item_baseline"));
                        }
                    } catch (RuntimeException exception) {
                        drops = new JsonArray();
                        status = "unknown";
                        failure = exception.getClass().getName() + ": " + exception.getMessage();
                        failedMiningBranches++;
                        if (miningFailures.size() < 20) miningFailures.add(object("source_id", id, "failure", failure));
                    }
                    writer.append("sources", object("id", id, "kind", "ore_mining", "display_name",
                        label + (silk ? " baseline silk-touch mining" : " baseline mining"), "outputs", drops,
                        "environment_ids", environments, "status", status,
                        "conditions", object("generation", generationConditions, "mining", mining),
                        "parameters", object("generated_source_id", generatedSourceId, "generated_resource_id", entry.getKey(),
                            "yield_semantics", "per_encountered_block_before_harvest_modifiers", "failure", failure),
                        "provenance", object("owner", "GTOreAdapter.getOreDrops", "adapter_class", GTOreAdapter.class.getName(),
                            "block_class", block.getClass().getName(), "generated_metadata", metadata)));
                    miningSourceCount++;
                }
            }
        }
    }
}
