package dev.gtnh.data;

import static dev.gtnh.data.Jsons.object;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import cpw.mods.fml.common.Loader;
import cpw.mods.fml.relauncher.ReflectionHelper;
import fox.spiteful.avaritia.crafting.ExtremeCraftingManager;
import fox.spiteful.avaritia.crafting.ExtremeShapedOreRecipe;
import fox.spiteful.avaritia.crafting.ExtremeShapedRecipe;
import fox.spiteful.avaritia.crafting.ExtremeShapelessRecipe;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import net.minecraft.item.ItemStack;
import net.minecraft.item.crafting.IRecipe;
import net.minecraftforge.oredict.ShapelessOreRecipe;

/** Captures the separate Extreme Crafting registry without executing native recipes. */
final class AvaritiaCapture {
    private final NativeCapture capture;

    AvaritiaCapture(NativeCapture capture) { this.capture = capture; }

    void capture() throws IOException {
        String version = Loader.instance().getIndexedModList().get("Avaritia").getVersion();
        if (!"1.100".equals(version)) {
            capture.coverage("avaritia.extreme_crafting", "unsupported", 0,
                "Native recipe API is verified only for Avaritia 1.100", object("native_version", version));
            return;
        }
        int index = 0;
        int interpreted = 0;
        for (IRecipe recipe : new ArrayList<>(ExtremeCraftingManager.getInstance().getRecipeList())) {
            Declaration declaration = declaration(recipe, version);
            JsonArray inputs = new JsonArray();
            boolean complete = declaration.known;
            int slot = 0;
            for (Object ingredient : declaration.inputs) {
                if (ingredient != null) {
                    List<ItemStack> choices = new ArrayList<>();
                    if (ingredient instanceof ItemStack stack) choices.add(stack);
                    else if (ingredient instanceof List<?> alternatives) {
                        for (Object alternative : alternatives) {
                            if (alternative instanceof ItemStack stack) choices.add(stack);
                            else complete = false;
                        }
                    } else complete = false;
                    JsonArray serialized = new JsonArray();
                    for (ItemStack choice : choices) {
                        ItemStack normalized = choice.copy();
                        normalized.stackSize = 1;
                        boolean nbt = !(ingredient instanceof List<?>) && !declaration.forgeShapeless
                            && choice.hasTagCompound();
                        JsonObject record = capture.itemSlot(new ItemStack[] {normalized}, -1, nbt, false)
                            .getAsJsonArray("choices").get(0).getAsJsonObject();
                        record.addProperty("declared_stack_size", choice.stackSize);
                        serialized.add(record);
                    }
                    if (serialized.size() == 0) complete = false;
                    inputs.add(object("role", "consume", "native_slot", slot, "choices", serialized));
                }
                slot++;
            }
            JsonArray outputs = new JsonArray();
            if (declaration.output != null && declaration.output.stackSize > 0) {
                outputs.add(object("resource_id", capture.item(declaration.output),
                    "amount", declaration.output.stackSize, "chance", object("numerator", 1, "denominator", 1)));
            } else complete = false;
            declaration.conditions.addProperty("declared_inputs", complete ? "captured" : "unresolved");
            if (!complete) declaration.conditions.addProperty("dynamic_inputs", "unresolved");
            if (complete) interpreted++;
            capture.emitProcess("avaritia:extreme_crafting", "Extreme Crafting", inputs, outputs,
                null, null, null, null, declaration.conditions,
                object("owner", "ExtremeCraftingManager", "index", index++));
        }
        capture.coverage("avaritia.extreme_crafting", "partial", index,
            "All registered declarations catalogued. Exact 1.100 recipe classes interpreted. Native precedence, repair and container accounting unresolved",
            object("native_version", version, "interpreted_declarations", interpreted));
    }

    static Declaration declaration(IRecipe recipe, String version) {
        JsonObject conditions = object("native_class", recipe == null ? null : recipe.getClass().getName(),
            "native_version", version, "grid_width", 9, "grid_height", 9,
            "container_returns", "native_unknown", "input_accounting", "one_item_per_occupied_slot",
            "native_precedence", "first_match_and_two_item_repair_unresolved",
            "recipe_voltage_applicability", "not_applicable_crafting_grid");
        List<?> inputs = Collections.emptyList();
        boolean known = false;
        boolean forgeShapeless = false;
        if (recipe != null && "1.100".equals(version)) {
            if (recipe.getClass() == ExtremeShapedRecipe.class) {
                ExtremeShapedRecipe shaped = (ExtremeShapedRecipe) recipe;
                inputs = Arrays.asList(shaped.recipeItems);
                shape(conditions, shaped.recipeWidth, shaped.recipeHeight, true);
                known = true;
            } else if (recipe.getClass() == ExtremeShapedOreRecipe.class) {
                ExtremeShapedOreRecipe shaped = (ExtremeShapedOreRecipe) recipe;
                inputs = Arrays.asList(shaped.getInput());
                boolean mirrored = ReflectionHelper.getPrivateValue(ExtremeShapedOreRecipe.class, shaped, "mirrored");
                shape(conditions, shaped.width, shaped.height, mirrored);
                known = true;
            } else if (recipe.getClass() == ExtremeShapelessRecipe.class) {
                inputs = ((ExtremeShapelessRecipe) recipe).recipeItems;
                conditions.addProperty("layout", "shapeless");
                known = true;
            } else if (recipe.getClass() == ShapelessOreRecipe.class) {
                inputs = ((ShapelessOreRecipe) recipe).getInput();
                conditions.addProperty("layout", "shapeless");
                known = true;
                forgeShapeless = true;
            }
        }
        ItemStack output = known ? recipe.getRecipeOutput() : null;
        conditions.addProperty("native_slot_count", inputs.size());
        conditions.addProperty("matching", !known ? "unresolved" : forgeShapeless ? "forge_ore_nbt_ignored"
            : "direct_stack_conditional_nbt_ore_alternatives_ignore_nbt");
        if (!known) {
            conditions.addProperty("dynamic_inputs", "unresolved");
            conditions.addProperty("dynamic_output", "unresolved");
        }
        return new Declaration(known, new ArrayList<>(inputs), output, conditions, forgeShapeless);
    }

    private static void shape(JsonObject conditions, int width, int height, boolean mirrored) {
        conditions.addProperty("layout", "shaped");
        conditions.addProperty("width", width);
        conditions.addProperty("height", height);
        conditions.addProperty("mirrored", mirrored);
        conditions.addProperty("translation", "within_9x9_grid_empty_outside_shape");
    }

    static final class Declaration {
        final boolean known;
        final List<?> inputs;
        final ItemStack output;
        final JsonObject conditions;
        final boolean forgeShapeless;

        Declaration(boolean known, List<?> inputs, ItemStack output, JsonObject conditions, boolean forgeShapeless) {
            this.known = known;
            this.inputs = inputs;
            this.output = output;
            this.conditions = conditions;
            this.forgeShapeless = forgeShapeless;
        }
    }
}
