# Lion's Roar Studio Notification Duplication Fix

## Issue
When entering the application, you receive 4 notifications:
1. "Server is working" 
2. "AI server offline"
3. "Server is working" (duplicate)
4. "AI server offline" (duplicate)

## Root Cause
The frontend is making duplicate health check requests, likely due to:
- React Strict Mode (renders components twice in development)
- Multiple useEffect hooks checking health
- Duplicate health check endpoints being called

## Backend Changes Made ✅
Added to `/health` endpoint response:
- `timestamp`: Unix timestamp to help deduplicate
- `server_type`: "ai-backend" identifier
- `Cache-Control` header: Prevents rapid duplicate requests (5 second cache)

## Lion's Roar Studio Fixes Needed

### Option 1: Deduplicate Notifications (Recommended)
Add notification deduplication logic in the frontend:

```typescript
// Store recent notifications to prevent duplicates
const recentNotifications = new Set<string>();

function showNotification(message: string, type: 'success' | 'error') {
  const key = `${type}-${message}`;
  
  // Skip if shown in last 5 seconds
  if (recentNotifications.has(key)) {
    return;
  }
  
  recentNotifications.add(key);
  
  // Show notification
  toast[type](message);
  
  // Clear after 5 seconds
  setTimeout(() => {
    recentNotifications.delete(key);
  }, 5000);
}
```

### Option 2: Fix React Strict Mode
Remove duplicate renders in development:

```tsx
// In your health check useEffect
useEffect(() => {
  const abortController = new AbortController();
  
  const checkHealth = async () => {
    try {
      const response = await fetch('/health', {
        signal: abortController.signal
      });
      
      if (response.ok) {
        showNotification('Server is working', 'success');
      }
    } catch (error) {
      if (error.name !== 'AbortError') {
        showNotification('AI server offline', 'error');
      }
    }
  };
  
  checkHealth();
  
  return () => {
    abortController.abort(); // Cancel on unmount
  };
}, []); // Empty deps to run only once
```

### Option 3: Use Timestamp to Deduplicate
Use the backend timestamp to prevent showing notifications for same health check:

```typescript
let lastHealthCheckTimestamp = 0;

async function checkHealth() {
  const response = await fetch('/health');
  const data = await response.json();
  
  // Only show notification if this is a new health check
  if (data.timestamp > lastHealthCheckTimestamp) {
    lastHealthCheckTimestamp = data.timestamp;
    showNotification('Server is working', 'success');
  }
}
```

### Option 4: Consolidate Health Checks
Ensure you're only calling health check once:

```typescript
// Create a single health check context/hook
export const useHealthCheck = () => {
  const [isHealthy, setIsHealthy] = useState<boolean | null>(null);
  
  useEffect(() => {
    let isMounted = true;
    
    const checkHealth = async () => {
      try {
        const response = await fetch('/health');
        const data = await response.json();
        
        if (isMounted) {
          setIsHealthy(data.status === 'healthy');
        }
      } catch {
        if (isMounted) {
          setIsHealthy(false);
        }
      }
    };
    
    checkHealth();
    
    return () => {
      isMounted = false;
    };
  }, []);
  
  return isHealthy;
};
```

Then use it once in your App component:

```tsx
function App() {
  const isHealthy = useHealthCheck();
  
  useEffect(() => {
    if (isHealthy === true) {
      toast.success('Server is working');
    } else if (isHealthy === false) {
      toast.error('AI server offline');
    }
  }, [isHealthy]);
  
  // Rest of your app...
}
```

## Recommended Solution
Implement **Option 1 (Deduplication)** + **Option 2 (Abort Controller)** together:

1. Add notification deduplication globally
2. Use AbortController in useEffect hooks
3. Ensure only one health check hook is active

## Testing
After implementing fixes:
1. Refresh the page
2. You should see only 1 "Server is working" notification
3. Check browser DevTools Network tab - should see max 1 `/health` request
4. Check React DevTools - ensure effects run once (or twice in Strict Mode, but aborted)

## Backend Endpoints Available
- `GET /health` - Main health check (now with caching)
- `GET /health/health` - Duplicate path handler
- `GET /health/status` - Alternative health endpoint
- `GET /status` - General status endpoint

Consider using only `/health` endpoint and removing others in frontend.
