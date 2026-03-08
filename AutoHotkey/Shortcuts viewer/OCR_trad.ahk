; Script AutoHotkey pour capture d'écran et traduction via un chat IA
#Requires AutoHotkey v2.0
#SingleInstance Force

; Configuration file
configFile := A_ScriptDir "\ocr_config.json"

; Load saved service or use default
LoadOCRService() {
    global configFile
    if FileExist(configFile) {
        try {
            configText := FileRead(configFile, "UTF-8")
            config := Jxon_Load(&configText)
            return config.Has("service") ? config["service"] : "mistral"
        }
    }
    return "mistral"  ; Default
}

; Save service choice
SaveOCRService(service) {
    global configFile
    config := Map()
    config["service"] := service
    configText := Jxon_Dump(config, 2)
    try {
        FileDelete(configFile)
    }
    FileAppend(configText, configFile, "UTF-8")
}

; Load service at startup
aiService := LoadOCRService()

; Menu to select OCR service (Win+Q)
#q::
{
    global aiService
    
    ocrMenu := Menu()
    ocrMenu.Add("Claude (incognito)", (*) => SelectOCRService("claude"))
    ocrMenu.Add("Mistral", (*) => SelectOCRService("mistral"))
    ocrMenu.Add("Gemini", (*) => SelectOCRService("gemini"))
    
    ; Mark current service
    switch aiService {
        case "claude": ocrMenu.Check("Claude (incognito)")
        case "mistral": ocrMenu.Check("Mistral")
        case "gemini": ocrMenu.Check("Gemini")
    }
    
    ocrMenu.Show()
}

; Function to select and save service
SelectOCRService(service) {
    global aiService
    aiService := service
    SaveOCRService(service)
    
    serviceName := ""
    switch service {
        case "claude": serviceName := "Claude"
        case "mistral": serviceName := "Mistral"
        case "gemini": serviceName := "Gemini"
    }
    
    ToolTip("OCR Service: " . serviceName)
    SetTimer(() => ToolTip(), -2000)
}

; Raccourci clavier: Shift + Win + Q
+#q::
{
    global aiService
    
    ; Prompt universel pour tous les services
    promptText := "Extract the text from this image. If the text is in French, just show the French text. Otherwise, show the original text first, then its French translation."
    
    ; Définir l'URL et les délais selon le service choisi
    switch aiService {
        case "claude":
            chatUrl := "https://claude.ai/new?incognito"
            waitTime := 5000  ; Claude en incognito prend plus de temps
        case "gemini":
            chatUrl := "https://gemini.google.com/app"
            waitTime := 3000
        case "mistral":
            chatUrl := "https://chat.mistral.ai/chat"
            waitTime := 3000
        default:
            chatUrl := "https://chat.mistral.ai/chat"  ; Par défaut: Mistral
            waitTime := 3000
    }
    
    try {
        ; Déclencher l'outil de capture Windows (Win+Shift+S)
        Send "#+s"
        
        ; Attendre que l'utilisateur fasse la capture
        Sleep 500
        KeyWait "LButton", "D"
        KeyWait "LButton"
        Sleep 1000
        
        ; Ouvrir le chat IA
        Run chatUrl
        Sleep waitTime  ; Délai adapté au service
        
        ; Envoyer le prompt d'abord, puis l'image
        Send promptText
        Sleep 200  ; Petit délai minimal
        Send "^v"  ; Coller l'image après le texte
        Sleep 2500  ; Attendre que l'image soit collée
        Send "{Enter}"
        
    } catch Error as e {
        MsgBox "Erreur: " e.Message, "OCR Traduction", "IconX"
    }
}