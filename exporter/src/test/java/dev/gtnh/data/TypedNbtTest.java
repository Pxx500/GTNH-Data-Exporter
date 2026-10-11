package dev.gtnh.data;

import static org.junit.Assert.*;

import com.google.gson.JsonObject;
import net.minecraft.nbt.NBTTagCompound;
import net.minecraft.nbt.NBTTagInt;
import net.minecraft.nbt.NBTTagList;
import org.junit.Test;

public final class TypedNbtTest {
    @Test
    public void retainsNativeNumericTypesArraysListsAndExactLongs() {
        NBTTagCompound compound = new NBTTagCompound();
        compound.setByte("byte", (byte) -2);
        compound.setLong("uuid", Long.MAX_VALUE);
        compound.setByteArray("bytes", new byte[]{-128, 127});
        compound.setIntArray("ints", new int[]{-1, 2147483647});
        NBTTagList list = new NBTTagList(); list.appendTag(new NBTTagInt(7)); compound.setTag("list", list);
        JsonObject values = TypedNbt.encode(compound).getAsJsonObject().getAsJsonObject("value");
        assertEquals("byte", values.getAsJsonObject("byte").get("type").getAsString());
        assertEquals(-2, values.getAsJsonObject("byte").get("value").getAsInt());
        assertEquals("9223372036854775807", values.getAsJsonObject("uuid").get("value").getAsString());
        assertTrue(values.getAsJsonObject("uuid").get("value").getAsJsonPrimitive().isString());
        assertEquals(-128, values.getAsJsonObject("bytes").getAsJsonArray("value").get(0).getAsInt());
        assertEquals(2147483647, values.getAsJsonObject("ints").getAsJsonArray("value").get(1).getAsInt());
        assertEquals("int", values.getAsJsonObject("list").getAsJsonArray("value").get(0).getAsJsonObject().get("type").getAsString());
    }
}
