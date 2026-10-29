package dev.gtnh.data;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

import fox.spiteful.avaritia.crafting.ExtremeShapedOreRecipe;
import fox.spiteful.avaritia.crafting.ExtremeShapedRecipe;
import fox.spiteful.avaritia.crafting.ExtremeShapelessRecipe;
import java.util.Arrays;
import java.util.Collections;
import net.minecraft.item.Item;
import net.minecraft.item.ItemStack;
import net.minecraftforge.oredict.ShapelessOreRecipe;
import org.junit.Test;

public class AvaritiaCaptureTest {
    @Test
    public void shapedDeclarationsRetainGridHolesAndDeclaredAmounts() {
        ItemStack input = new ItemStack(new Item(), 64, 0);
        ItemStack output = new ItemStack(new Item(), 3, 0);
        AvaritiaCapture.Declaration declaration = AvaritiaCapture.declaration(
            new ExtremeShapedRecipe(2, 2, new ItemStack[] {input, null, null, input}, output), "1.100");
        assertTrue(declaration.known);
        assertEquals(4, declaration.inputs.size());
        assertNull(declaration.inputs.get(1));
        assertEquals(64, ((ItemStack) declaration.inputs.get(3)).stackSize);
        assertEquals(3, declaration.output.stackSize);
        assertEquals(2, declaration.conditions.get("width").getAsInt());
        assertEquals(2, declaration.conditions.get("height").getAsInt());
        assertTrue(declaration.conditions.get("mirrored").getAsBoolean());
    }

    @Test
    public void oreShapeRetainsMirroringAndShapelessRetainsOccurrences() {
        ItemStack input = new ItemStack(new Item(), 1, 0);
        ItemStack output = new ItemStack(new Item(), 1, 0);
        ExtremeShapedOreRecipe shaped = new ExtremeShapedOreRecipe(output, "PP", 'P', input).setMirrored(false);
        AvaritiaCapture.Declaration declaration = AvaritiaCapture.declaration(shaped, "1.100");
        assertEquals(2, declaration.inputs.size());
        assertFalse(declaration.conditions.get("mirrored").getAsBoolean());
        declaration = AvaritiaCapture.declaration(new ExtremeShapelessRecipe(output, Arrays.asList(input, input)), "1.100");
        assertEquals(2, declaration.inputs.size());
        assertEquals("shapeless", declaration.conditions.get("layout").getAsString());
    }

    @Test
    public void unknownSubclassesAndVersionsNeverProbeNativeOverrides() {
        ExtremeShapelessRecipe custom = new ExtremeShapelessRecipe(null, Collections.emptyList()) {
            @Override public ItemStack getRecipeOutput() { throw new AssertionError("unexpected native call"); }
        };
        assertFalse(AvaritiaCapture.declaration(custom, "1.100").known);
        assertFalse(AvaritiaCapture.declaration(custom, "1.101").known);
        assertNull(AvaritiaCapture.declaration(custom, "1.100").output);
    }

    @Test
    public void forgeShapelessOreRegistryEntriesAreCapturedWithTheirOwnMatchingPolicy() {
        ItemStack input = new ItemStack(new Item(), 1, 0);
        ItemStack output = new ItemStack(new Item(), 2, 0);
        AvaritiaCapture.Declaration declaration = AvaritiaCapture.declaration(
            new ShapelessOreRecipe(output, input, input), "1.100");
        assertTrue(declaration.known);
        assertEquals(2, declaration.inputs.size());
        assertEquals("forge_ore_nbt_ignored", declaration.conditions.get("matching").getAsString());
        assertEquals(2, declaration.output.stackSize);
    }
}
