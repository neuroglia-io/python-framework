# Simple UI - Modular Architecture

## Overview

The Simple UI application has been refactored into a clean, modular architecture with:

- **Jinja2 template components** for reusable UI elements
- **JavaScript ES6 modules** for separation of concerns
- **SASS component stylesheets** for maintainable styling

## Project Structure

```
samples/simple-ui/
├── ui/
│   ├── src/
│   │   ├── scripts/
│   │   │   ├── main.js                 # Application entry point
│   │   │   └── modules/
│   │   │       ├── auth.js             # Authentication module
│   │   │       ├── tasks.js            # Task management module
│   │   │       ├── ui.js               # UI state management module
│   │   │       └── utils.js            # Utility functions module
│   │   └── styles/
│   │       ├── main.scss               # Main stylesheet
│   │       ├── _variables.scss         # SASS variables
│   │       └── components/
│   │           ├── _navbar.scss        # Navbar styles
│   │           ├── _login.scss         # Login form styles
│   │           ├── _tasks.scss         # Task card styles
│   │           └── _spinner.scss       # Loading spinner styles
│   └── templates/
│       ├── base.html                   # Base layout template
│       ├── index.html                  # Main page (extends base)
│       ├── components/
│       │   ├── navbar.html             # Navigation bar
│       │   ├── login_form.html         # Login form component
│       │   └── tasks_section.html      # Tasks display section
│       └── modals/
│           ├── create_task_modal.html  # Create task modal
│           └── task_details_modal.html # Task details modal
├── static/
│   └── dist/                           # Parcel build output
│       ├── scripts/
│       │   └── main.js                 # Bundled JavaScript
│       └── styles/
│           └── main.css                # Bundled CSS
└── main.py                             # Application entry point
```

## Template Architecture

### Base Template (`base.html`)

- Defines the HTML skeleton and common elements
- Includes CSS/JS references
- Provides blocks for content extension
- Uses Jinja2 template inheritance

### Component Templates

Reusable UI components that can be included anywhere:

- **`navbar.html`**: Navigation bar with user info and logout
- **`login_form.html`**: Login form with validation
- **`tasks_section.html`**: Task list display grid

### Modal Templates

Self-contained modal dialogs:

- **`create_task_modal.html`**: Form for creating new tasks
- **`task_details_modal.html`**: Display task details

### Template Usage Example

```html
{% extends "base.html" %} {% block title %}Custom Page Title{% endblock %} {% block content %} {% include
'components/login_form.html' %} {% include 'components/tasks_section.html' %} {% endblock %} {% block modals %} {%
include 'modals/create_task_modal.html' %} {% endblock %}
```

## JavaScript Module Architecture

### Main Entry Point (`main.js`)

- Initializes the application
- Sets up event listeners
- Coordinates between modules
- Manages application state

### Authentication Module (`modules/auth.js`)

**Exports:**

- `checkAuth()` - Check current authentication status
- `login(username, password)` - Authenticate user
- `logout()` - End user session
- `getAuthToken()` - Get stored JWT token

**Usage:**

```javascript
import { login, logout, checkAuth } from "./modules/auth.js";

const result = await login("admin", "admin123");
if (result.success) {
  console.log("Logged in:", result.user);
}
```

### Tasks Module (`modules/tasks.js`)

**Exports:**

- `loadTasks()` - Fetch all tasks
- `createTask(taskData)` - Create new task
- `getTask(taskId)` - Get single task
- `updateTask(taskId, taskData)` - Update existing task
- `deleteTask(taskId)` - Delete task

**Usage:**

```javascript
import { loadTasks, createTask } from "./modules/tasks.js";

const tasks = await loadTasks();
const newTask = await createTask({
  title: "My Task",
  description: "Task description",
  status: "pending",
});
```

### UI Module (`modules/ui.js`)

**Exports:**

- `showLoginSection()` - Display login form
- `showTasksSection()` - Display tasks view
- `updateUserInfo(user)` - Update navbar user info
- `displayTasks(tasks)` - Render tasks in grid
- `showTasksLoading()` - Show loading spinner
- `showTasksError(message)` - Show error message
- `showError(elementId, message)` - Show/hide error in element

**Usage:**

```javascript
import { showTasksSection, displayTasks } from "./modules/ui.js";

showTasksSection();
displayTasks([
  { title: "Task 1", status: "pending" },
  { title: "Task 2", status: "completed" },
]);
```

### Utils Module (`modules/utils.js`)

**Exports:**

- `escapeHtml(text)` - Escape HTML for XSS prevention
- `debounce(func, wait)` - Debounce function calls
- `formatDate(date)` - Format date string
- `formatDateTime(date)` - Format datetime string
- `validateForm(form)` - Validate HTML form
- `getFormData(form)` - Get form data as object

**Usage:**

```javascript
import { escapeHtml, getFormData } from "./modules/utils.js";

const safeText = escapeHtml(userInput);
const formData = getFormData(document.getElementById("myForm"));
```

## SASS Architecture

### Variables (`_variables.scss`)

Defines all design tokens:

- Colors: `$primary-color`, `$success-color`, etc.
- Spacing: `$spacer`
- Typography: `$font-family-base`
- Transitions: `$transition-base`
- Z-index levels

### Component Stylesheets

Each component has its own SASS file:

**`components/_navbar.scss`**

- Navbar styling
- Brand logo and user info
- Responsive behavior

**`components/_login.scss`**

- Login form container
- Card styling
- Form input focus states

**`components/_tasks.scss`**

- Task card styling with hover effects
- Priority borders (high/medium/low)
- Status badges
- Empty state display

**`components/_spinner.scss`**

- Loading spinner container
- Spinner sizing

### Main Stylesheet (`main.scss`)

Imports everything in the correct order:

```scss
@import "variables"; // Custom variables first
@import "~bootstrap/scss/bootstrap"; // Bootstrap
@import "components/navbar"; // Component styles
@import "components/login";
@import "components/tasks";
@import "components/spinner";
```

## Development Workflow

### Making Changes

1. **Template Changes**: Edit component templates in `ui/templates/`

   - Changes are reflected on page reload
   - Test with different user states

2. **JavaScript Changes**: Edit modules in `ui/src/scripts/modules/`

   - Parcel watches for changes and rebuilds automatically
   - Check browser console for errors

3. **Style Changes**: Edit SASS files in `ui/src/styles/`
   - Parcel compiles SASS to CSS automatically
   - Changes appear after rebuild (~3-5 seconds)

### Adding New Components

#### New Template Component

```html
<!-- ui/templates/components/my_component.html -->
<div class="my-component">
  <!-- Component HTML -->
</div>
```

Include in main template:

```html
{% include 'components/my_component.html' %}
```

#### New JavaScript Module

```javascript
// ui/src/scripts/modules/my_module.js
export function myFunction() {
  // Module code
}
```

Import in main.js:

```javascript
import { myFunction } from "./modules/my_module.js";
```

#### New SASS Component

```scss
// ui/src/styles/components/_my_component.scss
.my-component {
  // Component styles
}
```

Import in main.scss:

```scss
@import "components/my_component";
```

## Benefits of Modular Architecture

### Templates

✅ **Reusability**: Components can be included anywhere
✅ **Maintainability**: Changes in one place affect all uses
✅ **Testability**: Components can be rendered independently
✅ **Organization**: Clear structure by feature

### JavaScript

✅ **Separation of Concerns**: Each module has a single responsibility
✅ **Testability**: Modules can be unit tested
✅ **Reusability**: Functions can be imported where needed
✅ **Code Splitting**: Easier to optimize bundle size
✅ **Type Safety**: Can add TypeScript gradually

### SASS

✅ **Variables**: Consistent design tokens
✅ **Organization**: Styles grouped by component
✅ **Maintainability**: Easy to find and update styles
✅ **Performance**: Single compiled CSS file
✅ **DRY**: Reusable mixins and functions

## Migration Notes

### Old Files (Backup)

- `templates/index_old.html` - Monolithic template with inline JS
- `src/scripts/main_old.js` - Combined JavaScript
- `src/styles/main_old.scss` - Basic SASS file

### New Files (Active)

- `templates/index.html` - Modular template using components
- `templates/base.html` - Base layout
- `templates/components/` - Reusable components
- `templates/modals/` - Modal dialogs
- `src/scripts/main.js` - Application coordinator
- `src/scripts/modules/` - Feature modules
- `src/styles/main.scss` - Component-based styles
- `src/styles/components/` - Component stylesheets

## Testing Checklist

After making changes, verify:

- [ ] Static files are served correctly (`/static/dist/scripts/main.js` returns 200)
- [ ] Templates render without errors
- [ ] Login functionality works
- [ ] Task loading works
- [ ] Task creation works
- [ ] Logout works
- [ ] Parcel rebuilds on file changes
- [ ] No console errors in browser
- [ ] Styles are applied correctly
- [ ] Modals open and close properly

## Build Commands

```bash
# Watch mode (automatic rebuilds)
cd samples/simple-ui/ui
npm run dev

# Production build
npm run build

# Docker commands
cd deployment/docker-compose

# Check builder logs
docker-compose -f docker-compose.shared.yml \
               -f docker-compose.simple-ui.yml \
               logs simple-ui-builder

# Restart app
docker-compose -f docker-compose.shared.yml \
               -f docker-compose.simple-ui.yml \
               restart simple-ui-app
```

## Next Steps

- [ ] Add unit tests for JavaScript modules
- [ ] Add TypeScript types
- [ ] Add ESLint and Prettier
- [ ] Add Storybook for component documentation
- [ ] Add more interactive components (edit task, delete task, etc.)
- [ ] Add pagination for large task lists
- [ ] Add task filtering and search
- [ ] Add task sorting options
