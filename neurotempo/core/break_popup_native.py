import sys

# Keep references alive so PyObjC targets don't get garbage-collected
_KEEPALIVE = []

# Define the ObjC class ONCE (not inside the function), macOS only
if sys.platform == "darwin":
    import objc
    from Cocoa import NSObject

    try:
        # If module reloads, the class may already exist
        NTBreakCloseTarget = objc.lookUpClass("NTBreakCloseTarget")
    except Exception:
        class NTBreakCloseTarget(NSObject):
            # selector: initWithPanel:app:prevPolicy:
            def initWithPanel_app_prevPolicy_(self, panel, app, prev_policy):
                self = objc.super(NTBreakCloseTarget, self).init()
                if self is None:
                    return None
                self._panel = panel
                self._app = app
                self._prev_policy = prev_policy
                return self

            # selector: close:
            def close_(self, sender):
                global _KEEPALIVE
                try:
                    if getattr(self, "_panel", None) is not None:
                        self._panel.orderOut_(None)
                finally:
                    # Restore activation policy
                    try:
                        if getattr(self, "_app", None) is not None and getattr(self, "_prev_policy", None) is not None:
                            self._app.setActivationPolicy_(self._prev_policy)
                    except Exception:
                        pass

                    # Remove keepalive entry for this panel
                    try:
                        panel = getattr(self, "_panel", None)
                        if panel is not None:
                            _KEEPALIVE = [x for x in _KEEPALIVE if x[0] is not panel]
                    except Exception:
                        pass


def show_break_popup_center(title: str, message: str):
    if sys.platform != "darwin":
        raise RuntimeError("Native popup only supported on macOS")

    from AppKit import (
        NSScreen,
        NSApplication,
        NSApplicationActivationPolicyAccessory,
        NSStatusWindowLevel,
        NSWindowCollectionBehaviorMoveToActiveSpace,
        NSWindowCollectionBehaviorFullScreenAuxiliary,
    )
    from Cocoa import (
        NSPanel,
        NSMakeRect,
        NSTextField,
        NSButton,
        NSWindowStyleMaskNonactivatingPanel,
        NSWindowStyleMaskBorderless,
        NSColor,
        NSFont,
        NSBackingStoreBuffered,
        NSRoundedBezelStyle,
    )

    # Put app into "Accessory" mode so it doesn't steal focus
    app = NSApplication.sharedApplication()
    prev_policy = None
    try:
        prev_policy = app.activationPolicy()
        app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    except Exception:
        prev_policy = None

    # Center on visible frame
    w, h = 420, 180
    screen = NSScreen.mainScreen()
    frame = screen.visibleFrame()
    x = frame.origin.x + (frame.size.width - w) / 2
    y = frame.origin.y + (frame.size.height - h) / 2

    style = NSWindowStyleMaskNonactivatingPanel | NSWindowStyleMaskBorderless
    panel = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
        NSMakeRect(x, y, w, h),
        style,
        NSBackingStoreBuffered,
        False
    )

    # Show on active Space + over full-screen apps
    panel.setLevel_(NSStatusWindowLevel)
    panel.setCollectionBehavior_(
        NSWindowCollectionBehaviorMoveToActiveSpace |
        NSWindowCollectionBehaviorFullScreenAuxiliary
    )

    panel.setOpaque_(False)
    panel.setBackgroundColor_(NSColor.clearColor())
    panel.setHasShadow_(True)
    panel.setHidesOnDeactivate_(False)

    content = panel.contentView()

    # Card background
    bg = NSTextField.alloc().initWithFrame_(NSMakeRect(0, 0, w, h))
    bg.setBezeled_(False)
    bg.setDrawsBackground_(True)
    bg.setBackgroundColor_(NSColor.colorWithCalibratedWhite_alpha_(0.06, 0.98))
    bg.setEditable_(False)
    bg.setSelectable_(False)
    bg.setStringValue_("")
    content.addSubview_(bg)

    # Title
    t = NSTextField.alloc().initWithFrame_(NSMakeRect(22, h - 55, w - 44, 26))
    t.setBezeled_(False)
    t.setDrawsBackground_(False)
    t.setEditable_(False)
    t.setSelectable_(False)
    t.setTextColor_(NSColor.whiteColor())
    t.setFont_(NSFont.boldSystemFontOfSize_(18))
    t.setStringValue_(title)
    content.addSubview_(t)

    # Message
    m = NSTextField.alloc().initWithFrame_(NSMakeRect(22, 58, w - 44, 70))
    m.setBezeled_(False)
    m.setDrawsBackground_(False)
    m.setEditable_(False)
    m.setSelectable_(False)
    m.setTextColor_(NSColor.colorWithCalibratedWhite_alpha_(0.92, 0.85))
    m.setFont_(NSFont.systemFontOfSize_(13))
    m.setStringValue_(message)
    m.setUsesSingleLineMode_(False)
    content.addSubview_(m)

    # Button
    btn = NSButton.alloc().initWithFrame_(NSMakeRect(w - 110, 18, 88, 30))
    btn.setTitle_("Got it")
    btn.setBezelStyle_(NSRoundedBezelStyle)

    target = NTBreakCloseTarget.alloc().initWithPanel_app_prevPolicy_(panel, app, prev_policy)
    btn.setTarget_(target)
    btn.setAction_("close:")
    content.addSubview_(btn)

    # Show without activating (PyObjC name differs by version)
    if hasattr(panel, "orderFrontRegardless"):
        panel.orderFrontRegardless()
    else:
        panel.orderFront_(None)

    # Keep references alive (don't attach attributes to NSPanel)
    _KEEPALIVE.append((panel, target, prev_policy))

    return panel