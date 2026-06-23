# 📊 Mermaid Diagrams in Documentation

The Neuroglia Python Framework documentation supports [Mermaid](https://mermaid.js.org/) diagrams for creating visual representations of architecture, workflows, and system interactions.

## 🎯 Overview

Mermaid is a powerful diagramming tool that allows you to create diagrams using simple text-based syntax. Our documentation site automatically renders Mermaid diagrams when you include them in markdown files.

## 🏗️ Supported Diagram Types

### Flowcharts

Perfect for representing decision flows, process flows, and system workflows:

```mermaid
graph TD
    A[User Request] --> B{Authentication}
    B -->|Valid| C[Route to Controller]
    B -->|Invalid| D[Return 401]
    C --> E[Execute Handler]
    E --> F[Return Response]
    D --> G[End]
    F --> G
```

### Sequence Diagrams

Ideal for showing interaction between components over time:

```mermaid
sequenceDiagram
    participant C as Controller
    participant M as Mediator
    participant H as Handler
    participant R as Repository
    participant D as Database

    C->>M: Send Command
    M->>H: Route to Handler
    H->>R: Query/Save Data
    R->>D: Execute SQL
    D-->>R: Return Result
    R-->>H: Domain Objects
    H-->>M: Operation Result
    M-->>C: Response
```

### Class Diagrams

Great for documenting domain models and relationships:

```mermaid
classDiagram
    class Controller {
        +ServiceProvider service_provider
        +Mediator mediator
        +Mapper mapper
        +process(result) Response
    }

    class CommandHandler {
        <<abstract>>
        +handle_async(command) OperationResult
    }

    class Entity {
        +str id
        +datetime created_at
        +raise_event(event)
        +get_uncommitted_events()
    }

    class Repository {
        <<interface>>
        +save_async(entity)
        +get_by_id_async(id)
        +delete_async(id)
    }

    Controller --> CommandHandler : uses
    CommandHandler --> Entity : manipulates
    CommandHandler --> Repository : persists through
```

### Architecture Diagrams

Perfect for system overview and component relationships:

```mermaid
graph TB
    subgraph "🌐 API Layer"
        A[Controllers]
        B[DTOs]
        C[Middleware]
    end

    subgraph "💼 Application Layer"
        D[Commands/Queries]
        E[Handlers]
        F[Services]
        G[Mediator]
    end

    subgraph "🏛️ Domain Layer"
        H[Entities]
        I[Value Objects]
        J[Domain Events]
        K[Business Rules]
    end

    subgraph "🔌 Integration Layer"
        L[Repositories]
        M[External APIs]
        N[Database]
        O[Event Bus]
    end

    A --> G
    G --> E
    E --> H
    E --> L
    L --> N
    E --> O

    style A fill:#e1f5fe
    style G fill:#f3e5f5
    style H fill:#e8f5e8
    style L fill:#fff3e0
```

### State Diagrams

Useful for modeling entity lifecycle and business processes:

```mermaid
stateDiagram-v2
    [*] --> Draft
    Draft --> Submitted : submit()
    Submitted --> Approved : approve()
    Submitted --> Rejected : reject()
    Rejected --> Draft : revise()
    Approved --> Published : publish()
    Published --> Archived : archive()
    Archived --> [*]

    state Submitted {
        [*] --> PendingReview
        PendingReview --> InReview : assign_reviewer()
        InReview --> ReviewComplete : complete_review()
    }
```

## 🚀 Usage in Documentation

### Basic Syntax

To include a Mermaid diagram in your documentation:

````markdown
```mermaid
graph TD
    A[Start] --> B[Process]
    B --> C[End]
```
````

### Best Practices

1. **Use Descriptive Labels**: Make node labels clear and meaningful
2. **Consistent Styling**: Use subgraphs for logical grouping
3. **Appropriate Diagram Types**: Choose the right diagram for your content
4. **Keep It Simple**: Don't overcomplicate diagrams
5. **Use Colors Wisely**: Leverage styling for emphasis

### Advanced Styling

You can add custom styling to your diagrams:

```mermaid
graph TD
    A[API Request] --> B[Authentication]
    B --> C[Authorization]
    C --> D[Business Logic]
    D --> E[Data Access]
    E --> F[Response]

    classDef apiStyle fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    classDef processStyle fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    classDef dataStyle fill:#e8f5e8,stroke:#388e3c,stroke-width:2px

    class A,F apiStyle
    class B,C,D processStyle
    class E dataStyle
```

## 🔧 Configuration

The documentation site is configured with:

- **Theme**: Auto (follows system dark/light mode)
- **Primary Color**: Blue (#1976d2) matching Material theme
- **Auto-refresh**: Diagrams update automatically during development
- **High DPI**: Support for crisp diagrams on retina displays

## 📝 Documentation Standards

When adding Mermaid diagrams to documentation:

1. **Always include a text description** before the diagram
2. **Use consistent terminology** across all diagrams
3. **Reference framework concepts** (Controllers, Handlers, etc.)
4. **Include diagrams in relevant sections** of feature documentation
5. **Test rendering** locally before committing

## 🔗 Related Documentation

- [CQRS & Mediation](../patterns/cqrs.md)
- [Dependency Injection](../patterns/dependency-injection.md)
- [Sample Applications](../samples/openbank.md)

## 📚 External Resources

- [Mermaid Documentation](https://mermaid.js.org/)
- [Mermaid Live Editor](https://mermaid.live/)
- [MkDocs Material](https://squidfunk.github.io/mkdocs-material/)
