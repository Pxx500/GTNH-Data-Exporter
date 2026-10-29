package dev.gtnh.data;

import static dev.gtnh.data.Jsons.object;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import cpw.mods.fml.relauncher.ReflectionHelper;
import gregtech.api.items.GTGenericItem;
import gregtech.api.items.MetaBaseItem;
import gregtech.api.util.GTShapedRecipe;
import gregtech.api.util.GTShapelessRecipe;
import ic2.api.item.IElectricItem;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Map;
import net.minecraft.enchantment.Enchantment;
import net.minecraft.item.Item;
import net.minecraft.item.ItemStack;
import net.minecraft.item.crafting.CraftingManager;
import net.minecraft.item.crafting.IRecipe;
import net.minecraft.item.crafting.ShapedRecipes;
import net.minecraft.item.crafting.ShapelessRecipes;
import net.minecraftforge.oredict.ShapedOreRecipe;
import net.minecraftforge.oredict.ShapelessOreRecipe;

/**
 * Captures a declared native crafting catalog without evaluating inventories.
 * Native dispatch originally adapted from Calculation Oracle, Copyright (c) 2026 Samiracle64.
 * The MIT notice is retained in exporter/THIRD_PARTY_NOTICES.md.
 */
final class CraftingCapture {
    private final NativeCapture capture;

    CraftingCapture(NativeCapture capture) { this.capture = capture; }

    /** Resolves only declarations whose native output transformations are proven no-ops. */
    static boolean hasStaticOutput(IRecipe recipe) {
        return "static".equals(outputDecision(recipe).get("status").getAsString());
    }

    private static JsonObject outputDecision(IRecipe recipe) {
        JsonObject decision = object("status", "uninterpreted", "native_item_update", "unresolved",
            "electric_charge_transfer", "unresolved", "configured_enchantments", "unresolved");
        String reason = outputRejection(recipe, decision);
        if (reason == null) {
            decision.addProperty("status", "static");
            decision.addProperty("native_item_update", "verified_no_op");
            decision.addProperty("electric_charge_transfer", "not_applicable");
            decision.addProperty("configured_enchantments", "none");
        }
        decision.addProperty("reason", reason == null ? "verified_no_output_transformations" : reason);
        return decision;
    }

    private static String outputRejection(IRecipe recipe, JsonObject decision) {
        boolean keepingNBT;
        boolean overwriteNBT = false;
        Enchantment[] enchantments;
        JsonObject flags = object("native_class", recipe.getClass().getName());
        decision.add("native_flags", flags);
        if (recipe.getClass() == GTShapedRecipe.class) {
            GTShapedRecipe shaped = (GTShapedRecipe) recipe;
            keepingNBT = shaped.mKeepingNBT;
            enchantments = ReflectionHelper.getPrivateValue(GTShapedRecipe.class, shaped, "mEnchantmentsAdded");
            flags.addProperty("validator_interpretation", "not_applicable");
        } else if (recipe.getClass() == GTShapelessRecipe.class) {
            GTShapelessRecipe shapeless = (GTShapelessRecipe) recipe;
            keepingNBT = shapeless.mKeepingNBT;
            overwriteNBT = shapeless.overwriteNBT;
            enchantments = ReflectionHelper.getPrivateValue(GTShapelessRecipe.class, shapeless, "mEnchantmentsAdded");
            flags.addProperty("validator_present",
                ReflectionHelper.getPrivateValue(GTShapelessRecipe.class, shapeless, "mInputValidator") != null);
            flags.addProperty("validator_interpretation", "unresolved");
        } else return "unsupported_native_class";
        flags.addProperty("keeping_nbt", keepingNBT);
        flags.addProperty("overwrite_nbt", overwriteNBT);
        flags.addProperty("configured_enchantments_present", enchantments != null);
        flags.addProperty("configured_enchantment_count", enchantments == null ? 0 : enchantments.length);
        ItemStack output = recipe.getRecipeOutput();
        flags.addProperty("declared_output_present", output != null);
        if (output != null) {
            flags.addProperty("declared_output_stack_size", output.stackSize);
            flags.addProperty("declared_output_has_nbt", output.hasTagCompound());
        }
        if (keepingNBT) return "keeping_nbt";
        if (overwriteNBT) return "overwrite_nbt";
        if (output == null || output.stackSize <= 0) return "missing_or_nonpositive_output";
        if (output.hasTagCompound()) return "tagged_output";
        if (enchantments != null) return "configured_enchantments";
        Item item = output.getItem();
        if (item == null) return "missing_output_item";
        if (item instanceof IElectricItem electric && electric.getTier(output.copy()) < Integer.MAX_VALUE)
            return "electric_charge_transfer";
        if (!(item instanceof GTGenericItem)) return null;
        try {
            Class<?> updateOwner = item.getClass().getMethod("isItemStackUsable", ItemStack.class).getDeclaringClass();
            if (updateOwner == GTGenericItem.class) return null;
            if (updateOwner == MetaBaseItem.class && item instanceof MetaBaseItem base
                && base.mapEachBehavior(output, behavior -> Boolean.TRUE).isEmpty()) return null;
            return "native_item_update";
        } catch (NoSuchMethodException unknownUpdate) {
            return "unknown_native_item_update";
        }
    }

    static JsonObject outputConditions(IRecipe recipe) {
        JsonObject decision = outputDecision(recipe);
        boolean certain = "static".equals(decision.get("status").getAsString());
        JsonObject evidence = object("reason", decision.remove("reason"),
            "native_flags", decision.remove("native_flags"));
        JsonObject conditions = object("dynamic_output", certain ? "resolved_static" : "unresolved",
            "output_transformations", decision, "native_output_evidence", evidence);
        if (recipe.getClass() == GTShapelessRecipe.class) conditions.addProperty("dynamic_inputs", "unresolved");
        if (certain) {
            conditions.addProperty("recipe_voltage_applicability", "not_applicable_crafting_grid");
            conditions.addProperty("tool_accounting", "container_damage_and_breakage_unresolved");
            conditions.addProperty("input_accounting", "declared_consumption_without_container_return_credit");
        }
        return conditions;
    }

    void capture() throws IOException {
        List<IRecipe> recipes = CraftingManager.getInstance().getRecipeList();
        long count = 0;
        long gtShaped = 0;
        long gtShapeless = 0;
        for (IRecipe recipe : new ArrayList<>(recipes)) {
            JsonArray inputs = new JsonArray();
            Iterable<?> raw = null;
            JsonObject conditions = object("native_class", recipe.getClass().getName(), "container_returns", "native_unknown");
            boolean known = true;
            boolean gtTemplate = false;
            boolean staticGtOutput = false;
            boolean nativeMatchingUnknown = false;
            if (recipe.getClass() == ShapedRecipes.class) {
                ShapedRecipes shaped = (ShapedRecipes) recipe;
                raw = Arrays.asList(shaped.recipeItems);
                conditions.addProperty("width", shaped.recipeWidth);
                conditions.addProperty("height", shaped.recipeHeight);
            } else if (recipe.getClass() == ShapelessRecipes.class) raw = ((ShapelessRecipes) recipe).recipeItems;
            else if (recipe.getClass() == ShapedOreRecipe.class) raw = Arrays.asList(((ShapedOreRecipe) recipe).getInput());
            else if (recipe.getClass() == ShapelessOreRecipe.class) raw = ((ShapelessOreRecipe) recipe).getInput();
            else if (recipe.getClass() == GTShapedRecipe.class) {
                GTShapedRecipe shaped = (GTShapedRecipe) recipe;
                raw = Arrays.asList(shaped.getInput());
                gtTemplate = true;
                nativeMatchingUnknown = shaped.mKeepingNBT;
                conditions.addProperty("keeping_nbt", shaped.mKeepingNBT);
                conditions.addProperty("removable_by_gt", shaped.mRemovableByGT);
                gtShaped++;
            } else if (recipe.getClass() == GTShapelessRecipe.class) {
                GTShapelessRecipe shapeless = (GTShapelessRecipe) recipe;
                raw = shapeless.getInput();
                gtTemplate = true;
                nativeMatchingUnknown = true;
                conditions.addProperty("keeping_nbt", shapeless.mKeepingNBT);
                conditions.addProperty("overwrite_nbt", shapeless.overwriteNBT);
                conditions.addProperty("removable_by_gt", shapeless.mRemovableByGT);
                conditions.addProperty("custom_inventory_validator", "native_unknown");
                gtShapeless++;
            }
            else { known = false; conditions.addProperty("dynamic_inputs", "unresolved"); }
            if (gtTemplate) {
                JsonObject outputConditions = outputConditions(recipe);
                staticGtOutput = "resolved_static".equals(outputConditions.get("dynamic_output").getAsString());
                  known = staticGtOutput && !nativeMatchingUnknown;
                conditions.addProperty("declared_inputs", "captured");
                for (Map.Entry<String, JsonElement> field : outputConditions.entrySet()) {
                    conditions.add(field.getKey(), field.getValue());
                }
                if (nativeMatchingUnknown) {
                    conditions.addProperty("dynamic_inputs", "unresolved");
                    conditions.addProperty("native_input_correlation", "uninterpreted");
                }
            }
            if (raw != null) {
                int slot = 0;
                for (Object value : raw) {
                    if (value != null) {
                        List<ItemStack> alternatives = new ArrayList<>();
                        if (value instanceof ItemStack) alternatives.add((ItemStack) value);
                        else if (value instanceof Iterable) for (Object alternative : (Iterable<?>) value)
                            if (alternative instanceof ItemStack) alternatives.add((ItemStack) alternative);
                        if (alternatives.isEmpty()) { known = false; conditions.addProperty("unknown_ingredient", String.valueOf(value)); }
                        else {
                            ItemStack[] normalized = new ItemStack[alternatives.size()];
                            for (int index = 0; index < normalized.length; index++) {
                                normalized[index] = alternatives.get(index).copy(); normalized[index].stackSize = 1;
                            }
                            JsonObject input = capture.itemSlot(normalized, -1, false, false);
                            if (gtTemplate) {
                                JsonArray choices = input.getAsJsonArray("choices");
                                for (int index = 0; index < choices.size(); index++) {
                                    JsonObject choice = choices.get(index).getAsJsonObject();
                                    choice.addProperty("declared_stack_size", alternatives.get(index).stackSize);
                                    if (nativeMatchingUnknown) {
                                        choice.add("declared_match", choice.getAsJsonObject("match"));
                                        choice.add("match", object("mode", "native_unknown"));
                                    }
                                }
                            }
                            input.addProperty("native_slot", slot); inputs.add(input);
                        }
                    }
                    slot++;
                }
            }
            JsonArray outputs = new JsonArray();
            ItemStack output = recipe.getRecipeOutput();
            if (output != null) {
                JsonObject record = object("resource_id", capture.item(output), "amount", output.stackSize,
                    "chance", gtTemplate && !staticGtOutput ? null : object("numerator", 1, "denominator", 1));
                if (gtTemplate && !staticGtOutput) record.addProperty("native_template", true);
                outputs.add(record);
            }
            else { known = false; conditions.addProperty("dynamic_output", "unresolved"); }
            capture.emitProcess("minecraft:crafting", "Crafting", inputs, outputs, null, null, null,
                known ? Boolean.TRUE : null, conditions, object("owner", "CraftingManager", "index", count));
            count++;
        }
        capture.coverage("minecraft.crafting", "partial", count,
            "All IRecipe records catalogued. Vanilla/Forge and verified static exact GT shaped outputs interpreted. Dynamic GT matching/output, container accounting and other subclasses unresolved");
        capture.coverage("minecraft.crafting.gt_shaped_declared", "partial", gtShaped,
            "Exact GTShapedRecipe declared slots captured. Non-NBT, non-electric outputs without configured enchantments or native update behaviors are static. Container and tool accounting remains unresolved");
        capture.coverage("minecraft.crafting.gt_shapeless_declared", "partial", gtShapeless,
              "Exact GTShapelessRecipe declared slots and output decision facts captured. Verified no-op output transformations are static. Private inventory validator and input matching remain unresolved");
    }
}
