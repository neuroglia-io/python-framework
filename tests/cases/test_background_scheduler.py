"""Tests for the Background Task Scheduler module."""

import datetime
import logging
import pytest
from unittest.mock import Mock, patch, AsyncMock

from neuroglia.application.background_scheduler import (
    BackgroundJob,
    ScheduledBackgroundJob,
    RecurrentBackgroundJob,
    backgroundjob,
    TaskDescriptor,
    ScheduledTaskDescriptor,
    RecurrentTaskDescriptor,
    BackgroundTasksBus,
    BackgroundTaskScheduler,
    BackgroundTaskSchedulerOptions,
    BackgroundTaskException,
    scheduled_job_wrapper,
    recurrent_job_wrapper,
)

# Mock APScheduler components since they're optional dependencies
try:
    import apscheduler  # noqa: F401

    APSCHEDULER_AVAILABLE = True
except ImportError:
    APSCHEDULER_AVAILABLE = False


# Test background job classes
@backgroundjob("scheduled")
class TestScheduledJob(ScheduledBackgroundJob):
    def __init__(self, test_data: str = "test"):
        self.test_data = test_data
        self.__task_id__ = "test-scheduled-123"
        self.__task_name__ = "TestScheduledJob"
        self.__scheduled_at__ = datetime.datetime.now() + datetime.timedelta(seconds=1)

    def configure(self, *args, **kwargs):
        pass

    async def run_at(self, *args, **kwargs):
        logging.info(f"Running scheduled job with data: {self.test_data}")
        return f"Scheduled job executed: {self.test_data}"


@backgroundjob("recurrent")
class TestRecurrentJob(RecurrentBackgroundJob):
    def __init__(self, test_data: str = "recurring"):
        self.test_data = test_data
        self.__task_id__ = "test-recurrent-456"
        self.__task_name__ = "TestRecurrentJob"
        self.__interval__ = 5

    def configure(self, *args, **kwargs):
        pass

    async def run_every(self, *args, **kwargs):
        logging.info(f"Running recurrent job with data: {self.test_data}")
        return f"Recurrent job executed: {self.test_data}"


@backgroundjob()
class TestBackgroundJob(BackgroundJob):
    def __init__(self, test_data: str = "generic"):
        self.test_data = test_data
        self.__task_id__ = "test-background-789"
        self.__task_name__ = "TestBackgroundJob"

    def configure(self, *args, **kwargs):
        pass


class TestBackgroundJobDecorator:
    """Test the @backgroundjob decorator functionality."""

    def test_backgroundjob_decorator_with_scheduled_type(self):
        """Test backgroundjob decorator with scheduled type."""
        assert hasattr(TestScheduledJob, "__background_task_class_name__")
        assert TestScheduledJob.__background_task_class_name__ == "TestScheduledJob"
        assert TestScheduledJob.__background_task_type__ == "scheduled"

    def test_backgroundjob_decorator_with_recurrent_type(self):
        """Test backgroundjob decorator with recurrent type."""
        assert hasattr(TestRecurrentJob, "__background_task_class_name__")
        assert TestRecurrentJob.__background_task_class_name__ == "TestRecurrentJob"
        assert TestRecurrentJob.__background_task_type__ == "recurrent"

    def test_backgroundjob_decorator_without_type(self):
        """Test backgroundjob decorator without specific type."""
        assert hasattr(TestBackgroundJob, "__background_task_class_name__")
        assert TestBackgroundJob.__background_task_class_name__ == "TestBackgroundJob"
        assert TestBackgroundJob.__background_task_type__ is None


class TestTaskDescriptors:
    """Test task descriptor classes."""

    def test_task_descriptor_creation(self):
        """Test basic TaskDescriptor creation."""
        descriptor = TaskDescriptor(id="task-123", name="TestTask", data={"key": "value"})
        assert descriptor.id == "task-123"
        assert descriptor.name == "TestTask"
        assert descriptor.data == {"key": "value"}

    def test_scheduled_task_descriptor_creation(self):
        """Test ScheduledTaskDescriptor creation."""
        scheduled_at = datetime.datetime.now()
        descriptor = ScheduledTaskDescriptor(
            id="scheduled-123",
            name="TestScheduledTask",
            data={"key": "value"},
            scheduled_at=scheduled_at,
        )
        assert descriptor.id == "scheduled-123"
        assert descriptor.name == "TestScheduledTask"
        assert descriptor.scheduled_at == scheduled_at

    def test_recurrent_task_descriptor_creation(self):
        """Test RecurrentTaskDescriptor creation."""
        started_at = datetime.datetime.now()
        descriptor = RecurrentTaskDescriptor(
            id="recurrent-456",
            name="TestRecurrentTask",
            data={"key": "value"},
            interval=60,
            started_at=started_at,
        )
        assert descriptor.id == "recurrent-456"
        assert descriptor.name == "TestRecurrentTask"
        assert descriptor.interval == 60
        assert descriptor.started_at == started_at


class TestBackgroundTasksBus:
    """Test the BackgroundTasksBus functionality."""

    def test_background_tasks_bus_creation(self):
        """Test BackgroundTasksBus creation."""
        bus = BackgroundTasksBus()
        assert bus.input_stream is not None

    def test_schedule_task(self):
        """Test scheduling a task through the bus."""
        bus = BackgroundTasksBus()
        task_descriptor = TaskDescriptor(id="test-123", name="TestTask", data={"test": "data"})

        # Mock observer to capture the task
        received_tasks = []

        def task_observer(task):
            received_tasks.append(task)

        bus.input_stream.subscribe(task_observer)
        bus.schedule_task(task_descriptor)

        assert len(received_tasks) == 1
        assert received_tasks[0] == task_descriptor

    def test_dispose(self):
        """Test disposing of the bus."""
        bus = BackgroundTasksBus()
        # Should not raise an exception
        bus.dispose()


class TestBackgroundTaskSchedulerOptions:
    """Test BackgroundTaskSchedulerOptions functionality."""

    def test_options_creation(self):
        """Test creating scheduler options."""
        options = BackgroundTaskSchedulerOptions()
        assert len(options.type_maps) == 0

    def test_register_task_type(self):
        """Test registering a task type."""
        options = BackgroundTaskSchedulerOptions()
        options.register_task_type("TestJob", TestScheduledJob)

        assert "TestJob" in options.type_maps
        assert options.type_maps["TestJob"] == TestScheduledJob

    def test_get_task_type(self):
        """Test getting a registered task type."""
        options = BackgroundTaskSchedulerOptions()
        options.register_task_type("TestJob", TestScheduledJob)

        task_type = options.get_task_type("TestJob")
        assert task_type == TestScheduledJob

        unknown_type = options.get_task_type("UnknownJob")
        assert unknown_type is None


@pytest.mark.asyncio
class TestJobWrappers:
    """Test the job wrapper functions."""

    async def test_scheduled_job_wrapper_success(self):
        """Test successful execution of scheduled job wrapper."""
        job = TestScheduledJob("test-data")
        result = await scheduled_job_wrapper(job, test_param="value")
        assert "Scheduled job executed: test-data" in result

    async def test_scheduled_job_wrapper_exception(self):
        """Test scheduled job wrapper handling exceptions."""
        job = TestScheduledJob()
        # Mock the run_at method to raise an exception
        job.run_at = AsyncMock(side_effect=Exception("Test error"))

        with pytest.raises(Exception) as exc_info:
            await scheduled_job_wrapper(job)
        assert "Test error" in str(exc_info.value)

    async def test_recurrent_job_wrapper_success(self):
        """Test successful execution of recurrent job wrapper."""
        job = TestRecurrentJob("recurring-data")
        result = await recurrent_job_wrapper(job, test_param="value")
        assert "Recurrent job executed: recurring-data" in result

    async def test_recurrent_job_wrapper_exception(self):
        """Test recurrent job wrapper handling exceptions."""
        job = TestRecurrentJob()
        # Mock the run_every method to raise an exception
        job.run_every = AsyncMock(side_effect=Exception("Recurring error"))

        with pytest.raises(Exception) as exc_info:
            await recurrent_job_wrapper(job)
        assert "Recurring error" in str(exc_info.value)


@pytest.mark.skipif(not APSCHEDULER_AVAILABLE, reason="APScheduler not available")
@pytest.mark.asyncio
class TestBackgroundTaskScheduler:
    """Test BackgroundTaskScheduler functionality."""

    def setup_method(self):
        """Set up test dependencies."""
        self.options = BackgroundTaskSchedulerOptions()
        self.options.register_task_type("TestScheduledJob", TestScheduledJob)
        self.options.register_task_type("TestRecurrentJob", TestRecurrentJob)

        self.task_bus = BackgroundTasksBus()

        # Mock scheduler to avoid actual scheduling during tests
        self.mock_scheduler = Mock()
        self.mock_scheduler.start = Mock()
        self.mock_scheduler.shutdown = Mock()
        self.mock_scheduler.add_job = Mock()
        self.mock_scheduler.get_jobs = Mock(return_value=[])
        self.mock_scheduler.remove_job = Mock()
        self.mock_scheduler.get_job = Mock(return_value=None)

    async def test_scheduler_creation(self):
        """Test creating a background task scheduler."""
        with patch(
            "neuroglia.application.background_scheduler.AsyncIOScheduler",
            return_value=self.mock_scheduler,
        ):
            scheduler = BackgroundTaskScheduler(self.options, self.task_bus, self.mock_scheduler)
            assert scheduler._options == self.options
            assert scheduler._background_task_bus == self.task_bus

    async def test_scheduler_start_async(self):
        """Test starting the scheduler."""
        with patch(
            "neuroglia.application.background_scheduler.AsyncIOScheduler",
            return_value=self.mock_scheduler,
        ):
            scheduler = BackgroundTaskScheduler(self.options, self.task_bus, self.mock_scheduler)

            await scheduler.start_async()

            self.mock_scheduler.start.assert_called_once()
            assert scheduler._started is True

    async def test_scheduler_stop_async(self):
        """Test stopping the scheduler."""
        with patch(
            "neuroglia.application.background_scheduler.AsyncIOScheduler",
            return_value=self.mock_scheduler,
        ):
            scheduler = BackgroundTaskScheduler(self.options, self.task_bus, self.mock_scheduler)
            scheduler._started = True

            await scheduler.stop_async()

            self.mock_scheduler.shutdown.assert_called_once_with(wait=False)
            assert scheduler._started is False

    async def test_deserialize_scheduled_task(self):
        """Test deserializing a scheduled task."""
        with patch(
            "neuroglia.application.background_scheduler.AsyncIOScheduler",
            return_value=self.mock_scheduler,
        ):
            scheduler = BackgroundTaskScheduler(self.options, self.task_bus, self.mock_scheduler)

            scheduled_at = datetime.datetime.now()
            descriptor = ScheduledTaskDescriptor(
                id="test-123",
                name="TestScheduledJob",
                data={"test_data": "value"},
                scheduled_at=scheduled_at,
            )

            task = scheduler.deserialize_task(TestScheduledJob, descriptor)

            assert task.__task_id__ == "test-123"
            assert task.__task_name__ == "TestScheduledJob"
            assert task.test_data == "value"
            assert task.__scheduled_at__ == scheduled_at

    async def test_deserialize_recurrent_task(self):
        """Test deserializing a recurrent task."""
        with patch(
            "neuroglia.application.background_scheduler.AsyncIOScheduler",
            return_value=self.mock_scheduler,
        ):
            scheduler = BackgroundTaskScheduler(self.options, self.task_bus, self.mock_scheduler)

            descriptor = RecurrentTaskDescriptor(
                id="test-456", name="TestRecurrentJob", data={"test_data": "recurring"}, interval=30
            )

            task = scheduler.deserialize_task(TestRecurrentJob, descriptor)

            assert task.__task_id__ == "test-456"
            assert task.__task_name__ == "TestRecurrentJob"
            assert task.test_data == "recurring"
            assert task.__interval__ == 30

    async def test_enqueue_scheduled_task(self):
        """Test enqueuing a scheduled task."""
        with patch(
            "neuroglia.application.background_scheduler.AsyncIOScheduler",
            return_value=self.mock_scheduler,
        ):
            scheduler = BackgroundTaskScheduler(self.options, self.task_bus, self.mock_scheduler)

            task = TestScheduledJob("test-data")
            await scheduler.enqueue_task_async(task)

            self.mock_scheduler.add_job.assert_called_once()
            call_args = self.mock_scheduler.add_job.call_args
            assert call_args[1]["trigger"] == "date"
            assert call_args[1]["id"] == task.__task_id__

    async def test_enqueue_recurrent_task(self):
        """Test enqueuing a recurrent task."""
        with patch(
            "neuroglia.application.background_scheduler.AsyncIOScheduler",
            return_value=self.mock_scheduler,
        ):
            scheduler = BackgroundTaskScheduler(self.options, self.task_bus, self.mock_scheduler)

            task = TestRecurrentJob("recurring-data")
            await scheduler.enqueue_task_async(task)

            self.mock_scheduler.add_job.assert_called_once()
            call_args = self.mock_scheduler.add_job.call_args
            assert call_args[1]["trigger"] == "interval"
            assert call_args[1]["seconds"] == task.__interval__
            assert call_args[1]["id"] == task.__task_id__

    def test_list_tasks(self):
        """Test listing scheduled tasks."""
        with patch(
            "neuroglia.application.background_scheduler.AsyncIOScheduler",
            return_value=self.mock_scheduler,
        ):
            scheduler = BackgroundTaskScheduler(self.options, self.task_bus, self.mock_scheduler)
            mock_jobs = [Mock(), Mock()]
            self.mock_scheduler.get_jobs.return_value = mock_jobs

            tasks = scheduler.list_tasks()
            assert tasks == mock_jobs

    def test_stop_task(self):
        """Test stopping a task."""
        with patch(
            "neuroglia.application.background_scheduler.AsyncIOScheduler",
            return_value=self.mock_scheduler,
        ):
            scheduler = BackgroundTaskScheduler(self.options, self.task_bus, self.mock_scheduler)

            result = scheduler.stop_task("test-task-id")

            self.mock_scheduler.remove_job.assert_called_once_with("test-task-id")
            assert result is True

    def test_get_task_info(self):
        """Test getting task information."""
        with patch(
            "neuroglia.application.background_scheduler.AsyncIOScheduler",
            return_value=self.mock_scheduler,
        ):
            scheduler = BackgroundTaskScheduler(self.options, self.task_bus, self.mock_scheduler)

            # Mock job
            mock_job = Mock()
            mock_job.id = "test-id"
            mock_job.name = "test-name"
            mock_job.next_run_time = datetime.datetime.now()
            mock_job.trigger = Mock()
            mock_job.trigger.__str__ = Mock(return_value="trigger-info")
            mock_job.args = ()
            mock_job.kwargs = {}

            self.mock_scheduler.get_job.return_value = mock_job

            info = scheduler.get_task_info("test-id")

            assert info is not None
            assert info["id"] == "test-id"
            assert info["name"] == "test-name"


class TestBackgroundTaskSchedulerConfiguration:
    """Test scheduler configuration and module discovery."""

    @patch("neuroglia.application.background_scheduler.ModuleLoader")
    @patch("neuroglia.application.background_scheduler.TypeFinder")
    def test_configure_scheduler_success(self, mock_type_finder, mock_module_loader):
        """Test successful scheduler configuration."""
        # Mock builder with proper settings mock
        mock_builder = Mock()
        mock_builder.services = Mock()
        mock_builder.services.add_scoped = Mock()
        mock_builder.services.add_singleton = Mock()
        mock_builder.services.add_transient = Mock()
        mock_builder.services.try_add_singleton = Mock()

        # Mock settings to avoid the "Mock is not iterable" error
        mock_builder.settings = Mock()
        mock_builder.settings.background_job_store = {}

        # Mock module loading
        mock_module = Mock()
        mock_module_loader.load.return_value = mock_module

        # Mock type finding
        mock_type_finder.get_types.return_value = [TestScheduledJob, TestRecurrentJob]

        with patch(
            "neuroglia.application.background_scheduler.AsyncIOScheduler"
        ) as mock_scheduler_class, patch(
            "neuroglia.application.background_scheduler.AsyncIOExecutor"
        ) as mock_executor_class:
            mock_scheduler_class.return_value = Mock()
            mock_executor_class.return_value = Mock()

            result = BackgroundTaskScheduler.configure(mock_builder, ["test.module"])

            assert result == mock_builder
            mock_builder.services.add_transient.assert_called()
            mock_builder.services.add_singleton.assert_called()

    def test_configure_scheduler_without_apscheduler(self):
        """Test scheduler configuration failure without APScheduler."""
        mock_builder = Mock()

        with patch("neuroglia.application.background_scheduler.AsyncIOScheduler", None):
            with pytest.raises(BackgroundTaskException) as exc_info:
                BackgroundTaskScheduler.configure(mock_builder, ["test.module"])

            assert "APScheduler is required" in str(exc_info.value)


@pytest.mark.skipif(APSCHEDULER_AVAILABLE, reason="Testing without APScheduler")
class TestBackgroundTaskSchedulerWithoutAPScheduler:
    """Test scheduler behavior when APScheduler is not available."""

    def test_scheduler_creation_without_apscheduler(self):
        """Test scheduler creation fails without APScheduler."""
        options = BackgroundTaskSchedulerOptions()
        task_bus = BackgroundTasksBus()

        with pytest.raises(BackgroundTaskException) as exc_info:
            BackgroundTaskScheduler(options, task_bus)

        assert "APScheduler is required" in str(exc_info.value)
