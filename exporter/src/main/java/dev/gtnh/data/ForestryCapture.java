package dev.gtnh.data;

import static dev.gtnh.data.Jsons.object;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import forestry.api.recipes.ICentrifugeManager;
import forestry.api.recipes.ICentrifugeRecipe;
import forestry.api.recipes.RecipeManagers;
import forestry.factory.recipes.CentrifugeRecipe;
import forestry.factory.recipes.CentrifugeRecipeManager;
import java.io.IOException;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.Map;
import net.minecraft.item.ItemStack;

/** Native Forestry Centrifuge catalog, with exact-class execution semantics only. */
final class ForestryCapture {
    private final NativeCapture capture;

    ForestryCapture(NativeCapture capture) { this.capture = capture; }

    void capture() throws IOException {
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
        capture.coverage("forestry.other_factories", "unsupported", 0, "Only the native Centrifuge family is captured");
    }
}
