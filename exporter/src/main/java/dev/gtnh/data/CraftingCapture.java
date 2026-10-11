package dev.gtnh.data;

import static dev.gtnh.data.Jsons.object;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import gregtech.api.util.GTShapedRecipe;
import gregtech.api.util.GTShapelessRecipe;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
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
                known = false;
                conditions.addProperty("declared_inputs", "captured");
                conditions.addProperty("dynamic_output", "unresolved");
                conditions.add("output_transformations", object("status", "uninterpreted",
                    "native_item_update", "unresolved", "electric_charge_transfer", "unresolved",
                    "configured_enchantments", "unresolved"));
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
                    "chance", gtTemplate ? null : object("numerator", 1, "denominator", 1));
                if (gtTemplate) record.addProperty("native_template", true);
                outputs.add(record);
            }
            else { known = false; conditions.addProperty("dynamic_output", "unresolved"); }
            capture.emitProcess("minecraft:crafting", "Crafting", inputs, outputs, null, null, null,
                known ? Boolean.TRUE : null, conditions, object("owner", "CraftingManager", "index", count));
            count++;
        }
        capture.coverage("minecraft.crafting", "partial", count,
            "All IRecipe records catalogued. Native vanilla/Forge recipes interpreted, exact GT declared inputs captured, dynamic GT matching/output and other subclasses unresolved");
        capture.coverage("minecraft.crafting.gt_shaped_declared", "partial", gtShaped,
            "Exact GTShapedRecipe inherited declared slots captured. Keeping-NBT correlation and runtime output transformations are not evaluated");
        capture.coverage("minecraft.crafting.gt_shapeless_declared", "partial", gtShapeless,
            "Exact GTShapelessRecipe inherited declared slots captured. Private inventory validator, NBT behavior and runtime output transformations remain unresolved");
    }
}
