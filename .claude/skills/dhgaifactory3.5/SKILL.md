```markdown
# dhgaifactory3.5 Development Patterns

> Auto-generated skill from repository analysis

## Overview

This skill teaches you how to contribute to the `dhgaifactory3.5` Python codebase, which is organized around modular registry features and agent workflows. You'll learn the project's coding conventions, how to add or extend capture modules, how to refactor shared logic, and how to write and organize tests. The repository uses conventional commits, snake_case file naming, and emphasizes modular, maintainable code without reliance on a specific web framework.

## Coding Conventions

- **File Naming:**  
  Use `snake_case` for all Python files.  
  *Example:*  
  ```
  user_endpoints.py
  data_capture_service.py
  ```

- **Import Style:**  
  Use relative imports within modules.  
  *Example:*  
  ```python
  from .models import RegistryModel
  from .schemas import UserSchema
  ```

- **Export Style:**  
  Use named exports (explicitly define what is exported).  
  *Example:*  
  ```python
  __all__ = ["UserService", "UserSchema"]
  ```

- **Commit Messages:**  
  Follow [Conventional Commits](https://www.conventionalcommits.org/) with prefixes: `feat`, `fix`, `docs`, `refactor`.  
  *Example:*  
  ```
  feat(registry): add new endpoint for data capture
  fix(user): correct schema validation error
  ```

## Workflows

### Add New Capture Module or Feature to Registry
**Trigger:** When adding a new data capture domain or major feature to the registry API.  
**Command:** `/new-capture-module`

1. **Create or update endpoint file(s):**  
   - Add `<feature>_endpoints.py` in `registry/`  
   - *Example:* `registry/user_endpoints.py`
2. **Create or update schema file(s):**  
   - Add `<feature>_schemas.py`  
   - *Example:* `registry/user_schemas.py`
3. **Create or update service file(s):**  
   - Add `<feature>_service.py`  
   - *Example:* `registry/user_service.py`
4. **Update models:**  
   - Edit `registry/models.py` to add new models or fields.
5. **Add or update migration file(s):**  
   - Place in `registry/alembic/versions/` or `registry/migrations/`  
   - *Example:* `registry/alembic/versions/20240101_add_user_table.py`
6. **Update API registration:**  
   - Edit `registry/api.py` to register new routes or routers.
7. **Write or update tests:**  
   - Add `test_<feature>.py`  
   - *Example:* `registry/test_user.py`
8. **(Optional) Update write protection:**  
   - Edit `registry/write_auth.py` if needed.

*Example code for a new endpoint:*
```python
# registry/user_endpoints.py
from .user_service import UserService
from .user_schemas import UserCreate, UserRead

def register_user_routes(app):
    @app.route("/users", methods=["POST"])
    def create_user():
        data = request.json
        user = UserService.create(UserCreate(**data))
        return UserRead.from_orm(user)
```

---

### Extend Existing Capture Module or Feature in Registry
**Trigger:** When extending an existing registry feature with new attributes, endpoints, or logic.  
**Command:** `/extend-capture-module`

1. **Update schema file(s):**  
   - Edit `<feature>_schemas.py` to add new fields or enums.
2. **Update service file(s):**  
   - Edit `<feature>_service.py` for new logic.
3. **Update or append migration file(s):**  
   - Add/modify in `registry/migrations/`
4. **Update models:**  
   - Edit `registry/models.py` for new fields or enums.
5. **Update or add tests:**  
   - Edit or add `test_<feature>.py`

*Example:*
```python
# registry/user_schemas.py
class UserRead(BaseModel):
    id: int
    name: str
    email: str  # new field added

# registry/models.py
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String)  # new column
```

---

### Refactor Shared Constants or Rules Across Agents
**Trigger:** When deduplicating or centralizing shared code/constants used by multiple agents.  
**Command:** `/extract-shared-constants`

1. **Create new shared file(s):**  
   - Add to `langgraph_workflows/dhg-agents-cloud/src/prompts/`  
   - *Example:* `src/prompts/common_prompts.py`
2. **Move constants or logic:**  
   - Extract from agent modules to the shared file(s).
3. **Update imports:**  
   - Edit each agent module to import from the new shared location.
4. **Update or create rules documentation:**  
   - Edit `.claude/rules/llm-prompts.md`
5. **Verify imports:**  
   - Ensure all affected modules import-check clean.

*Example:*
```python
# src/prompts/common_prompts.py
SYSTEM_PROMPT = "You are a helpful assistant."

# src/user_agent.py
from .prompts.common_prompts import SYSTEM_PROMPT
```

## Testing Patterns

- **Test File Naming:**  
  Use `test_<feature>.py` or `*.test.*` patterns.
  *Example:*  
  ```
  registry/test_user.py
  registry/user_service.test.py
  ```

- **Framework:**  
  The specific test framework is not enforced; use standard Python test frameworks (e.g., `pytest` or `unittest`).

- **Test Structure:**  
  Place tests alongside or within the `registry/` directory, matching the feature/module name.

*Example:*
```python
# registry/test_user.py
def test_create_user():
    user = UserService.create(UserCreate(name="Alice", email="alice@example.com"))
    assert user.id is not None
```

## Commands

| Command                | Purpose                                                        |
|------------------------|----------------------------------------------------------------|
| /new-capture-module    | Scaffold a new capture module or major registry feature        |
| /extend-capture-module | Add new fields/endpoints to an existing registry module        |
| /extract-shared-constants | Refactor and centralize shared constants or logic across agents |
```
