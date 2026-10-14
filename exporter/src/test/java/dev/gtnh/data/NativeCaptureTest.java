package dev.gtnh.data;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotEquals;

import com.google.gson.JsonNull;
import net.minecraft.nbt.NBTTagCompound;
import org.junit.Test;

public class NativeCaptureTest {
    @Test
    public void exactResourceIdentitySeparatesNativeTagTypesMetadataAndKind() {
        NBTTagCompound byteTag = new NBTTagCompound();
        byteTag.setByte("mode", (byte) 1);
        NBTTagCompound intTag = new NBTTagCompound();
        intTag.setInteger("mode", 1);
        String identity = NativeCapture.resourceKey("item", "catalog:component", 55, TypedNbt.encode(byteTag));
        assertNotEquals(identity, NativeCapture.resourceKey("item", "catalog:component", 55, TypedNbt.encode(intTag)));
        assertNotEquals(identity, NativeCapture.resourceKey("item", "catalog:component", 56, TypedNbt.encode(byteTag)));
        assertNotEquals(identity, NativeCapture.resourceKey("fluid", "catalog:component", 55, TypedNbt.encode(byteTag)));
        assertNotEquals(identity, NativeCapture.resourceKey("item", "other:component", 55, TypedNbt.encode(byteTag)));
        assertNotEquals(NativeCapture.resourceKey("item", "catalog:component", 55, JsonNull.INSTANCE),
            NativeCapture.resourceKey("item", "catalog:component", 55, TypedNbt.encode(new NBTTagCompound())));
    }

    @Test
    public void catalogAndResourceIdentityUseCanonicalNativeCompoundOrdering() {
        NBTTagCompound catalog = new NBTTagCompound();
        catalog.setInteger("voltage", 4);
        catalog.setString("owner", "native");
        NBTTagCompound resource = new NBTTagCompound();
        resource.setString("owner", "native");
        resource.setInteger("voltage", 4);
        assertEquals(NativeCapture.resourceKey("item", "catalog:component", 55, TypedNbt.encode(catalog)),
            NativeCapture.resourceKey("item", "catalog:component", 55, TypedNbt.encode(resource)));
    }
}
