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
import java.io.IOException;
import java.util.Collection;
import java.util.HashMap;
import java.util.LinkedHashMap;
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

    WorldgenCapture(NativeCapture capture, SnapshotWriter writer) { this.capture = capture; this.writer = writer; }

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
            addSmallOre(outputs, ore.getMaterial(), ore);
            JsonArray contexts = new JsonArray();
            JsonObject gates = new JsonObject();
            for (String name : ore.getAllowedDimensions()) {
                contexts.add(new JsonPrimitive(environment(name))); gates.add(name, dimensionGate(name));
            }
            writer.append("sources", object("id", "small:" + ore.getName(), "kind", "small_ore", "display_name", ore.getName(),
                "outputs", outputs, "environment_ids", contexts, "status", "conditional",
                "conditions", object("dimension_gates", gates, "biome", ore.mBiome, "stone_specific", ore.isStoneSpecific()),
                "parameters", object("min_y", ore.mMinY, "max_y", ore.mMaxY, "amount_parameter", ore.mAmount,
                    "amount_semantics", "native_generation_parameter_not_guaranteed_yield"),
                "provenance", object("owner", "WorldgenGTOreSmallPieces.sList", "generator", ore.getName())));
            small++;
        }
        long fluids = 0;
        for (Map.Entry<String, GTUODimension> entry : GTMod.proxy.mUndergroundOil.getDimensionList().entrySet()) {
            GTUODimension dimension = entry.getValue();
            String context = "underground-rule:" + entry.getKey();
            environments.add(context);
            writer.append("environments", object("id", context, "name", dimension.Dimension,
                "dimension_id", null, "provider", null, "properties", object("rule", dimension.Dimension, "mapping", "unresolved"),
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
            "Active runtime list and stone resource variants captured. Potential mining drops remain separate unknown acquisition");
        capture.coverage("gt.worldgen.underground_fluids", "partial", fluids,
            "Native config rules captured. Numeric/provider matching, blacklist, seeded fields and depletion observations unresolved");
        capture.coverage("acquisition.gt_ore_mining_normal", "partial", miningSourceCount,
            "Conditional GT normal ore Fortune 0 plain/silk native base drops. Tool/event modifiers, positive Fortune and observed deposits are not modeled",
            object("native_drop_mode", GTMod.proxy.oreDropSystem.name(), "random_evaluation", "random_draws_rejected",
                "unsupported_generator_variants", unsupportedMiningVariants, "failed_branches", failedMiningBranches,
                "failure_examples", miningFailures, "records_semantics", "related_source_branches_not_deposit_count"));
        capture.coverage("acquisition.gt_ore_mining_small", "unsupported", small,
            "Small ore exclusive weighted selections, roll counts and host-stone side drops require a symbolic distribution. No guaranteed product list emitted");
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

    private void addSmallOre(JsonArray outputs, IOreMaterial material, WorldgenGTOreSmallPieces layer) throws IOException {
        for (IStoneType stone : material.getValidStones()) {
            if (layer.isStoneSpecific() && !layer.canGenerateIn(stone.getCategory())) continue;
            oreResource(outputs, material, stone, true, "small");
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
