package dev.gtnh.data;

import static dev.gtnh.data.Jsons.object;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import cpw.mods.fml.common.Loader;
import cpw.mods.fml.common.ModContainer;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import net.minecraft.block.Block;
import net.minecraft.item.ItemStack;
import net.minecraftforge.oredict.OreDictionary;
import vazkii.botania.api.BotaniaAPI;
import vazkii.botania.api.item.IManaDissolvable;
import vazkii.botania.api.recipe.RecipeManaInfusion;
import vazkii.botania.api.recipe.RecipeRuneAltar;
import vazkii.botania.common.block.ModBlocks;
import vazkii.botania.common.item.ModItems;

/** Bounded native Botania catalogs with explicit unresolved subclass declarations. */
final class BotaniaCapture {
    private final NativeCapture capture;

    BotaniaCapture(NativeCapture capture) { this.capture = capture; }

    void capture() throws IOException {
        ModContainer owner = Loader.instance().getIndexedModList().get("Botania");
        String version = owner == null ? null : owner.getVersion();
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
            JsonObject conditions = object("native_class", nativeClass, "native_version", version);
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
                        outputs.add(output(output, known, conditions));
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
                    "native_class", nativeClass, "native_version", version, "selection", "active_list_order"));
        }
        capture.coverage("botania:mana_infusion", "partial", index,
            "Public active registry. Exact base material semantics only. Mana, catalyst, entity age, list priority and item pre-hooks remain runtime requirements",
            object("native_recipe_classes", classes, "interpreted_records", interpreted, "unresolved_input_records", unresolvedInputs,
                "unresolved_output_records", unresolvedOutputs, "capture_errors", errors));
        captureRunicAltar(version);
        capture.coverage("botania.other_recipes", "unsupported", 0, "Only native Mana Infusion and bounded Runic Altar catalogs are captured");
    }

    private JsonObject output(ItemStack output, boolean known, JsonObject conditions) throws IOException {
        JsonObject identity = capture.itemSlot(new ItemStack[]{output}, -1, true, false)
            .getAsJsonArray("choices").get(0).getAsJsonObject();
        JsonObject record = object("resource_id", identity.get("resource_id"), "amount", output.stackSize,
            "chance", known ? object("numerator", 1, "denominator", 1) : null,
            "native_output_semantics", known ? "copied_output_no_rng" : "declared_getter_template");
        if (identity.has("native_item")) record.add("native_item", identity.get("native_item"));
        if (identity.get("resource_id").isJsonNull()) unresolved(conditions, false, true);
        return record;
    }

    private void captureRunicAltar(String version) throws IOException {
        Map<String, Integer> classes = new LinkedHashMap<>();
        int index = 0;
        int interpreted = 0;
        int unresolvedInputs = 0;
        int unresolvedOutputs = 0;
        int errors = 0;
        for (RecipeRuneAltar recipe : new ArrayList<>(BotaniaAPI.runeAltarRecipes)) {
            String nativeClass = recipe == null ? null : recipe.getClass().getName();
            classes.merge(nativeClass == null ? "null" : nativeClass, 1, Integer::sum);
            JsonObject conditions = object("native_class", nativeClass, "native_version", version);
            JsonArray inputs = new JsonArray();
            JsonArray outputs = new JsonArray();
            Boolean executable = null;
            try {
                RuneDeclaration declaration = runeDeclaration(recipe, version);
                conditions = declaration.conditions;
                if (declaration.known) {
                    JsonArray nativeInputs = new JsonArray();
                    for (Object input : declaration.inputs) {
                        JsonObject slot = runeInput(input, nativeInputs.size(), conditions);
                        nativeInputs.add(slot);
                        if (slot.has("role") && slot.getAsJsonArray("choices").size() != 0) inputs.add(slot);
                    }
                    conditions.add("native_inputs", nativeInputs);
                    JsonObject livingrock = capture.itemSlot(new ItemStack[]{new ItemStack(ModBlocks.livingrock, 1,
                        OreDictionary.WILDCARD_VALUE)}, -1, false, false);
                    livingrock.addProperty("role", "consume");
                    livingrock.addProperty("native_origin", "controller_completion_dropped_livingrock");
                    for (JsonElement value : livingrock.getAsJsonArray("choices")) {
                        JsonObject choice = value.getAsJsonObject();
                        choice.addProperty("amount", 1);
                        if (choice.get("resource_id").isJsonNull()) conditions.addProperty("dynamic_inputs", "unresolved_livingrock_identity");
                    }
                    conditions.add("native_controller_input", livingrock);
                    inputs.add(livingrock);
                    if (declaration.output == null) {
                        conditions.addProperty("dynamic_output", "missing_native_output");
                    } else outputs.add(output(declaration.output, true, conditions));
                    if (!conditions.has("dynamic_inputs") && !conditions.has("dynamic_output")) {
                        executable = declaration.inputs.size() <= 16 && declaration.mana > 0;
                        if (!executable) conditions.addProperty("native_nonexecutable_reason",
                            declaration.mana <= 0 ? "completion_requires_positive_mana_demand" : "more_than_sixteen_ingredient_occurrences");
                    }
                }
            } catch (RuntimeException error) {
                errors++;
                conditions.addProperty("dynamic_inputs", "native_declaration_capture_failed");
                conditions.addProperty("dynamic_output", "native_declaration_capture_failed");
                conditions.add("capture_error", object("phase", "native_runic_altar_declarations", "class", error.getClass().getName(),
                    "message", error.getMessage()));
            }
            if (conditions.has("dynamic_inputs")) {
                unresolvedInputs++;
                inputs = new JsonArray();
            }
            if (conditions.has("dynamic_output")) unresolvedOutputs++;
            if (Boolean.TRUE.equals(executable)) interpreted++;
            capture.emitProcess("botania:runic_altar", "Botania Runic Altar", inputs, outputs, null, null, null,
                executable, conditions, object("owner", "BotaniaAPI.runeAltarRecipes", "index", index++,
                    "native_class", nativeClass, "native_version", version, "selection", "active_list_order"));
        }
        capture.coverage("botania:runic_altar", runeVersionKnown(version) ? "partial" : "unsupported", index,
            "Exact base material declarations only for verified Botania 1.13.38-GTNH and 1.13.39-GTNH. Mana delivery, wand activation, inventory matching and list priority remain runtime requirements",
            object("native_version", version, "native_recipe_classes", classes, "interpreted_records", interpreted,
                "unresolved_input_records", unresolvedInputs, "unresolved_output_records", unresolvedOutputs, "capture_errors", errors));
    }

    private JsonObject runeInput(Object declared, int index, JsonObject conditions) throws IOException {
        ItemStack[] stacks = new ItemStack[0];
        int oreId = -1;
        boolean direct = declared instanceof ItemStack;
        if (direct) stacks = new ItemStack[]{(ItemStack) declared};
        else if (declared instanceof String && OreDictionary.doesOreNameExist((String) declared)) {
            oreId = OreDictionary.getOreID((String) declared);
            stacks = OreDictionary.getOres((String) declared).toArray(new ItemStack[0]);
        }
        JsonObject slot = capture.itemSlot(stacks, oreId, false, false);
        slot.remove("role");
        slot.addProperty("native_slot", index);
        slot.addProperty("native_input_class", declared == null ? null : declared.getClass().getName());
        if (declared instanceof String) slot.addProperty("native_input_ore", (String) declared);
        boolean retained = false;
        boolean consumed = false;
        JsonArray choices = slot.getAsJsonArray("choices");
        int choiceIndex = 0;
        for (ItemStack stack : stacks) {
            if (stack == null) {
                conditions.addProperty("dynamic_inputs", "null_native_ore_member");
                continue;
            }
            boolean returned = stack.getItem() == ModItems.rune;
            retained |= returned;
            consumed |= !returned;
            JsonObject choice = choices.get(choiceIndex++).getAsJsonObject();
            choice.addProperty("amount", 1);
            choice.addProperty("native_return_semantics", returned ? "same_selected_stack_copied" : "consumed_without_container_return");
            if (choice.get("resource_id").isJsonNull()) conditions.addProperty("dynamic_inputs", "unregistered_native_input");
            else if (direct) choice.add("match", object("mode", "exact", "nbt_sensitive", false));
            else if (!choice.getAsJsonObject("match").has("group_id")) conditions.addProperty("dynamic_inputs", "unresolved_native_ore_group");
        }
        if (choices.size() == 0) conditions.addProperty("dynamic_inputs", "empty_or_unsupported_native_input");
        else if (retained && consumed) conditions.addProperty("dynamic_inputs", "choice_dependent_rune_return");
        else slot.addProperty("role", retained ? "presence" : "consume");
        return slot;
    }

    private static boolean runeVersionKnown(String version) {
        return "1.13.38-GTNH".equals(version) || "1.13.39-GTNH".equals(version);
    }

    /** Reads only verified passive base getters. Custom matchers and outputs may mutate live state. */
    static RuneDeclaration runeDeclaration(RecipeRuneAltar recipe, String version) {
        JsonObject conditions = object("native_class", recipe == null ? null : recipe.getClass().getName(), "native_version", version);
        String reason = !runeVersionKnown(version) ? "unsupported_native_version" : recipe == null ? "null_native_recipe"
            : recipe.getClass() != RecipeRuneAltar.class ? "uninterpreted_native_subclass" : null;
        if (reason != null) {
            conditions.addProperty("dynamic_inputs", reason);
            conditions.addProperty("dynamic_output", reason);
            return new RuneDeclaration(false, Collections.emptyList(), null, 0, conditions);
        }
        int mana = recipe.getManaUsage();
        conditions.addProperty("native_semantics_basis", "verified_1.13.38_1.13.39_narrow_class_equivalence");
        conditions.addProperty("total_mana", mana);
        conditions.addProperty("energy_unit", "mana");
        conditions.addProperty("effective_duration", "mana_delivery_and_activation_runtime_unknown");
        conditions.addProperty("post_success_cooldown_ticks", 60);
        conditions.addProperty("selection", "first_matching_recipe_in_active_list_order");
        conditions.addProperty("inventory_matching", "greedy_contiguous_prefix_one_item_per_occurrence");
        conditions.addProperty("rune_accounting", "survival_literal_ModItems.rune_returned_as_same_selected_stack");
        conditions.add("runtime_gates", object("available_mana", "positive_demand_and_at_least_total_mana",
            "activation", "wand_interaction_and_live_dropped_livingrock_in_altar_aabb", "wand_consumed", false,
            "wand_wear", "none_in_altar_callback", "inventory_capacity", 16, "inventory_stack_limit", 1,
            "admission", "native_addItem_and_inventory_rules", "creative_execution", "outside_material_projection_scope"));
        return new RuneDeclaration(true, recipe.getInputs(), recipe.getOutput(), mana, conditions);
    }

    static final class RuneDeclaration {
        final boolean known;
        final List<Object> inputs;
        final ItemStack output;
        final int mana;
        final JsonObject conditions;

        RuneDeclaration(boolean known, List<Object> inputs, ItemStack output, int mana, JsonObject conditions) {
            this.known = known;
            this.inputs = inputs;
            this.output = output;
            this.mana = mana;
            this.conditions = conditions;
        }
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
