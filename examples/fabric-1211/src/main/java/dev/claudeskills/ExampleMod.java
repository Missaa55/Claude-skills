package dev.claudeskills;

import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.itemgroup.v1.ItemGroupEvents;
import net.minecraft.block.AbstractBlock;
import net.minecraft.block.Block;
import net.minecraft.item.BlockItem;
import net.minecraft.item.Item;
import net.minecraft.item.ItemGroups;
import net.minecraft.registry.Registries;
import net.minecraft.registry.Registry;
import net.minecraft.util.Identifier;

public final class ExampleMod implements ModInitializer {
    public static final String MOD_ID = "claudeskills_block";
    public static final Block WORKSHOP_BLOCK = new Block(
            AbstractBlock.Settings.create().strength(3.0f).requiresTool());

    @Override
    public void onInitialize() {
        Identifier id = Identifier.of(MOD_ID, "workshop_block");
        Registry.register(Registries.BLOCK, id, WORKSHOP_BLOCK);
        Registry.register(Registries.ITEM, id, new BlockItem(WORKSHOP_BLOCK, new Item.Settings()));
        ItemGroupEvents.modifyEntriesEvent(ItemGroups.BUILDING_BLOCKS)
                .register(entries -> entries.add(WORKSHOP_BLOCK));
    }
}
