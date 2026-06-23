"""Worker Scheduler Service.

This module implements the intelligent scheduling service that assigns
LabInstanceRequests to appropriate LabWorkers based on capacity, track,
lab type, and scheduling policies.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

from domain.resources.lab_instance_request import LabInstancePhase, LabInstanceRequest
from domain.resources.lab_worker import LabWorker, LabWorkerPhase
from domain.resources.lab_worker_pool import LabWorkerPool

log = logging.getLogger(__name__)


class SchedulingStrategy(str, Enum):
    """Scheduling strategy for worker selection."""

    LEAST_UTILIZED = "LeastUtilized"  # Choose worker with lowest utilization
    LEAST_LABS = "LeastLabs"  # Choose worker with fewest active labs
    ROUND_ROBIN = "RoundRobin"  # Distribute evenly across workers
    BEST_FIT = "BestFit"  # Choose worker that best matches resource requirements
    RANDOM = "Random"  # Random selection from available workers


class SchedulingFailureReason(str, Enum):
    """Reasons why scheduling might fail."""

    NO_WORKERS_AVAILABLE = "NoWorkersAvailable"
    NO_CAPACITY_AVAILABLE = "NoCapacityAvailable"
    NO_MATCHING_TRACK = "NoMatchingTrack"
    NO_MATCHING_TYPE = "NoMatchingType"
    WORKER_NOT_LICENSED = "WorkerNotLicensed"
    WORKER_NOT_READY = "WorkerNotReady"
    INVALID_LAB_TYPE = "InvalidLabType"


@dataclass
class SchedulingDecision:
    """Result of a scheduling decision."""

    success: bool
    worker: Optional[LabWorker] = None
    worker_name: Optional[str] = None
    worker_namespace: Optional[str] = None
    reason: Optional[str] = None
    failure_reason: Optional[SchedulingFailureReason] = None
    candidates_evaluated: int = 0
    scheduling_latency_ms: float = 0.0

    def get_worker_ref(self) -> Optional[str]:
        """Get the worker reference (namespace/name)."""
        if self.worker_namespace and self.worker_name:
            return f"{self.worker_namespace}/{self.worker_name}"
        return None


@dataclass
class WorkerScore:
    """Scoring information for a worker candidate."""

    worker: LabWorker
    score: float  # 0.0 to 1.0, higher is better
    utilization: float  # 0.0 to 1.0
    active_labs: int
    available_capacity: bool
    matches_track: bool
    matches_type: bool
    is_licensed: bool
    reasons: list[str]


class WorkerSchedulerService:
    """
    Service for scheduling LabInstanceRequests to LabWorkers.

    Responsibilities:
    - Find appropriate workers based on lab requirements
    - Consider capacity, track, and lab type
    - Apply scheduling strategy
    - Track scheduling metrics
    - Handle scheduling failures
    """

    def __init__(
        self,
        strategy: SchedulingStrategy = SchedulingStrategy.BEST_FIT,
        require_licensed_for_cml: bool = True,
    ):
        self.strategy = strategy
        self.require_licensed_for_cml = require_licensed_for_cml
        self._round_robin_index: dict[str, int] = {}  # Track per lab-track

    async def schedule_lab_instance(
        self,
        lab_request: LabInstanceRequest,
        available_workers: list[LabWorker],
        pools: Optional[list[LabWorkerPool]] = None,
    ) -> SchedulingDecision:
        """
        Schedule a lab instance request to an appropriate worker.

        Args:
            lab_request: The lab instance request to schedule
            available_workers: List of workers that could potentially host the lab
            pools: Optional list of worker pools for pool-aware scheduling

        Returns:
            SchedulingDecision with the selected worker or failure reason
        """
        start_time = datetime.now()

        log.info(f"Scheduling lab request {lab_request.metadata.name} " f"(type: {lab_request.spec.lab_instance_type}, " f"track: {lab_request.spec.lab_track})")

        # Validate lab request
        if not self._validate_lab_request(lab_request):
            return SchedulingDecision(
                success=False,
                failure_reason=SchedulingFailureReason.INVALID_LAB_TYPE,
                reason="Invalid lab request configuration",
            )

        # Filter workers based on lab requirements
        candidate_workers = self._filter_workers(lab_request, available_workers)

        if not candidate_workers:
            log.warning(f"No candidate workers found for lab request {lab_request.metadata.name}")
            return self._create_failure_decision(available_workers, lab_request, start_time)

        log.debug(f"Found {len(candidate_workers)} candidate workers for " f"{lab_request.metadata.name}")

        # Score and rank workers
        scored_workers = self._score_workers(lab_request, candidate_workers)

        if not scored_workers:
            return SchedulingDecision(
                success=False,
                failure_reason=SchedulingFailureReason.NO_CAPACITY_AVAILABLE,
                reason="No workers have sufficient capacity",
                candidates_evaluated=len(candidate_workers),
                scheduling_latency_ms=(datetime.now() - start_time).total_seconds() * 1000,
            )

        # Select best worker based on strategy
        selected_worker = self._select_worker(lab_request, scored_workers, self.strategy)

        if not selected_worker:
            return SchedulingDecision(
                success=False,
                failure_reason=SchedulingFailureReason.NO_WORKERS_AVAILABLE,
                reason="Failed to select worker from candidates",
                candidates_evaluated=len(candidate_workers),
                scheduling_latency_ms=(datetime.now() - start_time).total_seconds() * 1000,
            )

        latency_ms = (datetime.now() - start_time).total_seconds() * 1000

        log.info(f"Scheduled lab {lab_request.metadata.name} to worker " f"{selected_worker.worker.metadata.name} " f"(score: {selected_worker.score:.2f}, latency: {latency_ms:.2f}ms)")

        return SchedulingDecision(
            success=True,
            worker=selected_worker.worker,
            worker_name=selected_worker.worker.metadata.name,
            worker_namespace=selected_worker.worker.metadata.namespace,
            reason="; ".join(selected_worker.reasons),
            candidates_evaluated=len(candidate_workers),
            scheduling_latency_ms=latency_ms,
        )

    def _validate_lab_request(self, lab_request: LabInstanceRequest) -> bool:
        """Validate that the lab request is valid for scheduling."""
        # Must be in PENDING or SCHEDULING phase
        if lab_request.status.phase not in [
            LabInstancePhase.PENDING,
            LabInstancePhase.SCHEDULING,
        ]:
            log.warning(f"Lab request {lab_request.metadata.name} is in invalid phase " f"{lab_request.status.phase} for scheduling")
            return False

        # Must not already be assigned
        if lab_request.is_assigned_to_worker():
            log.warning(f"Lab request {lab_request.metadata.name} is already assigned to worker")
            return False

        # Spec must be valid
        spec_errors = lab_request.spec.validate()
        if spec_errors:
            log.warning(f"Lab request {lab_request.metadata.name} has invalid spec: {spec_errors}")
            return False

        return True

    def _filter_workers(self, lab_request: LabInstanceRequest, workers: list[LabWorker]) -> list[LabWorker]:
        """Filter workers that can potentially host this lab."""
        candidates = []

        for worker in workers:
            # Must be in ready or active phase
            if worker.status.phase not in [
                LabWorkerPhase.READY,
                LabWorkerPhase.ACTIVE,
                LabWorkerPhase.READY_UNLICENSED,
            ]:
                continue

            # CML labs require CML workers
            if lab_request.is_cml_type():
                # CML requires licensed worker (unless disabled)
                if self.require_licensed_for_cml and not worker.status.cml_licensed:
                    continue

            # VM labs require appropriate worker type
            # (For now, we assume CML workers can host VM-type labs)
            if lab_request.is_vm_type():
                # Could add additional filtering here
                pass

            # Container labs can run on any worker
            # (Would typically use a different path/scheduler for pure containers)

            # Check track matching if track is specified
            if lab_request.spec.lab_track:
                # Track could be stored in worker labels/annotations
                # For now, we assume workers are grouped by pools which have tracks
                # This filtering would be enhanced in production
                pass

            candidates.append(worker)

        return candidates

    def _score_workers(self, lab_request: LabInstanceRequest, workers: list[LabWorker]) -> list[WorkerScore]:
        """Score workers based on various criteria."""
        scored_workers = []

        for worker in workers:
            score_info = self._calculate_worker_score(lab_request, worker)
            if score_info.score > 0:
                scored_workers.append(score_info)

        # Sort by score (highest first)
        scored_workers.sort(key=lambda x: x.score, reverse=True)

        return scored_workers

    def _calculate_worker_score(self, lab_request: LabInstanceRequest, worker: LabWorker) -> WorkerScore:
        """Calculate a score for a worker based on lab requirements."""
        reasons = []
        score = 0.0

        # Check capacity availability
        has_capacity = False
        utilization = 1.0

        if worker.status.capacity:
            capacity = worker.status.capacity

            # Check if worker can accommodate the lab
            cpu_util = capacity.cpu_utilization_percent or 0.0
            mem_util = capacity.memory_utilization_percent or 0.0
            storage_util = capacity.storage_utilization_percent or 0.0

            utilization = (cpu_util + mem_util + storage_util) / 300.0  # Average

            # Consider worker available if utilization < 80%
            if cpu_util < 80.0 and mem_util < 80.0 and storage_util < 80.0:
                has_capacity = True
                score += 0.4
                reasons.append("has_capacity")
            else:
                reasons.append("insufficient_capacity")
                return WorkerScore(
                    worker=worker,
                    score=0.0,
                    utilization=utilization,
                    active_labs=worker.status.active_lab_count,
                    available_capacity=False,
                    matches_track=False,
                    matches_type=False,
                    is_licensed=worker.status.cml_licensed,
                    reasons=reasons,
                )

        # Check active lab count
        active_labs = worker.status.active_lab_count
        if active_labs < 15:  # Reasonable limit
            score += 0.2
            reasons.append(f"active_labs:{active_labs}")
        else:
            reasons.append(f"too_many_labs:{active_labs}")

        # Bonus for lower utilization (prefer less utilized workers)
        utilization_bonus = (1.0 - utilization) * 0.2
        score += utilization_bonus
        reasons.append(f"utilization:{utilization:.2f}")

        # Bonus for licensed workers (for CML labs)
        is_licensed = worker.status.cml_licensed
        if lab_request.is_cml_type() and is_licensed:
            score += 0.1
            reasons.append("licensed")

        # Bonus for ready phase (vs active)
        if worker.status.phase == LabWorkerPhase.READY:
            score += 0.05
            reasons.append("ready_phase")

        # Track matching (would be enhanced with actual track data)
        matches_track = True  # Placeholder
        if lab_request.spec.lab_track:
            # Could check worker labels/pool membership
            # For now, assume all workers match
            score += 0.05
            reasons.append(f"track:{lab_request.spec.lab_track}")

        # Type matching
        matches_type = True
        if lab_request.is_cml_type():
            # Verify worker is CML-capable
            if worker.status.cml_ready:
                score += 0.1
                reasons.append("cml_capable")
            else:
                matches_type = False
                reasons.append("not_cml_capable")
                score = 0.0

        return WorkerScore(
            worker=worker,
            score=score,
            utilization=utilization,
            active_labs=active_labs,
            available_capacity=has_capacity,
            matches_track=matches_track,
            matches_type=matches_type,
            is_licensed=is_licensed,
            reasons=reasons,
        )

    def _select_worker(
        self,
        lab_request: LabInstanceRequest,
        scored_workers: list[WorkerScore],
        strategy: SchedulingStrategy,
    ) -> Optional[WorkerScore]:
        """Select the best worker based on scheduling strategy."""
        if not scored_workers:
            return None

        if strategy == SchedulingStrategy.BEST_FIT:
            # Return highest scoring worker
            return scored_workers[0]

        elif strategy == SchedulingStrategy.LEAST_UTILIZED:
            # Return worker with lowest utilization
            scored_workers.sort(key=lambda x: x.utilization)
            return scored_workers[0]

        elif strategy == SchedulingStrategy.LEAST_LABS:
            # Return worker with fewest active labs
            scored_workers.sort(key=lambda x: x.active_labs)
            return scored_workers[0]

        elif strategy == SchedulingStrategy.ROUND_ROBIN:
            # Distribute evenly across workers
            track = lab_request.spec.lab_track or "default"
            if track not in self._round_robin_index:
                self._round_robin_index[track] = 0

            index = self._round_robin_index[track] % len(scored_workers)
            self._round_robin_index[track] += 1
            return scored_workers[index]

        elif strategy == SchedulingStrategy.RANDOM:
            # Random selection
            import random

            return random.choice(scored_workers)

        else:
            # Default to best fit
            return scored_workers[0]

    def _create_failure_decision(
        self,
        workers: list[LabWorker],
        lab_request: LabInstanceRequest,
        start_time: datetime,
    ) -> SchedulingDecision:
        """Create a scheduling decision for failure case."""
        latency_ms = (datetime.now() - start_time).total_seconds() * 1000

        # Determine the most specific failure reason
        if not workers:
            failure_reason = SchedulingFailureReason.NO_WORKERS_AVAILABLE
            reason = "No workers available in the cluster"
        else:
            # Check why workers were filtered out
            ready_workers = [
                w
                for w in workers
                if w.status.phase
                in [
                    LabWorkerPhase.READY,
                    LabWorkerPhase.ACTIVE,
                    LabWorkerPhase.READY_UNLICENSED,
                ]
            ]

            if not ready_workers:
                failure_reason = SchedulingFailureReason.WORKER_NOT_READY
                reason = f"No workers in ready state (total: {len(workers)})"
            elif lab_request.is_cml_type():
                licensed_workers = [w for w in ready_workers if w.status.cml_licensed]
                if not licensed_workers:
                    failure_reason = SchedulingFailureReason.WORKER_NOT_LICENSED
                    reason = "No licensed workers available for CML lab"
                else:
                    failure_reason = SchedulingFailureReason.NO_CAPACITY_AVAILABLE
                    reason = "No workers have sufficient capacity"
            else:
                failure_reason = SchedulingFailureReason.NO_CAPACITY_AVAILABLE
                reason = "No workers have sufficient capacity"

        return SchedulingDecision(
            success=False,
            failure_reason=failure_reason,
            reason=reason,
            candidates_evaluated=len(workers),
            scheduling_latency_ms=latency_ms,
        )

    # Pool-aware scheduling methods

    async def schedule_with_pools(
        self,
        lab_request: LabInstanceRequest,
        pools: list[LabWorkerPool],
    ) -> SchedulingDecision:
        """
        Schedule a lab instance using pool-aware scheduling.

        This method first selects the appropriate pool based on the lab track,
        then schedules within that pool.
        """
        start_time = datetime.now()

        # Find pools matching the lab track
        matching_pools = self._find_matching_pools(lab_request, pools)

        if not matching_pools:
            log.warning(f"No pools found matching track '{lab_request.spec.lab_track}' " f"for lab request {lab_request.metadata.name}")
            return SchedulingDecision(
                success=False,
                failure_reason=SchedulingFailureReason.NO_MATCHING_TRACK,
                reason=f"No pools available for track '{lab_request.spec.lab_track}'",
                scheduling_latency_ms=(datetime.now() - start_time).total_seconds() * 1000,
            )

        # Select best pool based on available capacity
        selected_pool = self._select_pool(lab_request, matching_pools)

        if not selected_pool:
            return SchedulingDecision(
                success=False,
                failure_reason=SchedulingFailureReason.NO_CAPACITY_AVAILABLE,
                reason="No pools have sufficient capacity",
                scheduling_latency_ms=(datetime.now() - start_time).total_seconds() * 1000,
            )

        # Get workers from the selected pool
        pool_workers = self._get_workers_from_pool(selected_pool)

        # Schedule within the selected pool
        return await self.schedule_lab_instance(lab_request, pool_workers, [selected_pool])

    def _find_matching_pools(self, lab_request: LabInstanceRequest, pools: list[LabWorkerPool]) -> list[LabWorkerPool]:
        """Find pools that match the lab request requirements."""
        if not lab_request.spec.lab_track:
            # No track specified, return all ready pools
            return [p for p in pools if p.is_ready()]

        matching_pools = []
        for pool in pools:
            # Check if pool serves the required track
            if pool.spec.lab_track == lab_request.spec.lab_track and pool.is_ready():
                matching_pools.append(pool)

        return matching_pools

    def _select_pool(self, lab_request: LabInstanceRequest, pools: list[LabWorkerPool]) -> Optional[LabWorkerPool]:
        """Select the best pool for hosting the lab."""
        if not pools:
            return None

        # Score pools based on available capacity
        pool_scores = []
        for pool in pools:
            capacity = pool.status.capacity
            if capacity.ready_workers > 0:
                # Score based on available capacity and utilization
                utilization = capacity.get_overall_utilization()
                score = (1.0 - utilization) * capacity.ready_workers
                pool_scores.append((pool, score))

        if not pool_scores:
            return None

        # Return pool with highest score
        pool_scores.sort(key=lambda x: x[1], reverse=True)
        return pool_scores[0][0]

    def _get_workers_from_pool(self, pool: LabWorkerPool) -> list[LabWorker]:
        """Get worker resources from a pool."""
        # TODO: This would query the actual worker resources
        # For now, this is a placeholder that would be implemented
        # when we have the ResourceRepository integrated
        return []
