# Documentation Refactoring Plan

**Date**: October 25, 2025
**Status**: 🎯 Planning Phase
**Branch**: `docs/refactor-documentation`

## 🎯 Objectives

1. **Align documentation with current framework state** - Ensure docs reflect all implemented features
2. **Create beginner-friendly learning path** - Progressive learning from basics to advanced
3. **Focus on Mario's Pizzeria as primary example** - Real-world, complete application showcase
4. **Explain architectural patterns clearly** - Assume learners are new to DDD, CQRS, Clean Architecture
5. **Reduce redundancy and improve discoverability** - Clear navigation and cross-linking

## 📊 Current State Analysis

### ✅ What's Working

- **Good pattern documentation** - Comprehensive coverage of Clean Architecture, DDD, CQRS
- **Mario's Pizzeria case study exists** - Detailed business analysis and domain design
- **Feature documentation present** - Most features have dedicated pages
- **Good tooling setup** - MkDocs with Material theme, Mermaid diagrams

### ❌ Critical Gaps Identified

#### 1. **Missing Framework Module Documentation**

**Undocumented Modules** (exist in `src/neuroglia/` but missing from docs):

- ✗ **`hosting/`** - WebApplicationBuilder, application lifecycle, startup/shutdown
- ✗ **`observability/`** - OpenTelemetry integration, tracing, metrics, logging
- ✗ **`validation/`** - Business rule validation, entity validation
- ✗ **`logging/`** - Structured logging, correlation IDs
- ✗ **`expressions/`** - JavaScript expression evaluation
- ✗ **`reactive/`** - RxPY integration, reactive patterns
- ✗ **`extensions/`** - Framework extension points
- ✗ **`application/`** - Application layer patterns (partially documented)
- ✗ **`core/`** - Core abstractions and base classes

**Impact**: Users don't know these features exist or how to use them.

#### 2. **Mario's Pizzeria Documentation Issues**

**Problems**:

- Scattered across multiple files without clear flow
- Heavy business analysis but light on implementation walkthrough
- Doesn't showcase all framework features actually used
- Missing step-by-step tutorial from zero to working app
- Implementation notes in `samples/mario-pizzeria/notes/` not reflected in public docs

**Impact**: Users can't easily learn by following the main example.

#### 3. **Pattern Documentation Assumes Too Much Knowledge**

**Problems**:

- Jumps straight into advanced concepts
- Lacks "why" and "when to use" guidance
- No progression from simple to complex
- Examples are abstract, not from Mario's Pizzeria
- Missing anti-patterns and common mistakes

**Impact**: Beginners feel overwhelmed and confused.

#### 4. **Navigation and Information Architecture**

**Problems**:

- Too many top-level sections (7 main nav items)
- Getting Started doesn't provide clear learning path
- Features and Patterns have significant overlap
- Sample applications section underutilized
- No clear "beginner → intermediate → advanced" flow

**Impact**: Users don't know where to start or what to read next.

#### 5. **Getting Started Experience**

**Current Issues**:

- `getting-started.md` is too generic
- 3-minute bootstrap is good but disconnected from main tutorial
- Mario's Pizzeria tutorial exists but isn't the main path
- No "Hello World" → "Simple CRUD" → "Full App" progression

**Impact**: High barrier to entry for new users.

## 🎯 Proposed New Documentation Structure

### Phase 1: Core Learning Path (High Priority)

```
📚 Documentation
├── 🏠 Home (index.md)
│   └── Overview, key features, quick links, "What can you build?"
│
├── 🚀 Getting Started
│   ├── Installation & Setup
│   ├── Your First Application (Hello World)
│   ├── Understanding Clean Architecture
│   └── Next Steps (links to tutorials)
│
├── 📖 Tutorials
│   ├── Tutorial Overview
│   ├── Building Mario's Pizzeria (Step-by-Step)
│   │   ├── Part 1: Project Setup & Domain Model
│   │   ├── Part 2: Commands & Queries (CQRS)
│   │   ├── Part 3: API Controllers & Routing
│   │   ├── Part 4: Event-Driven Features
│   │   ├── Part 5: Persistence & Repositories
│   │   ├── Part 6: Authentication & Authorization
│   │   ├── Part 7: Observability & Monitoring
│   │   └── Part 8: Deployment
│   └── Additional Examples
│
├── 🧩 Core Concepts (Beginner-Friendly)
│   ├── Introduction to Architecture Patterns
│   ├── Clean Architecture Explained
│   ├── Domain-Driven Design Basics
│   ├── CQRS (Command Query Responsibility Segregation)
│   ├── Event-Driven Architecture
│   ├── Dependency Injection
│   └── When to Use Each Pattern
│
├── 📦 Framework Features
│   ├── Dependency Injection
│   ├── CQRS & Mediation
│   ├── MVC Controllers
│   ├── Data Access & Repositories
│   ├── Event Sourcing
│   ├── Object Mapping
│   ├── Serialization
│   ├── Validation
│   ├── Hosting & Application Lifecycle
│   ├── Observability (Tracing, Metrics, Logging)
│   ├── HTTP Client
│   ├── Caching
│   ├── Background Tasks
│   └── Reactive Programming
│
├── 📋 How-To Guides
│   ├── Setting Up Your Project
│   ├── Implementing CRUD Operations
│   ├── Adding Authentication
│   ├── Working with Events
│   ├── Setting Up Observability
│   ├── Testing Your Application
│   ├── Deploying with Docker
│   └── Common Patterns & Solutions
│
└── 📚 Reference
    ├── API Reference (auto-generated?)
    ├── Configuration Options
    ├── Best Practices
    └── Troubleshooting
```

### Phase 2: Pattern Documentation Improvements

**Restructure patterns/** to be more educational:

```
🏗️ Architecture Patterns
├── Overview: Why Architecture Matters
├── Clean Architecture
│   ├── What & Why
│   ├── Layers Explained
│   ├── Dependency Rules
│   ├── Mario's Pizzeria Example
│   └── Common Mistakes
├── Domain-Driven Design
│   ├── Core Concepts
│   ├── Entities vs Value Objects
│   ├── Aggregates & Boundaries
│   ├── Domain Events
│   ├── Mario's Pizzeria Domain Model
│   └── When NOT to Use DDD
└── [Continue for each pattern...]
```

### Phase 3: Mario's Pizzeria Showcase

**Create comprehensive Mario's Pizzeria documentation:**

```
🍕 Mario's Pizzeria Case Study
├── Overview & Features
├── Business Requirements
├── Domain Model Design
├── Step-by-Step Implementation Tutorial
│   ├── 1. Project Structure
│   ├── 2. Domain Layer
│   ├── 3. Application Layer
│   ├── 4. API Layer
│   ├── 5. Integration Layer
│   ├── 6. UI Layer
│   ├── 7. Testing Strategy
│   └── 8. Deployment
├── Architecture Deep Dive
├── Design Decisions & Trade-offs
├── Performance Considerations
└── Running & Testing
```

## 📝 Detailed Action Plan

### ✅ Phase 1: Foundation (Week 1)

#### 1.1 Update Getting Started

**File**: `docs/getting-started.md`

**Changes**:

- Rewrite as progressive introduction
- Add "Hello World" FastAPI + Neuroglia example
- Show simple CRUD with CQRS
- Link to full Mario's Pizzeria tutorial
- Include troubleshooting section

**Estimated effort**: 4 hours

#### 1.2 Create New Tutorial Structure

**New directory**: `docs/tutorials/`

**Files to create**:

- `tutorials/index.md` - Tutorial overview and learning path
- `tutorials/mario-pizzeria-01-setup.md` - Project setup
- `tutorials/mario-pizzeria-02-domain.md` - Domain model
- `tutorials/mario-pizzeria-03-cqrs.md` - Commands and queries
- `tutorials/mario-pizzeria-04-api.md` - Controllers and routing
- `tutorials/mario-pizzeria-05-events.md` - Event-driven features
- `tutorials/mario-pizzeria-06-persistence.md` - Repositories
- `tutorials/mario-pizzeria-07-auth.md` - Authentication
- `tutorials/mario-pizzeria-08-observability.md` - Tracing and monitoring
- `tutorials/mario-pizzeria-09-deployment.md` - Docker deployment

**Source material**:

- Extract from `samples/mario-pizzeria/notes/`
- Use actual implementation code
- Show progressive feature addition

**Estimated effort**: 16 hours (2 hours per tutorial part)

#### 1.3 Create Core Concepts Section

**New directory**: `docs/concepts/`

**Files to create**:

- `concepts/index.md` - Introduction to architecture
- `concepts/clean-architecture.md` - Simple explanation with diagrams
- `concepts/domain-driven-design.md` - DDD basics for beginners
- `concepts/cqrs.md` - CQRS explained simply
- `concepts/event-driven.md` - Events and async patterns
- `concepts/dependency-injection.md` - DI explained
- `concepts/when-to-use.md` - Pattern selection guide

**Approach**:

- Start with "What problem does this solve?"
- Use Mario's Pizzeria examples
- Include anti-patterns
- Add decision flowcharts

**Estimated effort**: 12 hours

### ✅ Phase 2: Feature Documentation (Week 2)

#### 2.1 Document Missing Framework Modules

**New files to create**:

- `docs/features/hosting.md` - WebApplicationBuilder, lifecycle
- `docs/features/observability.md` - OpenTelemetry, tracing, metrics
- `docs/features/validation.md` - Business rules, entity validation
- `docs/features/logging.md` - Structured logging, correlation
- `docs/features/reactive.md` - RxPY integration
- `docs/features/expressions.md` - JavaScript expression evaluation

**Each file should include**:

- What it is and why it exists
- When to use it
- Basic example
- Mario's Pizzeria usage
- API reference
- Common patterns
- Troubleshooting

**Estimated effort**: 12 hours (2 hours per module)

#### 2.2 Update Existing Feature Documentation

**Files to update**:

- `docs/features/simple-cqrs.md` - Add more examples, link to tutorial
- `docs/features/mvc-controllers.md` - Show actual controller from Mario's
- `docs/features/data-access.md` - Add MongoDB examples
- `docs/features/http-service-client.md` - Real integration examples

**Estimated effort**: 6 hours

### ✅ Phase 3: Pattern Improvements (Week 3)

#### 3.1 Restructure Pattern Documentation

**Approach**:

- Add "Overview" intro to each pattern
- Include "Problem Statement" sections
- Show progression: Simple → Complex
- Use Mario's Pizzeria as primary example
- Add "When NOT to use" sections
- Include common mistakes

**Files to update**:

- `docs/patterns/clean-architecture.md`
- `docs/patterns/domain-driven-design.md`
- `docs/patterns/cqrs.md`
- `docs/patterns/event-driven.md`
- `docs/patterns/repository.md`
- `docs/patterns/dependency-injection.md`

**Estimated effort**: 12 hours

#### 3.2 Consolidate Redundant Content

**Actions**:

- Merge `concepts/` and `patterns/` where they overlap
- Keep patterns/ for detailed reference
- Keep concepts/ for beginner explanations
- Add clear cross-references

**Estimated effort**: 4 hours

### ✅ Phase 4: Mario's Pizzeria Showcase (Week 3-4)

#### 4.1 Create Comprehensive Case Study

**New directory**: `docs/case-studies/mario-pizzeria/`

**Files to create**:

- `overview.md` - What it demonstrates
- `business-requirements.md` - Updated from current docs
- `domain-model.md` - Visual domain model with events
- `architecture.md` - System architecture diagrams
- `implementation-highlights.md` - Key implementation patterns
- `running-the-app.md` - Setup and usage guide

**Estimated effort**: 10 hours

#### 4.2 Extract Implementation Patterns

**From** `samples/mario-pizzeria/notes/`

**To** public documentation:

- Authentication setup (Keycloak)
- Observability configuration (OTEL)
- MongoDB repository patterns
- Docker deployment
- Event-driven workflows
- UI integration patterns

**Estimated effort**: 6 hours

### ✅ Phase 5: Navigation & Polish (Week 4)

#### 5.1 Update mkdocs.yml

**New navigation structure**:

```yaml
nav:
  - Home: index.md
  - Getting Started:
      - Installation: getting-started.md
      - Your First App: getting-started/first-app.md
      - Understanding the Framework: getting-started/framework-overview.md
  - Tutorials:
      - Overview: tutorials/index.md
      - Mario's Pizzeria Tutorial:
          - Part 1 - Setup: tutorials/mario-pizzeria-01-setup.md
          - Part 2 - Domain: tutorials/mario-pizzeria-02-domain.md
        # ... etc
  - Core Concepts:
      - Introduction: concepts/index.md
      - Clean Architecture: concepts/clean-architecture.md
    # ... etc
  - Framework Features:
      - features/index.md
    # ... reorganized by importance
  - How-To Guides:
      - guides/index.md
    # ... practical guides
  - Architecture Patterns:
      - patterns/index.md
    # ... detailed pattern reference
  - Case Studies:
      - Mario's Pizzeria: case-studies/mario-pizzeria/overview.md
  - Reference:
      - API Reference: reference/api.md
      - Best Practices: reference/best-practices.md
```

**Estimated effort**: 4 hours

#### 5.2 Add Navigation Aids

**Changes**:

- Add "Next Steps" sections to each page
- Include breadcrumbs
- Add "Related Topics" sidebars
- Create learning path diagrams
- Add "Prerequisites" sections

**Estimated effort**: 4 hours

#### 5.3 Clean Up Old Content

**Actions**:

- Move `docs/old/` content to archive or delete
- Remove duplicate pattern files (found several in file list)
- Remove samples that aren't Mario's Pizzeria from main nav
- Update or remove outdated references

**Estimated effort**: 3 hours

### ✅ Phase 6: Quality Assurance (Ongoing)

#### 6.1 Cross-Reference Validation

- Ensure all internal links work
- Verify code examples are current
- Test all commands and setup instructions
- Validate Mermaid diagrams render

**Estimated effort**: 4 hours

#### 6.2 Technical Review

- Verify framework alignment
- Check code examples against current API
- Ensure Mario's Pizzeria examples are accurate
- Test documentation against actual implementation

**Estimated effort**: 6 hours

## 📋 Content Extraction Checklist

### From `samples/mario-pizzeria/notes/` to Public Docs

#### Architecture

- [ ] Extract event flow diagrams → tutorials
- [ ] Extract entity vs aggregate decisions → concepts/domain-driven-design.md
- [ ] Extract architecture review → case-studies/mario-pizzeria/architecture.md

#### Implementation

- [ ] Extract delivery system implementation → tutorial part 5
- [ ] Extract order management patterns → how-to guides
- [ ] Extract repository implementations → features/data-access.md
- [ ] Extract refactoring notes → best practices

#### Infrastructure

- [ ] Extract Keycloak setup → tutorials/mario-pizzeria-07-auth.md
- [ ] Extract Docker configuration → tutorials/mario-pizzeria-09-deployment.md
- [ ] Extract MongoDB setup → features/data-access.md
- [ ] Extract observability setup → features/observability.md

#### UI

- [ ] Extract UI patterns → case-studies (if relevant)
- [ ] Extract build system setup → deployment guide

#### Guides

- [ ] Extract QUICK_START.md → getting-started.md
- [ ] Extract test guides → testing documentation

## 🎯 Success Criteria

### For Beginners

- [ ] Can install and run Hello World in < 10 minutes
- [ ] Understands Clean Architecture by end of Getting Started
- [ ] Can follow Mario's Pizzeria tutorial without confusion
- [ ] Knows when to use DDD, CQRS, Event Sourcing

### For Framework Users

- [ ] Can find documentation for every framework feature
- [ ] Understands hosting, observability, validation modules
- [ ] Has working examples for every feature
- [ ] Knows how to integrate with external services

### For Documentation Quality

- [ ] No broken internal links
- [ ] All code examples tested and working
- [ ] Consistent terminology throughout
- [ ] Clear progression from simple to advanced
- [ ] Mario's Pizzeria is the primary teaching tool

## 📊 Effort Summary

| Phase                     | Tasks                                | Estimated Hours |
| ------------------------- | ------------------------------------ | --------------- |
| Phase 1: Foundation       | Getting Started, Tutorials, Concepts | 32 hours        |
| Phase 2: Features         | Missing modules, Updates             | 18 hours        |
| Phase 3: Patterns         | Restructure, Consolidate             | 16 hours        |
| Phase 4: Mario's Pizzeria | Case study, Implementation           | 16 hours        |
| Phase 5: Navigation       | mkdocs.yml, Navigation aids, Cleanup | 11 hours        |
| Phase 6: QA               | Validation, Review                   | 10 hours        |
| **Total**                 |                                      | **103 hours**   |

**Timeline**: ~2.5 weeks of full-time work, or ~5 weeks at 20 hours/week

## 🚀 Implementation Strategy

### Recommended Approach

1. **Start with high-impact items** - Getting Started and Tutorials first
2. **Work in small, testable increments** - One tutorial at a time
3. **Get feedback early** - Review after Phase 1 completion
4. **Keep old docs during transition** - Mark as deprecated, redirect
5. **Update as we implement** - Make small improvements continuously

### Quick Wins (Can Do First)

1. ✅ Update `getting-started.md` with clear learning path
2. ✅ Create `tutorials/index.md` with overview
3. ✅ Document `hosting` module (most requested)
4. ✅ Document `observability` module (commonly used)
5. ✅ Fix navigation structure in `mkdocs.yml`

## 📝 Notes

- Keep this plan updated as we implement
- Track completed items with checkboxes
- Add discovered gaps as we find them
- Document decisions and trade-offs
- Review after each phase

---

**Next Steps**: Begin Phase 1 implementation starting with `getting-started.md` refactoring.
