import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

try:
    from models.character import CharacterListing, EquippedItem
    print("Import successful!")
    
    # Test creation
    item = EquippedItem(slot="test", item_type="equip", item_id=123)
    print("EquippedItem created!")
    
    char = CharacterListing(
        token_id="123",
        name="Test",
        level=100
    )
    print(f"CharacterListing created: {char.nickname}")
except Exception as e:
    import traceback
    traceback.print_exc()
    sys.exit(1)
