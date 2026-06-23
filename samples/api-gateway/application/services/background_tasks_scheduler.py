import asyncio
import datetime
import inspect
import logging
import typing
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.jobstores.redis import RedisJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from neuroglia.core import ModuleLoader, TypeFinder
from neuroglia.hosting.abstractions import ApplicationBuilderBase, HostedService
from neuroglia.reactive import AsyncRx
from rx.subject.subject import Subject

from application.exceptions import ApplicationException

log = logging.getLogger(__name__)


def backgroundjob(type: Optional[str] = None):
    """Marks a class as a background task that will be scheduled by the BackgroundTaskScheduler.
    This is required so that the BackgroundTaskScheduler can automatically find the class and instantiate it when needed.
    """

    def decorator(cls):
        """Adds metadata to the class with the specified schedule_at_field_name"""
        cls.__background_task_class_name__ = cls.__name__
        cls.__background_task_type__ = type if type == "scheduled" or type == "recurrent" else None
        return cls

    return decorator


class BackgroundJob(ABC):
    """Defines the fundamentals of a background job"""

    __background_task_type__: Optional[str] = None

    __task_id__: Optional[str] = None

    __task_name__: Optional[str] = None

    __task_type__: Optional[str] = None

    @abstractmethod
    def configure(self, *args, **kwargs):
        """Instantiate the necessary dependencies"""


class ScheduledBackgroundJob(BackgroundJob, ABC):
    """Defines the fundamentals of a background job"""

    __scheduled_at__: Optional[datetime.datetime] = None

    @abstractmethod
    async def run_at(self, *args, **kwargs):
        """Args must be serializable"""


class RecurrentBackgroundJob(BackgroundJob, ABC):
    """Defines the fundamentals of a background job"""

    __interval__: Optional[int] = None

    @abstractmethod
    async def run_every(self, *args, **kwargs):
        """Args must be serializable"""


@dataclass
class TaskDescriptor:
    """Represents the description of the task that will be passed through the bus and instantiated then executed by the background scheduler."""

    id: str

    name: str

    data: dict


@dataclass
class ScheduledTaskDescriptor(TaskDescriptor):
    """Represents a serialized description of the task that will be scheduled."""

    scheduled_at: datetime.datetime


@dataclass
class RecurrentTaskDescriptor(TaskDescriptor):
    """Represents a serialized description of the task that will be executed recurrently."""

    interval: int

    started_at: Optional[datetime.datetime] = None


class BackgroundTasksBus:
    """Defines the fundamentals of a service used to manage incoming and outgoing streams of background tasks"""

    input_stream: Subject = Subject()
    """ Gets the stream of events ingested by the BackgroundTaskScheduler """


class BackgroundTaskSchedulerOptions:
    """Represents the mapping between background task types and Python types"""

    type_maps: dict[str, typing.Type] = dict[str, typing.Type]()
    """ Gets/sets a task type mapping of all supported tasks"""


async def scheduled_job_wrapper(t, **kwargs):
    """Define wrapper function to pass the task instance to the job function"""
    # Call the run method of the task
    job_func = t.run_at
    return await job_func(**kwargs)


async def recurrent_job_wrapper(t, **kwargs):
    """Define wrapper function to pass the task instance to the job function"""
    # Call the run method of the task
    job_func = t.run_every
    return await job_func(**kwargs)


class BackgroundTaskScheduler(HostedService):
    """Represents the service used to schedule background tasks"""

    _options: BackgroundTaskSchedulerOptions

    _background_task_bus: BackgroundTasksBus

    _scheduler: AsyncIOScheduler

    def __init__(self, options: BackgroundTaskSchedulerOptions, background_task_bus: BackgroundTasksBus, scheduler: AsyncIOScheduler):
        self._options = options
        self._background_task_bus = background_task_bus
        if scheduler is None:
            raise ValueError("AsyncIOScheduler instance is required")
        self._scheduler = scheduler

    async def start_async(self):
        log.info("Starting background task scheduler")
        self._scheduler.start()
        AsyncRx.subscribe(self._background_task_bus.input_stream, lambda t: asyncio.ensure_future(self._on_job_request_async(t)))

    async def stop_async(self):
        log.info("Stopping background task scheduler")
        # Prevent blocking on shutdown
        self._scheduler.shutdown(wait=False)
        # Wait for currently running jobs to finish (optional)
        running_jobs = self._scheduler.get_jobs()
        if running_jobs:
            tasks = [asyncio.create_task(job.modify(next_run_time=None)) for job in running_jobs]
            await asyncio.gather(*tasks)  # Wait for modifications (cancellation) to finish

    async def _on_job_request_async(self, task_descriptor: TaskDescriptor):
        # Find the Python type of the task
        task_type = self._options.type_maps.get(task_descriptor.name, None)
        if task_type is None:
            logging.warning(f"Ignored incoming job request: the specified type '{task_descriptor.name}' is not supported. Did you forget to put the '@backgroundjob' decorator on the class?")
            return
        await self.enqueue_task_async(self.deserialize_task(task_type, task_descriptor))

    def deserialize_task(self, task_type: typing.Type, task_descriptor: TaskDescriptor) -> BackgroundJob:
        """Deserialize the task into its Python type and return the instance"""
        try:
            t: BackgroundJob = object.__new__(task_type)  # type: ignore
            t.__dict__ = task_descriptor.data
            t.__task_id__ = task_descriptor.id
            t.__task_name__ = task_descriptor.name
            t.__task_type__ = None

            if isinstance(task_descriptor, ScheduledTaskDescriptor) and t.__background_task_type__ == "scheduled":
                t.__scheduled_at__ = task_descriptor.scheduled_at  # type: ignore
                t.__task_type__ = "ScheduledTaskDescriptor"

            if isinstance(task_descriptor, RecurrentTaskDescriptor) and t.__background_task_type__ == "recurrent":
                t.__interval__ = task_descriptor.interval  # type: ignore
                t.__task_type__ = "RecurrentTaskDescriptor"

            return t
        except Exception as ex:
            logging.error(f"An error occured while reading a task of type '{task_type.type}': '{ex}'")
            raise

    async def enqueue_task_async(self, task: BackgroundJob):
        """Enqueues a task to be scheduled by the background task scheduler"""
        try:
            kwargs = {k: v for k, v in task.__dict__.items() if not k.startswith("_")}

            if isinstance(task, ScheduledBackgroundJob):
                self._scheduler.add_job(
                    scheduled_job_wrapper,
                    "date",
                    run_date=task.__scheduled_at__,
                    id=task.__task_id__,
                    kwargs=kwargs,
                    misfire_grace_time=None,
                    args=(task,),
                )

            if isinstance(task, RecurrentBackgroundJob):
                self._scheduler.add_job(
                    recurrent_job_wrapper,
                    "interval",
                    seconds=task.__interval__,
                    id=task.__task_id__,
                    kwargs=kwargs,
                    misfire_grace_time=None,
                    args=(task,),
                )

        except Exception as ex:
            logging.error(f"An error occured while dispatching a task of type '{type(task.__task_type__)}': '{ex}'")
            raise

    def list_tasks(self):
        """List all scheduled tasks"""
        return self._scheduler.get_jobs()

    def stop_task(self, task_id: str):
        """Stop a scheduled task"""
        self._scheduler.remove_job(task_id)

    @staticmethod
    def configure(builder: ApplicationBuilderBase, modules: list[str]) -> ApplicationBuilderBase:
        """Registers and configures background tasks related services to the specified service collection.

        Args:
            services (ServiceCollection): the service collection to configure
            modules (List[str]): a list containing the names of the modules to scan for classes marked with the 'backgroundtask' decorator. Marked classes as used tasks that will be registered in the Scheduler
        """
        options: BackgroundTaskSchedulerOptions = BackgroundTaskSchedulerOptions()
        for module in [ModuleLoader.load(module_name) for module_name in modules]:
            for background_task in TypeFinder.get_types(module, lambda cls: inspect.isclass(cls) and hasattr(cls, "__background_task_class_name__")):
                background_task_name = background_task.__background_task_class_name__
                background_task_type = background_task.__background_task_type__
                options.type_maps[background_task_name] = background_task
                builder.services.add_transient(background_task, background_task)
                log.debug(f"Registered background task '{background_task_name}' of type '{background_task_type}'")

        if not "redis_host" in builder.settings.background_job_store or not "redis_port" in builder.settings.background_job_store or not "redis_db" in builder.settings.background_job_store:
            raise ApplicationException(f"Redis connection string for background_job_store not found in the application settings")

        jobstores = {"default": RedisJobStore(host=builder.settings.background_job_store["redis_host"], port=builder.settings.background_job_store["redis_port"], db=builder.settings.background_job_store["redis_db"])}
        builder.services.add_singleton(AsyncIOScheduler, singleton=AsyncIOScheduler(executor=AsyncIOExecutor(), jobstores=jobstores))
        builder.services.try_add_singleton(BackgroundTasksBus)
        builder.services.add_singleton(BackgroundTaskSchedulerOptions, singleton=options)
        builder.services.add_singleton(HostedService, BackgroundTaskScheduler)
        builder.services.add_singleton(BackgroundTaskScheduler, BackgroundTaskScheduler)
        return builder
