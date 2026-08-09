"""Tests for identity module."""
import sys
import tempfile
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.identity import IdentityGate


def test_primary_user():
    """Test primary user detection."""
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = os.path.join(tmpdir, "vault")
        os.makedirs(vault_path)
        
        identity = IdentityGate(vault_path)
        
        assert identity.is_primary("primary") == True
        assert identity.is_primary("sir") == True
        assert identity.is_primary("other") == False
        print("✓ test_primary_user passed")


def test_wake_phrase_exact_match():
    """Test exact wake phrase matching."""
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = os.path.join(tmpdir, "vault")
        os.makedirs(vault_path)
        
        identity = IdentityGate(vault_path)
        
        assert identity.verify_wake_phrase("what's up buddy") == True
        assert identity.verify_wake_phrase("daddy's home") == True
        assert identity.verify_wake_phrase("how's going on") == True
        print("✓ test_wake_phrase_exact_match passed")


def test_wake_phrase_fuzzy_match():
    """Test fuzzy wake phrase matching for STT tolerance."""
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = os.path.join(tmpdir, "vault")
        os.makedirs(vault_path)
        
        identity = IdentityGate(vault_path)
        
        # Fuzzy matches (typos, STT errors)
        assert identity.verify_wake_phrase("whats up buddy") == True  # missing apostrophe
        assert identity.verify_wake_phrase("daddys home") == True  # missing apostrophe
        assert identity.verify_wake_phrase("hows going on") == True  # missing apostrophe
        assert identity.verify_wake_phrase("what's up budy") == True  # typo
        print("✓ test_wake_phrase_fuzzy_match passed")


def test_wake_phrase_rejection():
    """Test that non-wake phrases are rejected."""
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = os.path.join(tmpdir, "vault")
        os.makedirs(vault_path)
        
        identity = IdentityGate(vault_path)
        
        assert identity.verify_wake_phrase("hello") == False
        assert identity.verify_wake_phrase("hey kairon") == False
        assert identity.verify_wake_phrase("okay google") == False
        assert identity.verify_wake_phrase("") == False
        print("✓ test_wake_phrase_rejection passed")


def test_session_tier_gating():
    """Test tier-based access control."""
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = os.path.join(tmpdir, "vault")
        os.makedirs(vault_path)
        
        identity = IdentityGate(vault_path)
        
        # Read tier - always allowed
        assert identity.can("anyone", "read") == True
        
        # Side effect - primary or trusted
        assert identity.can("primary", "side_effect") == True
        assert identity.can("sir", "side_effect") == True
        assert identity.can("random", "side_effect") == False
        
        # Destructive - primary only
        assert identity.can("primary", "destructive") == True
        assert identity.can("sir", "destructive") == True
        assert identity.can("random", "destructive") == False
        print("✓ test_session_tier_gating passed")


def test_trusted_users():
    """Test trusted user management."""
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = os.path.join(tmpdir, "vault")
        os.makedirs(vault_path)
        
        identity = IdentityGate(vault_path)
        
        identity.add_trusted("alice")
        assert identity.is_trusted("alice") == True
        assert identity.can("alice", "side_effect") == True
        print("✓ test_trusted_users passed")


if __name__ == "__main__":
    test_primary_user()
    test_wake_phrase_exact_match()
    test_wake_phrase_fuzzy_match()
    test_wake_phrase_rejection()
    test_session_tier_gating()
    test_trusted_users()
    print("\nAll identity tests passed!")