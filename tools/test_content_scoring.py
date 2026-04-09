#!/usr/bin/env python3
# Basic tests for content scoring author parsing

import sys
import os
import logging
import types

# create fake steem package and submodules so tests don't require the real dependency
fake_steem = types.ModuleType('steem')
# the real module exports Steem, but our dummy just provides a callable
def fake_Steem(*args, **kwargs):
    return None
fake_steem.Steem = fake_Steem

fake_account = types.ModuleType('steem.account')
def fake_Account(*args, **kwargs):
    # will be monkeypatched later if needed
    return None
fake_account.Account = fake_Account
fake_account.AccountDoesNotExistsException = Exception

fake_post = types.ModuleType('steem.post')
# leave Post as None since not used directly in tests
fake_post.Post = None

sys.modules['steem'] = fake_steem
sys.modules['steem.account'] = fake_account
sys.modules['steem.post'] = fake_post

# also stub utils to avoid langdetect etc.
fake_utils = types.ModuleType('utils')

import random

def fake_get_rng():
    return random.Random()

fake_utils.get_rng = fake_get_rng

# we don't need other utils functions for author scoring
sys.modules['utils'] = fake_utils

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from contentScoring import ContentScorer

# Dummy objects used for tests
class DummyConfig:
    def get_float(self, section, key, default):
        return default
    def get_int(self, section, key, default):
        return default

class DummyAccount:
    """Minimal fake account that mimics the interface used by ContentScorer._score_author."""
    def __init__(self, author, steemd_instance=None):
        # basic metrics
        self.rep = 1000
        self._followers = []
        self._following = []
        # attributes accessed via __getitem__ in scoring
        self.created = '2025-01-01T00:00:00Z'  # string with Z
        self.last_vote_time = '2026-02-01T00:00:00'
        self.last_post = None
        self.last_root_post = None
    def get_followers(self):
        return self._followers
    def get_following(self):
        return self._following
    def __getitem__(self, key):
        # allow both dictionary-style and attribute-style access
        return getattr(self, key)

class UnparsableAccount(DummyAccount):
    def __init__(self, author, steemd_instance=None):
        super().__init__(author, steemd_instance)
        self.created = 'not-a-date'


def run_tests():
    logging.basicConfig(level=logging.DEBUG)
    print("Running content scoring author tests")

    # monkeypatch Account class in module
    import contentScoring
    contentScoring.Account = DummyAccount

    scorer = ContentScorer(None, DummyConfig())

    print("Test 1: created_date as ISO string with Z should not crash")
    score = scorer._score_author('anyone')
    print(f"  Score returned: {score}")

    # now test an unparsable created_date
    contentScoring.Account = UnparsableAccount
    print("Test 2: unparsable created_date treated gracefully (should not raise)")
    score2 = scorer._score_author('anyone')
    print(f"  Score returned for unparsable date: {score2}")

    print("Content scoring author tests completed")

if __name__ == '__main__':
    run_tests()
