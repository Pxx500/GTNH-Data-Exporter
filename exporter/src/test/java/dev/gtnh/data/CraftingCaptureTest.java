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
        assertFalse(CraftingCapture.outputConditions(keepingNbt).has("recipe_voltage_applicability"));
        assertFalse(CraftingCapture.hasStaticOutput(new GTShapedRecipe(output, true, false,
            new Enchantment[] {null}, new int[] {1}, "P", 'P', input)));
        output.setTagCompound(new NBTTagCompound());
        assertFalse(CraftingCapture.hasStaticOutput(new GTShapedRecipe(output, true, false, null, null,
            "P", 'P', input)));
    }

    @Test
    public void customShapeAndShapelessValidatorsAreNotStaticDeclarations() {
        ItemStack output = new ItemStack(new Item(), 1, 0);
        ItemStack input = new ItemStack(new Item(), 1, 0);
        GTShapedRecipe custom = new GTShapedRecipe(output, true, false, null, null, "P", 'P', input) {
            @Override
            public ItemStack getRecipeOutput() { return output; }
        };
        assertFalse(CraftingCapture.hasStaticOutput(custom));
        assertFalse(CraftingCapture.hasStaticOutput(new GTShapelessRecipe(output, true, false, false,
            null, null, grid -> false, input)));
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
