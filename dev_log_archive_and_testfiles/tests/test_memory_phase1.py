#!/usr/bin/env python3
"""
Phase 1 Memory Enhancement Test Script

Tests:
1. Create new vector with enhanced metadata
2. Verify all new fields are present
3. Test track_access() functionality
4. Run migration on existing vectors
5. Verify search still works
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tools.vector_search import (
    vector_add_knowledge,
    vector_search_knowledge,
    migrate_existing_vectors_to_v2,
    _get_vector_db
)
from datetime import datetime
import json


def test_new_vector_with_enhanced_metadata():
    """Test 1: Create new vector and verify enhanced metadata"""
    print("\n" + "="*70)
    print("TEST 1: Creating new vector with enhanced metadata")
    print("="*70)

    # Add a test fact
    result = vector_add_knowledge(
        fact="Phase 1 Memory Enhancement test fact",
        category="testing",
        confidence=1.0,
        source="phase1_test"
    )

    print(f"\n✓ Vector created: {result}")

    if not result.get("success"):
        print("❌ FAILED: Could not create vector")
        return False

    # Get the vector back and check metadata
    db = _get_vector_db()
    coll = db.get_or_create_collection("knowledge")

    # Get the vector we just created
    vector_id = result["id"]
    docs = coll.get(ids=[vector_id])

    if not docs["ids"]:
        print("❌ FAILED: Could not retrieve vector")
        return False

    metadata = docs["metadatas"][0]

    print(f"\n📋 Retrieved metadata:")
    print(json.dumps(metadata, indent=2))

    # Check all required fields
    required_fields = ["access_count", "last_accessed_ts", "related_memories", "embedding_version"]
    missing_fields = [field for field in required_fields if field not in metadata]

    if missing_fields:
        print(f"\n❌ FAILED: Missing fields: {missing_fields}")
        return False

    # Verify field values
    checks = [
        (metadata["access_count"] == 0, "access_count should be 0"),
        (isinstance(metadata["last_accessed_ts"], (int, float)), "last_accessed_ts should be numeric"),
        (isinstance(metadata["related_memories"], str), "related_memories should be a JSON string"),
        (metadata["related_memories"] == "[]", "related_memories should be empty JSON array"),
        ("embedding_version" in metadata, "embedding_version should exist")
    ]

    for check, description in checks:
        if not check:
            print(f"❌ FAILED: {description}")
            return False
        print(f"✓ {description}")

    print("\n✅ TEST 1 PASSED: New vector has all enhanced metadata fields!")
    return True, vector_id


def test_track_access(vector_id):
    """Test 2: Test track_access() functionality"""
    print("\n" + "="*70)
    print("TEST 2: Testing track_access() functionality")
    print("="*70)

    db = _get_vector_db()
    coll = db.get_or_create_collection("knowledge")

    # Get initial metadata
    docs_before = coll.get(ids=[vector_id])
    metadata_before = docs_before["metadatas"][0]

    print(f"\n📊 Before tracking:")
    print(f"  access_count: {metadata_before['access_count']}")
    print(f"  last_accessed_ts: {metadata_before['last_accessed_ts']}")

    # Track access
    print("\n⏳ Tracking access...")
    success = coll.track_access([vector_id])

    if not success:
        print("❌ FAILED: track_access() returned False")
        return False

    # Get updated metadata
    docs_after = coll.get(ids=[vector_id])
    metadata_after = docs_after["metadatas"][0]

    print(f"\n📊 After tracking:")
    print(f"  access_count: {metadata_after['access_count']}")
    print(f"  last_accessed_ts: {metadata_after['last_accessed_ts']}")

    # Verify changes
    if metadata_after["access_count"] != metadata_before["access_count"] + 1:
        print(f"❌ FAILED: access_count not incremented correctly")
        return False

    if metadata_after["last_accessed_ts"] <= metadata_before["last_accessed_ts"]:
        print(f"❌ FAILED: last_accessed_ts not updated")
        return False

    print("\n✓ access_count incremented from 0 to 1")
    print("✓ last_accessed_ts updated")

    # Track access again
    print("\n⏳ Tracking access again...")
    coll.track_access([vector_id])

    docs_final = coll.get(ids=[vector_id])
    metadata_final = docs_final["metadatas"][0]

    if metadata_final["access_count"] != 2:
        print(f"❌ FAILED: Second tracking didn't work (count={metadata_final['access_count']})")
        return False

    print(f"✓ Second tracking successful (count={metadata_final['access_count']})")

    print("\n✅ TEST 2 PASSED: track_access() works correctly!")
    return True


def test_migration():
    """Test 3: Test migration on existing vectors"""
    print("\n" + "="*70)
    print("TEST 3: Testing migration utility")
    print("="*70)

    # Run migration
    print("\n⏳ Running migration on 'knowledge' collection...")
    result = migrate_existing_vectors_to_v2("knowledge")

    print(f"\n📊 Migration result:")
    print(json.dumps(result, indent=2))

    if not result.get("success"):
        print(f"\n❌ FAILED: Migration failed: {result.get('error')}")
        return False

    print(f"\n✓ Total vectors: {result['total_vectors']}")
    print(f"✓ Migrated: {result['migrated']}")
    print(f"✓ Skipped (already migrated): {result['skipped']}")

    # Verify all vectors now have enhanced metadata
    db = _get_vector_db()
    coll = db.get_or_create_collection("knowledge")
    all_docs = coll.get(limit=10)  # Check first 10

    if not all_docs["ids"]:
        print("\n⚠️  WARNING: No vectors in collection to verify")
        print("✅ TEST 3 PASSED: Migration ran successfully!")
        return True

    print(f"\n🔍 Verifying {len(all_docs['ids'])} vectors have enhanced metadata...")

    for i, metadata in enumerate(all_docs["metadatas"]):
        required_fields = ["access_count", "last_accessed_ts", "related_memories", "embedding_version"]
        missing = [f for f in required_fields if f not in metadata]

        if missing:
            print(f"❌ FAILED: Vector {i} missing fields: {missing}")
            return False

    print(f"✓ All {len(all_docs['ids'])} checked vectors have enhanced metadata")

    # Test idempotency - run migration again
    print("\n⏳ Testing idempotency (running migration again)...")
    result2 = migrate_existing_vectors_to_v2("knowledge")

    if not result2.get("success"):
        print(f"❌ FAILED: Second migration failed")
        return False

    if result2["migrated"] != 0:
        print(f"❌ FAILED: Second migration modified {result2['migrated']} vectors (should be 0)")
        return False

    print(f"✓ Second migration skipped all vectors (idempotent)")

    print("\n✅ TEST 3 PASSED: Migration works correctly and is idempotent!")
    return True


def test_search_still_works():
    """Test 4: Verify search functionality still works"""
    print("\n" + "="*70)
    print("TEST 4: Verifying search still works with enhanced metadata")
    print("="*70)

    # Search for our test fact
    print("\n⏳ Searching for 'Phase 1 Memory Enhancement'...")
    results = vector_search_knowledge(
        query="Phase 1 Memory Enhancement test",
        category="testing",
        top_k=5
    )

    if isinstance(results, dict) and not results.get("success"):
        print(f"❌ FAILED: Search failed: {results.get('error')}")
        return False

    if not results:
        print("❌ FAILED: No results returned")
        return False

    print(f"\n✓ Search returned {len(results)} results")

    # Check that results have similarity scores
    for i, result in enumerate(results[:3]):
        print(f"\n📄 Result {i+1}:")
        print(f"  Text: {result['text'][:60]}...")
        print(f"  Similarity: {result.get('similarity', 'N/A')}")
        print(f"  Metadata keys: {list(result.get('metadata', {}).keys())}")

    # Verify first result has enhanced metadata
    if results[0].get("metadata"):
        metadata = results[0]["metadata"]
        enhanced_fields = ["access_count", "last_accessed_ts", "related_memories"]
        has_enhanced = any(field in metadata for field in enhanced_fields)

        if not has_enhanced:
            print("\n⚠️  WARNING: Results don't include enhanced metadata fields")
        else:
            print(f"\n✓ Results include enhanced metadata")

    print("\n✅ TEST 4 PASSED: Search functionality works correctly!")
    return True


def main():
    print("\n" + "="*70)
    print("🚀 PHASE 1 MEMORY ENHANCEMENT TEST SUITE")
    print("="*70)
    print(f"Timestamp: {datetime.now().isoformat()}")

    try:
        # Test 1: New vector with enhanced metadata
        result1 = test_new_vector_with_enhanced_metadata()
        if not result1:
            print("\n❌ Test suite FAILED at Test 1")
            return False

        success, vector_id = result1

        # Test 2: Track access
        if not test_track_access(vector_id):
            print("\n❌ Test suite FAILED at Test 2")
            return False

        # Test 3: Migration
        if not test_migration():
            print("\n❌ Test suite FAILED at Test 3")
            return False

        # Test 4: Search still works
        if not test_search_still_works():
            print("\n❌ Test suite FAILED at Test 4")
            return False

        # All tests passed!
        print("\n" + "="*70)
        print("🎉 ALL TESTS PASSED! PHASE 1 COMPLETE!")
        print("="*70)
        print("\n✅ Enhanced metadata is now active")
        print("✅ track_access() method works correctly")
        print("✅ Migration utility is functional and idempotent")
        print("✅ Search functionality unchanged")
        print("\nPhase 1 Memory Enhancement is production-ready! 🚀")

        return True

    except Exception as e:
        print(f"\n❌ TEST SUITE FAILED WITH EXCEPTION:")
        print(f"{type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
