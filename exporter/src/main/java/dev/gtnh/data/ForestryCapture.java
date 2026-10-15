package dev.gtnh.data;

import static dev.gtnh.data.Jsons.object;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonNull;
import com.google.gson.JsonObject;
import cpw.mods.fml.common.Loader;
import cpw.mods.fml.common.ModContainer;
import forestry.api.recipes.ICentrifugeManager;
import forestry.api.recipes.ICentrifugeRecipe;
import forestry.api.recipes.ICarpenterManager;
import forestry.api.recipes.ICarpenterRecipe;
import forestry.api.recipes.IDescriptiveRecipe;
import forestry.api.recipes.ISqueezerManager;
import forestry.api.recipes.ISqueezerRecipe;
import forestry.api.recipes.RecipeManagers;
import forestry.factory.recipes.CentrifugeRecipe;
import forestry.factory.recipes.CentrifugeRecipeManager;
import forestry.core.recipes.ShapedRecipeCustom;
import forestry.factory.recipes.CarpenterRecipe;
import forestry.factory.recipes.CarpenterRecipeManager;
import forestry.factory.recipes.SqueezerRecipe;
import forestry.factory.recipes.SqueezerRecipeManager;
import java.io.IOException;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.Map;
import net.minecraft.item.ItemStack;
import net.minecraftforge.fluids.FluidStack;

/** Native Forestry catalogs with family-specific interpretation limits. */
final class ForestryCapture {
    private final NativeCapture capture;

    ForestryCapture(NativeCapture capture) { this.capture = capture; }

    void capture() throws IOException {
        centrifuge();
        squeezer();
        carpenter();
        capture.coverage("forestry.other_factories", "unsupported", 0,
            "Only the native Centrifuge catalog and static Squeezer and Carpenter declarations are captured");
    }

    private void centrifuge() throws IOException {
        ICentrifugeManager manager = RecipeManagers.centrifugeManager;
        if (manager == null) {
            capture.coverage("forestry:centrifuge", "unsupported", 0, "Native Centrifuge manager is unavailable");
            return;
        }
        boolean nativeManager = manager.getClass() == CentrifugeRecipeManager.class;
        Map<String, Integer> classes = new LinkedHashMap<>();
        int index = 0;
        long interpreted = 0;
        long unresolvedInputs = 0;
        long unresolvedOutputs = 0;
        for (ICentrifugeRecipe recipe : new ArrayList<>(manager.recipes())) {
            String nativeClass = recipe == null ? null : recipe.getClass().getName();
            classes.merge(nativeClass == null ? "null" : nativeClass, 1, Integer::sum);
            boolean known = nativeManager && recipe != null && recipe.getClass() == CentrifugeRecipe.class;
            JsonObject conditions = object("native_class", nativeClass, "native_registry_class", manager.getClass().getName(),
                "registry_binding", nativeManager ? "exact_native_manager_static_registry" : "uninterpreted_manager",
                "selection", nativeManager ? "first_matching_native_hashset_iteration" : "uninterpreted_manager", "registry_order", "within_run_only",
                "machine", "forestry_centrifuge", "native_processing_time", recipe == null ? null : recipe.getProcessingTime(),
                "processing_time_unit", "forestry_work_ticks", "native_work_tick_interval_game_ticks", 5,
                "effective_duration", "machine_owned_unknown", "effective_energy", "machine_owned_unknown",
                "machine_context", "power_redstone_speed_upgrades_and_pending_output_space",
                "output_roll", known ? object("shared", false, "rng", "java.util.Random.nextFloat", "range", "[0,1)",
                    "comparison", "roll < threshold", "draws", "separate_per_output_below_one",
                    "probability_model", "native_uniform_24_bit_float_lattice") : null);
            if (!known) {
                conditions.addProperty("dynamic_inputs", "unresolved");
                conditions.addProperty("dynamic_output", "unresolved");
            }
            JsonArray inputs = new JsonArray();
            ItemStack input = recipe == null ? null : recipe.getInput();
            boolean sensitive = input != null && input.hasTagCompound() && !input.getTagCompound().hasNoTags();
            JsonObject slot = capture.itemSlot(input == null ? new ItemStack[0] : new ItemStack[]{input}, -1, sensitive, false);
            slot.addProperty("role", "consume");
            slot.addProperty("native_slot", 0);
            slot.add("consumption_chance", object("numerator", 1, "denominator", 1));
            if (input == null) conditions.addProperty("dynamic_inputs", "unresolved");
            for (JsonElement value : slot.getAsJsonArray("choices")) {
                JsonObject choice = value.getAsJsonObject();
                choice.addProperty("amount", 1);
                if (choice.get("resource_id").isJsonNull()) conditions.addProperty("dynamic_inputs", "unresolved");
                if (!known) {
                    choice.add("declared_match", choice.get("match"));
                    choice.add("match", object("mode", "native_unknown"));
                }
            }
            if (slot.getAsJsonArray("choices").size() != 0) inputs.add(slot);
            JsonArray outputs = new JsonArray();
            Map<ItemStack, Float> products = recipe == null ? null : recipe.getAllProducts();
            if (products == null) conditions.addProperty("dynamic_output", "unresolved");
            else for (Map.Entry<ItemStack, Float> entry : products.entrySet()) {
                ItemStack product = entry.getKey();
                Float threshold = entry.getValue();
                JsonObject probability = known && threshold != null ? NativeCapture.floatRollChance(threshold, false) : null;
                if (probability == null || product == null) conditions.addProperty("dynamic_output", "unresolved");
                if (product == null) {
                    conditions.addProperty("native_null_product", true);
                    continue;
                }
                JsonObject identity = capture.itemSlot(new ItemStack[]{product}, -1, true, false)
                    .getAsJsonArray("choices").get(0).getAsJsonObject();
                if (identity.get("resource_id").isJsonNull()) conditions.addProperty("dynamic_output", "unresolved");
                JsonObject output = object("resource_id", identity.get("resource_id"), "amount", product.stackSize,
                    "chance", probability, "native_chance_threshold", threshold == null ? null
                        : Float.isNaN(threshold) || Float.isInfinite(threshold) ? Float.toString(threshold) : threshold,
                    "native_output_index", outputs.size(), "native_roll", !known ? "uninterpreted"
                        : threshold != null && threshold >= 1 ? "not_drawn_threshold_at_least_one" : "separate_output_draw",
                    "native_chance_semantics", known ? "strict_native_threshold" : "declared_api_estimate");
                if (identity.has("native_item")) output.add("native_item", identity.get("native_item"));
                outputs.add(output);
            }
            if (conditions.has("dynamic_inputs")) unresolvedInputs++;
            if (conditions.has("dynamic_output")) unresolvedOutputs++;
            Boolean executable = known && !conditions.has("dynamic_inputs") && !conditions.has("dynamic_output")
                ? Boolean.TRUE : null;
            if (Boolean.TRUE.equals(executable)) interpreted++;
            capture.emitProcess("forestry:centrifuge", "Forestry Centrifuge", inputs, outputs, null, null, null,
                executable, conditions, object("owner", "RecipeManagers.centrifugeManager.recipes", "index", index++,
                    "native_class", nativeClass, "native_version", "4.11.39", "order_stability", "within_run_only"));
        }
        capture.coverage("forestry:centrifuge", "partial", index,
            "All public manager entries. Exact native recipe classes preserve matching, single-item consumption and separate output rolls. Effective machine timing and energy remain unknown",
            object("registry_class", manager.getClass().getName(), "native_registry_binding", nativeManager,
                "native_recipe_classes", classes, "interpreted_records", interpreted,
                "unresolved_input_records", unresolvedInputs, "unresolved_output_records", unresolvedOutputs));
    }

    private void squeezer() throws IOException {
        ModContainer owner = Loader.instance().getIndexedModList().get("Forestry");
        String version = owner == null ? null : owner.getVersion();
        if (!"4.11.39".equals(version)) {
            capture.coverage("forestry:squeezer", "unsupported", 0,
                "No verified native Squeezer declaration contract for this version",
                object("native_version", version));
            return;
        }
        ISqueezerManager manager = RecipeManagers.squeezerManager;
        if (manager == null || manager.getClass() != SqueezerRecipeManager.class) {
            capture.coverage("forestry:squeezer", "unsupported", 0,
                "Verified native Squeezer manager is unavailable",
                object("native_version", version, "registry_class", manager == null ? null : manager.getClass().getName()));
            return;
        }
        Map<String, Integer> classes = new LinkedHashMap<>();
        int index = 0;
        long declared = 0;
        long unresolvedOutputs = 0;
        int containerTemplates = SqueezerRecipeManager.containerRecipes.size();
        for (ISqueezerRecipe recipe : new ArrayList<>(manager.recipes())) {
            String nativeClass = recipe == null ? null : recipe.getClass().getName();
            classes.merge(nativeClass == null ? "null" : nativeClass, 1, Integer::sum);
            boolean known = recipe != null && recipe.getClass() == SqueezerRecipe.class;
            JsonObject conditions = object("native_class", nativeClass, "native_registry_class", manager.getClass().getName(),
                "native_version", version, "registry_binding", "exact_native_manager_static_registry",
                "selection", "container_templates_first_then_static_hashset_iteration",
                "registry_order", "within_run_only", "machine", "forestry_squeezer",
                "dynamic_inputs", "unresolved", "input_matching", known ? "initial_literal_cached_ore_equivalence" : "uninterpreted_recipe",
                "effective_duration", "machine_owned_unknown", "effective_energy", "machine_owned_unknown",
                "machine_context", "cached_recipe_power_redstone_speed_upgrades_and_output_space",
                "container_generation", "not_expanded");
            JsonArray inputs = new JsonArray();
            JsonArray outputs = new JsonArray();
            if (!known) {
                conditions.addProperty("dynamic_output", "unresolved");
            } else {
                declared++;
                conditions.addProperty("native_processing_time", recipe.getProcessingTime());
                conditions.addProperty("processing_time_unit", "forestry_work_ticks");
                conditions.addProperty("native_work_tick_interval_game_ticks", 5);
                ItemStack[] resources = recipe.getResources();
                conditions.addProperty("native_resource_array_length", resources == null ? null : Integer.valueOf(resources.length));
                if (resources == null) conditions.addProperty("native_resources_null", true);
                else for (int slotIndex = 0; slotIndex < resources.length; slotIndex++) {
                    ItemStack resource = resources[slotIndex];
                    boolean sensitive = resource != null && resource.hasTagCompound() && !resource.getTagCompound().hasNoTags();
                    JsonObject slot = capture.itemSlot(resource == null ? new ItemStack[0] : new ItemStack[]{resource}, -1, sensitive, false);
                    slot.addProperty("role", "consume");
                    slot.addProperty("native_slot", slotIndex);
                    slot.add("consumption_chance", object("numerator", 1, "denominator", 1));
                    for (JsonElement value : slot.getAsJsonArray("choices")) {
                        JsonObject choice = value.getAsJsonObject();
                        choice.addProperty("amount", resource.stackSize);
                        choice.add("declared_match", choice.get("match"));
                        choice.add("match", object("mode", "native_unknown"));
                    }
                    if (slot.getAsJsonArray("choices").size() == 0) slot.addProperty("native_input_missing", true);
                    inputs.add(slot);
                }
                FluidStack fluid = recipe.getFluidOutput();
                if (fluid == null || fluid.getFluid() == null) {
                    conditions.addProperty("dynamic_output", "unresolved");
                    conditions.addProperty("native_fluid_output_missing", true);
                } else {
                    outputs.add(object("resource_id", capture.fluid(fluid), "amount", fluid.amount,
                        "chance", object("numerator", 1, "denominator", 1), "native_output_kind", "fluid"));
                }
                ItemStack remnant = recipe.getRemnants();
                float threshold = recipe.getRemnantsChance();
                if (Float.isNaN(threshold) || Float.isInfinite(threshold)) {
                    conditions.addProperty("native_remnants_chance_threshold", Float.toString(threshold));
                } else conditions.addProperty("native_remnants_chance_threshold", threshold);
                conditions.add("output_roll", object("rng", "java.util.Random.nextFloat", "range", "[0,1)",
                    "comparison", "roll < threshold", "draws", remnant == null ? "none_without_remnant" : "one_per_cycle_with_remnant",
                    "probability_model", "native_uniform_24_bit_float_lattice"));
                if (remnant != null) {
                    JsonObject probability = NativeCapture.floatRollChance(threshold, false);
                    JsonObject identity = capture.itemSlot(new ItemStack[]{remnant}, -1, true, false)
                        .getAsJsonArray("choices").get(0).getAsJsonObject();
                    if (probability == null || identity.get("resource_id").isJsonNull()) conditions.addProperty("dynamic_output", "unresolved");
                    JsonObject output = object("resource_id", identity.get("resource_id"), "amount", remnant.stackSize,
                        "chance", probability, "native_output_kind", "remnant", "native_chance_semantics", "strict_native_threshold");
                    if (identity.has("native_item")) output.add("native_item", identity.get("native_item"));
                    outputs.add(output);
                }
            }
            if (conditions.has("dynamic_output")) unresolvedOutputs++;
            capture.emitProcess("forestry:squeezer", "Forestry Squeezer", inputs, outputs, null, null, null,
                null, conditions, object("owner", "RecipeManagers.squeezerManager.recipes", "index", index++,
                    "native_class", nativeClass, "native_version", version, "order_stability", "within_run_only"));
        }
        capture.coverage("forestry:squeezer", "partial", index,
            "Static native declarations only. Cached matching, generated container recipes and effective machine timing and energy remain unresolved",
            object("registry_class", manager.getClass().getName(), "native_version", version,
                "native_recipe_classes", classes, "declared_records", declared, "interpreted_records", 0,
                "unresolved_input_records", index, "unresolved_output_records", unresolvedOutputs,
                "container_templates", containerTemplates, "generated_container_recipes", "unsupported"));
    }

    private void carpenter() throws IOException {
        ModContainer owner = Loader.instance().getIndexedModList().get("Forestry");
        String version = owner == null ? null : owner.getVersion();
        ICarpenterManager manager = RecipeManagers.carpenterManager;
        if (!"4.11.39".equals(version) || manager == null || manager.getClass() != CarpenterRecipeManager.class) {
            capture.coverage("forestry:carpenter", "unsupported", 0,
                "Verified Forestry 4.11.39 native Carpenter manager is unavailable",
                object("native_version", version, "registry_class", manager == null ? null : manager.getClass().getName()));
            return;
        }
        ArrayList<ICarpenterRecipe> recipes;
        try {
            recipes = new ArrayList<>(manager.recipes());
        } catch (RuntimeException error) {
            capture.coverage("forestry:carpenter", "error", 0, "Native Carpenter catalog could not be read",
                object("native_version", version, "error_class", error.getClass().getName(), "message", error.getMessage()));
            return;
        }
        Map<String, Integer> classes = new LinkedHashMap<>();
        Map<String, Integer> gridClasses = new LinkedHashMap<>();
        int index = 0;
        int declared = 0;
        int uninterpretedClasses = 0;
        int unresolvedPatterns = 0;
        int unresolvedOutputs = 0;
        int missingIdentities = 0;
        int errors = 0;
        for (ICarpenterRecipe recipe : recipes) {
            String nativeClass = recipe == null ? null : recipe.getClass().getName();
            classes.merge(nativeClass == null ? "null" : nativeClass, 1, Integer::sum);
            JsonObject conditions = object("native_class", nativeClass, "native_version", version,
                "dynamic_inputs", "unresolved", "dynamic_output", "unresolved");
            JsonArray outputs = new JsonArray();
            try {
                CarpenterDeclaration declaration = carpenterDeclaration(recipe, version);
                conditions = declaration.conditions;
                if (!declaration.known) uninterpretedClasses++;
                conditions.addProperty("native_registry_class", manager.getClass().getName());
                if (conditions.has("native_grid_class")) {
                    JsonElement gridClass = conditions.get("native_grid_class");
                    gridClasses.merge(gridClass.isJsonNull() ? "null" : gridClass.getAsString(), 1, Integer::sum);
                }
                JsonArray nativeInputs = new JsonArray();
                if (declaration.known) {
                    JsonArray cells = new JsonArray();
                    Object[] ingredients = declaration.ingredients;
                    if (ingredients == null) conditions.addProperty("native_pattern_missing", true);
                    else for (int cell = 0; cell < ingredients.length; cell++) {
                        JsonArray choices = new JsonArray();
                        cells.add(carpenterCell(ingredients[cell], choices, conditions));
                        if (ingredients[cell] != null) nativeInputs.add(object("native_slot", cell,
                            "native_origin", "pattern_cell", "role", "consume", "choices", choices,
                            "quantity_scope", "selected_phantom_stock_debit_unresolved"));
                    }
                    conditions.add("native_pattern", object("width", declaration.width, "height", declaration.height,
                        "cell_count", ingredients == null ? null : Integer.valueOf(ingredients.length), "cells", cells,
                        "cell_order", "row_major_with_empty_cells", "matching", "offsets_and_horizontal_mirror_with_empty_outside_cells"));
                    if (declaration.width < 1 || declaration.height < 1 || declaration.width > 3 || declaration.height > 3
                        || ingredients == null || ingredients.length != declaration.width * declaration.height)
                        conditions.addProperty("native_pattern_shape_unresolved", true);
                }
                if (declaration.box != null) {
                    JsonObject box = carpenterChoice(declaration.box, conditions);
                    box.addProperty("amount", 1);
                    nativeInputs.add(object("native_origin", "dedicated_packaging_slot", "role", "consume",
                        "quantity_scope", "one_packaging_item_per_craft", "choices", Jsons.array(box)));
                }
                if (declaration.fluid != null) {
                    if (declaration.fluid.getFluid() == null) {
                        conditions.addProperty("native_fluid_identity_unresolved", true);
                    } else {
                        String fluidId = capture.fluid(declaration.fluid);
                        if (fluidId == null) conditions.addProperty("native_identity_unresolved", true);
                        nativeInputs.add(object("native_origin", "recipe_fluid_requirement", "role", "consume",
                            "quantity_scope", "native_declared_fluid_drain", "choices", Jsons.array(object(
                                "resource_id", fluidId, "amount", declaration.fluid.amount,
                                "declared_match", object("mode", "exact", "nbt_sensitive", true),
                                "match", object("mode", "native_unknown")))));
                    }
                }
                conditions.add("native_inputs", nativeInputs);
                conditions.addProperty("native_packaging_present", declaration.box != null);
                conditions.addProperty("native_fluid_present", declaration.fluid != null);
                if (declaration.output != null) {
                    JsonObject identity = capture.itemSlot(new ItemStack[]{declaration.output}, -1, true, false)
                        .getAsJsonArray("choices").get(0).getAsJsonObject();
                    JsonObject output = object("resource_id", identity.get("resource_id"), "amount", declaration.output.stackSize,
                        "chance", object("numerator", 1, "denominator", 1), "native_output_semantics", "fixed_main_output_no_rng");
                    if (identity.has("native_item")) output.add("native_item", identity.get("native_item"));
                    outputs.add(output);
                    if (identity.get("resource_id").isJsonNull()) {
                        conditions.addProperty("native_identity_unresolved", true);
                        conditions.addProperty("dynamic_output", "unresolved");
                    }
                }
                if (declaration.known) declared++;
            } catch (RuntimeException error) {
                errors++;
                conditions.addProperty("dynamic_output", "unresolved");
                conditions.add("capture_error", object("phase", "native_carpenter_declarations", "class", error.getClass().getName(),
                    "message", error.getMessage()));
            }
            if (conditions.has("dynamic_output")) unresolvedOutputs++;
            if (conditions.has("native_pattern_missing") || conditions.has("native_pattern_shape_unresolved")
                || conditions.has("native_pattern_contains_uninterpreted_values")) unresolvedPatterns++;
            if (conditions.has("native_identity_unresolved") || conditions.has("native_fluid_identity_unresolved")) missingIdentities++;
            capture.emitProcess("forestry:carpenter", "Forestry Carpenter", new JsonArray(), outputs, null, null, null,
                null, conditions, object("owner", "RecipeManagers.carpenterManager.recipes", "index", index++,
                    "native_class", nativeClass, "native_version", version, "order_stability", "within_run_only"));
        }
        capture.coverage("forestry:carpenter", "partial", index,
            "Passive static declarations only. Phantom stock quantities, ore-aware removal, container returns and effective machine timing and energy remain unresolved",
            object("native_version", version, "registry_class", manager.getClass().getName(), "native_recipe_classes", classes,
                "native_grid_classes", gridClasses, "declared_records", declared, "interpreted_records", 0,
                "uninterpreted_class_records", uninterpretedClasses, "unresolved_pattern_records", unresolvedPatterns,
                "unresolved_input_records", index,
                "unresolved_output_records", unresolvedOutputs, "missing_identity_records", missingIdentities, "capture_errors", errors));
    }

    private JsonElement carpenterCell(Object value, JsonArray choices, JsonObject conditions) throws IOException {
        if (value == null) return JsonNull.INSTANCE;
        if (value instanceof ItemStack) {
            JsonObject choice = carpenterChoice((ItemStack) value, conditions);
            choices.add(choice);
            return object("kind", "item_stack", "choice", choice);
        }
        if (value instanceof Iterable) {
            JsonArray alternatives = new JsonArray();
            for (Object alternative : (Iterable<?>) value) alternatives.add(carpenterCell(alternative, choices, conditions));
            return object("kind", "alternatives", "native_class", value.getClass().getName(), "values", alternatives);
        }
        conditions.addProperty("native_pattern_contains_uninterpreted_values", true);
        return object("kind", "uninterpreted", "native_class", value.getClass().getName());
    }

    private JsonObject carpenterChoice(ItemStack stack, JsonObject conditions) throws IOException {
        boolean sensitive = stack.hasTagCompound() && !stack.getTagCompound().hasNoTags();
        JsonObject choice = capture.itemSlot(new ItemStack[]{stack}, -1, sensitive, false)
            .getAsJsonArray("choices").get(0).getAsJsonObject();
        choice.addProperty("declared_stack_size", stack.stackSize);
        choice.add("amount", JsonNull.INSTANCE);
        choice.add("declared_match", choice.get("match"));
        choice.add("match", object("mode", "native_unknown"));
        if (choice.get("resource_id").isJsonNull()) conditions.addProperty("native_identity_unresolved", true);
        return choice;
    }

    /** Reads only verified base getters, without matching a phantom inventory or invoking item container callbacks. */
    static CarpenterDeclaration carpenterDeclaration(ICarpenterRecipe recipe, String version) {
        JsonObject conditions = object("native_class", recipe == null ? null : recipe.getClass().getName(), "native_version", version,
            "material_projection", "declaration_only_not_complete_material_transaction", "dynamic_inputs", "unresolved",
            "registry_binding", "exact_native_manager_static_registry", "registry_order", "within_run_only",
            "selection", "cached_current_recipe_then_first_matching_hashset_entry",
            "input_matching", "phantom_grid_configuration_and_ore_equivalent_selected_stock_removal_unresolved",
            "container_returns", "unresolved_selected_item_callbacks", "effective_duration", "machine_owned_unknown",
            "effective_energy", "machine_owned_unknown", "machine_context", "power_redstone_speed_difficulty_and_output_space");
        String reason = !"4.11.39".equals(version) ? "unsupported_native_version" : recipe == null ? "null_native_recipe"
            : recipe.getClass() != CarpenterRecipe.class ? "uninterpreted_native_subclass" : null;
        if (reason != null) {
            conditions.addProperty("declaration_status", reason);
            conditions.addProperty("dynamic_output", "unresolved");
            return new CarpenterDeclaration(false, null, 0, 0, null, null, null, conditions);
        }
        conditions.addProperty("native_processing_time", recipe.getPackagingTime());
        conditions.addProperty("processing_time_unit", "forestry_work_ticks");
        conditions.addProperty("native_work_tick_interval_game_ticks", 5);
        conditions.addProperty("native_cycle_energy_multiplier", 204);
        ItemStack box = recipe.getBox();
        FluidStack fluid = recipe.getFluidResource();
        IDescriptiveRecipe grid = recipe.getCraftingGridRecipe();
        conditions.addProperty("native_grid_class", grid == null ? null : grid.getClass().getName());
        if (grid == null || grid.getClass() != ShapedRecipeCustom.class) {
            conditions.addProperty("declaration_status", grid == null ? "null_native_grid" : "uninterpreted_grid_subclass");
            conditions.addProperty("dynamic_output", "unresolved");
            return new CarpenterDeclaration(false, null, 0, 0, box, fluid, null, conditions);
        }
        Object[] ingredients = grid.getIngredients();
        ItemStack output = grid.getRecipeOutput();
        if (output == null) conditions.addProperty("dynamic_output", "unresolved");
        conditions.addProperty("declaration_status", "captured_exact_native_classes");
        return new CarpenterDeclaration(true, ingredients == null ? null : ingredients.clone(), grid.getWidth(), grid.getHeight(),
            box == null ? null : box.copy(), fluid == null ? null : fluid.copy(), output == null ? null : output.copy(), conditions);
    }

    static final class CarpenterDeclaration {
        final boolean known;
        final Object[] ingredients;
        final int width;
        final int height;
        final ItemStack box;
        final FluidStack fluid;
        final ItemStack output;
        final JsonObject conditions;

        CarpenterDeclaration(boolean known, Object[] ingredients, int width, int height, ItemStack box,
            FluidStack fluid, ItemStack output, JsonObject conditions) {
            this.known = known;
            this.ingredients = ingredients;
            this.width = width;
            this.height = height;
            this.box = box;
            this.fluid = fluid;
            this.output = output;
            this.conditions = conditions;
        }
    }
}
