package dev.gtnh.data;

import static org.junit.Assert.*;

import com.google.gson.JsonElement;
import com.google.gson.JsonNull;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import net.minecraft.nbt.*;
import org.junit.Test;

public final class TypedNbtTest {
    @Test
    public void reconstructsEveryNativeTypeWithoutLosingIdentity() {
        NBTTagCompound compound = new NBTTagCompound();
        compound.setByte("byte", Byte.MIN_VALUE);
        compound.setShort("short", Short.MAX_VALUE);
        compound.setInteger("int", Integer.MIN_VALUE);
        compound.setLong("longMin", Long.MIN_VALUE);
        compound.setLong("longMax", Long.MAX_VALUE);
        compound.setFloat("float", -0.0f);
        compound.setFloat("floatMin", Float.MIN_VALUE);
        compound.setFloat("floatMax", Float.MAX_VALUE);
        compound.setDouble("double", Double.MAX_VALUE);
        compound.setDouble("doubleMin", Double.MIN_VALUE);
        compound.setString("string", "1B");
        compound.setByteArray("bytes", new byte[]{Byte.MIN_VALUE, Byte.MAX_VALUE});
        compound.setIntArray("ints", new int[]{Integer.MIN_VALUE, Integer.MAX_VALUE});
        compound.setByteArray("emptyBytes", new byte[0]);
        compound.setIntArray("emptyInts", new int[0]);
        NBTTagList list = new NBTTagList();
        list.appendTag(new NBTTagCompound());
        NBTTagCompound nested = new NBTTagCompound();
        nested.setString("nested", "text");
        list.appendTag(nested);
        compound.setTag("list", list);
        compound.setTag("compound", new NBTTagCompound());
        JsonElement encoded = TypedNbt.encode(compound);
        NBTBase decoded = TypedNbt.decode(new JsonParser().parse(encoded.toString()));
        assertEquals(compound, decoded);
        assertEquals(encoded, TypedNbt.encode(decoded));
        assertNotSame(compound, decoded);
        assertNull(TypedNbt.decode(JsonNull.INSTANCE));
        assertTrue(TypedNbt.decode(TypedNbt.encode(new NBTTagCompound())) instanceof NBTTagCompound);
        assertTrue(TypedNbt.decode(TypedNbt.encode(new NBTTagEnd())) instanceof NBTTagEnd);
    }

    @Test
    public void retainsEmptyListElementTypesAndListOrder() {
        for (int type = 0; type <= 11; type++) {
            JsonElement encoded = new JsonParser().parse("{\"type\":\"list\",\"value\":[],\"element_type_id\":" + type + "}");
            NBTTagList decoded = (NBTTagList) TypedNbt.decode(encoded);
            assertEquals(0, decoded.tagCount());
            assertEquals(type, decoded.func_150303_d());
            assertEquals(encoded, TypedNbt.encode(decoded));
        }
        JsonElement encoded = new JsonParser().parse("{\"type\":\"list\",\"element_type_id\":3,\"value\":[{\"type\":\"int\",\"value\":9},{\"type\":\"int\",\"value\":-2}]}");
        assertEquals(encoded, TypedNbt.encode(TypedNbt.decode(encoded)));
    }

    @Test
    public void rejectsMalformedShapesOverflowAndInconsistentTypes() {
        String[] invalid = {
            "null", "[]", "1", "{}", "{\"type\":\"int\"}",
            "{\"type\":3,\"value\":1}", "{\"type\":\"unknown\",\"value\":0}",
            "{\"type\":\"int\",\"value\":1,\"extra\":true}",
            "{\"type\":\"byte\",\"value\":128}", "{\"type\":\"short\",\"value\":-32769}",
            "{\"type\":\"int\",\"value\":2147483648}", "{\"type\":\"int\",\"value\":1.5}",
            "{\"type\":\"int\",\"value\":\"1\"}", "{\"type\":\"int\",\"value\":true}",
            "{\"type\":\"long\",\"value\":9223372036854775807}",
            "{\"type\":\"long\",\"value\":\"9223372036854775808\"}",
            "{\"type\":\"long\",\"value\":\"1.0\"}",
            "{\"type\":\"float\",\"value\":1e100}", "{\"type\":\"double\",\"value\":1e1000}",
            "{\"type\":\"string\",\"value\":3}", "{\"type\":\"end\",\"value\":1}",
            "{\"type\":\"byte_array\",\"value\":[-129]}", "{\"type\":\"int_array\",\"value\":[1.2]}",
            "{\"type\":\"compound\",\"value\":[]}", "{\"type\":\"compound\",\"value\":{\"x\":null}}",
            "{\"type\":\"compound\",\"value\":{\"x\":{\"type\":\"end\",\"value\":null}}}",
            "{\"type\":\"list\",\"value\":[]}", "{\"type\":\"list\",\"value\":[],\"element_type_id\":12}",
            "{\"type\":\"list\",\"value\":[],\"element_type_id\":\"3\"}",
            "{\"type\":\"list\",\"value\":[{\"type\":\"int\",\"value\":1}],\"element_type_id\":2}",
            "{\"type\":\"list\",\"value\":[{\"type\":\"int\",\"value\":1},{\"type\":\"byte\",\"value\":2}],\"element_type_id\":3}",
            "{\"type\":\"list\",\"value\":[null],\"element_type_id\":3}",
            "{\"type\":\"list\",\"value\":[{\"type\":\"end\",\"value\":null}],\"element_type_id\":0}"
        };
        for (String value : invalid) {
            // A Java null argument is malformed. JSON null is the supported absent tag.
            JsonElement encoded = value.equals("null") ? null : new JsonParser().parse(value);
            assertThrows(value, IllegalArgumentException.class, () -> TypedNbt.decode(encoded));
        }
    }

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
