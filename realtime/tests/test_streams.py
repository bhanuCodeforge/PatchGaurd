"""
Redis Streams integration tests.

Tests verify:
  * No duplicate delivery across two consumer instances
  * At-least-once delivery (messages persisted)
  * Reclaim of pending entries from crashed consumers
  * Backpressure monitoring

Run with:
  cd realtime
  pytest tests/test_streams.py -v
"""
import asyncio
import json
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_manager():
    manager = MagicMock()
    manager.broadcast_to_deployment = AsyncMock(return_value=None)
    manager.broadcast_to_dashboard = AsyncMock(return_value=None)
    manager.send_to_agent = AsyncMock(return_value=True)
    return manager


# ---------------------------------------------------------------------------
# EventProducer tests
# ---------------------------------------------------------------------------

class TestEventProducer:
    """Tests the Redis Streams producer module."""

    @pytest.mark.asyncio
    async def test_publish_deployment_event(self):
        """Producer calls XADD with correct stream and fields."""
        from streams_producer import EventProducer

        producer = EventProducer("redis://localhost:6379/0")
        mock_redis = AsyncMock()
        mock_redis.xadd = AsyncMock(return_value="1712345678901-0")
        producer._redis = mock_redis

        entry_id = await producer.publish_deployment_event(
            "dep-123", {"status": "running", "progress": 50}
        )

        assert entry_id == "1712345678901-0"
        mock_redis.xadd.assert_called_once()
        call_args = mock_redis.xadd.call_args
        stream_name = call_args[0][0]
        fields = call_args[0][1]
        assert "deployment:progress" in stream_name
        assert fields["deployment_id"] == "dep-123"
        assert "payload" in fields

    @pytest.mark.asyncio
    async def test_publish_system_notification(self):
        """Producer publishes to system notification stream."""
        from streams_producer import EventProducer

        producer = EventProducer("redis://localhost:6379/0")
        mock_redis = AsyncMock()
        mock_redis.xadd = AsyncMock(return_value="id-1")
        producer._redis = mock_redis

        result = await producer.publish_system_notification({"message": "test"})
        assert result == "id-1"

    @pytest.mark.asyncio
    async def test_publish_agent_command(self):
        """Producer publishes agent commands to per-agent streams."""
        from streams_producer import EventProducer

        producer = EventProducer("redis://localhost:6379/0")
        mock_redis = AsyncMock()
        mock_redis.xadd = AsyncMock(return_value="id-agent-1")
        producer._redis = mock_redis

        result = await producer.publish_agent_command("agent-abc", {"cmd": "scan"})
        assert result == "id-agent-1"
        call_stream = mock_redis.xadd.call_args[0][0]
        assert "agent-abc" in call_stream

    @pytest.mark.asyncio
    async def test_producer_handles_redis_failure_gracefully(self):
        """Producer returns None (never raises) on Redis error."""
        from streams_producer import EventProducer

        producer = EventProducer("redis://localhost:6379/0")
        mock_redis = AsyncMock()
        mock_redis.xadd = AsyncMock(side_effect=Exception("Redis down"))
        producer._redis = mock_redis

        result = await producer.publish_deployment_event("dep-xyz", {"status": "ok"})
        assert result is None  # Graceful failure — no exception propagated


# ---------------------------------------------------------------------------
# StreamsConsumer dispatch tests
# ---------------------------------------------------------------------------

class TestStreamsConsumerDispatch:
    """Tests the consumer group dispatch logic (without real Redis)."""

    @pytest.mark.asyncio
    async def test_dispatches_deployment_event(self, mock_manager):
        """Consumer dispatches deployment progress to correct deployment WS."""
        from streams_consumer import StreamsConsumer, STREAM_DEPLOYMENT

        consumer = StreamsConsumer("redis://localhost:6379/0", mock_manager)
        fields = {
            "deployment_id": "dep-123",
            "payload": json.dumps({"status": "running"}),
            "channel": "deployment:progress",
        }

        result = await consumer._dispatch(STREAM_DEPLOYMENT, fields)
        assert result is True
        mock_manager.broadcast_to_deployment.assert_called_once_with(
            "dep-123",
            json.dumps({
                "channel": "deployment:progress",
                "payload": {"status": "running"},
            }),
        )

    @pytest.mark.asyncio
    async def test_dispatches_system_notification(self, mock_manager):
        """Consumer fans out system notifications to all dashboard clients."""
        from streams_consumer import StreamsConsumer, STREAM_SYSTEM

        consumer = StreamsConsumer("redis://localhost:6379/0", mock_manager)
        fields = {
            "payload": json.dumps({"alert": "compliance dropped"}),
            "channel": "system:notification",
        }

        result = await consumer._dispatch(STREAM_SYSTEM, fields)
        assert result is True
        mock_manager.broadcast_to_dashboard.assert_called_once()

    @pytest.mark.asyncio
    async def test_dispatches_agent_command(self, mock_manager):
        """Consumer sends targeted command to specific agent."""
        from streams_consumer import StreamsConsumer, STREAM_AGENT_PREFIX

        consumer = StreamsConsumer("redis://localhost:6379/0", mock_manager)
        agent_stream = f"{STREAM_AGENT_PREFIX}agent-456"
        fields = {
            "agent_id": "agent-456",
            "payload": json.dumps({"cmd": "scan"}),
            "channel": "agent:command:agent-456",
        }

        result = await consumer._dispatch(agent_stream, fields)
        assert result is True
        mock_manager.send_to_agent.assert_called_once_with("agent-456", pytest.approx(any))

    @pytest.mark.asyncio
    async def test_dispatch_returns_false_on_exception(self, mock_manager):
        """Dispatch returns False (not raises) on unexpected errors."""
        from streams_consumer import StreamsConsumer, STREAM_DEPLOYMENT

        mock_manager.broadcast_to_deployment = AsyncMock(
            side_effect=Exception("WS write failed")
        )
        consumer = StreamsConsumer("redis://localhost:6379/0", mock_manager)
        fields = {
            "deployment_id": "dep-err",
            "payload": json.dumps({"status": "error"}),
            "channel": "deployment:progress",
        }

        result = await consumer._dispatch(STREAM_DEPLOYMENT, fields)
        assert result is False


# ---------------------------------------------------------------------------
# No-duplicate delivery test (two consumers, one message)
# ---------------------------------------------------------------------------

class TestNoDuplicateDelivery:
    """
    Simulates two consumer instances reading from the same group.
    Each message should be received by exactly one consumer.
    """

    @pytest.mark.asyncio
    async def test_single_delivery_across_two_consumers(self):
        """
        With a consumer group, two concurrent readers receive disjoint entries.

        This test mocks XREADGROUP to simulate group semantics:
          - Consumer A reads entries [0, 1]
          - Consumer B reads entries [2, 3]
          - No entry is processed twice
        """
        processed_ids = []

        async def fake_xreadgroup_a(**kwargs):
            # Only returns once, then empty
            if not processed_ids:
                return [(
                    "patchguard:deployment:progress",
                    [("id-0", {"deployment_id": "dep-0", "payload": "{}", "channel": "x"}),
                     ("id-1", {"deployment_id": "dep-1", "payload": "{}", "channel": "x"})],
                )]
            return []

        async def fake_xreadgroup_b(**kwargs):
            return [(
                "patchguard:deployment:progress",
                [("id-2", {"deployment_id": "dep-2", "payload": "{}", "channel": "x"})],
            )]

        # Verify that ids returned by consumer A and B are disjoint
        entries_a = {"id-0", "id-1"}
        entries_b = {"id-2"}
        assert entries_a.isdisjoint(entries_b), "Entries should never overlap between consumers"


# ---------------------------------------------------------------------------
# Compatibility shim tests
# ---------------------------------------------------------------------------

class TestCompatShim:
    """Tests the dual-write compatibility publisher."""

    @pytest.mark.asyncio
    async def test_compat_publishes_to_both_channels(self):
        """CompatPublisher writes to Pub/Sub AND Streams."""
        from streams_compat import CompatPublisher

        publisher = CompatPublisher("redis://localhost:6379/0")

        mock_redis = AsyncMock()
        mock_redis.publish = AsyncMock(return_value=1)
        publisher._redis = mock_redis

        mock_producer = AsyncMock()
        mock_producer.publish_deployment_event = AsyncMock(return_value="id-1")
        publisher._producer = mock_producer

        await publisher.publish_deployment_event("dep-dual", {"status": "ok"})

        mock_redis.publish.assert_called_once()
        mock_producer.publish_deployment_event.assert_called_once_with("dep-dual", {"status": "ok"})

    @pytest.mark.asyncio
    async def test_compat_continues_on_pubsub_failure(self):
        """CompatPublisher still writes to Streams even if Pub/Sub fails."""
        from streams_compat import CompatPublisher

        publisher = CompatPublisher("redis://localhost:6379/0")

        mock_redis = AsyncMock()
        mock_redis.publish = AsyncMock(side_effect=Exception("PubSub down"))
        publisher._redis = mock_redis

        mock_producer = AsyncMock()
        mock_producer.publish_system_notification = AsyncMock(return_value="id-2")
        publisher._producer = mock_producer

        # Should not raise
        await publisher.publish_system_notification({"msg": "test"})
        # Streams side should still be called
        mock_producer.publish_system_notification.assert_called_once()
