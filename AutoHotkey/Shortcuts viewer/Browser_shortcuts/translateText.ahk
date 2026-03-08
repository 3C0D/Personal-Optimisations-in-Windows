; translateText.ahk - Translate selected text/clipboard using Google
; Standalone script or include in other scripts with #Include translateText.ahk
; Hotkey: Win+Shift+T

#Requires AutoHotkey v2.0

; Include helper functions
#Include helpers.ahk

; Hotkey definition (comment out if including in another script)
#+t:: translateText()

; Function to translate selected text using Google Search + "trad"
translateText() {
    result := getSelectedOrClipboardText()
    if (result.text != "") {
        ; Encode the text for the URL
        EncodedText := UrlEncode(result.text)
        
        ; Construct the Google Search URL with " trad" appended
        TranslateUrl := "https://www.google.com/search?q=" . EncodedText . "+trad"
        ; Open the URL in the default browser
        Run TranslateUrl
    }
}
