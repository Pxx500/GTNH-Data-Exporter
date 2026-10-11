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
