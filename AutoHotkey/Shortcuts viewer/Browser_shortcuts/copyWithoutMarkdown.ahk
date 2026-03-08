; copyWithoutMarkdown.ahk - Strip Markdown formatting from selected text or clipboard
; Standalone script or include in other scripts with #Include copyWithoutMarkdown.ahk
; Hotkey: Ctrl+Shift+C

#Requires AutoHotkey v2.0

; Include helper functions
#Include helpers.ahk

; Hotkey definition (comment out if including in another script)
^+c:: copyWithoutMarkdown()

; Function to strip Markdown formatting
stripMarkdown(text) {
    s := text
    
    ; Obsidian-specific
    s := RegExReplace(s, "m)^>\s*\[![\w-]+\].*$", "")
    s := RegExReplace(s, "!\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", "")
    s := RegExReplace(s, "\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", "$2$1")
    s := RegExReplace(s, "m)\s+\^[A-Za-z0-9-]+\s*$", "")
    
    ; Code blocks
    s := RegExReplace(s, "s)(``{3,5})[\w]*\n([\s\S]*?)\1", "$2")
    
    ; Headings
    s := RegExReplace(s, "m)^#{1,6}\s+", "")
    
    ; Bold & underline
    s := RegExReplace(s, "\*\*(.+?)\*\*", "$1")
    s := RegExReplace(s, "__(.+?)__", "$1")
    
    ; Italic
    s := RegExReplace(s, "\*(.+?)\*", "$1")
    s := RegExReplace(s, "_(.+?)_", "$1")
    
    ; Inline code
    s := RegExReplace(s, "``([^``\r\n]+)``", "$1")
    
    ; Blockquotes
    s := RegExReplace(s, "m)^>\s+", "")
    
    ; Horizontal rules
    s := RegExReplace(s, "m)^[\-\*_]{3,}\s*$", "")
    
    ; Tables
    s := RegExReplace(s, "m)^\|?[\s\-:|]+\|?\s*$", "")
    s := RegExReplace(s, "m)^\|\s*", "")
    s := RegExReplace(s, "m)\s*\|$", "")
    s := RegExReplace(s, "\s*\|\s*", " ")
    
    ; Images
    s := RegExReplace(s, "!\[([^\]]*)\]\([^)]+\)", "$1")
    
    ; Links
    s := RegExReplace(s, "\[([^\]]+)\]\([^)]+\)", "$1")
    
    ; Collapse blank lines
    s := RegExReplace(s, "\r\n?", "`n")
    s := RegExReplace(s, "`n{3,}", "`n`n")
    
    return Trim(s)
}

; Copy without Markdown formatting
copyWithoutMarkdown() {
    result := getSelectedOrClipboardText()
    
    if (result.text != "" && Trim(result.text) != "") {
        plainText := stripMarkdown(result.text)
        A_Clipboard := plainText
        
        if (result.isFromClipboard)
            showPopup("✓ Clipboard converted")
        else
            showPopup("✓ Copied without Markdown")
    }
}

; Show confirmation popup
showPopup(message) {
    CoordMode "Mouse", "Screen"
    MouseGetPos &mouseX, &mouseY
    
    popup := Gui("+AlwaysOnTop -Caption +ToolWindow")
    popup.BackColor := "2D2D30"
    popup.SetFont("s10 cWhite", "Segoe UI")
    popup.AddText("x10 y8 w200 Center", message)
    
    popupX := mouseX - 100
    popupY := mouseY - 60
    if (popupY < 0)
        popupY := mouseY + 20
    if (popupX < 0)
        popupX := 0
    
    popup.Show("x" . popupX . " y" . popupY . " w220 h35 NoActivate")
    SetTimer(() => popup.Destroy(), -1500)
}
