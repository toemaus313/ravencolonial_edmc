# Logging Conversion Guide

## Pattern
Replace `print(f"[RAVENCOLONIAL DEBUG] message")` with appropriate logger calls:

### DEBUG Level (Verbose diagnostic info)
- Journal parsing details
- API URL construction  
- State checks and transitions
- Button state changes
- Response bodies

### INFO Level (Important events)
- Cargo contributions submitted
- Project updates completed
- Docked at station
- Created projects

### WARNING Level  
- Missing data but continuing
- Deprecated features

### ERROR Level
- API failures
- Exceptions
- Invalid state

## Examples

**Before:**
```python
print(f"[RAVENCOLONIAL DEBUG] Contribution URL: {url}")
```

**After:**
```python
logger.debug(f"Contribution URL: {url}")
```

**Before:**
```python
print(f"[RAVENCOLONIAL DEBUG] Contributed cargo to project {build_id}: {cargo_diff}")
```

**After:**
```python
logger.info(f"Contributed cargo to project {build_id}: {cargo_diff}")
```
