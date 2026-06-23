"""UI controller for serving HTML pages."""

from classy_fastapi import Routable, get
from classy_fastapi.decorators import get
from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from neuroglia.dependency_injection.service_provider import ServiceProviderBase
from neuroglia.mapping import Mapper
from neuroglia.mediation import Mediator
from neuroglia.mvc import ControllerBase
from neuroglia.mvc.controller_base import generate_unique_id_function

templates = Jinja2Templates(directory="ui/templates")


class UIController(ControllerBase):
    """Controller for UI pages."""

    def __init__(
        self,
        service_provider: ServiceProviderBase,
        mapper: Mapper,
        mediator: Mediator,
    ):
        # Store DI services first
        self.service_provider = service_provider
        self.mapper = mapper
        self.mediator = mediator
        self.name = "UI"

        # Call Routable.__init__ directly with empty prefix for root routes
        Routable.__init__(
            self,
            prefix="",  # Empty prefix for root routes
            tags=["UI"],
            generate_unique_id_function=generate_unique_id_function,
        )

    @get("/", response_class=HTMLResponse)
    async def index(self, request: Request):
        """Render main application page."""
        return templates.TemplateResponse("index.html", {"request": request})
