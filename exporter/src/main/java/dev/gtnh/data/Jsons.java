package dev.gtnh.data;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonNull;
import com.google.gson.JsonObject;

final class Jsons {
    private Jsons() {}
    static JsonObject object(Object... pairs) {
        JsonObject result = new JsonObject();
        for (int index = 0; index < pairs.length; index += 2) {
            Object value = pairs[index + 1];
            result.add((String) pairs[index], value == null ? JsonNull.INSTANCE
                : value instanceof JsonElement ? (JsonElement) value : SnapshotWriter.JSON.toJsonTree(value));
        }
        return result;
    }
    static JsonArray array(JsonElement... values) {
        JsonArray result = new JsonArray();
        for (JsonElement value : values) result.add(value);
        return result;
    }
}
