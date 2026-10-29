package dev.gtnh.data;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import com.google.gson.JsonObject;
import gregtech.api.util.GTShapedRecipe;
import gregtech.api.util.GTShapelessRecipe;
import ic2.api.item.IElectricItem;
import net.minecraft.enchantment.Enchantment;
import net.minecraft.item.Item;
import net.minecraft.item.ItemStack;
import net.minecraft.item.crafting.IRecipe;
import net.minecraft.nbt.NBTTagCompound;
import org.junit.Test;

public class CraftingCaptureTest {
    @Test
    public void ordinaryGtShapedRecipeHasCertainOutputWithoutCraftingAnInventory() {
        ItemStack output = new ItemStack(new Item(), 1, 0);
        IRecipe recipe = new GTShapedRecipe(output, true, false, null, null,
            "PP", 'P', new ItemStack(new Item(), 1, 0));
        assertTrue(CraftingCapture.hasStaticOutput(recipe));
        JsonObject conditions = CraftingCapture.outputConditions(recipe);
        assertEquals("{\"status\":\"static\",\"native_item_update\":\"verified_no_op\","
            + "\"electric_charge_transfer\":\"not_applicable\",\"configured_enchantments\":\"none\"}",
            conditions.getAsJsonObject("output_transformations").toString());
        assertEquals("verified_no_output_transformations", conditions.getAsJsonObject("native_output_evidence")
            .get("reason").getAsString());
        assertFalse(conditions.getAsJsonObject("native_output_evidence").getAsJsonObject("native_flags")
            .get("keeping_nbt").getAsBoolean());
        assertEquals("not_applicable_crafting_grid", conditions.get("recipe_voltage_applicability").getAsString());
        assertEquals("container_damage_and_breakage_unresolved", conditions.get("tool_accounting").getAsString());
        assertFalse(conditions.has("eu_per_tick"));
    }

    @Test
    public void keepingNbtAndConfiguredEnchantmentsRemainDynamic() {
        ItemStack output = new ItemStack(new Item(), 1, 0);
        ItemStack input = new ItemStack(new Item(), 1, 0);
        IRecipe keepingNbt = new GTShapedRecipe(output, true, true, null, null, "P", 'P', input);
        assertFalse(CraftingCapture.hasStaticOutput(keepingNbt));
        JsonObject conditions = CraftingCapture.outputConditions(keepingNbt);
        assertFalse(conditions.has("recipe_voltage_applicability"));
        assertEquals("{\"status\":\"uninterpreted\",\"native_item_update\":\"unresolved\","
            + "\"electric_charge_transfer\":\"unresolved\",\"configured_enchantments\":\"unresolved\"}",
            conditions.getAsJsonObject("output_transformations").toString());
        assertEquals("keeping_nbt", conditions.getAsJsonObject("native_output_evidence").get("reason").getAsString());
        assertFalse(CraftingCapture.hasStaticOutput(new GTShapedRecipe(output, true, false,
            new Enchantment[] {null}, new int[] {1}, "P", 'P', input)));
        output.setTagCompound(new NBTTagCompound());
        assertFalse(CraftingCapture.hasStaticOutput(new GTShapedRecipe(output, true, false, null, null,
            "P", 'P', input)));
    }

    @Test
    public void customShapesAreNotStaticDeclarations() {
        ItemStack output = new ItemStack(new Item(), 1, 0);
        ItemStack input = new ItemStack(new Item(), 1, 0);
        GTShapedRecipe custom = new GTShapedRecipe(output, true, false, null, null, "P", 'P', input) {
            @Override
            public ItemStack getRecipeOutput() { return output; }
        };
        assertFalse(CraftingCapture.hasStaticOutput(custom));
    }

    @Test
    public void shapelessOutputCanBeStaticWhileItsValidatorRemainsUnresolved() {
        ItemStack output = new ItemStack(new Item(), 1, 0);
        IRecipe recipe = new GTShapelessRecipe(output, true, false, false, null, null,
            grid -> { throw new AssertionError("Capture must not execute the native validator"); },
            new ItemStack(new Item(), 1, 0));
        assertTrue(CraftingCapture.hasStaticOutput(recipe));
        JsonObject conditions = CraftingCapture.outputConditions(recipe);
        assertEquals("resolved_static", conditions.get("dynamic_output").getAsString());
        assertEquals("unresolved", conditions.get("dynamic_inputs").getAsString());
        JsonObject decision = conditions.getAsJsonObject("output_transformations");
        assertEquals("verified_no_op", decision.get("native_item_update").getAsString());
        assertTrue(conditions.getAsJsonObject("native_output_evidence").getAsJsonObject("native_flags")
            .get("validator_present").getAsBoolean());
    }

    @Test
    public void shapelessNbtAndElectricTransformationsKeepTheirReasons() {
        ItemStack input = new ItemStack(new Item(), 1, 0);
        ItemStack output = new ItemStack(new Item(), 1, 0);
        IRecipe overwrite = new GTShapelessRecipe(output, true, false, true, null, null, input);
        assertFalse(CraftingCapture.hasStaticOutput(overwrite));
        assertEquals("overwrite_nbt", CraftingCapture.outputConditions(overwrite)
            .getAsJsonObject("native_output_evidence").get("reason").getAsString());
        assertFalse(CraftingCapture.hasStaticOutput(new GTShapelessRecipe(output, true, true, false,
            null, null, input)));
        assertFalse(CraftingCapture.hasStaticOutput(new GTShapelessRecipe(output, true, false, false,
            new Enchantment[] {null}, new int[] {1}, input)));
        assertFalse(CraftingCapture.hasStaticOutput(new GTShapelessRecipe(new ItemStack(new ElectricOutput()),
            true, false, false, null, null, input)));
    }

    @Test
    public void electricOutputChargeTransferRemainsUnresolved() {
        ItemStack output = new ItemStack(new ElectricOutput(), 1, 0);
        assertFalse(CraftingCapture.hasStaticOutput(new GTShapedRecipe(output, true, false, null, null,
            "P", 'P', new ItemStack(new Item(), 1, 0))));
    }

    private static final class ElectricOutput extends Item implements IElectricItem {
        @Override
        public boolean canProvideEnergy(ItemStack stack) { return false; }
        @Override
        public Item getChargedItem(ItemStack stack) { return this; }
        @Override
        public Item getEmptyItem(ItemStack stack) { return this; }
        @Override
        public double getMaxCharge(ItemStack stack) { return 1; }
        @Override
        public int getTier(ItemStack stack) { return 1; }
        @Override
        public double getTransferLimit(ItemStack stack) { return 1; }
    }
}
