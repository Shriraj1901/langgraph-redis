"""Regression tests for issue #238 - prune()/aprune() must reject unknown strategies.

Any ``strategy`` other than ``"delete"`` used to fall through to ``"keep_latest"``,
so a typo such as ``strategy="keep_last"`` quietly deleted every checkpoint of the
thread except the newest one.  The strategy is now validated before anything is
read or deleted.

The check runs before the first Redis call, so these tests only need savers built
around a stub client; the end-to-end behaviour of valid strategies is covered by
``test_issue_159_aprune_keep_last.py``.
"""

from unittest.mock import MagicMock

import pytest

from langgraph.checkpoint.redis import RedisSaver
from langgraph.checkpoint.redis.aio import AsyncRedisSaver
from langgraph.checkpoint.redis.ashallow import AsyncShallowRedisSaver
from langgraph.checkpoint.redis.shallow import ShallowRedisSaver

BAD_STRATEGIES = ["keep_last", "Delete", "KEEP_LATEST", "zzz", ""]


@pytest.mark.parametrize("saver_cls", [RedisSaver, ShallowRedisSaver])
@pytest.mark.parametrize("strategy", BAD_STRATEGIES)
def test_prune_rejects_unknown_strategy(saver_cls, strategy: str) -> None:
    client = MagicMock()
    saver = saver_cls(redis_client=client)
    client.reset_mock()

    with pytest.raises(ValueError, match="strategy"):
        saver.prune(["thread-1"], strategy=strategy)

    # Nothing was read or deleted before the error.
    assert client.mock_calls == []


@pytest.mark.parametrize("saver_cls", [AsyncRedisSaver, AsyncShallowRedisSaver])
@pytest.mark.parametrize("strategy", BAD_STRATEGIES)
async def test_aprune_rejects_unknown_strategy(saver_cls, strategy: str) -> None:
    client = MagicMock()
    saver = saver_cls(redis_client=client)
    client.reset_mock()

    with pytest.raises(ValueError, match="strategy"):
        await saver.aprune(["thread-1"], strategy=strategy)

    assert client.mock_calls == []


def test_prune_rejects_unknown_strategy_even_with_explicit_keep_last() -> None:
    """``keep_last`` overrides the strategy, but a typo should still be reported."""
    saver = RedisSaver(redis_client=MagicMock())
    with pytest.raises(ValueError, match="got 'keep_last'"):
        saver.prune(["thread-1"], strategy="keep_last", keep_last=3)


def test_prune_error_names_the_supported_strategies() -> None:
    saver = ShallowRedisSaver(redis_client=MagicMock())
    with pytest.raises(ValueError) as excinfo:
        saver.prune(["thread-1"], strategy="keep_last")
    message = str(excinfo.value)
    assert "keep_latest" in message
    assert "delete" in message


def test_shallow_prune_still_accepts_both_documented_strategies() -> None:
    saver = ShallowRedisSaver(redis_client=MagicMock())
    saver.prune(["thread-1"], strategy="keep_latest")  # documented no-op
    saver.prune(["thread-1"], strategy="delete")  # equivalent to delete_thread
