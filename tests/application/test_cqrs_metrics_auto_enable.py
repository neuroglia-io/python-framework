#!/usr/bin/env python3
"""
Test script to verify CQRS metrics auto-enablement.

This script verifies that:
1. Observability.configure() detects Mediator configuration
2. CQRS metrics are automatically enabled when Mediator is present
3. The MetricsPipelineBehavior is registered in the service collection
"""

import logging
import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from neuroglia.hosting.web import WebApplicationBuilder
from neuroglia.mediation import Mediator
from neuroglia.observability import Observability
from neuroglia.observability.settings import ApplicationSettingsWithObservability

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
log = logging.getLogger(__name__)


def test_auto_enable_with_mediator():
    """Test that CQRS metrics are auto-enabled when Mediator is configured."""

    log.info("=" * 80)
    log.info("TEST 1: CQRS Metrics Auto-Enable with Mediator")
    log.info("=" * 80)

    # Create minimal settings
    class TestSettings(ApplicationSettingsWithObservability):
        service_name: str = "test-service"
        metrics_enabled: bool = True
        tracing_enabled: bool = False
        logging_enabled: bool = False
        health_endpoint_enabled: bool = False
        metrics_endpoint_enabled: bool = False

    settings = TestSettings()
    builder = WebApplicationBuilder(settings)

    # Configure Mediator (this should trigger auto-detection)
    log.info("📦 Configuring Mediator...")
    Mediator.configure(builder, [])

    # Configure Observability (should auto-enable CQRS metrics)
    log.info("🔭 Configuring Observability with auto_enable_cqrs_metrics=True...")
    Observability.configure(builder, auto_enable_cqrs_metrics=True)

    # Build the service provider and check if MetricsPipelineBehavior is registered
    provider = builder.services.build()

    # Check if PipelineBehavior is registered (generic type check)
    from neuroglia.mediation.pipeline_behavior import PipelineBehavior

    behaviors = [desc for desc in builder.services if PipelineBehavior in str(desc.service_type)]

    log.info(f"\n✅ Pipeline behaviors registered: {len(behaviors)}")
    for behavior in behaviors:
        log.info(f"   - {behavior.service_type}")

    # Look specifically for MetricsPipelineBehavior
    metrics_behavior = any("Metrics" in str(b.service_type) for b in behaviors)

    if metrics_behavior:
        log.info("\n✅ SUCCESS: MetricsPipelineBehavior was auto-enabled!")
    else:
        log.warning("\n⚠️ WARNING: MetricsPipelineBehavior not found in registered behaviors")

    return metrics_behavior


def test_auto_enable_without_mediator():
    """Test that CQRS metrics are NOT auto-enabled when Mediator is not configured."""

    log.info("\n" + "=" * 80)
    log.info("TEST 2: CQRS Metrics Auto-Enable WITHOUT Mediator")
    log.info("=" * 80)

    # Create minimal settings
    class TestSettings(ApplicationSettingsWithObservability):
        service_name: str = "test-service-no-mediator"
        metrics_enabled: bool = True
        tracing_enabled: bool = False
        logging_enabled: bool = False
        health_endpoint_enabled: bool = False
        metrics_endpoint_enabled: bool = False

    settings = TestSettings()
    builder = WebApplicationBuilder(settings)

    # DO NOT configure Mediator
    log.info("📦 Skipping Mediator configuration...")

    # Configure Observability (should NOT auto-enable CQRS metrics)
    log.info("🔭 Configuring Observability with auto_enable_cqrs_metrics=True...")
    Observability.configure(builder, auto_enable_cqrs_metrics=True)

    # Build the service provider and check if MetricsPipelineBehavior is registered
    provider = builder.services.build()

    # Check if PipelineBehavior is registered
    from neuroglia.mediation.pipeline_behavior import PipelineBehavior

    behaviors = [desc for desc in builder.services if PipelineBehavior in str(desc.service_type)]

    log.info(f"\n✅ Pipeline behaviors registered: {len(behaviors)}")

    # Look specifically for MetricsPipelineBehavior
    metrics_behavior = any("Metrics" in str(b.service_type) for b in behaviors)

    if not metrics_behavior:
        log.info("\n✅ SUCCESS: MetricsPipelineBehavior was NOT auto-enabled (expected behavior)")
    else:
        log.warning("\n⚠️ WARNING: MetricsPipelineBehavior found but Mediator not configured")

    return not metrics_behavior


def test_opt_out():
    """Test that CQRS metrics can be disabled with auto_enable_cqrs_metrics=False."""

    log.info("\n" + "=" * 80)
    log.info("TEST 3: CQRS Metrics Opt-Out")
    log.info("=" * 80)

    # Create minimal settings
    class TestSettings(ApplicationSettingsWithObservability):
        service_name: str = "test-service-opt-out"
        metrics_enabled: bool = True
        tracing_enabled: bool = False
        logging_enabled: bool = False
        health_endpoint_enabled: bool = False
        metrics_endpoint_enabled: bool = False

    settings = TestSettings()
    builder = WebApplicationBuilder(settings)

    # Configure Mediator
    log.info("📦 Configuring Mediator...")
    Mediator.configure(builder, [])

    # Configure Observability with opt-out
    log.info("🔭 Configuring Observability with auto_enable_cqrs_metrics=False...")
    Observability.configure(builder, auto_enable_cqrs_metrics=False)

    # Build the service provider and check if MetricsPipelineBehavior is registered
    provider = builder.services.build()

    # Check if PipelineBehavior is registered
    from neuroglia.mediation.pipeline_behavior import PipelineBehavior

    behaviors = [desc for desc in builder.services if PipelineBehavior in str(desc.service_type)]

    log.info(f"\n✅ Pipeline behaviors registered: {len(behaviors)}")

    # Look specifically for MetricsPipelineBehavior
    metrics_behavior = any("Metrics" in str(b.service_type) for b in behaviors)

    if not metrics_behavior:
        log.info("\n✅ SUCCESS: MetricsPipelineBehavior was NOT enabled (opt-out worked)")
    else:
        log.warning("\n⚠️ WARNING: MetricsPipelineBehavior found despite opt-out")

    return not metrics_behavior


if __name__ == "__main__":
    log.info("🧪 Starting CQRS Metrics Auto-Enablement Tests\n")

    try:
        test1_passed = test_auto_enable_with_mediator()
        test2_passed = test_auto_enable_without_mediator()
        test3_passed = test_opt_out()

        log.info("\n" + "=" * 80)
        log.info("TEST SUMMARY")
        log.info("=" * 80)
        log.info(f"Test 1 (Auto-enable with Mediator): {'✅ PASSED' if test1_passed else '❌ FAILED'}")
        log.info(f"Test 2 (No auto-enable without Mediator): {'✅ PASSED' if test2_passed else '❌ FAILED'}")
        log.info(f"Test 3 (Opt-out capability): {'✅ PASSED' if test3_passed else '❌ FAILED'}")

        if test1_passed and test2_passed and test3_passed:
            log.info("\n🎉 All tests PASSED! CQRS metrics auto-enablement is working correctly.")
            sys.exit(0)
        else:
            log.error("\n❌ Some tests FAILED. Please review the implementation.")
            sys.exit(1)

    except Exception as e:
        log.error(f"\n❌ Test execution failed with error: {e}", exc_info=True)
        sys.exit(1)
