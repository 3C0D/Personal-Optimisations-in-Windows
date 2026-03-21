; Unpin_window.ahk - Toggle always-on-top with a persistent 📌 indicator
; À inclure dans le script principal avec #Include Unpin_window.ahk

#Requires AutoHotkey v2.0

; ── Calibration offsets (adjust if pin appears misplaced) ────────────────────
PIN_OFFSET_X := -118   ; from right edge of window (negative = move left)
PIN_OFFSET_Y := 4     ; from top edge of window

; Map of pinned windows: hwnd (Integer) → Gui
global pinnedWindows := Map()

; Track positions every 150ms
SetTimer(UpdatePinPositions, 150)

; ── Shortcut ─────────────────────────────────────────────────────────────────
^#t::
{
    ToggleWindowPin()
}

; ── Core toggle ──────────────────────────────────────────────────────────────
ToggleWindowPin()
{
    global pinnedWindows
    hwnd := WinGetID("A")

    exStyle := WinGetExStyle("ahk_id " hwnd)
    isTopmost := (exStyle & 0x8)  ; WS_EX_TOPMOST

    if (isTopmost) {
        DllCall("SetWindowPos"
            , "Ptr", hwnd, "Ptr", -2
            , "Int", 0, "Int", 0, "Int", 0, "Int", 0
            , "UInt", 0x0003)
        if pinnedWindows.Has(hwnd)
            RemovePinGui(hwnd)      ; pinned by us → the pin disappearing is enough
        else
            ShowUnpinNotif()        ; topmost set externally → show notification
    } else {
        DllCall("SetWindowPos"
            , "Ptr", hwnd, "Ptr", -1   ; HWND_TOPMOST
            , "Int", 0, "Int", 0, "Int", 0, "Int", 0
            , "UInt", 0x0003)
        CreatePinGui(hwnd)
    }
}

; ── Pin GUI ───────────────────────────────────────────────────────────────────
CreatePinGui(hwnd)
{
    global pinnedWindows

    if pinnedWindows.Has(hwnd)
        RemovePinGui(hwnd)

    pinGui := Gui("+AlwaysOnTop -Caption +ToolWindow +LastFound")
    ; Click-through so the pin doesn't intercept mouse events
    WinSetExStyle("+0x20")

    pinGui.BackColor := "1a1a1a"
    pinGui.MarginX := 2
    pinGui.MarginY := 1

    txt := pinGui.AddText("Center w22 h22 cFF4444", "📌")
    txt.SetFont("s11 Bold", "Segoe UI")

    pos := GetPinPos(hwnd)
    pinGui.Show("x" pos.x " y" pos.y " w26 h24 NoActivate")

    ; Semi-transparent overall (0=transparent, 255=opaque)
    WinSetTransparent(210, pinGui)

    pinnedWindows[hwnd] := pinGui
}

RemovePinGui(hwnd)
{
    global pinnedWindows
    if pinnedWindows.Has(hwnd) {
        pinnedWindows[hwnd].Destroy()
        pinnedWindows.Delete(hwnd)
    }
}

; ── Position helper ───────────────────────────────────────────────────────────
GetPinPos(hwnd)
{
    global PIN_OFFSET_X, PIN_OFFSET_Y
    WinGetPos(&wx, &wy, &ww, , "ahk_id " hwnd)
    scale := A_ScreenDPI / 96
    posY := Max(wy / scale, 0) + PIN_OFFSET_Y
    return { x: (wx + ww) / scale + PIN_OFFSET_X, y: posY }
}

; ── Position tracking timer ───────────────────────────────────────────────────
UpdatePinPositions()
{
    global pinnedWindows
    toRemove := []

    for hwnd, pinGui in pinnedWindows {
        if !WinExist("ahk_id " hwnd) {
            toRemove.Push(hwnd)
            continue
        }
        exStyle := WinGetExStyle("ahk_id " hwnd)
        if !(exStyle & 0x8) {   ; topmost removed externally
            toRemove.Push(hwnd)
            continue
        }
        pos := GetPinPos(hwnd)
        pinGui.Move(pos.x, pos.y)
        ; Re-assert pin z-order above the pinned window
        DllCall("SetWindowPos"
            , "Ptr", pinGui.Hwnd, "Ptr", -1   ; HWND_TOPMOST
            , "Int", 0, "Int", 0, "Int", 0, "Int", 0
            , "UInt", 0x0003)                  ; SWP_NOMOVE | SWP_NOSIZE
    }

    for hwnd in toRemove
        RemovePinGui(hwnd)
}

ShowUnpinNotif()
{
    n := Gui("+AlwaysOnTop -Caption +ToolWindow")
    n.BackColor := "1a1a1a"
    n.MarginX := 4
    n.MarginY := 8
    txt := n.AddText("c90EE90 Center w180 h24", "📌  Most Top off")
    txt.SetFont("s11 Bold", "Segoe UI")
    n.Show("x" (A_ScreenWidth - 240) " y20 NoActivate")
    WinSetTransparent(220, n)
    SetTimer(() => n.Destroy(), -2500)
}
