# Desktop Architecture Refactoring Plan

## Problem Statement
The `MediaGrabApp` class is a 675-line god object mixing UI, business logic, and infrastructure concerns.

## Target Architecture

### 1. UIManager (desktop/ui_manager.py)
**Responsibilities:**
- CustomTkinter UI creation and event handling
- Progress bar updates and status displays
- Theme switching and appearance management
- Component state synchronization

**Extracted Methods:**
- `_build_header()` (lines 700-716)
- `_build_url_section()` (lines 717-729)
- `_build_info_section()` (lines 731-734)
- `_render_info()` (lines 873-905)
- `_update_progress()` (lines 1005-1070)
- `_toggle_theme()` (existing)

### 2. DownloadOrchestrator (desktop/download_orchestrator.py)
**Responsibilities:**
- Download workflow coordination
- Task lifecycle management
- Progress callback handling
- Error recovery and retry logic

**Extracted Methods:**
- `_start_download()` (lines 930-949)
- `_start_analysis()` (lines 847-852)
- `_analyze_thread()` (lines 854-859)
- `_on_analysis_ok()` (lines 861-866)
- `_on_analysis_err()` (lines 868-871)

### 3. HistoryManager (desktop/history_manager.py)
**Responsibilities:**
- Download history persistence
- History item state management
- History card lifecycle

**Extracted Methods:**
- `_add_history_card()` (lines 1076-1083)
- `_history_pause/resume/cancel/retry/delete()` (lines 1085-1099)
- `save_history()` integration

### 4. ConfigManager (desktop/config_manager.py)
**Responsibilities:**
- Configuration loading and validation
- Settings persistence
- Environment variable handling

**Extracted Methods:**
- `load_config()` (lines 368-375)
- `save_config()` (lines 377-382)
- Settings UI integration

### 5. UpdateManager (desktop/update_manager.py) - Enhance Existing
**Responsibilities:**
- Update checking and downloading
- Installation coordination
- Version management

**Extracted Methods:**
- `_check_updates()` (lines 1154-1173)
- `_manual_check_updates()` (existing)
- Update UI integration

## Implementation Strategy

### Phase 1: Extract Managers (Low Risk)
1. Create manager classes with extracted methods
2. Use dependency injection in MediaGrabApp
3. Maintain existing public API
4. Add comprehensive unit tests

### Phase 2: UI Separation (Medium Risk)
1. Extract UIManager with all UI logic
2. Implement observer pattern for state changes
3. Test UI interactions independently

### Phase 3: Integration Testing (High Risk)
1. End-to-end workflow testing
2. Performance regression testing
3. User experience validation

## Dependency Injection Design
```python
class MediaGrabApp(ctk.CTk):
    def __init__(self):
        self.ui_manager = UIManager(self)
        self.download_orchestrator = DownloadOrchestrator(self)
        self.history_manager = HistoryManager(self)
        self.config_manager = ConfigManager()
        self.update_manager = UpdateManager(self)
```

## Backward Compatibility
- Maintain all existing public methods
- Preserve keyboard shortcuts and UI behavior
- Keep configuration file format unchanged
- Ensure seamless upgrade path for users
