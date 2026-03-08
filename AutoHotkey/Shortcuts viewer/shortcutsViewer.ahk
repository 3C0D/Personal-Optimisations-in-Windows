#Requires AutoHotkey v2.0
; AutoHotkey v2 Script - Shortcuts Viewer with Sleep Control
;https://github.com/TheArkive/JXON_ahk2
#Include JXON.ahk
#Include Browser_shortcuts/browserShortcuts.ahk
#Include OCR_trad.ahk

; Global variables for sleep control
sleepDisabled := false

; Chemin vers le fichier JSON
filePath := A_ScriptDir "\shortcuts.json"
exampleFilePath := A_ScriptDir "\shortcuts.example.json"

; Initialize shortcuts file if it doesn't exist
if !FileExist(filePath) {
    if FileExist(exampleFilePath) {
        ; Copy example file to shortcuts.json
        FileCopy(exampleFilePath, filePath)
    } else {
        ; Create default file if example doesn't exist
        FileAppend('{"General": "## Welcome to Shortcuts Viewer!\n\nAdd your shortcuts here."}', filePath, "UTF-8")
    }
}

; Raccourci pour ouvrir l'interface (Win+Shift+/)
#+/:: ShowShortcutsGUI()

; Sleep control shortcut (Shift+Win+V)
+#v:: ToggleSleepMode()

; Inclure les raccourcis personnels

; Generate built-in shortcuts section
GetBuiltInShortcuts() {
    shortcuts := ""
    shortcuts .= "## Shortcuts Viewer`n"
    shortcuts .= "Win+Shift+/     : Open this shortcuts viewer`n"
    shortcuts .= "Shift+Win+V     : Toggle sleep mode (prevent/allow PC sleep)`n`n"
    shortcuts .= "## Browser Shortcuts`n"
    shortcuts .= "Win+Shift+I     : AI Services Menu (Claude, ChatGPT, Gemini, etc.)`n"
    shortcuts .= "Win+Shift+U     : Open URL or search selected text/clipboard`n"
    shortcuts .= "Win+Shift+T     : Translate text via Google`n"
    shortcuts .= "Ctrl+Shift+C    : Copy without Markdown formatting`n`n"
    shortcuts .= "## OCR Translation`n"
    shortcuts .= "Win+Q           : Select OCR service (Claude/Mistral/Gemini)`n"
    shortcuts .= "Shift+Win+Q     : Screen capture and translate with AI`n"
    return shortcuts
}

ShowShortcutsGUI() {
    global filePath

    if !FileExist(filePath)
        FileAppend('{"General": ""}', filePath, "UTF-8")

    jsonText := FileRead(filePath, "UTF-8")
    data := jxon_load(&jsonText)

    ; Get user's personal shortcuts
    userText := data.Has("General") ? data["General"] : ""

    ShortcutsGUI := Gui()
    ShortcutsGUI.Opt("+AlwaysOnTop")
    ShortcutsGUI.BackColor := "1A1A1A"
    ShortcutsGUI.Title := "Shortcut Viewer 1.0"

    ShortcutsGUI.SetFont("s14 c916c35", "Segoe UI")
    ShortcutsGUI.Add("Text", "w600", "Application Shortcuts (auto-generated)")

    ; Built-in shortcuts (read-only)
    ShortcutsGUI.SetFont("s12 cC0C0C0", "Consolas")
    builtInEdit := ShortcutsGUI.Add("Edit", "r10 w590 +ReadOnly", GetBuiltInShortcuts())
    builtInEdit.Opt("+Background1A1A1A")

    ; Separator
    ShortcutsGUI.SetFont("s14 c916c35", "Segoe UI")
    ShortcutsGUI.Add("Text", "w600", "My Shortcuts (editable)")

    ; User shortcuts (editable)
    ShortcutsGUI.SetFont("s12 cC0C0C0", "Consolas")
    userEdit := ShortcutsGUI.Add("Edit", "r20 w590 vShortcutsEdit", userText)
    userEdit.Opt("+Background2A2A2A")

    ShortcutsGUI.SetFont("s10 cC0C0C0", "Segoe UI")
    closeButton := ShortcutsGUI.Add("Button", "w100", "Fermer")
    closeButton.OnEvent("Click", (*) => SaveAndClose(ShortcutsGUI))

    ShortcutsGUI.OnEvent("Close", (*) => SaveAndClose(ShortcutsGUI))
    ShortcutsGUI.OnEvent("Escape", (*) => SaveAndClose(ShortcutsGUI))

    ShortcutsGUI.Show()
    userEdit.Focus()
}

SaveAndClose(ShortcutsGUI) {
    global filePath
    newContent := ShortcutsGUI["ShortcutsEdit"].Value

    data := Map()
    data["General"] := newContent

    jsonText := jxon_dump(data, 2)

    try {
        file := FileOpen(filePath, "w", "UTF-8")
        if !IsObject(file) {
            Error("Erreur lors de l'ouverture du fichier pour l'écriture.")
        }
        file.Write(jsonText)
        file.Close()
    } catch as err {
        MsgBox("Erreur lors de l'enregistrement du fichier : " . err.Message)
    }
    ShortcutsGUI.Destroy()
}

; Sleep control function
ToggleSleepMode() {
    global sleepDisabled

    if (!sleepDisabled) {
        ; Disable sleep mode
        DllCall("kernel32.dll\SetThreadExecutionState", "UInt", 0x80000003) ; ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
        sleepDisabled := true
        ShowMessage("Mode veille DÉSACTIVÉ", "Votre PC ne rentrera pas en mode veille")
    } else {
        ; Re-enable sleep mode
        DllCall("kernel32.dll\SetThreadExecutionState", "UInt", 0x80000000) ; ES_CONTINUOUS only to reset
        sleepDisabled := false
        ShowMessage("Mode veille ACTIVÉ", "Votre PC peut maintenant rentrer en mode veille normalement")
    }
}

; Function to show status message
global msgGui := 0

ShowMessage(title, message) {
    global msgGui
    if msgGui {
        msgGui.Destroy()
    }
    msgGui := Gui()
    msgGui.Opt("+AlwaysOnTop +Owner +Border")
    msgGui.Title := title
    msgGui.SetFont("s13 bold", "Segoe UI")
    msgGui.MarginX := 30
    msgGui.MarginY := 20
    msgGui.BackColor := "F8F8F8"
    msgGui.Add("Text", "w380 r3 Center", message)
    btn := msgGui.Add("Button", "w120 h35 Center", "OK")
    btn.SetFont("s12 bold", "Segoe UI")
    btn.OnEvent("Click", (*) => (msgGui.Destroy(), msgGui := 0))
    msgGui.OnEvent("Escape", (*) => (msgGui.Destroy(), msgGui := 0))
    msgGui.Show("w420 h150")
    btn.Focus()
    ; Fermeture automatique après 4 secondes
    SetTimer((*) => (msgGui ? (msgGui.Destroy(), msgGui := 0) : msgGui := 0), -4000)
}

; Clean exit function to restore normal sleep settings
OnExit(ExitFunc)

ExitFunc(ExitReason, ExitCode) {
    global sleepDisabled
    ; Ensure normal settings are restored before exit
    if (sleepDisabled) {
        DllCall("kernel32.dll\SetThreadExecutionState", "UInt", 0x80000000)
    }
}
