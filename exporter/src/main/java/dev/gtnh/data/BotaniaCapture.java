package dev.gtnh.data;

import static dev.gtnh.data.Jsons.object;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import java.io.IOException;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.Map;
import net.minecraft.block.Block;
import net.minecraft.item.ItemStack;
import net.minecraftforge.oredict.OreDictionary;
import vazkii.botania.api.BotaniaAPI;
import vazkii.botania.api.item.IManaDissolvable;
import vazkii.botania.api.recipe.RecipeManaInfusion;
import vazkii.botania.common.block.ModBlocks;

/** Native Mana Infusion catalog, preserving exact base recipes and unresolved subclass declarations. */
final class BotaniaCapture {
    private final NativeCapture capture;

    BotaniaCapture(NativeCapture capture) { this.capture = capture; }

    void capture() throws IOException {
        Map<String, Integer> classes = new LinkedHashMap<>();
        int index = 0;
        long interpreted = 0;
        long unresolvedInputs = 0;
        long unresolvedOutputs = 0;
        long errors = 0;
        for (RecipeManaInfusion recipe : new ArrayList<>(BotaniaAPI.manaInfusionRecipes)) {
            String nativeClass = recipe == null ? null : recipe.getClass().getName();
            classes.merge(nativeClass == null ? "null" : nativeClass, 1, Integer::sum);
            boolean known = recipe != null && recipe.getClass() == RecipeManaInfusion.class;
            JsonObject conditions = object("native_class", nativeClass, "native_version", "1.13.38-GTNH");
            JsonArray inputs = new JsonArray();
            JsonArray outputs = new JsonArray();
            Boolean executable = null;
            if (!known) unresolved(conditions, true, true);
            try {
                if (recipe == null) {
                    conditions.addProperty("native_null_recipe", true);
                    unresolved(conditions, true, true);
                } else {
                    JsonObject nativeConditions = conditions(recipe.getManaToConsume(), recipe.isAlchemy(), recipe.isConjuration());
                    for (Map.Entry<String, JsonElement> entry : nativeConditions.entrySet()) conditions.add(entry.getKey(), entry.getValue());
                    JsonObject catalysts = conditions.getAsJsonObject("catalyst_below");
                    catalysts.add("alchemy_block", catalyst(ModBlocks.alchemyCatalyst));
                    catalysts.add("conjuration_block", catalyst(ModBlocks.conjurationCatalyst));
                    Object declared = recipe.getInput();
                    JsonObject input = input(declared, known, conditions);
                    if (input.getAsJsonArray("choices").size() != 0) inputs.add(input);
                    else {
                        conditions.addProperty("native_input_empty", true);
                        unresolved(conditions, true, !known);
                    }
                    ItemStack output = recipe.getOutput();
                    if (output == null) {
                        conditions.addProperty("native_output_missing", true);
                        unresolved(conditions, false, true);
                    } else {
                        JsonObject identity = capture.itemSlot(new ItemStack[]{output}, -1, true, false)
                            .getAsJsonArray("choices").get(0).getAsJsonObject();
                        JsonObject record = object("resource_id", identity.get("resource_id"), "amount", output.stackSize,
                            "chance", known ? object("numerator", 1, "denominator", 1) : null,
                            "native_output_semantics", known ? "copied_output_no_rng" : "declared_getter_template");
                        if (identity.has("native_item")) record.add("native_item", identity.get("native_item"));
                        if (identity.get("resource_id").isJsonNull()) unresolved(conditions, false, true);
                        outputs.add(record);
                    }
                    if (known && conditions.has("native_input_empty")) executable = Boolean.FALSE;
                    else if (known && !conditions.has("dynamic_inputs") && !conditions.has("dynamic_output")) executable = Boolean.TRUE;
                }
            } catch (RuntimeException error) {
                errors++;
                unresolved(conditions, true, true);
                conditions.add("capture_error", object("phase", "native_recipe_declarations", "class", error.getClass().getName(),
                    "message", error.getMessage()));
            }
            if (conditions.has("dynamic_inputs")) unresolvedInputs++;
            if (conditions.has("dynamic_output")) unresolvedOutputs++;
            if (Boolean.TRUE.equals(executable)) interpreted++;
            capture.emitProcess("botania:mana_infusion", "Botania Mana Infusion", inputs, outputs, null, null, null,
                executable, conditions, object("owner", "BotaniaAPI.manaInfusionRecipes", "index", index++,
                    "native_class", nativeClass, "native_version", "1.13.38-GTNH", "selection", "active_list_order"));
        }
        capture.coverage("botania:mana_infusion", "partial", index,
            "Public active registry. Exact base material semantics only. Mana, catalyst, entity age, list priority and item pre-hooks remain runtime requirements",
            object("native_recipe_classes", classes, "interpreted_records", interpreted, "unresolved_input_records", unresolvedInputs,
                "unresolved_output_records", unresolvedOutputs, "capture_errors", errors));
        capture.coverage("botania.other_recipes", "unsupported", 0, "Only the native Mana Infusion family is captured");
    }

    private JsonObject input(Object declared, boolean known, JsonObject conditions) throws IOException {
        conditions.addProperty("native_input_class", declared == null ? null : declared.getClass().getName());
        ItemStack[] stacks = new ItemStack[0];
        int oreId = -1;
        if (declared instanceof ItemStack) stacks = new ItemStack[]{(ItemStack) declared};
        else if (declared instanceof String) {
            String name = (String) declared;
            conditions.addProperty("native_input_ore", name);
            if (OreDictionary.doesOreNameExist(name)) {
                oreId = OreDictionary.getOreID(name);
                stacks = OreDictionary.getOres(name).toArray(new ItemStack[0]);
            }
        }
        JsonObject slot = capture.itemSlot(stacks, oreId, false, false);
        slot.addProperty("role", "consume");
        slot.addProperty("native_slot", 0);
        slot.add("consumption_chance", object("numerator", 1, "denominator", 1));
        JsonArray hooks = new JsonArray();
        for (ItemStack stack : stacks) if (stack != null && stack.getItem() instanceof IManaDissolvable)
            hooks.add(object("item_class", stack.getItem().getClass().getName(), "hook", "IManaDissolvable.onDissolveTick",
                "status", "uninterpreted", "metadata", stack.getItemDamage()));
        if (hooks.size() != 0) {
            conditions.add("native_input_pre_hooks", hooks);
            unresolved(conditions, true, false);
        }
        // An ore-group matcher can accept every member, including a hooked member behind another choice.
        boolean predicateKnown = known && hooks.size() == 0;
        for (JsonElement value : slot.getAsJsonArray("choices")) {
            JsonObject choice = value.getAsJsonObject();
            choice.addProperty("amount", 1);
            if (choice.get("resource_id").isJsonNull()) unresolved(conditions, true, false);
            if (oreId >= 0 && !choice.getAsJsonObject("match").has("group_id")) {
                predicateKnown = false;
                unresolved(conditions, true, false);
            }
        }
        if (!predicateKnown) for (JsonElement value : slot.getAsJsonArray("choices")) {
            JsonObject choice = value.getAsJsonObject();
            choice.add("declared_match", choice.get("match"));
            choice.add("match", object("mode", "native_unknown"));
            choice.addProperty("declared_predicate_basis", "native_getInput_template_only");
        }
        return slot;
    }

    private JsonObject catalyst(Block block) throws IOException {
        JsonObject identity = capture.itemSlot(new ItemStack[]{new ItemStack(block)}, -1, false, false)
            .getAsJsonArray("choices").get(0).getAsJsonObject();
        return object("resource_id", identity.get("resource_id"), "registry_name", Block.blockRegistry.getNameForObject(block),
            "match", "block_identity", "metadata", "ignored", "consumed", false);
    }

    /** Captures required state, without claiming that a pool or dropped item satisfies it. */
    static JsonObject conditions(int mana, boolean alchemy, boolean conjuration) {
        return object("total_mana", mana, "energy_unit", "mana", "effective_duration", "collision_runtime_gate_unknown",
            "selection", "first_matching_recipe_and_catalyst_before_mana_check", "registry_order", "active_list_order",
            "catalyst_below", object("position", "one_block_below_pool", "alchemy_required", alchemy,
                "conjuration_required", conjuration),
            "runtime_gates", object("entity", "live_dropped_item", "excluded_entity_age_ticks", object("minimum", 101, "maximum", 129),
                "catalyst_registration", "required", "available_mana", "at_least_total_mana",
                "item_pre_hook", "IManaDissolvable_before_recipe_matching"));
    }

    private static void unresolved(JsonObject conditions, boolean inputs, boolean outputs) {
        if (inputs) conditions.addProperty("dynamic_inputs", "unresolved");
        if (outputs) conditions.addProperty("dynamic_output", "unresolved");
    }
}
