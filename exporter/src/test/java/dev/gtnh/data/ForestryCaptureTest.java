package dev.gtnh.data;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

import com.google.gson.JsonObject;
import forestry.api.recipes.ICarpenterRecipe;
import forestry.api.recipes.IDescriptiveRecipe;
import forestry.core.recipes.ShapedRecipeCustom;
import forestry.factory.recipes.CarpenterRecipe;
import java.util.Arrays;
import java.util.List;
import net.minecraft.item.Item;
import net.minecraft.item.ItemStack;
import net.minecraft.nbt.NBTTagCompound;
import net.minecraftforge.fluids.FluidStack;
import org.junit.Test;

public class ForestryCaptureTest {
    @Test
    public void carpenterDeclarationsRetainPatternCountsNbtAndPackaging() {
        ItemStack ingredient = new ItemStack(new Item(), 7, 32767);
        ingredient.setTagCompound(new NBTTagCompound());
        ingredient.getTagCompound().setByte("grade", (byte) 2);
        ItemStack output = new ItemStack(new Item(), 4, 3);
        output.setTagCompound(new NBTTagCompound());
        output.getTagCompound().setString("owner", "native");
        ItemStack box = new ItemStack(new Item(), 8, 1);
        // Fluid-bearing declarations need Forge's initialized registry and remain a runtime acceptance check.
        ShapedRecipeCustom grid = new ShapedRecipeCustom(output, "AA", " A", 'A', ingredient);
        List<Object> alternatives = Arrays.asList(ingredient, Arrays.asList(ingredient.copy(), ingredient.copy()));
        grid.getIngredients()[1] = alternatives;
        ForestryCapture.CarpenterDeclaration declaration = ForestryCapture.carpenterDeclaration(
            new CarpenterRecipe(12, null, box, grid), "4.11.39");
        assertTrue(declaration.known);
        assertEquals(2, declaration.width);
        assertEquals(2, declaration.height);
        assertEquals(4, declaration.ingredients.length);
        assertNull(declaration.ingredients[2]);
        assertEquals(7, ((ItemStack) declaration.ingredients[0]).stackSize);
        assertEquals(32767, ((ItemStack) declaration.ingredients[0]).getItemDamage());
        assertEquals(2, ((ItemStack) declaration.ingredients[0]).getTagCompound().getByte("grade"));
        assertEquals(alternatives, declaration.ingredients[1]);
        assertEquals(8, declaration.box.stackSize);
        assertEquals(4, declaration.output.stackSize);
        assertEquals("native", declaration.output.getTagCompound().getString("owner"));
        assertEquals(12, declaration.conditions.get("native_processing_time").getAsInt());
        assertEquals("declaration_only_not_complete_material_transaction",
            declaration.conditions.get("material_projection").getAsString());
        assertEquals("unresolved", declaration.conditions.get("dynamic_inputs").getAsString());
        assertFalse(declaration.conditions.has("dynamic_output"));
    }

    @Test
    public void carpenterUnknownOuterAndInnerClassesNeverProbeTheirOverrides() {
        ICarpenterRecipe unsafe = new ICarpenterRecipe() {
            @Override public int getPackagingTime() { throw new AssertionError("time getter called"); }
            @Override public ItemStack getBox() { throw new AssertionError("box getter called"); }
            @Override public FluidStack getFluidResource() { throw new AssertionError("fluid getter called"); }
            @Override public IDescriptiveRecipe getCraftingGridRecipe() { throw new AssertionError("grid getter called"); }
        };
        ItemStack output = new ItemStack(new Item(), 1, 0);
        CarpenterRecipe unsafeOuter = new CarpenterRecipe(1, null, null, null) {
            @Override public int getPackagingTime() { throw new AssertionError("subclass time getter called"); }
            @Override public ItemStack getBox() { throw new AssertionError("subclass box getter called"); }
            @Override public FluidStack getFluidResource() { throw new AssertionError("subclass fluid getter called"); }
            @Override public IDescriptiveRecipe getCraftingGridRecipe() { throw new AssertionError("subclass grid getter called"); }
        };
        ShapedRecipeCustom unsafeGrid = new ShapedRecipeCustom(output, "A", 'A', new Item()) {
            @Override public int getWidth() { throw new AssertionError("width getter called"); }
            @Override public int getHeight() { throw new AssertionError("height getter called"); }
            @Override public Object[] getIngredients() { throw new AssertionError("ingredients getter called"); }
            @Override public ItemStack getRecipeOutput() { throw new AssertionError("output getter called"); }
        };
        for (ICarpenterRecipe recipe : Arrays.asList(unsafe, unsafeOuter, new CarpenterRecipe(1, null, null, unsafeGrid), null)) {
            ForestryCapture.CarpenterDeclaration declaration = ForestryCapture.carpenterDeclaration(recipe, "4.11.39");
            assertFalse(declaration.known);
            assertNull(declaration.ingredients);
            assertNull(declaration.output);
            assertTrue(declaration.conditions.has("dynamic_output"));
        }
        ForestryCapture.CarpenterDeclaration unchecked = ForestryCapture.carpenterDeclaration(unsafe, "4.11.40");
        assertEquals("unsupported_native_version", unchecked.conditions.get("declaration_status").getAsString());
        assertNull(unchecked.output);
    }

    @Test
    public void carpenterAbsentPackagingAndFluidAreNotInventedRequirements() {
        ShapedRecipeCustom grid = new ShapedRecipeCustom(new ItemStack(new Item()), "A", 'A', new Item());
        ForestryCapture.CarpenterDeclaration declaration = ForestryCapture.carpenterDeclaration(
            new CarpenterRecipe(0, null, null, grid), "4.11.39");
        assertTrue(declaration.known);
        assertNull(declaration.box);
        assertNull(declaration.fluid);
        assertEquals(0, declaration.conditions.get("native_processing_time").getAsInt());
        assertEquals("machine_owned_unknown", declaration.conditions.get("effective_duration").getAsString());
        assertEquals("unresolved_selected_item_callbacks",
            declaration.conditions.get("container_returns").getAsString());
    }

    @Test
    public void separateFloatRollsUseStrictThresholdsIncludingZeroAndTinyPositiveChance() {
        assertChance(0f, 0, 16777216);
        assertChance(-0.0f, 0, 16777216);
        assertChance(Float.MIN_VALUE, 1, 16777216);
        assertChance(0.5f, 8388608, 16777216);
        assertChance(Math.nextDown(1f), 16777215, 16777216);
        assertChance(1f, 1, 1);
        assertChance(2f, 1, 1);
        assertChance(-0.5f, 0, 1);
        assertNull(NativeCapture.floatRollChance(Float.NaN, false));
        assertNull(NativeCapture.floatRollChance(Float.POSITIVE_INFINITY, false));
        assertNull(NativeCapture.floatRollChance(Float.NEGATIVE_INFINITY, false));
    }

    private void assertChance(float threshold, long numerator, long denominator) {
        JsonObject actual = NativeCapture.floatRollChance(threshold, false);
        assertEquals(numerator, actual.get("numerator").getAsLong());
        assertEquals(denominator, actual.get("denominator").getAsLong());
    }
}
