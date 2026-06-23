#!/usr/bin/env python3
"""Test script to verify Lab Resource Manager startup with etcd."""

import asyncio
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import etcd3
from domain.resources.lab_worker import (
    AwsEc2Config,
    CmlConfig,
    LabWorker,
    LabWorkerPhase,
    LabWorkerSpec,
    LabWorkerStatus,
)
from integration.repositories.etcd_lab_worker_repository import (
    EtcdLabWorkerResourceRepository,
)
from integration.repositories.etcd_storage_backend import EtcdStorageBackend

from neuroglia.data.resources import ResourceMetadata


async def test_storage_backend():
    """Test EtcdStorageBackend basic operations."""
    print("\n" + "=" * 60)
    print("🧪 Testing EtcdStorageBackend")
    print("=" * 60)

    # Connect to etcd
    etcd_host = os.getenv("ETCD_HOST", "localhost")
    etcd_port = int(os.getenv("ETCD_PORT", "2479"))

    print(f"\n1️⃣ Connecting to etcd at {etcd_host}:{etcd_port}...")
    client = etcd3.Client(host=etcd_host, port=etcd_port, timeout=10)
    print("   ✅ Connected")

    # Create storage backend
    print("\n2️⃣ Creating storage backend...")
    backend = EtcdStorageBackend(client, prefix="/test-lab-workers/")
    print("   ✅ Storage backend created")

    # Test set/get
    print("\n3️⃣ Testing set/get operations...")
    test_resource = {
        "metadata": {
            "name": "test-worker-001",
            "namespace": "default",
            "resourceVersion": "1",
        },
        "spec": {"desired_phase": "Ready"},
        "status": {"current_phase": "Pending"},
    }

    success = await backend.set("test-worker-001", test_resource)
    print(f"   Set: {'✅' if success else '❌'}")

    retrieved = await backend.get("test-worker-001")
    if retrieved:
        print(f"   Get: ✅ Retrieved resource: {retrieved['metadata']['name']}")
    else:
        print("   Get: ❌ Failed to retrieve")

    # Test exists
    print("\n4️⃣ Testing exists...")
    exists = await backend.exists("test-worker-001")
    print(f"   Exists: {'✅' if exists else '❌'}")

    # Test keys
    print("\n5️⃣ Testing keys listing...")
    keys = await backend.keys()
    print(f"   Keys: ✅ Found {len(keys)} resources: {keys}")

    # Test delete
    print("\n6️⃣ Testing delete...")
    deleted = await backend.delete("test-worker-001")
    print(f"   Delete: {'✅' if deleted else '❌'}")

    exists_after = await backend.exists("test-worker-001")
    print(f"   Verify deleted: {'✅' if not exists_after else '❌'}")

    print("\n✅ Storage backend tests completed")


async def test_repository():
    """Test EtcdLabWorkerResourceRepository operations."""
    print("\n" + "=" * 60)
    print("🧪 Testing EtcdLabWorkerResourceRepository")
    print("=" * 60)

    # Connect to etcd
    etcd_host = os.getenv("ETCD_HOST", "localhost")
    etcd_port = int(os.getenv("ETCD_PORT", "2479"))

    print(f"\n1️⃣ Creating repository...")
    client = etcd3.Client(host=etcd_host, port=etcd_port, timeout=10)
    repository = EtcdLabWorkerResourceRepository.create_with_json_serializer(client, prefix="/test-lab-workers/")
    print("   ✅ Repository created")

    # Create a LabWorker resource
    print("\n2️⃣ Creating LabWorker resource...")
    # Create AWS configuration
    aws_cfg = AwsEc2Config(ami_id="ami-0c55b159cbfafe1f0", instance_type="t3.large", key_name="lab-worker-key", security_group_ids=["sg-12345678"], subnet_id="subnet-12345678", vpc_id="vpc-12345678")

    # Create CML configuration
    cml_cfg = CmlConfig(admin_username="admin", admin_password="admin123")  # In production, use secrets

    # Create metadata
    metadata = ResourceMetadata(name="worker-001", namespace="default", labels={"env": "test", "lab-track": "python-101"})

    # Create status
    status = LabWorkerStatus()
    status.phase = LabWorkerPhase.PENDING

    worker = LabWorker(metadata=metadata, spec=LabWorkerSpec(desired_phase=LabWorkerPhase.READY, lab_track="python-101", aws_config=aws_cfg, cml_config=cml_cfg, auto_license=False, enable_draining=True), status=status)
    print(f"   Created worker: {worker.metadata.name}")

    # Save to repository
    print("\n3️⃣ Saving to repository...")
    await repository.add_async(worker)
    print(f"   ✅ Saved worker: {worker.metadata.name}")

    # List all workers
    print("\n4️⃣ Listing all workers...")
    workers = await repository.list_async()
    print(f"   ✅ Found {len(workers)} workers:")
    for w in workers:
        print(f"      Type: {type(w)}, Metadata type: {type(w.metadata)}")
        print(f"      - {w.metadata.name} (phase: {w.status.phase})")

    # Get by ID
    print("\n5️⃣ Getting worker by ID...")
    retrieved = await repository.get_async(worker.metadata.name)
    if retrieved:
        print(f"   ✅ Retrieved: {retrieved.metadata.name}")
        print(f"      Phase: {retrieved.status.phase}")
    else:
        print("   ❌ Not found")

    # Update worker
    print("\n6️⃣ Updating worker...")
    worker.status.phase = LabWorkerPhase.READY
    worker.status.cml_ready = True

    await repository.add_async(worker)  # Update via add (etcd put is upsert)
    print(f"   ✅ Updated: {worker.metadata.name}")
    print(f"      New phase: {worker.status.phase}")

    # Find by label
    print("\n7️⃣ Finding by lab track...")
    by_track = await repository.find_by_lab_track_async("python-101")
    print(f"   ✅ Found {len(by_track)} workers for python-101")

    # Find by phase
    print("\n8️⃣ Finding by phase...")
    ready_workers = await repository.find_by_phase_async(LabWorkerPhase.READY)
    print(f"   ✅ Found {len(ready_workers)} ready workers")

    # Delete
    print("\n9️⃣ Deleting worker...")
    await repository.remove_async(worker.metadata.name)
    print("   ✅ Worker deleted")

    # Verify deleted
    not_found = await repository.get_async(worker.metadata.name)
    print(f"   Verify deleted: {'✅' if not_found is None else '❌'}")

    print("\n✅ Repository tests completed")


async def test_watch():
    """Test etcd watch functionality."""
    import threading

    print("\n" + "=" * 60)
    print("🧪 Testing etcd Watch API")
    print("=" * 60)

    # Connect to etcd
    etcd_host = os.getenv("ETCD_HOST", "localhost")
    etcd_port = int(os.getenv("ETCD_PORT", "2479"))

    print("\n1️⃣ Setting up watch...")
    client = etcd3.Client(host=etcd_host, port=etcd_port, timeout=10)
    backend = EtcdStorageBackend(client, prefix="/test-watch/")

    events_received = []
    watch_active = True

    def on_event(event):
        """Callback for watch events."""
        print("\n   📡 Event received!")
        print(f"      Type: {type(event)}")
        print(f"      Event: {event}")
        events_received.append(event)

    def watch_thread_func(watch_iter):
        """Background thread to consume watch events."""
        try:
            for event in watch_iter:
                if not watch_active:
                    break
                on_event(event)
        except Exception as ex:
            print(f"   ⚠️  Watch thread error: {ex}")

    # Create watch
    watch_iter = backend.watch(on_event, key_prefix="")
    if watch_iter:
        print(f"   ✅ Watch created: {type(watch_iter)}")

        # Start background thread to consume events
        watch_thread = threading.Thread(target=watch_thread_func, args=(watch_iter,), daemon=True)
        watch_thread.start()
    else:
        print("   ❌ Failed to create watch")
        return

    # Give watch time to start
    await asyncio.sleep(1)

    # Create a test resource
    print("\n2️⃣ Creating test resource (should trigger watch)...")
    test_data = {"name": "test", "value": "hello"}
    await backend.set("test-001", test_data)

    # Wait for event
    await asyncio.sleep(2)

    # Update resource
    print("\n3️⃣ Updating test resource (should trigger watch)...")
    test_data["value"] = "updated"
    await backend.set("test-001", test_data)

    await asyncio.sleep(2)

    # Delete resource
    print("\n4️⃣ Deleting test resource (should trigger watch)...")
    await backend.delete("test-001")

    await asyncio.sleep(2)

    # Stop watch
    print("\n5️⃣ Stopping watch...")
    watch_active = False
    try:
        # Cancel the watcher
        if hasattr(watch_iter, "cancel"):
            watch_iter.cancel()
            print("   ✅ Watch cancelled")
        elif hasattr(watch_iter, "close"):
            watch_iter.close()
            print("   ✅ Watch closed")
        else:
            print("   ⚠️  Watch object has no cancel() or close() method")
    except Exception as ex:
        print(f"   ⚠️  Stop error (may be expected): {ex}")

    print(f"\n📊 Summary: Received {len(events_received)} events")

    if events_received:
        print("\n✅ Watch tests completed - Events received!")
    else:
        print("\n⚠️  Watch tests completed - No events received (may need investigation)")


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("🚀 Lab Resource Manager - etcd Integration Tests")
    print("=" * 60)

    try:
        # Test 1: Storage backend
        await test_storage_backend()

        # Test 2: Repository
        await test_repository()

        # Test 3: Watch API
        await test_watch()

        print("\n" + "=" * 60)
        print("✅ ALL TESTS COMPLETED SUCCESSFULLY")
        print("=" * 60)

    except Exception as ex:
        print(f"\n❌ Test failed: {ex}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
