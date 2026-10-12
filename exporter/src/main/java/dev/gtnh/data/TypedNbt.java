package dev.gtnh.data;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonNull;
import com.google.gson.JsonObject;
import java.util.Set;
import java.util.TreeSet;
import net.minecraft.nbt.*;

/** Detached native tags. Decimal strings keep 64-bit values exact in JavaScript. */
final class TypedNbt {
    private TypedNbt() {}

    /** Reconstructs detached native tags. Malformed typed values are rejected, never coerced. */
    static NBTBase decode(JsonElement encoded) {
        require(encoded != null, "Typed NBT must be a JSON value");
        if (encoded.isJsonNull()) return null;
        require(encoded.isJsonObject(), "Typed NBT must be an object or JSON null");
        JsonObject object = encoded.getAsJsonObject();
        String type = string(object.get("type"));
        require(object.has("value"), "Typed NBT is missing value");
        require(object.entrySet().size() == (type.equals("list") ? 3 : 2), "Unexpected typed NBT fields");
        JsonElement value = object.get("value");
        switch (type) {
            case "end":
                require(value.isJsonNull(), "End tag value must be null");
                return new NBTTagEnd();
            case "byte": return new NBTTagByte((byte) integer(value, Byte.MIN_VALUE, Byte.MAX_VALUE));
            case "short": return new NBTTagShort((short) integer(value, Short.MIN_VALUE, Short.MAX_VALUE));
            case "int": return new NBTTagInt(integer(value, Integer.MIN_VALUE, Integer.MAX_VALUE));
            case "long":
                String decimal = string(value);
                require(decimal.matches("-?(0|[1-9][0-9]*)"), "Long tag must be a decimal integer string");
                return new NBTTagLong(Long.parseLong(decimal));
            case "float":
                float single = number(value).getAsFloat();
                require(Float.isFinite(single), "Float tag must be finite and within range");
                return new NBTTagFloat(single);
            case "double":
                double precision = number(value).getAsDouble();
                require(Double.isFinite(precision), "Double tag must be finite and within range");
                return new NBTTagDouble(precision);
            case "byte_array":
                JsonArray bytes = array(value);
                byte[] byteValues = new byte[bytes.size()];
                for (int index = 0; index < bytes.size(); index++)
                    byteValues[index] = (byte) integer(bytes.get(index), Byte.MIN_VALUE, Byte.MAX_VALUE);
                return new NBTTagByteArray(byteValues);
            case "string": return new NBTTagString(string(value));
            case "list":
                int elementType = integer(object.get("element_type_id"), 0, 11);
                JsonArray entries = array(value);
                NBTTagList list = new NBTTagList();
                for (JsonElement entry : entries) {
                    NBTBase tag = decode(entry);
                    require(tag != null && tag.getId() != 0 && tag.getId() == elementType,
                        "List entries must match the non-end element type");
                    list.appendTag(tag);
                }
                if (entries.size() == 0 && elementType != 0) {
                    // Native removeTag retains the element type after removing the last entry.
                    list.appendTag(emptyTag(elementType));
                    list.removeTag(0);
                }
                return list;
            case "compound":
                require(value.isJsonObject(), "Compound tag value must be an object");
                NBTTagCompound compound = new NBTTagCompound();
                for (java.util.Map.Entry<String, JsonElement> entry : value.getAsJsonObject().entrySet()) {
                    NBTBase tag = decode(entry.getValue());
                    require(tag != null && tag.getId() != 0, "Compound entries must be non-null, non-end tags");
                    compound.setTag(entry.getKey(), tag);
                }
                return compound;
            case "int_array":
                JsonArray ints = array(value);
                int[] intValues = new int[ints.size()];
                for (int index = 0; index < ints.size(); index++)
                    intValues[index] = integer(ints.get(index), Integer.MIN_VALUE, Integer.MAX_VALUE);
                return new NBTTagIntArray(intValues);
            default: throw new IllegalArgumentException("Unsupported typed NBT type: " + type);
        }
    }

    private static int integer(JsonElement value, int minimum, int maximum) {
        try {
            int integer = number(value).getAsBigDecimal().intValueExact();
            require(integer >= minimum && integer <= maximum, "Integer tag value is outside its native range");
            return integer;
        } catch (ArithmeticException error) {
            throw new IllegalArgumentException("Integer tag value must be integral and within range", error);
        }
    }

    private static JsonElement number(JsonElement value) {
        require(value != null && value.isJsonPrimitive() && value.getAsJsonPrimitive().isNumber(),
            "Numeric tag value must be a JSON number");
        return value;
    }

    private static String string(JsonElement value) {
        require(value != null && value.isJsonPrimitive() && value.getAsJsonPrimitive().isString(),
            "String tag value must be a JSON string");
        return value.getAsString();
    }

    private static JsonArray array(JsonElement value) {
        require(value.isJsonArray(), "Array or list tag value must be a JSON array");
        return value.getAsJsonArray();
    }

    private static void require(boolean valid, String message) {
        if (!valid) throw new IllegalArgumentException(message);
    }

    private static NBTBase emptyTag(int type) {
        switch (type) {
            case 1: return new NBTTagByte((byte) 0);
            case 2: return new NBTTagShort((short) 0);
            case 3: return new NBTTagInt(0);
            case 4: return new NBTTagLong(0);
            case 5: return new NBTTagFloat(0);
            case 6: return new NBTTagDouble(0);
            case 7: return new NBTTagByteArray(new byte[0]);
            case 8: return new NBTTagString("");
            case 9: return new NBTTagList();
            case 10: return new NBTTagCompound();
            case 11: return new NBTTagIntArray(new int[0]);
            default: throw new IllegalArgumentException("Unsupported list element type: " + type);
        }
    }

    static JsonElement encode(NBTBase tag) {
        if (tag == null) return JsonNull.INSTANCE;
        switch (tag.getId()) {
            case 0: return Jsons.object("type", "end", "value", null);
            case 1: return Jsons.object("type", "byte", "value", ((NBTTagByte) tag).func_150290_f());
            case 2: return Jsons.object("type", "short", "value", ((NBTTagShort) tag).func_150289_e());
            case 3: return Jsons.object("type", "int", "value", ((NBTTagInt) tag).func_150287_d());
            case 4: return Jsons.object("type", "long", "value", Long.toString(((NBTTagLong) tag).func_150291_c()));
            case 5: return Jsons.object("type", "float", "value", ((NBTTagFloat) tag).func_150288_h());
            case 6: return Jsons.object("type", "double", "value", ((NBTTagDouble) tag).func_150286_g());
            case 7: return Jsons.object("type", "byte_array", "value", ((NBTTagByteArray) tag).func_150292_c());
            case 8: return Jsons.object("type", "string", "value", ((NBTTagString) tag).func_150285_a_());
            case 9:
                NBTTagList list = (NBTTagList) tag;
                JsonArray entries = new JsonArray();
                NBTTagList detached = (NBTTagList) list.copy();
                JsonElement[] elements = new JsonElement[list.tagCount()];
                for (int index = elements.length - 1; index >= 0; index--) elements[index] = encode(detached.removeTag(index));
                for (JsonElement element : elements) entries.add(element);
                return Jsons.object("type", "list", "value", entries, "element_type_id", list.func_150303_d());
            case 10:
                NBTTagCompound compound = (NBTTagCompound) tag;
                JsonObject values = new JsonObject();
                @SuppressWarnings("unchecked") Set<String> keys = compound.func_150296_c();
                for (String key : new TreeSet<>(keys)) values.add(key, encode(compound.getTag(key)));
                return Jsons.object("type", "compound", "value", values);
            case 11: return Jsons.object("type", "int_array", "value", ((NBTTagIntArray) tag).func_150302_c());
            default: throw new IllegalArgumentException("Unsupported native NBT type: " + tag.getId());
        }
    }
}
