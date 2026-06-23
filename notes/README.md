# Neuroglia Framework Notes

This directory contains framework-level documentation and implementation notes for the Neuroglia Python framework.

## 📁 Directory Structure

### `/architecture` - Architectural Patterns

Domain-Driven Design, CQRS, repository patterns, and architectural principles.

- **DDD.md** - Domain-Driven Design fundamentals
- **DDD_recommendations.md** - Best practices for DDD implementation
- **FLAT_STATE_STORAGE_PATTERN.md** - State storage optimization pattern
- **REPOSITORY_SWAPPABILITY_ANALYSIS.md** - Repository abstraction and swappability
- **HOSTING_ARCHITECTURE.md** - ✨ Hosting system architecture and design

### `/framework` - Core Framework Implementation

Dependency injection, service lifetimes, mediator pattern, and core framework features.

- **APPLICATION_BUILDER_UNIFICATION_COMPLETE.md** - ✨ WebApplicationBuilder unification status
- Dependency injection refactoring and enhancements
- Service lifetime management (Singleton, Scoped, Transient)
- Pipeline behaviors for cross-cutting concerns
- String annotations and type resolution fixes
- Event handler reorganization

### `/data` - Data Access & Persistence

MongoDB integration, repository patterns, serialization, and state management.

- Aggregate root refactoring and serialization
- Value object and enum serialization fixes
- MongoDB schema and Motor repository implementation
- Async MongoDB migration (Motor integration)
- Repository optimization and query performance
- State prefix handling and datetime timezone fixes

### `/api` - API Development

Controllers, routing, OAuth2 authentication, and Swagger integration.

- Controller routing fixes and improvements
- OAuth2 settings and Swagger UI integration
- OAuth2 redirect fixes
- Abstract method implementation fixes

### `/observability` - OpenTelemetry & Monitoring

Distributed tracing, metrics, logging, and observability patterns.

- OpenTelemetry integration guides
- Automatic instrumentation documentation
- Grafana dashboard setup
- Multi-app instrumentation fixes

### `/testing` - Test Strategies

Unit testing, integration testing, and test utilities.

- Type equality testing
- Framework test utilities

### `/migrations` - Version Migrations & Historical Plans

Version upgrade guides, breaking changes documentation, and archived planning documents.

- **V042_VALIDATION_SUMMARY.md** - Version 0.4.2 changes
- **V043_RELEASE_SUMMARY.md** - Version 0.4.3 release notes
- **VERSION_ATTRIBUTE_UPDATE.md** - Version attribute updates
- **VERSION_MANAGEMENT.md** - Version management strategy
- **APPLICATION_BUILDER_ARCHITECTURE_UNIFICATION_PLAN.md** - ✨ Archived planning document

### `/tools` - Development Tools

CLI tools, utilities, and development environment setup.

- **PYNEUROCTL_SETUP.md** - PyNeuro CLI tool setup
- **MERMAID_SETUP.md** - Mermaid diagram integration

### `/reference` - Quick References

Quick reference guides and documentation updates.

- **QUICK_REFERENCE.md** - Framework quick reference
- **DOCSTRING_UPDATES.md** - Documentation standards
- **DOCUMENTATION_UPDATES.md** - Ongoing documentation changes

## 📝 Recent Updates (October 2025)

### ✅ WebApplicationBuilder Unification

The framework has completed a major architectural improvement by unifying `WebApplicationBuilder` and `EnhancedWebApplicationBuilder` into a single, adaptive builder class.

**Key Changes**:

- ✅ Single builder supporting both simple and advanced modes
- ✅ Automatic mode detection based on configuration
- ✅ Backward compatibility maintained via alias
- ✅ Enhanced documentation and type safety
- ✅ `enhanced_web_application_builder.py` module removed

**Documentation**:

- Implementation: `/framework/APPLICATION_BUILDER_UNIFICATION_COMPLETE.md`
- Architecture: `/architecture/hosting_architecture.md`
- Original Plan: `/migrations/APPLICATION_BUILDER_ARCHITECTURE_UNIFICATION_PLAN.md` (archived)

## 🎯 Usage

These notes serve multiple purposes:

1. **Framework Documentation Source**: Content will be extracted to the MkDocs documentation site
2. **Implementation History**: Tracking framework evolution and design decisions
3. **Developer Reference**: Quick access to framework patterns and best practices
4. **Migration Guides**: Version upgrade instructions and breaking change documentation

## 📚 Related Documentation

- **Application Examples**: See `/samples/mario-pizzeria/notes/` for real-world application patterns
- **MkDocs Site**: Comprehensive framework documentation at `/docs/`
- **Quick Start**: See `/docs/getting-started.md` for framework introduction
- **Public Docs**: https://bvandewe.github.io/pyneuro/

## 🔄 Maintenance

These notes are living documents. When making framework changes:

1. Update relevant notes in appropriate category folders
2. Extract important content to MkDocs documentation
3. Maintain clear separation: framework-generic vs application-specific
4. Follow naming conventions: descriptive, uppercase with underscores
