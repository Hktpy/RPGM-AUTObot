from typing import Optional
try:
    from AppKit import NSRunningApplication, NSApplicationActivateIgnoringOtherApps
    HAVE_APPKIT = True
except Exception:
    HAVE_APPKIT = False

def activate_pid(pid: int) -> bool:
    if not HAVE_APPKIT or not pid:
        return False
    app = NSRunningApplication.runningApplicationWithProcessIdentifier_(pid)
    if app is None:
        return False
    app.activateWithOptions_(NSApplicationActivateIgnoringOtherApps)
    return True
