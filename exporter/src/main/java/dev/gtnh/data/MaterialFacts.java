package dev.gtnh.data;

import static dev.gtnh.data.Jsons.object;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import gregtech.api.enums.Element;
import gregtech.api.enums.GTValues;
import gregtech.api.enums.Materials;
import gregtech.api.enums.OrePrefixes;
import gregtech.api.objects.ItemData;
import gregtech.api.objects.MaterialStack;
import gregtech.api.util.GTOreDictUnificator;
import gregtech.api.util.GTRecipeBuilder;
import gtPlusPlus.core.block.base.BlockBaseModular;
import gtPlusPlus.core.item.base.BaseItemComponent;
import gtPlusPlus.core.material.Material;
import java.util.Arrays;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.IdentityHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import net.minecraft.block.Block;
import net.minecraft.item.Item;
import net.minecraft.item.ItemBlock;
import net.minecraft.item.ItemStack;
import net.minecraftforge.fluids.Fluid;
import net.minecraftforge.fluids.FluidStack;
import net.minecraftforge.oredict.OreDictionary;

/** Native declarations and quantity bases. These facts do not certify chemical purity. */
final class MaterialFacts {
    private static final String PROFILE_VERSION = "5.09.54.221";
    private static final Set<String> ACCOUNTING_NATIVE_VERSIONS = new HashSet<>(Arrays.asList(
        PROFILE_VERSION, "5.09.54.223", "5.09.54.225"));
    private static final String FLUID_SOURCE = "Materials.getGtMaterialFromFluid + Materials.getAll public phase identity union";
    private static final int NATIVE_DECLARATION_DEPTH = 32;
    private static final int NATIVE_DECLARATION_NODES = 1024;
    private static final Set<String> SOLID_PREFIXES = new HashSet<>(Arrays.asList(
        "dust", "dustSmall", "dustTiny", "ingot", "ingotHot", "nugget", "block",
        "gem", "gemChipped", "gemFlawed", "gemFlawless", "gemExquisite", "plate", "plateDouble",
        "plateDense", "stick", "stickLong", "foil", "ring", "bolt", "screw", "gearGt", "gearGtSmall",
        "rotor", "wireFine", "round"));
    private final Map<Materials, JsonObject> materials = new IdentityHashMap<>();
    private final String nativeVersion;

    MaterialFacts(String nativeVersion) { this.nativeVersion = nativeVersion; }

    JsonObject item(ItemStack original) {
        JsonObject facts = gtItem(original);
        JsonObject owner = nativeOwner(original);
        if (owner != null) facts.add("native_owner", owner);
        return facts;
    }

    private JsonObject gtItem(ItemStack original) {
        try {
            ItemStack query = original.copy();
            query.stackSize = 1;
            ItemData data = GTOreDictUnificator.getItemData(query);
            JsonObject facts = facts("GTOreDictUnificator.getItemData", data == null ? "unassociated" : "associated");
            if (data == null) {
                facts.add("accounting", unresolved("No native GT ItemData association"));
                return facts;
            }
            String prefix = data.mPrefix == null ? null : data.mPrefix.getName();
            JsonArray secondary = new JsonArray();
            for (MaterialStack part : data.mByProducts) secondary.add(part(part));
            JsonObject primary = data.mMaterial == null ? null : part(data.mMaterial);
            facts.add("association", object("prefix", prefix,
                "prefix_material_amount", data.mPrefix == null ? null : Long.toString(data.mPrefix.getMaterialAmount()),
                "has_explicit_composition", data.hasExplicitComposition,
                "lookup_nbt_semantics", "ignored", "lookup_wildcard_fallback", true,
                "primary", primary, "byproducts", secondary));
            String reason = null;
            if (!ACCOUNTING_NATIVE_VERSIONS.contains(nativeVersion)) reason = "Runtime GT version has no proved accounting profile";
            else if (prefix == null || !SOLID_PREFIXES.contains(prefix)) reason = "Prefix has no bounded solid accounting profile";
            else if (data.hasExplicitComposition) reason = "Explicit recycling composition is not a chemical-purity declaration";
            else if (secondary.size() != 0) reason = "Item association includes secondary materials";
            else if (original.hasTagCompound()) reason = "GT association ignores this resource's NBT state";
            else if (original.getItemDamage() == OreDictionary.WILDCARD_VALUE) reason = "Wildcard resource identity";
            else if (primary == null || !complete(primary.getAsJsonObject("material"))) reason = "Native material composition is unresolved";
            else if (data.mMaterial.mAmount <= 0) reason = "Native material amount is not positive";
            facts.add("accounting", reason == null
                ? quantity("gt_material_units", data.mMaterial.mAmount, GTValues.M, "native_top_level_component_parts")
                : unresolved(reason));
            return facts;
        } catch (RuntimeException error) {
            return failure("GTOreDictUnificator.getItemData", error);
        }
    }

    private static JsonObject nativeOwner(ItemStack original) {
        if (original == null) return null;
        Item item = original.getItem();
        Object owner = item;
        Material material;
        JsonObject form;
        String source = null;
        String sourceClass = null;
        String scope = "native_item_owner";
        try {
            if (item instanceof BaseItemComponent) {
                BaseItemComponent component = (BaseItemComponent) item;
                material = component.componentMaterial;
                source = "BaseItemComponent.componentMaterial + componentType";
                sourceClass = BaseItemComponent.class.getName();
                OrePrefixes prefix = component.componentType == null ? null : component.componentType.getGtOrePrefix();
                form = object("native_class", BaseItemComponent.ComponentTypes.class.getName(),
                    "native_type", component.componentType == null ? null : component.componentType.name(),
                    "prefix", prefix == null ? null : prefix.getName(),
                    "nominal_material_amount", prefix == null ? null : Long.toString(prefix.getMaterialAmount()),
                    "amount_basis", prefix == null ? null : "OrePrefixes.getMaterialAmount");
            } else if (item instanceof ItemBlock && Block.getBlockFromItem(item) instanceof BlockBaseModular) {
                BlockBaseModular block = (BlockBaseModular) Block.getBlockFromItem(item);
                owner = block;
                material = block.getMaterialEx();
                source = "BlockBaseModular.getMaterialEx + blockType";
                sourceClass = BlockBaseModular.class.getName();
                scope = "native_block_owner";
                form = object("native_class", BlockBaseModular.BlockTypes.class.getName(),
                    "native_type", block.blockType == null ? null : block.blockType.name());
            } else {
                return null;
            }
            JsonObject tree = nativeMaterial(material, new IdentityHashMap<>(), 0,
                new int[] {NATIVE_DECLARATION_NODES});
            boolean associated = material != null && !form.get("native_type").isJsonNull();
            JsonObject result = object("status", associated ? "associated" : "unresolved", "source_api", source,
                "source_class", sourceClass, "scope", scope, "item_class", item.getClass().getName(),
                "owner_class", owner.getClass().getName(), "form", form, "material", tree);
            if (!associated) result.addProperty("reason", material == null ? "Missing native owner material" : "Missing native owner form");
            return result;
        } catch (RuntimeException error) {
            return object("status", "failed", "source_api", source, "source_class", sourceClass,
                "scope", scope, "item_class", item.getClass().getName(), "owner_class", owner.getClass().getName(),
                "failure", object("class", error.getClass().getName(), "message", error.getMessage()));
        }
    }

    /** A complete traversal retains exposed declarations, not a chemical quantity profile. */
    private static JsonObject nativeMaterial(Material material, Map<Material, Boolean> active, int depth, int[] remaining) {
        if (remaining[0] == 0) return object("traversal_status", "unresolved", "reason", "Native declaration node limit");
        remaining[0]--;
        if (material == null) return object("traversal_status", "unresolved", "reason", "Missing native material");
        JsonObject tree = object("native_class", material.getClass().getName(), "native_system", "gtpp",
            "internal_name", material.getUnlocalizedName(), "default_local_name", material.getDefaultLocalName(),
            "identity_basis", "literal_native_internal_name_not_global_unique_id");
        String reason = null;
        if (active.containsKey(material)) reason = "Native component cycle";
        else if (depth >= NATIVE_DECLARATION_DEPTH) reason = "Native declaration depth limit";
        if (reason != null) {
            tree.addProperty("traversal_status", "unresolved");
            tree.addProperty("reason", reason);
            return tree;
        }
        List<gtPlusPlus.core.material.MaterialStack> declaration = material.getComposites();
        if (declaration == null) {
            tree.addProperty("traversal_status", "unresolved");
            tree.addProperty("reason", "Missing native component list");
            return tree;
        }
        active.put(material, true);
        JsonArray components = new JsonArray();
        boolean traversed = true;
        for (gtPlusPlus.core.material.MaterialStack part : declaration) {
            if (remaining[0] == 0) {
                traversed = false;
                reason = "Native declaration node limit";
                break;
            }
            Material childMaterial = part == null ? null : part.getStackMaterial();
            JsonObject child = nativeMaterial(childMaterial, active, depth + 1, remaining);
            components.add(object("declared_parts", part == null ? null : Integer.toString(part.getPartsPerOneHundred()),
                "quantity_basis", "gtpp_parts_per_one_hundred_api", "source_api", "MaterialStack.getPartsPerOneHundred",
                "quantity_semantics", "Native integer getter result. Fractional declarations are not retained here and no molar coefficient is certified",
                "material", child));
            traversed &= "complete".equals(child.get("traversal_status").getAsString());
        }
        active.remove(material);
        tree.add("components", components);
        tree.addProperty("declared_component_count", declaration.size());
        tree.addProperty("omitted_component_count", declaration.size() - components.size());
        tree.addProperty("declaration_kind", declaration.isEmpty() ? "terminal" : "composite");
        tree.addProperty("traversal_status", traversed ? "complete" : "unresolved");
        if (!traversed) tree.addProperty("reason", reason == null ? "Native component traversal is unresolved" : reason);
        return tree;
    }

    JsonObject fluid(FluidStack original) {
        JsonObject facts = gtFluid(original);
        facts.add("native_owner", nativeFluidOwner(original));
        return facts;
    }

    private static JsonObject nativeFluidOwner(FluidStack original) {
        String source = "Material.mMaterialMap + Material.getFluid/getPlasma";
        JsonArray candidates = new JsonArray();
        JsonObject result = object("status", "unassociated", "scope", "native_fluid_owner",
            "source_api", source, "source_class", Material.class.getName(), "fluid_class", null,
            "candidate_count", 0, "candidates", candidates);
        try {
            Fluid fluid = original == null ? null : original.getFluid();
            if (fluid == null) {
                result.addProperty("reason", "Missing native fluid");
                return result;
            }
            result.addProperty("fluid_class", fluid.getClass().getName());
            Set<Material> seen = java.util.Collections.newSetFromMap(new IdentityHashMap<>());
            for (Material candidate : Material.mMaterialMap) {
                if (candidate == null || seen.contains(candidate)) continue;
                JsonArray bindings = new JsonArray();
                if (candidate.getFluid() == fluid) bindings.add(new com.google.gson.JsonPrimitive("mFluid"));
                if (candidate.getPlasma() == fluid) bindings.add(new com.google.gson.JsonPrimitive("mPlasma"));
                if (bindings.size() == 0) continue;
                seen.add(candidate);
                JsonObject owner = object("owner_class", candidate.getClass().getName(), "bindings", bindings,
                    "material", null);
                candidates.add(owner);
                result.addProperty("candidate_count", candidates.size());
                owner.add("material", nativeMaterial(candidate, new IdentityHashMap<>(), 0,
                    new int[] {NATIVE_DECLARATION_NODES}));
            }
            result.addProperty("status", candidates.size() == 0 ? "unassociated"
                : candidates.size() == 1 ? "associated" : "ambiguous");
            if (candidates.size() == 0) result.addProperty("reason", "No native GT++ material fluid binding");
            return result;
        } catch (RuntimeException error) {
            result.addProperty("status", "failed");
            result.add("failure", object("class", error.getClass().getName(), "message", error.getMessage()));
            return result;
        }
    }

    private JsonObject gtFluid(FluidStack original) {
        try {
            FluidStack query = original.copy();
            Fluid fluid = query.getFluid();
            Materials dispatcher = Materials.getGtMaterialFromFluid(fluid);
            Map<Materials, Set<String>> evidence = new IdentityHashMap<>();
            List<Materials> candidateOrder = new ArrayList<>();
            Set<Materials> catalogMatches = java.util.Collections.newSetFromMap(new IdentityHashMap<Materials, Boolean>());
            if (dispatcher != null) {
                evidence.put(dispatcher, phases(dispatcher, fluid));
                candidateOrder.add(dispatcher);
            }
            for (Materials candidate : Materials.getAll()) {
                Set<String> matches = phases(candidate, fluid);
                if (matches.isEmpty()) continue;
                catalogMatches.add(candidate);
                if (!evidence.containsKey(candidate)) candidateOrder.add(candidate);
                evidence.put(candidate, matches);
            }
            String uniquePhase = uniqueFluidPhase(evidence);
            JsonObject facts = facts(FLUID_SOURCE, evidence.isEmpty() ? "unassociated"
                : uniquePhase == null ? "ambiguous" : "associated");
            facts.addProperty("native_fluid_density", fluid.getDensity(query));
            facts.addProperty("native_fluid_density_semantics", "Forge property, not a chemical quantity conversion");
            if (evidence.isEmpty()) {
                facts.add("accounting", unresolved("No native GT fluid association"));
                return facts;
            }
            JsonArray candidates = new JsonArray();
            for (Materials candidate : candidateOrder) {
                JsonObject tree = material(candidate, new IdentityHashMap<Materials, Boolean>());
                Set<String> matches = evidence.get(candidate);
                String candidatePhase = matches.size() == 1 ? matches.iterator().next() : "unresolved";
                JsonArray phaseNames = new JsonArray();
                for (String name : matches) phaseNames.add(new com.google.gson.JsonPrimitive(name));
                JsonObject accounting = ACCOUNTING_NATIVE_VERSIONS.contains(nativeVersion)
                    ? fluidAccounting(candidatePhase, original.tag != null, complete(tree))
                    : unresolved("Runtime GT version has no proved accounting profile");
                candidates.add(object("material", tree, "phase", candidatePhase, "phases", phaseNames,
                    "accounting", accounting, "evidence", object("dispatcher", candidate == dispatcher,
                        "phase_catalog", catalogMatches.contains(candidate))));
            }
            JsonObject soleCandidate = uniquePhase == null ? null : candidates.get(0).getAsJsonObject();
            facts.add("association", object("prefix", null, "has_explicit_composition", false,
                "primary", soleCandidate == null ? null : object("amount", null, "material", soleCandidate.get("material")),
                "byproducts", new JsonArray(), "fluid_phase", uniquePhase == null ? "unresolved" : uniquePhase,
                "candidates", candidates));
            facts.add("accounting", soleCandidate == null
                ? unresolved("Native fluid evidence does not establish exactly one material and one phase")
                : soleCandidate.get("accounting"));
            return facts;
        } catch (RuntimeException error) {
            return failure(FLUID_SOURCE, error);
        }
    }

    /** The public phase identities choose distinct native quantity conventions. */
    static JsonObject fluidAccounting(String phase, boolean tagged, boolean knownComposition) {
        if (tagged) return unresolved("Tagged fluid state is not established by the native material association");
        if (!knownComposition) return unresolved("Native material composition is unresolved");
        if ("molten".equals(phase))
            return quantity("gt_material_units", 1, GTRecipeBuilder.INGOTS, "native_top_level_component_parts");
        if ("fluid".equals(phase) || "gas".equals(phase))
            return quantity("formula_units", 1, 1000, "native_formula_unit");
        return unresolved("Fluid phase has no bounded chemical accounting profile: " + phase);
    }

    /** Both evidence sources must agree on one native identity and one phase. */
    static String uniqueFluidPhase(Map<?, Set<String>> evidence) {
        if (evidence.size() != 1) return null;
        Set<String> matches = evidence.values().iterator().next();
        return matches.size() == 1 ? matches.iterator().next() : null;
    }

    private static Set<String> phases(Materials material, Fluid fluid) {
        Set<String> result = new LinkedHashSet<>();
        if (material.mStandardMoltenFluid == fluid) result.add("molten");
        if (material.mFluid == fluid) result.add("fluid");
        if (material.mGas == fluid) result.add("gas");
        if (material.mPlasma == fluid) result.add("plasma");
        if (material.mSolid == fluid) result.add("slurry");
        return result;
    }

    private JsonObject part(MaterialStack part) {
        return object("amount", Long.toString(part.mAmount),
            "material", material(part.mMaterial, new IdentityHashMap<Materials, Boolean>()));
    }

    private JsonObject material(Materials material, Map<Materials, Boolean> active) {
        if (material == null) return object("status", "unresolved", "reason", "Missing native material");
        JsonObject cached = materials.get(material);
        if (cached != null) return cached;
        if (active.containsKey(material))
            return object("name", material.mName, "status", "unresolved", "reason", "Native component cycle");
        JsonObject tree = object("name", material.mName, "native_class", material.getClass().getName(),
            "density_gt_units", Long.toString(material.mDensity), "density_multiplier", material.mDensityMultiplier,
            "density_divider", material.mDensityDivider);
        if (material.getClass() != Materials.class || material == Materials._NULL) {
            tree.addProperty("status", "unresolved");
            tree.addProperty("reason", "Unknown native material class or null sentinel");
            return tree;
        }
        tree.addProperty("formula_display", material.getChemicalFormula());
        tree.addProperty("formula_semantics", "native display text, not parsed or used to certify composition");
        active.put(material, true);
        String componentBasis = material.getDust(1) != null ? "solid_material_unit"
            : material.mFluid != null || material.mGas != null ? "fluid_formula_unit" : "unresolved";
        tree.addProperty("component_unit_basis", componentBasis);
        Element element = material.mElement;
        boolean known = material.mDensity > 0;
        if (element != null && element != Element._NULL) {
            tree.add("element", object("id", element.name(), "name", element.mName,
                "protons", Long.toString(element.mProtons), "neutrons", Long.toString(element.mNeutrons),
                "additional_mass", Long.toString(element.mAdditionalMass), "isotope", element.mIsIsotope));
            known &= material.mMaterialList.isEmpty();
        } else {
            tree.add("element", com.google.gson.JsonNull.INSTANCE);
            known &= !material.mMaterialList.isEmpty() && !"unresolved".equals(componentBasis);
        }
        JsonArray components = new JsonArray();
        for (MaterialStack component : material.mMaterialList) {
            JsonObject child = material(component.mMaterial, active);
            components.add(object("coefficient", Long.toString(component.mAmount), "material", child));
            known &= component.mAmount > 0 && complete(child);
        }
        tree.add("components", components);
        tree.addProperty("status", known ? "complete" : "unresolved");
        if (!known) tree.addProperty("reason", material.mDensity <= 0 ? "Native material density is not positive"
            : "Element/component declaration or nested quantity basis is unresolved");
        active.remove(material);
        materials.put(material, tree);
        return tree;
    }

    private static boolean complete(JsonObject tree) {
        return "complete".equals(tree.get("status").getAsString());
    }

    private JsonObject facts(String source, String status) {
        return object("schema_version", 1, "native_version", nativeVersion, "profile_version", PROFILE_VERSION, "source_api", source,
            "status", status, "gt_material_unit", Long.toString(GTValues.M), "chemistry_purity", "not_certified");
    }

    private static JsonObject quantity(String basis, long numerator, long denominator, String normalization) {
        return object("status", "eligible", "basis", basis,
            "quantity", object("numerator", Long.toString(numerator), "denominator", Long.toString(denominator)),
            "normalization", normalization, "reason", null);
    }

    private static JsonObject unresolved(String reason) {
        return object("status", "unresolved", "basis", null, "quantity", null, "normalization", null, "reason", reason);
    }

    private JsonObject failure(String source, RuntimeException error) {
        JsonObject result = facts(source, "failed");
        result.add("failure", object("class", error.getClass().getName(), "message", error.getMessage()));
        result.add("accounting", unresolved("Native material query failed"));
        return result;
    }
}
