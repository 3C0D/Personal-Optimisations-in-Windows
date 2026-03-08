; helpers.ahk - Common utility functions for browser shortcuts
; Include in other scripts with #Include helpers.ahk
; No hotkeys - just helper functions

#Requires AutoHotkey v2.0

; ============================================
; CLIPBOARD OPERATIONS
; ============================================

; Helper function for clipboard operations
; Returns object with {text: string, isFromClipboard: boolean}
getSelectedOrClipboardText() {
    OldClipboard := A_Clipboard
    A_Clipboard := ""
    Send "^c" ; Copy the selected text
    if !ClipWait(0.5) {
        ; If no selection, restore the clipboard and use it
        if (OldClipboard != "") {
            A_Clipboard := OldClipboard
            return {text: OldClipboard, isFromClipboard: true}
        } else {
            return {text: "", isFromClipboard: false}
        }
    } else {
        ; Use the selected text
        text := A_Clipboard
        A_Clipboard := OldClipboard
        return {text: text, isFromClipboard: false}
    }
}

; ============================================
; URL OPERATIONS
; ============================================

; Function to encode the URL
UrlEncode(str) {
    static chars := "0123456789ABCDEF"
    encodedStr := ""
    for i, char in StrSplit(str) {
        if char ~= "[a-zA-Z0-9-_.~]"
            encodedStr .= char
        else {
            code := Ord(char)
            encodedStr .= "%" . SubStr(chars, (code >> 4) + 1, 1) . SubStr(chars, (code & 15) + 1, 1)
        }
    }
    return encodedStr
}
