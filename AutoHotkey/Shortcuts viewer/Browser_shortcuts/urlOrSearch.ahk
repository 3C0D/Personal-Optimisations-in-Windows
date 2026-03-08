; urlOrSearch.ahk - Open URL or search selected text/clipboard
; Standalone script or include in other scripts with #Include urlOrSearch.ahk
; Hotkey: Win+Shift+U

#Requires AutoHotkey v2.0

; Include helper functions
#Include helpers.ahk

; Hotkey definition (comment out if including in another script)
#+u:: openUrlOrSearch()

; Universal URL/Search handler
openUrlOrSearch() {
    result := getSelectedOrClipboardText()
    if (result.text != "") {
        ; If it looks like a URL, open directly, otherwise search
        if RegExMatch(result.text, "^(https?://|www\.)")
            Run(result.text)
        else
            Run("https://www.google.com/search?q=" . UrlEncode(result.text))
    }
}
